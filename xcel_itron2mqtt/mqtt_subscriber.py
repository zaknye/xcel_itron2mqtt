import os
import logging
import paho.mqtt.client as mqtt
from time import sleep

# Configure logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(format='%(levelname)s: %(message)s', level=LOGLEVEL)
logger = logging.getLogger(__name__)


class MQTTSubscriber:
    """
    MQTT Subscriber class to listen to Xcel meter data topics
    and print received data to screen for monitoring purposes.
    """

    def __init__(self, mqtt_server, mqtt_port=1883, mqtt_user=None, mqtt_password=None):
        self.mqtt_server = mqtt_server
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_password = mqtt_password
        self.client = None
        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker"""
        if rc == 0:
            logger.info("MQTT Subscriber connected to broker successfully!")
            self.connected = True
        else:
            logger.error(
                f"MQTT Subscriber failed to connect, return code: {rc}")
            self.connected = False

    def on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker"""
        logger.warning(
            f"MQTT Subscriber disconnected with return code: {rc}")
        self.connected = False

    def on_message(self, client, userdata, msg):
        """Callback for when a message is received"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')

        print(f"\nMQTT Message Received:")
        print(f"   Topic: {topic}")
        print(f"   Payload: {payload}")
        print(f"   QoS: {msg.qos}")
        print(f"   Retain: {msg.retain}")
        print("-" * 50)

        # Parse and display energy data if it's the Current Summation Received topic
        if "Current_Summation_Received" in topic:
            try:
                energy_value = float(payload)
                print(f"⚡ Energy Received: {energy_value} Wh")
                print(f"   ({energy_value/1000:.3f} kWh)")
            except ValueError:
                print(f"Could not parse energy value: {payload}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback for when the client subscribes to a topic"""
        logger.info(f"Subscribed to topic with QoS: {granted_qos}")

    def setup_client(self):
        """Setup the MQTT client with callbacks"""
        self.client = mqtt.Client()

        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe

        # Set credentials if provided
        if self.mqtt_user and self.mqtt_password:
            self.client.username_pw_set(self.mqtt_user, self.mqtt_password)

        return self.client

    def connect(self):
        """Connect to the MQTT broker"""
        if not self.client:
            logger.error("MQTT client not initialized")
            return False

        try:
            logger.info(
                f"Connecting to MQTT broker at {self.mqtt_server}:{self.mqtt_port}")
            self.client.connect(self.mqtt_server, self.mqtt_port, 60)
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def subscribe_to_topics(self):
        """Subscribe to the Xcel meter topics"""
        if not self.client:
            logger.error("MQTT client not initialized")
            return

        topics = [
            ("homeassistant/sensor/xcel_itron_5/Current_Summation_Received/state", 0),
            ("homeassistant/sensor/xcel_itron_5/Instantaneous_Demand/state", 0),
            ("homeassistant/sensor/xcel_itron_5/Current_Summation_Delivered/state", 0)
        ]

        for topic, qos in topics:
            logger.info(f"Subscribing to topic: {topic}")
            self.client.subscribe(topic, qos)

    def start(self):
        """Start the MQTT subscriber"""
        print("Starting MQTT Subscriber for Xcel Meter Data...")
        print("=" * 60)

        # Setup and connect
        self.setup_client()
        if not self.connect():
            return False

        # Subscribe to topics
        self.subscribe_to_topics()

        # Start the loop
        if self.client:
            self.client.loop_start()

        print("Listening for MQTT messages...")
        print("   Press Ctrl+C to stop")
        print("=" * 60)

        return True

    def stop(self):
        """Stop the MQTT subscriber"""
        if self.client:
            logger.info("Stopping MQTT Subscriber...")
            self.client.loop_stop()
            self.client.disconnect()


def main():
    """Main function to run the MQTT subscriber"""
    # Get MQTT configuration from environment variables
    mqtt_server = os.getenv('MQTT_SERVER', 'localhost')
    mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
    mqtt_user = os.getenv('MQTT_USER')
    mqtt_password = os.getenv('MQTT_PASSWORD')

    # Create and start subscriber
    subscriber = MQTTSubscriber(
        mqtt_server=mqtt_server,
        mqtt_port=mqtt_port,
        mqtt_user=mqtt_user,
        mqtt_password=mqtt_password
    )

    try:
        if subscriber.start():
            # Keep the subscriber running
            while True:
                sleep(1)
        else:
            logger.error("Failed to start MQTT subscriber")
            return 1
    except KeyboardInterrupt:
        print("\nStopping MQTT Subscriber...")
    except Exception as e:
        logger.error(f"Error in MQTT subscriber: {e}")
        return 1
    finally:
        subscriber.stop()

    return 0


if __name__ == "__main__":
    exit(main())
