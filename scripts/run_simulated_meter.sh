#!/bin/bash

# Simulated Xcel Meter Data Generator Runner
# This script runs the simulated meter to generate test data

echo "Starting Simulated Xcel Smart Meter Data Generator"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "xcel_itron2mqtt/simulated_meter.py" ]; then
    echo "Error: simulated_meter.py not found"
    echo "   Please run this script from the project root directory"
    exit 1
fi

# Set default MQTT settings if not provided
# Use localhost when running outside Docker, mqtt when inside Docker
export MQTT_SERVER=${MQTT_SERVER:-localhost}
export MQTT_PORT=${MQTT_PORT:-1883}

echo "MQTT Server: $MQTT_SERVER:$MQTT_PORT"
echo "MQTT User: ${MQTT_USER:-None}"
echo "=================================================="

# Run the simulated meter
cd xcel_itron2mqtt
python3 simulated_meter.py 