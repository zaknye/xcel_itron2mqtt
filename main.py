import os
import ssl
import yaml
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from time import sleep
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
from requests.packages.urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter

IEEE_PREFIX = '{urn:ieee:std:2030.5:ns}'

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
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers(CIPHERS)
        kwargs['ssl_context'] = context
        return super(CCM8Adapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        ssl_version=ssl.PROTOCOL_TLSv1_2
        context = create_urllib3_context(ssl_version=ssl_version)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
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

def find_endpoints(session: requests.session, ip_address: str) -> dict:
    prefix = 'https://'
    port = ':8081'
    suffix = "/upt/"
    request_url = f"{prefix}{ip_address}{port}{suffix}"
    initial_response = make_meter_request(session, request_url)
    print("Initial response!")
    print(initial_response)
    # Parse incoming XML
    root = ET.fromstring(initial_response)
    # Check to make sure we have the XML entries we're looking for
    if root.tag == f'{IEEE_PREFIX}UsagePointList' and isinstance(root.attrib, dict):
        pass
    else:
        raise KeyError('UsagePoint key not found!')

    poll_rate = root.attrib['pollRate']

    reading_link = root.find(f'.//{IEEE_PREFIX}MeterReadingListLink')
    
    print(reading_link)
    try:
        suffix = reading_link.attrib['href']
        num_readings = reading_link.attrib['all']
        print(suffix)
    except:
        raise KeyError('MeterReadingListLink tag not found!')
    
    # Cycle through all the readings, and find their endpoints
    for num in num_readings:    
        request_url = f"{prefix}{ip_address}{port}{suffix}"
        print(f"New request URL {request_url}")
        response = make_meter_request(session, request_url)
        root = ET.fromstring(response)
        reading_link = root.find(f'.//{IEEE_PREFIX}MeterReading')
        try:
            suffix = reading_link.attrib['href']
            print(suffix)
        except:
            raise KeyError('MeterReading tag not found!')
    request_url = f"{prefix}{ip_address}{port}{suffix}"
    print(f"New request URL {request_url}")
    response = make_meter_request(session, request_url)

    print(response)

    return asd

def parse_response(response: str, tags: list) -> dict:
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

def probe_endpoints(session: requests.session, endpoints: list, ip_address: str) -> dict:
    data = {}
    for point in endpoints:
        for k, v in point.items():
            try:
                request_url = f'https://{ip_address}:8081{v["url"]}'
                print(request_url)
                response = make_meter_request(session, request_url)
            except:
                raise ConnectionError("Failed to get response from meter")
            parsed_data = parse_response(response, v['tags'])
            data[k] = parsed_data
    
    return data

def make_meter_request(session: requests.session, address: str) -> str:
    x = session.get(address, verify=False)
    
    return x.text

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
    if cert and key:
        return cert, key
    # If not, look in the local directory
    elif Path('cert.pem').is_file() and Path('key.pem').is_file():
        return (Path('cert.pem'), Path('key.pem'))
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
    with open('endpoints.yaml', mode='r', encoding='utf-8') as file:
        endpoints = yaml.safe_load(file)
    while True:
        probe_results = probe_endpoints(session, endpoints, ip_address)
        print(probe_results)

    #endpoints = find_endpoints(session, ip_address)
