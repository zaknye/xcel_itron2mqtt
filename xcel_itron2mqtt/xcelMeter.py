import os
import ssl
import yaml
import json
import requests
import logging
import paho.mqtt.client as mqtt
import xml.etree.ElementTree as ET
from time import sleep
from typing import Tuple
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
from requests.adapters import HTTPAdapter
from tenacity import retry, stop_after_attempt, before_sleep_log, wait_exponential

# Local imports
from xcelEndpoint import xcelEndpoint

IEEE_PREFIX = '{urn:ieee:std:2030.5:ns}'
# Our target cipher is: ECDHE-ECDSA-AES128-CCM8
# Security level 0 is required to allow CCM8 ciphers in OpenSSL 3.x
CIPHERS = 'ECDHE-ECDSA-AES128-CCM8:@SECLEVEL=0'

logger = logging.getLogger(__name__)

# Enable verbose SSL/TLS debugging
# Uncomment these lines to see detailed SSL handshake information
# logging.getLogger('urllib3').setLevel(logging.DEBUG)
# import http.client
# http.client.HTTPConnection.debuglevel = 1

# Create an adapter for our request to enable the non-standard cipher
# From https://lukasa.co.uk/2017/02/Configuring_TLS_With_Requests/
class CCM8Adapter(HTTPAdapter):
    """
    A TransportAdapter that re-enables ECDHE support in Requests.
    Not really sure how much redundancy is actually required here
    """
    def __init__(self, cert_file=None, key_file=None, *args, **kwargs):
        self.cert_file = cert_file
        self.key_file = key_file
        super(CCM8Adapter, self).__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.create_ssl_context()
        return super(CCM8Adapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs['ssl_context'] = self.create_ssl_context()
        return super(CCM8Adapter, self).proxy_manager_for(*args, **kwargs)

    def create_ssl_context(self):
        # Create SSL context with TLSv1.2
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

        # Disable hostname checking and set verify mode
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # Changed from CERT_REQUIRED since we're using verify=False anyway

        # Set the specific cipher WITH @SECLEVEL=0
        # The @SECLEVEL=0 is critical - it sets the OpenSSL security level to 0,
        # which is required to allow CCM8 ciphers in OpenSSL 3.x
        context.set_ciphers(CIPHERS)
        logger.debug(f"Set ciphers with security level 0 (current security_level: {context.security_level})")

        # Load client certificate if provided
        if self.cert_file and self.key_file:
            try:
                context.load_cert_chain(self.cert_file, self.key_file)
                logger.debug(f"Loaded client certificate: {self.cert_file}")
            except Exception as e:
                logger.error(f"Failed to load client certificate: {e}")
        else:
            logger.warning(f"No client certificate provided to SSL context")

        # Enable legacy renegotiation for devices that don't support RFC 5746
        # Required for Itron meters with OpenSSL 3.x
        context.options |= ssl.OP_LEGACY_SERVER_CONNECT

        # Disable various modern TLS features that might cause issues
        context.options |= ssl.OP_NO_COMPRESSION
        if hasattr(ssl, 'OP_NO_TLSv1_3'):
            context.options |= ssl.OP_NO_TLSv1_3  # Disable TLS 1.3

        # Debug logging to verify SSL context configuration
        logger.debug(f"SSL Context created with:")
        logger.debug(f"  Protocol: TLSv1.2")
        logger.debug(f"  Ciphers: ECDHE-ECDSA-AES128-CCM8")
        logger.debug(f"  Legacy renegotiation: enabled (OP_LEGACY_SERVER_CONNECT)")
        logger.debug(f"  Verify mode: {context.verify_mode}")
        logger.debug(f"  Check hostname: {context.check_hostname}")
        logger.debug(f"  Options: {hex(context.options)}")

        return context

class xcelMeter():

    def __init__(self, name: str, ip_address: str, port: int, creds: Tuple[str, str]):
        self.name = name
        self.POLLING_RATE = 5.0
        # Base URL used to query the meter
        self.url = f'https://{ip_address}:{port}'

        # Setup the MQTT server connection
        self.mqtt_server_address = os.getenv('MQTT_SERVER')
        self.mqtt_port = self.get_mqtt_port()
        self.mqtt_client = self.setup_mqtt(self.mqtt_server_address, self.mqtt_port)

        # Create a new requests session based on the passed in ip address and port #
        self.requests_session = self.setup_session(creds, ip_address)

        # Set to uninitialized
        self.initalized = False

    @retry(stop=stop_after_attempt(15),
           wait=wait_exponential(multiplier=1, min=1, max=15),
           before_sleep=before_sleep_log(logger, logging.WARNING),
           reraise=True)
    def setup(self) -> None:
        # XML Entries we're looking for within the endpoint
        hw_info_names = ['lFDI', 'swVer', 'mfID']
        # Endpoint of the meter used for HW info
        hw_info_url = '/sdev/sdi'
        # Query the meter to get some more details about it
        details_dict = self.get_hardware_details(hw_info_url, hw_info_names)
        self._mfid = details_dict['mfID']
        self._lfdi = details_dict['lFDI']
        self._swVer = details_dict['swVer']

        # Device info used for home assistant MQTT discovery
        self.device_info = {
                            "device": {
                                "identifiers": [self._lfdi],
                                "name": self.name,
                                "model": self._mfid,
                                "sw_version": self._swVer
                                }
                            }
        # Send homeassistant a new device config for the meter
        self.send_mqtt_config()

        # The swVer will dictate which version of endpoints we use
        endpoints_file_ver = 'default' if str(self._swVer) != '3.2.39' else '3_2_39'
        # List to store our endpoint objects in
        self.endpoints_list = self.load_endpoints(f'configs/endpoints_{endpoints_file_ver}.yaml')

        # create endpoints from list
        self.endpoints = self.create_endpoints(self.endpoints_list, self.device_info)

        # ready to go
        self.initalized = True

    def get_hardware_details(self, hw_info_url: str, hw_names: list) -> dict:
        """
        Queries the meter hardware endpoint at the ip address passed
        to the class.

        Returns: dict, {<element name>: <meter response>}
        """
        query_url = f'{self.url}{hw_info_url}'
        logger.debug(f"Querying meter at: {query_url}")

        try:
            # query the hw specs endpoint
            x = self.requests_session.get(query_url, verify=False, timeout=4.0)
            logger.debug(f"Successfully received response from meter")
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL Error details:")
            logger.error(f"  Error: {e}")
            logger.error(f"  Cipher configured: {CIPHERS}")
            logger.error(f"  SSL module version: {ssl.OPENSSL_VERSION}")
            # Check if OP_LEGACY_SERVER_CONNECT is available
            if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
                logger.error(f"  OP_LEGACY_SERVER_CONNECT: available")
            else:
                logger.error(f"  OP_LEGACY_SERVER_CONNECT: NOT AVAILABLE - this may be the issue!")
            raise

        # Parse the response xml looking for the passed in element names
        root = ET.fromstring(x.text)
        hw_info_dict = {}
        for name in hw_names:
            hw_info_dict[name] = root.find(f'.//{IEEE_PREFIX}{name}').text

        return hw_info_dict

    @staticmethod
    def setup_session(creds: tuple, ip_address: str) -> requests.Session:
        """
        Creates a new requests session with the given credentials pointed
        at the give IP address. Will be shared across each xcelQuery object.

        Returns: request.session
        """
        session = requests.Session()
        session.cert = creds
        # Mount our adapter to the domain, passing the client cert/key
        # creds is a tuple of (cert_file, key_file)
        cert_file, key_file = creds
        session.mount(f'https://{ip_address}', CCM8Adapter(cert_file=cert_file, key_file=key_file))

        return session

    @staticmethod
    def load_endpoints(file_path: str) -> list:
        """
        Loads the yaml file passed containing meter endpoint information

        Returns: list
        """
        with open(file_path, mode='r', encoding='utf-8') as file:
            endpoints = yaml.safe_load(file)

        return endpoints

    def create_endpoints(self, endpoints: dict, device_info: dict) -> None:
        # Build query objects for each endpoint
        query_obj = []
        for point in endpoints:
            for endpoint_name, v in point.items():
                request_url = f'{self.url}{v["url"]}'
                query_obj.append(xcelEndpoint(self.requests_session, self.mqtt_client,
                                    request_url, endpoint_name, v['tags'], device_info))

        return query_obj

    @staticmethod
    def get_mqtt_port() -> int:
        """
        Identifies the port to use for the MQTT server. Very basic,
        just offers a detault of 1883 if no other port is set

        Returns: int
        """
        env_port = os.getenv('MQTT_PORT')
        # If environment variable for MQTT port is set, use that
        # if not, use the default
        mqtt_port = int(env_port) if env_port else 1883

        return mqtt_port

    @staticmethod
    def setup_mqtt(mqtt_server_address, mqtt_port) -> mqtt.Client:
        """
        Creates a new mqtt client to be used for the the xcelQuery
        objects.

        Returns: mqtt.Client object
        """
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logging.info("Connected to MQTT Broker!")
            else:
                logging.error("Failed to connect, return code %d\n", rc)

        # Check if a username/PW is setup for the MQTT connection
        mqtt_username = os.getenv('MQTT_USER')
        mqtt_password = os.getenv('MQTT_PASSWORD')
        # If no env variable was set, skip setting creds?
        client = mqtt.Client()
        if mqtt_username and mqtt_password:
            client.username_pw_set(mqtt_username, mqtt_password)
        client.on_connect = on_connect
        logging.info(f"MQTT connection details:")
        logging.info(f"MQTT_ADDRESS: {mqtt_server_address}")
        logging.info(f"MQTT_PORT: {mqtt_port}")
        logging.info(f"MQTT_USER: {mqtt_username}")
        client.connect(mqtt_server_address, mqtt_port)
        client.loop_start()

        return client

    # Send MQTT config setup to Home assistant
    def send_configs(self):
        """
        Sends the MQTT config to the homeassistant topic for
        automatic discovery

        Returns: None
        """
        for obj in self.query_obj:
            obj.mqtt_send_config()
            input()

    def send_mqtt_config(self) -> None:
        """
        Sends a discovery payload to homeassistant for the new meter device

        Returns: None
        """
        mqtt_topic_prefix = os.getenv('MQTT_TOPIC_PREFIX', 'homeassistant')
        state_topic = f'{mqtt_topic_prefix}/device/energy/{self.name.replace(" ", "_").lower()}'
        config_dict = {
            "name": self.name,
            "device_class": "energy",
            "state_topic": state_topic,
            "unique_id": self._lfdi
            }
        config_dict.update(self.device_info)
        config_json = json.dumps(config_dict)
        logging.debug(f"Sending MQTT Discovery Payload")

        result = self.mqtt_client.publish(state_topic, str(config_json))
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logging.debug(f"MQTT discovery payload published successfully (mid: {result.mid})")
            logging.debug(f"TOPIC: {state_topic}")
            logging.debug(f"Config: {config_json}")
        elif result.rc == mqtt.MQTT_ERR_NO_CONN:
            logging.error(f"MQTT publish failed: Not connected to broker")
        else:
            logging.error(f"MQTT publish failed with return code: {result.rc}")

    def run(self) -> None:
        """
        Main business loop. Just repeatedly queries the meter endpoints,
        parses the results, packages these up into MQTT payloads, and sends
        them off to the MQTT server

        Returns: None
        """
        while True:
            sleep(self.POLLING_RATE)
            for obj in self.endpoints:
                obj.run()
