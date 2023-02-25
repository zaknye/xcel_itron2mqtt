import os
import ssl
import yaml
import requests
import paho.mqtt.client as mqtt
import xml.etree.ElementTree as ET
from pathlib import Path
from time import sleep
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
from requests.packages.urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter

IEEE_PREFIX = '{urn:ieee:std:2030.5:ns}'
MQTT_TOPIC = 'xcel_itron2mqtt/meter_reading/'
POLLING_RATE = 5

# Our target cipher is: ECDHE-ECDSA-AES128-CCM8
CIPHERS = ('ECDHE')

class XcelQuery():
    def __init__(self, session: requests.session, url: str, name: str, 
                    tags: list, mqtt_client: mqtt.Client, poll_rate = 5.0):
        self.requests_session = session
        self.url = url
        self.name = name
        self.tags = tags
        self.client = mqtt_client
        self.current_response = None
        self.poll_rate = poll_rate
        
    def query_endpoint(self) -> str:
        x = self.requests_session.get(self.url, verify=False, timeout=4.0)
    
        return x.text

    def parse_response(self, response: str, tags: list) -> dict:
        readings_dict = {}
        root = ET.fromstring(response)
        for tag in tags:
            if not isinstance(tag, dict):
                search_val = f'{IEEE_PREFIX}{tag}'
                value = root.find(f'.//{IEEE_PREFIX}{tag}').text
                readings_dict[tag] = value
            else:
                # A lot of assumptions on the format of the endpoints YAML
                for k, v in tag.items():
                    for val in v:
                        if k not in readings_dict.keys():
                            readings_dict[k] = {}
                        search_val = f'{IEEE_PREFIX}{val}'
                        value = root.find(f'.//{IEEE_PREFIX}{val}').text
                        readings_dict[k][val] = value
    
        return readings_dict

    def get_reading(self) -> str:
        response = self.query_endpoint()
        self.current_response = self.parse_response(response, self.tags)
        
        return self.current_response
    
    def mqtt_create_message() -> str:
        return

    def mqtt_publish(messsage: str) -> int:
        result = client.publish(topic, message)
        
        # Return status of the published message
        return result[0]

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
    session = requests.session()
    session.cert = creds
    # Mount our adapter to the domain
    session.mount('https://{ip_address}', CCM8Adapter())

    return session

def look_for_creds() -> tuple:
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
    # create a zeroconf object and listener to query mDNS for the meter
    zeroconf = Zeroconf()
    listener = XcelListener()
    # Meter will respone on _smartenergy._tcp.local. port 5353
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
    # Read in the API structure for a dictionary of endpoints and XML structure
    with open('endpoints.yaml', mode='r', encoding='utf-8') as file:
        endpoints = yaml.safe_load(file)
    # Build query objects for each endpoint
    query_obj = []
    for point in endpoints:
        for endpoint_name, v in point.items():
            request_url = f'https://{ip_address}:8081{v["url"]}'
            query_obj.append(XcelQuery(session, request_url, endpoint_name, v['tags']))
    while True:
        sleep(POLLING_RATE)
        for obj in query_obj:
            reading = obj.get_reading()
            print(reading)
