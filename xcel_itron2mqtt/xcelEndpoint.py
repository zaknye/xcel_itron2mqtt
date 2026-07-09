import os
import yaml
import json
import logging
import requests
import paho.mqtt.client as mqtt
import xml.etree.ElementTree as ET
from copy import deepcopy
from tenacity import retry, stop_after_attempt, before_sleep_log, wait_exponential

logger = logging.getLogger(__name__)

# Prefix that appears on all of the XML elements
# IEEE 2030.5 spec reference: https://zepben.github.io/evolve/docs/2030-5/
IEEE_PREFIX = '{urn:ieee:std:2030.5:ns}'

# Default device/integration name. When the configured name matches this,
# unique_ids and MQTT topics are byte-for-byte identical to previous
# single-meter releases. Setting a different name (via the DEVICE_NAME env
# var) namespaces both, so two meters can be published to the same broker /
# Home Assistant instance without clobbering each other.
DEFAULT_DEVICE_NAME = "Xcel Itron 5"

class xcelEndpoint():
    """
    Class wrapper for all readings associated with the Xcel meter.
    Expects a request session that should be shared amongst the
    instances.
    """
    def __init__(self, session: requests.Session, mqtt_client: mqtt.Client,
                    url: str, name: str, tags: list, device_info: dict):
        self.requests_session = session
        self.url = url
        self.name = name
        self.tags = tags
        self.client = mqtt_client
        self.device_info = device_info

        self._mqtt_topic_prefix = os.getenv('MQTT_TOPIC_PREFIX', 'homeassistant')
        self._mqtt_topic = None
        # Record all of the sensor state topics in an easy to lookup dict
        self._sensor_state_topics = {}

        # Setup the rest of what we need for this endpoint
        self._mqtt_send_config()

    @retry(stop=stop_after_attempt(5),
           wait=wait_exponential(multiplier=1, min=1, max=5),
           before_sleep=before_sleep_log(logger, logging.WARNING),
           reraise=True)
    def query_endpoint(self) -> str:
        """
        Sends a request to the given endpoint associated with the
        object instance

        Returns: str in XML format of the meter's response
        """
        x = self.requests_session.get(self.url, timeout=15.0)

        return x.text

    @staticmethod
    def parse_response(response: str, tags: dict) -> dict:
        """
        Drill down the XML response from the meter and extract the
        readings according to the endpoints.yaml structure.

        Returns: dict in the nesting structure of found below each tag
        in the endpoints.yaml
        """
        readings_dict = {}
        root = ET.fromstring(response)
        # Kinda gross
        for k, v in tags.items():
            if isinstance(v, list):
                for val_items in v:
                    for k2, v2 in val_items.items():
                        search_val = f'{IEEE_PREFIX}{k2}'
                        elem = root.find(f'.//{search_val}')
                        if elem is not None:
                            readings_dict[f'{k}{k2}'] = elem.text
            else:
                search_val = f'{IEEE_PREFIX}{k}'
                elem = root.find(f'.//{search_val}')
                if elem is not None:
                    readings_dict[k] = elem.text

        return readings_dict

    def _get_reading(self) -> dict:
        """
        Query the endpoint associated with the object instance and
        return the parsed XML response in the form of a dictionary

        Returns: Dict in the form of {reading: value}
        """
        response = self.query_endpoint()
        parsed_response = self.parse_response(response, self.tags)

        return parsed_response

    def _create_config(self, sensor_name: str,  details: dict) -> tuple[str, dict]:
        """
        Helper to generate the JSON sonfig payload for setting
        up the new Homeassistant entities

        Returns: Tuple consisting of a string representing the mqtt
        topic, and a dict to be used as the payload.
        """
        payload = deepcopy(details)
        mqtt_friendly_name = self.name.replace(" ", "_")
        entity_type = payload.pop('entity_type')
        # Namespace the discovery/state topic path by the device name so that
        # two meters (each configured with a distinct DEVICE_NAME) publish to
        # different topics and don't overwrite each other's retained configs.
        # With the default name this is a no-op, preserving the exact legacy
        # topic layout for existing single-meter installs.
        device_name = self.device_info['device']['name']
        if device_name == DEFAULT_DEVICE_NAME:
            node_id = mqtt_friendly_name
        else:
            device_slug = device_name.replace(" ", "_")
            node_id = f'{device_slug}_{mqtt_friendly_name}'
        payload["state_topic"] = f'{self._mqtt_topic_prefix}/{entity_type}/{node_id}/{sensor_name}/state'
        payload['name'] = f'{self.name} {sensor_name}'
        # Mouthful
        # Unique ID becomes the device name + class name + sensor name, all lower case, all underscores instead of spaces
        payload['unique_id'] = f"{device_name}_{self.name}_{sensor_name}".lower().replace(' ', '_')
        payload.update(self.device_info)
        # MQTT Topics don't like spaces
        mqtt_topic = f'{self._mqtt_topic_prefix}/{entity_type}/{node_id}/{sensor_name}/config'
        # Capture the state topic the sensor is associated with for later use
        self._sensor_state_topics[sensor_name] = payload['state_topic']
        payload = json.dumps(payload)

        return mqtt_topic, payload

    def _mqtt_send_config(self) -> None:
        """
        Homeassistant requires a config payload to be sent to more
        easily setup the sensor/device once it appears over mqtt
        https://www.home-assistant.io/integrations/mqtt/
        """
        _tags = deepcopy(self.tags)
        for k, v in _tags.items():
            if isinstance(v, list):
                for val_items in v:
                    name, details = val_items.popitem()
                    sensor_name = f'{k}{name}'
                    mqtt_topic, payload = self._create_config(sensor_name, details)
                    # Send MQTT payload
                    self._mqtt_publish(mqtt_topic, str(payload))
            else:
                mqtt_topic, payload = self._create_config(k, v)
                self._mqtt_publish(mqtt_topic, str(payload), retain=True)

    def _process_send_mqtt(self, reading: dict) -> None:
        """
        Run through the readings from the meter and translate
        and prepare these readings to send over mqtt

        Returns: None
        """
        mqtt_topic_message = {}
        # Cycle through all the readings for the given sensor
        for k, v in reading.items():
            # Figure out which topic this reading needs to be sent to
            topic = self._sensor_state_topics[k]
            mqtt_topic_message[topic] = v

        # Cycle through and send the payload to the associated keys
        for topic, payload in mqtt_topic_message.items():
            self._mqtt_publish(topic, payload)

    def _mqtt_publish(self, topic: str, message: str, retain=False) -> int:
        """
        Publish the given message to the topic associated with the class

        Returns: integer (return code)
        """
        result = self.client.publish(topic, str(message), retain=retain)

        # Check the return code and log appropriately
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug(f"Published to {topic} (mid: {result.mid})")
        elif result.rc == mqtt.MQTT_ERR_NO_CONN:
            logger.error(f"MQTT publish to {topic} failed: Not connected to broker")
        else:
            logger.error(f"MQTT publish to {topic} failed with return code: {result.rc}")

        # Return status of the published message (backwards compatibility)
        return result.rc

    def run(self) -> None:
        """
        Main business loop for the endpoint class.
        Read from the meter, process and send over MQTT

        Returns: None
        """
        reading = self._get_reading()
        self._process_send_mqtt(reading)
