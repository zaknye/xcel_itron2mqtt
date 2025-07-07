#!/usr/bin/env python3
"""
Simple script to run the MQTT subscriber for testing Xcel meter data.
This will listen to the MQTT topics and print received data to the screen.
"""

import os
import sys
from mqtt_subscriber import MQTTSubscriber


def main():
    """Run the MQTT subscriber"""
    print("🔌 Xcel Meter MQTT Subscriber")
    print("=" * 40)

    # Get MQTT configuration
    mqtt_server = os.getenv('MQTT_SERVER', 'localhost')
    mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
    mqtt_user = os.getenv('MQTT_USER')
    mqtt_password = os.getenv('MQTT_PASSWORD')

    print(f"MQTT Server: {mqtt_server}:{mqtt_port}")
    print(f"MQTT User: {mqtt_user or 'None'}")
    print("=" * 40)

    # Create subscriber
    subscriber = MQTTSubscriber(
        mqtt_server=mqtt_server,
        mqtt_port=mqtt_port,
        mqtt_user=mqtt_user,
        mqtt_password=mqtt_password
    )

    try:
        if subscriber.start():
            print("✅ Subscriber started successfully!")
            print("📡 Listening for messages...")
            print("   Press Ctrl+C to stop")

            # Keep running
            while True:
                import time
                time.sleep(1)
        else:
            print("❌ Failed to start subscriber")
            return 1

    except KeyboardInterrupt:
        print("\n🛑 Stopping subscriber...")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        subscriber.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
