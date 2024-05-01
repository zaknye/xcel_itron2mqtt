import yaml
import os
import json
import requests
import logging
import paho.mqtt.client as mqtt
import xml.etree.ElementTree as ET
from copy import deepcopy
from tenacity import retry, stop_after_attempt, before_sleep_log, wait_exponential

logger = logging.getLogger(__name__)

# Prefix that appears on all of the XML elements
IEEE_PREFIX = '{urn:ieee:std:2030.5:ns}'

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

        self._mqtt_topic_prefix = os.getenv('MQTT_TOPIC_PREFIX', 'homeassistant/')
        self._current_response = None
        self._mqtt_topic = None
        # Record all of the sensor state topics in an easy to lookup dict
        self._sensor_state_topics = {}

        # Setup the rest of what we need for this endpoint
        self.mqtt_send_config()

    @retry(stop=stop_after_attempt(15),
           wait=wait_exponential(multiplier=1, min=1, max=15),
           before_sleep=before_sleep_log(logger, logging.WARNING),
           reraise=True)
    def query_endpoint(self) -> str:
        """
        Sends a request to the given endpoint associated with the 
        object instance

        Returns: str in XML format of the meter's response
        """
        x = self.requests_session.get(self.url, verify=False, timeout=15.0)
    
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
                        if root.find(f'.//{search_val}') is not None:
                            value = root.find(f'.//{search_val}').text
                            readings_dict[f'{k}{k2}'] = value
            else:
                search_val = f'{IEEE_PREFIX}{k}'
                if root.find(f'.//{IEEE_PREFIX}{k}') is not None:
                    value = root.find(f'.//{IEEE_PREFIX}{k}').text
                    readings_dict[k] = value
    
        return readings_dict

    def get_reading(self) -> dict:
        """
        Query the endpoint associated with the object instance and
        return the parsed XML response in the form of a dictionary
        
        Returns: Dict in the form of {reading: value}
        """
        response = self.query_endpoint()
        self.current_response = self.parse_response(response, self.tags)

        return self.current_response

    def create_config(self, sensor_name: str,  details: dict) -> tuple[str, dict]:
        """
        Helper to generate the JSON sonfig payload for setting
        up the new Homeassistant entities

        Returns: Tuple consisting of a string representing the mqtt
        topic, and a dict to be used as the payload.
        """
        payload = deepcopy(details)
        mqtt_friendly_name = self.name.replace(" ", "_")
        entity_type = payload.pop('entity_type')
        payload["state_topic"] = f'{self._mqtt_topic_prefix}{entity_type}/{mqtt_friendly_name}/{sensor_name}/state'
        payload['name'] = f'{self.name} {sensor_name}'
        # Mouthful
        # Unique ID becomes the device name + class name + sensor name, all lower case, all underscores instead of spaces
        payload['unique_id'] = f"{self.device_info['device']['name']}_{self.name}_{sensor_name}".lower().replace(' ', '_')
        payload.update(self.device_info)
        # MQTT Topics don't like spaces
        mqtt_topic = f'{self._mqtt_topic_prefix}{entity_type}/{mqtt_friendly_name}/{sensor_name}/config'
        # Capture the state topic the sensor is associated with for later use
        self._sensor_state_topics[sensor_name] = payload['state_topic']
        payload = json.dumps(payload)

        return mqtt_topic, payload

    def mqtt_send_config(self) -> None:
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
                    mqtt_topic, payload = self.create_config(sensor_name, details)
                    # Send MQTT payload
                    self.mqtt_publish(mqtt_topic, str(payload))
            else:
                name_suffix = f'{k[0].upper()}'
                mqtt_topic, payload = self.create_config(k, v)
                self.mqtt_publish(mqtt_topic, str(payload), retain=True)

    def process_send_mqtt(self, reading: dict) -> None:
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
            if topic not in mqtt_topic_message.keys():
                mqtt_topic_message[topic] = {}
            # Create dict of {topic: payload}
            mqtt_topic_message[topic] = v

        # Cycle through and send the payload to the associated keys
        for topic, payload in mqtt_topic_message.items():
            self.mqtt_publish(topic, payload)

    def mqtt_publish(self, topic: str, message: str, retain=False) -> int:
        """
        Publish the given message to the topic associated with the class
       
        Returns: integer
        """
        result = [0]
        #print(f"Sending to MQTT TOPIC:\t{topic}")
        #print(f"Payload:\t\t{message}")
        result = self.client.publish(topic, str(message), retain=retain)
        #print('Error in sending MQTT payload')
        #print(f"MQTT Send Result: \t\t{result}")
        # Return status of the published message
        return result[0]

    def run(self) -> None:
        """
        Main business loop for the endpoint class.
        Read from the meter, process and send over MQTT

        Returns: None
        """
        reading = self.get_reading()
        self.process_send_mqtt(reading)
