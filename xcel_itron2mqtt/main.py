import os
import logging
from time import sleep
from pathlib import Path
from xcelMeter import xcelMeter
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

INTEGRATION_NAME = "Xcel Itron 5"

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(format='%(levelname)s: %(message)s', level=LOGLEVEL)

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
    cert_path = Path('certs/.cert.pem')
    key_path = Path('certs/.key.pem')
    if cert and key:
        return cert, key
    # If not, look in the local directory
    elif cert_path.is_file() and key_path.is_file():
        return (cert_path, key_path)
    else:
        raise FileNotFoundError('Could not find cert and key credentials')

def mDNS_search_for_meter() -> str | int:
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
    port = listener.info.port
    # Close out our mDNS discovery device
    zeroconf.close()
  
    return ip_address, port


if __name__ == '__main__':
    if os.getenv('METER_IP') and os.getenv('METER_PORT'):
        ip_address = os.getenv('METER_IP')
        port_num = os.getenv('METER_PORT')
    else:
        ip_address, port_num = mDNS_search_for_meter()
    creds = look_for_creds()
    meter = xcelMeter(INTEGRATION_NAME, ip_address, port_num, creds)
    meter.setup()

    if meter.initalized:
        # The run method controls all the looping, querying, and mqtt sending
        meter.run()