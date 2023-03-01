import os
import ssl
import yaml
import requests
import paho.mqtt.client as mqtt
import xml.etree.ElementTree as ET
from time import sleep
from pathlib import Path
from xcelEndpoint import xcelEndpoint
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
from requests.packages.urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter

# Prefix that appears on all of the XML elements
IEEE_PREFIX = '{urn:ieee:std:2030.5:ns}'
POLLING_RATE = 5
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

# mDNS listener to find the IP Address of the meter on the network
class XcelListener(ServiceListener):
    def __init__(self):
        self.info = None

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.info = zc.get_service_info(type_, name)
        print(f"Service {name} added, service info: {self.info}")

# Setup MQTT client that will be shared with each XcelQuery object
def setup_mqtt() -> mqtt.Client:
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

    mqtt_server_address = os.getenv('MQTT_SERVER')
    env_port = os.getenv('MQTT_SERVER')
    # If environment variable for MQTT port is set, use that
    # if not, use the default
    mqtt_port = env_port if env_port else 1883
    # Check if a username/PW is setup for the MQTT connection
    mqtt_username = os.getenv('MQTT_USER')
    mqtt_password = os.getenv('MQTT_PASSWORD')
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)
    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect(mqtt_server_address, mqtt_port)
    client.loop_start()

    return client

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

def look_for_creds() -> tuple:
    """
    Defaults to extracting the cert and key path from environment variables,
    but if those don't exist it tries to find the hidden credentials files 
    in the default folder of /certs.

    Returns: tuple of paths for cert and key files
    """
    # Find if the cred paths are on PATH
    cert = os.getenv('CERT_PATH')
    key = os.getenv('KEY_PATH')
    cert_path = Path('cert.pem')
    key_path = Path('key.pem')
    if cert and key:
        return cert, key
    # If not, look in the local directory
    elif cert_path.is_file() and key_path.is_file():
        return (cert_path, key_path)
    else:
        raise FileNotFoundError('Could not find cert and key credentials')

def mDNS_search_for_meter() -> str:
    """
    Creates a new zeroconf instance to probe the network for the meter
    to extract its ip address and port. Closes the instance down when complete.

    Returns: string, ip address of the meter
    """
    zeroconf = Zeroconf()
    listener = XcelListener()
    # Meter will respond on _smartenergy._tcp.local. port 5353
    browser = ServiceBrowser(zeroconf, "_smartenergy._tcp.local.", listener)
    # Have to wait to hear back from the asynchrounous listener/browser task
    sleep(10)
    try:
        addresses = listener.info.addresses
    except:
        raise TimeoutError('Waiting too long to get response from meter')
    print(listener.info)
    # Auto parses the network byte format into a legible address
    ip_address = listener.info.parsed_addresses()[0]
    # TODO: Add port capturing here
    # Close out our mDNS discovery device
    zeroconf.close()
  
    return ip_address

if __name__ == '__main__':

    ip_address = mDNS_search_for_meter()
    creds = look_for_creds()
    session = setup_session(creds, ip_address)
    #mqtt_client = setup_mqtt()
    # Read in the API structure for a dictionary of endpoints and XML structure
    with open('endpoints.yaml', mode='r', encoding='utf-8') as file:
        endpoints = yaml.safe_load(file)
    # Build query objects for each endpoint
    query_obj = []
    for point in endpoints:
        for endpoint_name, v in point.items():
            request_url = f'https://{ip_address}:8081{v["url"]}'
            #query_obj.append(XcelQuery(session, request_url, endpoint_name, v['tags'], mqtt_client))
            query_obj.append(xcelEndpoint(session, request_url, endpoint_name, v['tags']))
    
    # Send MQTT config setup to Home assistant
    for obj in query_obj:
        obj.mqtt_send_config()
        input()

    while True:
        sleep(POLLING_RATE)
        for obj in query_obj:
            reading = obj.get_reading()
            print(reading)
