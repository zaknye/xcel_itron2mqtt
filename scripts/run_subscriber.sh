#!/bin/bash

# Xcel Meter MQTT Subscriber Runner
# This script runs the MQTT subscriber to listen to Xcel meter data

echo "Meter MQTT Subscriber"
echo "================================"

# Check if we're in the right directory
if [ ! -f "xcel_itron2mqtt/mqtt_subscriber.py" ]; then
    echo "Error: mqtt_subscriber.py not found"
    echo "   Please run this script from the project root directory"
    exit 1
fi

# Set default MQTT settings if not provided
export MQTT_SERVER=${MQTT_SERVER:-localhost}
export MQTT_PORT=${MQTT_PORT:-1883}

echo "MQTT Server: $MQTT_SERVER:$MQTT_PORT"
echo "MQTT User: ${MQTT_USER:-None}"
echo "================================"

# Run the subscriber
cd xcel_itron2mqtt
python3 run_subscriber.py 