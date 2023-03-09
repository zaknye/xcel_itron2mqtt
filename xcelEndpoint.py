import yaml
import requests
import paho.mqtt.client as mqtt
import xml.etree.ElementTree as ET
from copy import deepcopy

# Prefix that appears on all of the XML elements
IEEE_PREFIX = '{urn:ieee:std:2030.5:ns}'

class xcelEndpoint():
    """
    Class wrapper for all readings associated with the Xcel meter.
    Expects a request session that should be shared amongst the 
    instances.
    """
    def __init__(self, session: requests.session, url: str, name: str, 
                    tags: list, poll_rate = 5.0):
        self.requests_session = session
        self.url = url
        self.name = name
        self.tags = tags
        #self.client = mqtt_client
        self.poll_rate = poll_rate

        self._mqtt_topic_prefix = 'homeassistant/'
        self._current_response = None
        self._mqtt_topic = None
        self._entity_type_lookup = {}
        
    def query_endpoint(self) -> str:
        """
        Sends a request to the given endpoint associated with the 
        object instance

        Returns: str in XML format of the meter's response
        """
        x = self.requests_session.get(self.url, verify=False, timeout=4.0)
    
        return x.text

    def parse_response(self, response: str, tags: dict) -> dict:
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
                        value = root.find(f'.//{search_val}').text
                        readings_dict[f'{k}{k2}'] = value
            else:
                search_val = f'{IEEE_PREFIX}{k}'
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

    def create_config(self, sensor_name: str, name_suffix: str, details: dict) -> tuple[str, dict]:
        """
        Helper to generate the JSON sonfig payload for setting
        up the new Homeassistant entities

        Returns: Tuple consisting of a string representing the mqtt
        topic, and a dict to be used as the payload.
        """
        payload = deepcopy(details)
        entity_type = payload.pop('entity_type')
        payload['state_topic'] = f'{self._mqtt_topic_prefix}{entity_type}/{self.name}/state'
        payload['value_template'] = f"{{{{ value_template.{sensor_name} }}}}"
        mqtt_topic = f'{self._mqtt_topic_prefix}{entity_type}/{self.name}{name_suffix}/config'
        # Capture the state topic the sensor is associated with for later use
        self._entity_type_lookup[sensor_name] = payload['state_topic']

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
                    name_suffix = f'{k[0].upper()}{name[0].upper()}'
                    sensor_name = f'{k}{name}'
                    mqtt_topic, payload = self.create_config(sensor_name, name_suffix, details)
                    print(f"Sending to MQTT TOPIC:\t{mqtt_topic}")
                    print(f"Payload:\t\t{payload}")
                    # Send MQTT payload
                    self.mqtt_publish(mqtt_topic, payload)
            else:
                name_suffix = f'{k[0].upper()}'
                mqtt_topic, payload = self.create_config(k, name_suffix, v)
                print(f"Sending to MQTT TOPIC:\t{mqtt_topic}")
                print(f"Payload:\t\t{payload}")
                self.mqtt_publish(mqtt_topic, payload)

    def process_send_mqtt(self, reading: dict) -> None:
        """
        Run through the readings from the meter and translate
        and prepare these readings to send over mqtt
        """
        mqtt_topic_message = {}
        # Cycle through all the readings for the given sensor
        for k, v in reading.items():
            # Figure out which topic this reading needs to be sent to
            topic = self._entity_type_lookup[k]
            if topic not in mqtt_topic_message.keys():
                mqtt_topic_message[topic] = {}
            # Create dict of {topic: payload}
            mqtt_topic_message[topic].update({k: v})

        # Cycle through and send the payload to the associated keys
        for topic, payload in mqtt_topic_message.items():
            print(f'Sending to MQTT Topic: {topic}\tPayload: {payload}')
            self.mqtt_publish(topic, payload)

    def mqtt_publish(topic: str, messsage: str) -> int:
        """
        Publish the given message to the topic associated with the class
       
        Returns status integer
        """
        try:
            result = client.publish(topic, message)
        except:
            print('Error in sending MQTT payload')
            
        # Return status of the published message
        return result[0]