import os
import logging
from time import sleep
from pathlib import Path
from xcelMeter import xcelMeter
from xcelEndpoint import DEFAULT_DEVICE_NAME
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

# Name used for the Home Assistant device and as the prefix for every entity's
# unique_id and MQTT topic. Override with DEVICE_NAME to run more than one meter
# against the same broker / HA instance (each meter needs a distinct name).
INTEGRATION_NAME = os.environ.get('DEVICE_NAME', DEFAULT_DEVICE_NAME)

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(format='%(levelname)s: %(message)s', level=LOGLEVEL)
logger = logging.getLogger(__name__)

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
        logger.info(f"Service {name} added, service info: {self.info}")

def look_for_creds() -> tuple:
    """
    Defaults to extracting the cert and key path from environment variables,
    but if those don't exist it tries to find the hidden credentials files
    in the default folder of /certs.

    Returns: tuple of paths for cert and key files
    """
    cert_env = os.getenv('CERT_PATH')
    key_env = os.getenv('KEY_PATH')
    if cert_env or key_env:
        if not (cert_env and key_env):
            raise ValueError('CERT_PATH and KEY_PATH must both be set, or neither')
        return Path(cert_env), Path(key_env)

    cert_path = Path('certs/.cert.pem')
    key_path = Path('certs/.key.pem')
    if cert_path.is_file() and key_path.is_file():
        return cert_path, key_path

    raise FileNotFoundError('Could not find cert and key credentials')

def mDNS_search_for_meter() -> tuple[str, int]:
    """
    Creates a new zeroconf instance to probe the network for the meter
    to extract its ip address and port. Closes the instance down when complete.

    Returns: (ip_address, port) tuple
    """
    zeroconf = Zeroconf()
    listener = XcelListener()
    # Meter will respond on _smartenergy._tcp.local. port 5353
    browser = ServiceBrowser(zeroconf, "_smartenergy._tcp.local.", listener)
    # Have to wait to hear back from the asynchrounous listener/browser task
    sleep(10)
    if listener.info is None:
        raise TimeoutError('Waiting too long to get response from meter')
    logger.info(listener.info)
    # Auto parses the network byte format into a legible address
    ip_address = listener.info.parsed_addresses()[0]
    port = listener.info.port
    # Close out our mDNS discovery device
    zeroconf.close()

    return ip_address, port


if __name__ == '__main__':
    if os.getenv('METER_IP') and os.getenv('METER_PORT'):
        ip_address = os.getenv('METER_IP')
        port_num = int(os.getenv('METER_PORT'))
    else:
        ip_address, port_num = mDNS_search_for_meter()
    creds = look_for_creds()
    meter = xcelMeter(INTEGRATION_NAME, ip_address, port_num, creds)

    if meter.initialized:
        # The run method controls all the looping, querying, and mqtt sending
        meter.run()