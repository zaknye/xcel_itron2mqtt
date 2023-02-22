import os
import ssl
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from time import sleep
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
from requests.packages.urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter

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
    if root.tag == '{urn:ieee:std:2030.5:ns}UsagePoint' and isinstance(root.child, dict):
        prefix = root.atrrib['href']
    else:
        raise KeyError('UsagePoint key not found!')
    print(f"Tag: {child.tag}, \tattrib: {child.attrib}")
    suffix = child.attrib['href']
    request_url = f"{prefix}{ip_address}{port}{suffix}"
    response = make_meter_request(session, request_url)
    new_tree = ET.fromstring(response)
    for a in new_tree:
        print(f"Tag: {a.tag}, \tattrib: {a.attrib}")
    #input()
    asd = {}
    return asd

def parse_meter_response(text: str) -> None:
    
    return

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
    counter = 0
    listener = None
    # Have to wait to hear back from the asynchrounous listener/browser task
    while listener == None and counter < 20:
        # create a zeroconf object and listener to query mDNS for the meter
        zeroconf = Zeroconf()
        listener = XcelListener()
        # Meter will respone on _smartenergy._tcp.local. port 5353
        browser = ServiceBrowser(zeroconf, "_smartenergy._tcp.local.", listener)
        # Fun (a)synchronicities
        sleep(1)
        addresses = listener.info.addresses
        print(listener.info)
        # Auto parses the network byte format into a legible address
        ip_address = listener.info.parsed_addresses()[0]
        counter += 1
    
    if counter > 20:
        raise TimeoutError('Waiting too long to get response from meter')
    # Close out our mDNS discovery device
    zeroconf.close()
  
    return ip_address

if __name__ == '__main__':
    ip_address = mDNS_search_for_meter()
    creds = look_for_creds()
    session = setup_session(creds, ip_address)
    endpoints = find_endpoints(session, ip_address)
