#!/usr/bin/env python3
"""
Simulated Xcel Smart Meter Data Generator
This module generates realistic smart meter data in XML format and publishes it to MQTT topics
for testing the MQTT subscriber and monitoring stack.
"""

import os
import time
import random
import logging
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# Configure logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(format='%(levelname)s: %(message)s', level=LOGLEVEL)
logger = logging.getLogger(__name__)


class SimulatedMeter:
    """
    Simulated Xcel smart meter that generates realistic data
    and publishes it to MQTT topics for testing.
    """

    def __init__(self, mqtt_server='localhost', mqtt_port=1883, mqtt_user=None, mqtt_password=None):
        self.mqtt_server = mqtt_server
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_password = mqtt_password
        self.client = None
        self.connected = False

        # Simulated meter data
        self.base_energy_received = 12345678  # Wh
        self.base_energy_delivered = 5432100   # Wh
        self.base_power_demand = 2500          # W
        self.billing_start = datetime.now() - timedelta(days=30)

        # Energy consumption patterns (simulate realistic usage)
        self.hourly_patterns = {
            0: 0.3,   # 3 AM - low usage
            1: 0.2,   # 4 AM - very low
            2: 0.2,   # 5 AM - very low
            3: 0.3,   # 6 AM - low
            4: 0.5,   # 7 AM - medium
            5: 0.8,   # 8 AM - high
            6: 1.0,   # 9 AM - peak
            7: 0.9,   # 10 AM - high
            8: 0.8,   # 11 AM - high
            9: 0.7,   # 12 PM - medium-high
            10: 0.6,  # 1 PM - medium
            11: 0.5,  # 2 PM - medium
            12: 0.4,  # 3 PM - medium-low
            13: 0.5,  # 4 PM - medium
            14: 0.7,  # 5 PM - medium-high
            15: 0.9,  # 6 PM - high
            16: 1.0,  # 7 PM - peak
            17: 0.9,  # 8 PM - high
            18: 0.8,  # 9 PM - high
            19: 0.6,  # 10 PM - medium
            20: 0.4,  # 11 PM - medium-low
            21: 0.3,  # 12 AM - low
            22: 0.2,  # 1 AM - very low
            23: 0.2,  # 2 AM - very low
        }

    def on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker"""
        if rc == 0:
            logger.info(
                "Simulated Meter connected to MQTT broker successfully!")
            self.connected = True
        else:
            logger.error(
                f"Simulated Meter failed to connect, return code: {rc}")
            self.connected = False

    def on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker"""
        logger.warning(f"Simulated Meter disconnected with return code: {rc}")
        self.connected = False

    def setup_client(self):
        """Setup the MQTT client with callbacks"""
        self.client = mqtt.Client()

        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

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
            logger.error(
                f"Make sure MQTT broker is running and accessible at {self.mqtt_server}:{self.mqtt_port}")
            logger.error(
                f"If running locally, ensure Docker containers are started with: docker-compose up -d")
            return False

    def generate_instantaneous_demand_xml(self):
        """Generate XML for instantaneous demand (power usage)"""
        current_hour = datetime.now().hour
        pattern_multiplier = self.hourly_patterns.get(current_hour, 0.5)

        # Add some randomness to make it more realistic
        random_factor = random.uniform(0.8, 1.2)
        power_demand = int(self.base_power_demand *
                           pattern_multiplier * random_factor)

        # Ensure power demand is reasonable
        power_demand = max(100, min(8000, power_demand))

        xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<ns:Reading xmlns:ns="urn:ieee:std:2030.5:ns">
    <ns:value>{power_demand}</ns:value>
    <ns:quality>0</ns:quality>
    <ns:timeStamp>{int(time.time())}</ns:timeStamp>
    <ns:ReadingType>
        <ns:accumulationBehaviour>0</ns:accumulationBehaviour>
        <ns:commodity>1</ns:commodity>
        <ns:dataQualifier>0</ns:dataQualifier>
        <ns:flowDirection>0</ns:flowDirection>
        <ns:intervalLength>0</ns:intervalLength>
        <ns:kind>1</ns:kind>
        <ns:powerOfTenMultiplier>0</ns:powerOfTenMultiplier>
        <ns:uom>72</ns:uom>
    </ns:ReadingType>
</ns:Reading>"""

        return xml_template, power_demand

    def generate_summation_received_xml(self):
        """Generate XML for energy received (consumption)"""
        # Simulate energy consumption over time
        hours_since_start = (
            datetime.now() - self.billing_start).total_seconds() / 3600
        energy_increment = random.uniform(0.1, 0.3)  # kWh per hour
        energy_received = self.base_energy_received + \
            int(hours_since_start * energy_increment * 1000)

        xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<ns:Reading xmlns:ns="urn:ieee:std:2030.5:ns">
    <ns:value>{energy_received}</ns:value>
    <ns:quality>0</ns:quality>
    <ns:timeStamp>{int(time.time())}</ns:timeStamp>
    <ns:timePeriod>
        <ns:duration>2592000</ns:duration>
        <ns:start>{int(self.billing_start.timestamp())}</ns:start>
    </ns:timePeriod>
    <ns:touTier>1</ns:touTier>
    <ns:ReadingType>
        <ns:accumulationBehaviour>1</ns:accumulationBehaviour>
        <ns:commodity>1</ns:commodity>
        <ns:dataQualifier>0</ns:dataQualifier>
        <ns:flowDirection>0</ns:flowDirection>
        <ns:intervalLength>0</ns:intervalLength>
        <ns:kind>2</ns:kind>
        <ns:powerOfTenMultiplier>0</ns:powerOfTenMultiplier>
        <ns:uom>33</ns:uom>
    </ns:ReadingType>
</ns:Reading>"""

        return xml_template, energy_received

    def generate_summation_delivered_xml(self):
        """Generate XML for energy delivered (solar production)"""
        # Simulate solar panel production (only during day hours)
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 18:  # Daytime hours
            solar_factor = random.uniform(0.3, 0.8)  # Solar production varies
        else:
            solar_factor = 0  # No solar at night

        energy_delivered = self.base_energy_delivered + \
            int(solar_factor * 1000)

        xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<ns:Reading xmlns:ns="urn:ieee:std:2030.5:ns">
    <ns:value>{energy_delivered}</ns:value>
    <ns:quality>0</ns:quality>
    <ns:timeStamp>{int(time.time())}</ns:timeStamp>
    <ns:timePeriod>
        <ns:duration>2592000</ns:duration>
        <ns:start>{int(self.billing_start.timestamp())}</ns:start>
    </ns:timePeriod>
    <ns:touTier>1</ns:touTier>
    <ns:ReadingType>
        <ns:accumulationBehaviour>1</ns:accumulationBehaviour>
        <ns:commodity>1</ns:commodity>
        <ns:dataQualifier>0</ns:dataQualifier>
        <ns:flowDirection>1</ns:flowDirection>
        <ns:intervalLength>0</ns:intervalLength>
        <ns:kind>2</ns:kind>
        <ns:powerOfTenMultiplier>0</ns:powerOfTenMultiplier>
        <ns:uom>33</ns:uom>
    </ns:ReadingType>
</ns:Reading>"""

        return xml_template, energy_delivered

    def publish_data(self):
        """Publish simulated meter data to MQTT topics"""
        if not self.connected or not self.client:
            logger.error("Not connected to MQTT broker")
            return

        # Get current timestamp for display
        current_time = datetime.now().strftime("%H:%M:%S")

        print(f"\n{'='*60}")
        print(f"📊 SIMULATED METER DATA - {current_time}")
        print(f"{'='*60}")

        # Generate and publish Instantaneous Demand
        xml_demand, power_value = self.generate_instantaneous_demand_xml()
        topic_demand = "homeassistant/sensor/xcel_itron_5/Instantaneous_Demand/state"
        self.client.publish(topic_demand, str(power_value))
        print(f"⚡ POWER USAGE:")
        print(f"   Current Demand: {power_value:>6} W")
        print(f"   Topic: {topic_demand}")
        print()

        # Generate and publish Current Summation Received
        xml_received, energy_received = self.generate_summation_received_xml()
        topic_received = "homeassistant/sensor/xcel_itron_5/Current_Summation_Received/state"
        self.client.publish(topic_received, str(energy_received))
        print(f"🔌 ENERGY CONSUMPTION:")
        print(f"   Total Received: {energy_received:>8} Wh")
        print(f"   Converted:      {energy_received/1000:>8.3f} kWh")
        print(f"   Topic: {topic_received}")
        print()

        # Generate and publish Current Summation Delivered
        xml_delivered, energy_delivered = self.generate_summation_delivered_xml()
        topic_delivered = "homeassistant/sensor/xcel_itron_5/Current_Summation_Delivered/state"
        self.client.publish(topic_delivered, str(energy_delivered))
        print(f"☀️  SOLAR PRODUCTION:")
        print(f"   Total Delivered: {energy_delivered:>8} Wh")
        print(f"   Converted:       {energy_delivered/1000:>8.3f} kWh")
        print(f"   Topic: {topic_delivered}")
        print()

        # Calculate net energy (consumption - production)
        net_energy = energy_received - energy_delivered
        print(f"📈 NET ENERGY:")
        print(f"   Net Consumption: {net_energy:>8} Wh")
        print(f"   Net Converted:   {net_energy/1000:>8.3f} kWh")
        print(f"{'='*60}")

        # Update base values for next iteration
        self.base_energy_received = energy_received
        self.base_energy_delivered = energy_delivered
        self.base_power_demand = power_value

    def start(self):
        """Start the simulated meter"""
        print("\n" + "="*70)
        print("🚀 STARTING SIMULATED XCEL SMART METER")
        print("="*70)
        print("📡 Connecting to MQTT broker...")

        # Setup and connect
        self.setup_client()
        if not self.connect():
            return False

        # Start the loop
        if self.client:
            self.client.loop_start()

        print("✅ Connected successfully!")
        print("📊 Publishing simulated meter data every 5 seconds...")
        print("⏹️  Press Ctrl+C to stop")
        print("="*70)
        print()

        return True

    def stop(self):
        """Stop the simulated meter"""
        if self.client:
            logger.info("Stopping Simulated Meter...")
            self.client.loop_stop()
            self.client.disconnect()


def main():
    """Main function to run the simulated meter"""
    # Get MQTT configuration from environment variables
    mqtt_server = os.getenv('MQTT_SERVER', 'localhost')
    mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
    mqtt_user = os.getenv('MQTT_USER')
    mqtt_password = os.getenv('MQTT_PASSWORD')

    print(f"🔧 MQTT Configuration:")
    print(f"   Server: {mqtt_server}:{mqtt_port}")
    print(f"   User: {mqtt_user or 'None'}")
    print()

    # Create and start simulated meter
    meter = SimulatedMeter(
        mqtt_server=mqtt_server,
        mqtt_port=mqtt_port,
        mqtt_user=mqtt_user,
        mqtt_password=mqtt_password
    )

    try:
        if meter.start():
            # Publish data every 5 seconds (matching real meter polling rate)
            while True:
                meter.publish_data()
                time.sleep(5)
        else:
            print("\n❌ Failed to start simulated meter")
            return 1
    except KeyboardInterrupt:
        print("\n\n🛑 STOPPING SIMULATED METER...")
        print("📊 Final data published. Shutting down gracefully.")
    except Exception as e:
        print(f"\n❌ Error in simulated meter: {e}")
        return 1
    finally:
        meter.stop()

    print("\n✅ Simulated meter stopped successfully.")
    return 0


if __name__ == "__main__":
    exit(main())
