import os
import ssl
import yaml
import requests
import paho.mqtt.client as mqtt
from typing import Tuple
from time import sleep
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
from requests.packages.urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter

# Local imports
from xcelEndpoint import xcelEndpoint

# Our target cipher is: ECDHE-ECDSA-AES128-CCM8
CIPHERS = ('ECDHE')

# Create an adapter for our request to enable the non-standard cipher
# From https://lukasa.co.uk/2017/02/Configuring_TLS_With_Requests/
class CCM8Adapter(HTTPAdapter):
    """
    A TransportAdapter that re-enables ECDHE support in Requests.
    Not really sure how much redundancy is actually required here
    """
    def init_poolmanager(self, *args, **kwargs):
        ssl_version=ssl.PROTOCOL_TLSv1_2
        context = create_urllib3_context(ssl_version=ssl_version)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        context.set_ciphers(CIPHERS)
        kwargs['ssl_context'] = context
        return super(CCM8Adapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        ssl_version=ssl.PROTOCOL_TLSv1_2
        context = create_urllib3_context(ssl_version=ssl_version)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        context.set_ciphers(CIPHERS)
        kwargs['ssl_context'] = context
        return super(CCM8Adapter, self).proxy_manager_for(*args, **kwargs)

class xcelMeter():

    def __init__(self, name: str, ip_address: str, port: int, creds: Tuple[str, str]):
        self.name = name
        # Base URL used to query the meter
        self.url = f'https://{ip_address}:{port}'
        self._mfid = None
        self._lfdi = None
        self._swVer = None

        # Setup the MQTT server connection
        self.mqtt_server_address = os.getenv('MQTT_SERVER')
        self.mqtt_port = self.get_mqtt_port()
        self.mqtt_client = self.setup_mqtt(self.mqtt_server_address, self.mqtt_port)

        # Create a new requests session based on the passed in ip address and port #
        self.session = self.setup_session(creds, ip_address)

        # List to store our endpoint objects in
        self.endpoints_list = self.load_endpoints('endpoints.yaml')
        self.endpoints = self.create_endpoints(self.endpoints_list)
        self.POLLING_RATE = 5.0

    @staticmethod
    def setup_session(creds: tuple, ip_address: str) -> requests.session:
        """
        Creates a new requests session with the given credentials pointed
        at the give IP address. Will be shared across each xcelQuery object.

        Returns: request.session
        """
        session = requests.session()
        session.cert = creds
        # Mount our adapter to the domain
        session.mount('https://{ip_address}', CCM8Adapter())

        return session

    # Read in the API structure for a dictionary of endpoints and XML structure
    @staticmethod
    def load_endpoints(file_path: str) -> list:
        with open(file_path, mode='r', encoding='utf-8') as file:
            endpoints = yaml.safe_load(file)
        
        return endpoints
    
    def create_endpoints(self, endpoints: dict) -> None:
        # Build query objects for each endpoint
        query_obj = []
        for point in endpoints:
            for endpoint_name, v in point.items():
                request_url = f'{self.url}{v["url"]}'
                query_obj.append(xcelEndpoint(self.session, self.mqtt_client, 
                                    request_url, endpoint_name, v['tags']))
        
        return query_obj
    
    @staticmethod
    def get_mqtt_port() -> int:
        env_port = int(os.getenv('MQTT_PORT'))
        # If environment variable for MQTT port is set, use that
        # if not, use the default
        mqtt_port = env_port if env_port else 1883
        
        return mqtt_port

    # Setup MQTT client that will be shared with each XcelQuery object
    @staticmethod
    def setup_mqtt(mqtt_server_address, mqtt_port) -> mqtt.Client:
        """
        Creates a new mqtt client to be used for the the xcelQuery
        objects.

        Returns: mqtt.Client object
        """
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("Connected to MQTT Broker!")
            else:
                print("Failed to connect, return code %d\n", rc)

        # Check if a username/PW is setup for the MQTT connection
        mqtt_username = os.getenv('MQTT_USER')
        mqtt_password = os.getenv('MQTT_PASSWORD')
        if mqtt_username and mqtt_password:
            client.username_pw_set(mqtt_username, mqtt_password)
        # If no env variable was set, skip setting creds?
        client = mqtt.Client()
        client.on_connect = on_connect
        client.connect(mqtt_server_address, mqtt_port)
        client.loop_start()

        return client

    # Send MQTT config setup to Home assistant
    def send_configs(self):
        for obj in self.query_obj:
            obj.mqtt_send_config()
            input()

    def run(self) -> None:
        while True:
            sleep(self.POLLING_RATE)
            for obj in self.endpoints:
                reading = obj.get_reading()
                obj.process_send_mqtt(reading)
                print(reading)
    