# Xcel Itron2MQTT - Repository Explanation

## **Overview**

This repository contains a Python application that bridges **Xcel Energy smart meters** with clinet applications (Home Assistant or any other MQTT compatible clients).

The application connects to your smart meter through **Energy Launch Pad** (a feature available in your Xcel Energy customer account) and converts real-time meter readings into **MQTT messages**.

The MQTT messages can then be consumed with MQTT-compatible Client applications such Home Assistant or other tools (e.g Grafana using Telegraph and InfluxDB) to provide real time insights on energy usage patterns.

### **What it does:**

1. Energy Launchpad —— a tile within Xcel energy account, **Discovers your smart meter** on your local network ( WiFi) using mDNS (multicast DNS) and **Establishes a secure connection** to the meter using TLS certificates (According to EEE2030.5 protocol).

2. The main python application under `xcel_itron2mqtt` **Queries the meter** for real-time energy data (power usage, energy consumption, etc.) and **Converts the queried data** into MQTT messages which are then sent to **MQTT topics** where **MQTT Subscribers of a topic** will get the message/data.

3. The application also **Automatically creates sensors** in Home Assistant for easy monitoring using **Home Assistant's MQTT Discovery protocol** ([see MQTT to Home Assistant Integration Guide](mqtt2HomeAssistant.md)).

## **Key Components:**

### **Main Application (`xcel_itron2mqtt/`)**

- **`main.py`**: Entry point that discovers the meter and initializes the connection
- **`xcelMeter.py`**: Core class that handles meter communication and MQTT setup
- **`xcelEndpoint.py`**: Handles individual data endpoints from the meter (power, energy, etc.)

### **Configuration (`configs/`)**

- **`endpoints_default.yaml`**: Defines what data to read from the meter (power usage, energy consumption, time periods)
- **`endpoints_3_2_39.yaml`**: Alternative configuration for specific meter firmware versions

### **Security (`scripts/`)**

- **`generate_keys.sh`**: Creates the SSL certificates needed to authenticate with your meter
- Generates the LFDI (Logical Field Device Identifier) string you need to register with Xcel

## **Smart Meter Data Format**

### **XML Response Structure**

The smart meters communicate using XML responses following the IEEE 2030.5 standard. All XML elements are prefixed with the namespace `{urn:ieee:std:2030.5:ns}`.

#### **Example XML Response from Hardware Info Endpoint (`/sdev/sdi`):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ns:DeviceInformation xmlns:ns="urn:ieee:std:2030.5:ns">
    <ns:lFDI>1234567890123456789012345678901234567890</ns:lFDI>
    <ns:swVer>3.2.39</ns:swVer>
    <ns:mfID>Itron</ns:mfID>
    <ns:deviceCategory>1</ns:deviceCategory>
    <ns:deviceInformationLink>https://192.168.1.100:8081/sdev/sdi</ns:deviceInformationLink>
</ns:DeviceInformation>
```

#### **Example XML Response from Instantaneous Demand Endpoint (`/upt/1/mr/1/r`):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ns:Reading xmlns:ns="urn:ieee:std:2030.5:ns">
    <ns:value>1234</ns:value>
    <ns:quality>0</ns:quality>
    <ns:timeStamp>1234567890</ns:timeStamp>
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
</ns:Reading>
```

#### **Example XML Response from Current Summation Endpoint (`/upt/1/mr/2/rs/1/r/1`):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ns:Reading xmlns:ns="urn:ieee:std:2030.5:ns">
    <ns:value>12345678</ns:value>
    <ns:quality>0</ns:quality>
    <ns:timeStamp>1234567890</ns:timeStamp>
    <ns:timePeriod>
        <ns:duration>3600</ns:duration>
        <ns:start>1234567890</ns:start>
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
</ns:Reading>
```

### **Data Parsing**

The application parses these XML responses by:

1. **Extracting specific elements** based on the configuration in `endpoints_*.yaml`
2. **Converting to structured data** using the `parse_response()` method in `xcelEndpoint.py`
3. **Mapping to MQTT topics** for Home Assistant integration

## **MQTT Implementation**

### **MQTT Client Setup**

The application uses the **paho-mqtt** library to establish a connection to the MQTT broker:

```python
client = mqtt.Client()
if mqtt_username and mqtt_password:
    client.username_pw_set(mqtt_username, mqtt_password)
client.on_connect = on_connect
client.connect(mqtt_server_address, mqtt_port)
client.loop_start()
```

#### **MQTT Credentials Storage**

The MQTT username and password are retrieved from **environment variables**:

```python
mqtt_username = os.getenv('MQTT_USER')
mqtt_password = os.getenv('MQTT_PASSWORD')
```

**Credential Sources:**

1. **Environment Variables**: Set via Docker environment variables or system environment
2. **Docker Compose**: Defined in the `environment` section or loaded from `.env` file
3. **Optional Authentication**: If no credentials are provided, the application connects without authentication

**Example Docker environment setup:**

```yaml
environment:
  - MQTT_USER=your_mqtt_username
  - MQTT_PASSWORD=your_mqtt_password
  - MQTT_SERVER=mqtt_broker_ip
  - MQTT_PORT=1883
```

### **MQTT Topics Structure**

The application uses a hierarchical topic structure following Home Assistant's MQTT discovery format:

#### **Topic Prefix**

- **Default**: `homeassistant/`
- **Configurable**: via `MQTT_TOPIC_PREFIX` environment variable

#### **Topic Format**

```
{prefix}{entity_type}/{device_name}/{sensor_name}/{config|state}
```

#### **Example Topics**

**Configuration Topics (for Home Assistant discovery):**

- `homeassistant/sensor/xcel_itron_5/Instantaneous_Demand/config`
- `homeassistant/sensor/xcel_itron_5/Current_Summation_Received/config`
- `homeassistant/sensor/xcel_itron_5/Current_Summation_Delivered/config`

**State Topics (for actual data):**

- `homeassistant/sensor/xcel_itron_5/Instantaneous_Demand/state`
- `homeassistant/sensor/xcel_itron_5/Current_Summation_Received/state`
- `homeassistant/sensor/xcel_itron_5/Current_Summation_Delivered/state`

**Device Information Topic:**

- `homeassistant/device/energy/xcel_itron_5`

### **MQTT Publishers**

The application acts as a **publisher-only** MQTT client. It publishes to two types of topics:

1. **Configuration Messages**: Sent once during setup to register sensors with Home Assistant
2. **State Messages**: Sent continuously with real-time meter readings

#### **Publisher Implementation**

```python
def mqtt_publish(self, topic: str, message: str, retain=False) -> int:
    result = self.client.publish(topic, str(message), retain=retain)
    return result[0]
```

### **MQTT Subscribers**

**There are no MQTT subscribers in this application.** The application is designed as a one-way data bridge from the smart meter to MQTT. The only consumers of the MQTT messages are:

1. **Home Assistant**: Automatically discovers and creates sensors from the configuration messages
2. **Other MQTT clients**: Can subscribe to the state topics to receive real-time meter data

### **MQTT QoS (Quality of Service)**

**Current Implementation:**

- **QoS Level**: **0 (At most once)** - Default QoS level used by paho-mqtt
- **No explicit QoS configuration** in the code
- **No QoS parameter** passed to `client.publish()`

**Implications:**

- Messages are delivered **at most once**
- No guarantee of delivery
- No acknowledgment from the broker
- **Fire-and-forget** approach

**Retention Settings:**

- **Configuration messages**: `retain=True` - Ensures Home Assistant receives the configuration even if it starts after the application
- **State messages**: `retain=False` - Real-time data is not retained

### **MQTT Message Examples**

#### **Configuration Message Example:**

```json
{
  "name": "Xcel Itron 5 Instantaneous Demand",
  "device_class": "power",
  "unit_of_measurement": "W",
  "state_topic": "homeassistant/sensor/xcel_itron_5/Instantaneous_Demand/state",
  "unique_id": "xcel_itron_5_instantaneous_demand_instantaneous_demand",
  "device": {
    "identifiers": ["1234567890123456789012345678901234567890"],
    "name": "Xcel Itron 5",
    "model": "Itron",
    "sw_version": "3.2.39"
  }
}
```

#### **State Message Example:**

```
1234
```

_(Simple numeric value representing power in Watts)_

## **How it works:**

### **Setup Phase:**

1. Generate SSL certificates using the script
2. Register the LFDI with Xcel Energy's Launchpad
3. Configure your meter to join your network

### **Discovery:**

1. Uses mDNS to find your meter's IP address automatically
2. Establishes a secure TLS connection using your certificates

### **Data Collection:**

1. Queries multiple endpoints on the meter for different types of data
2. Parses XML responses from the meter
3. Converts readings into structured data

### **MQTT Publishing:**

1. Sends Home Assistant discovery messages to automatically create sensors
2. Publishes real-time data updates to MQTT topics
3. Supports different sensor types (power, energy, timestamps)

## **Data Types Collected:**

- **Instantaneous Demand**: Real-time power usage (Watts)
- **Current Summation Received**: Total energy received (Wh)
- **Current Summation Delivered**: Total energy delivered (Wh)
- **Time Periods**: Duration and start times for billing periods
- **TOU Tiers**: Time-of-Use pricing tier information

## **Shell Scripts and Environment Configuration**

### **run.sh Script**

The `run.sh` script serves as the **entry point** for the Docker container:

```bash
#!/bin/sh
python3 -Wignore main.py
```

**Purpose:**

- **Container entrypoint**: Called when the Docker container starts
- **Python execution**: Runs the main application with warning suppression
- **Simple wrapper**: Provides a clean interface for container execution

### **Environment Variables (.env file)**

The application uses environment variables for configuration. You need to create a `.env` file based on the expected structure:

**Required .env file structure:**

```bash
# MQTT Configuration
MQTT_SERVER=your_mqtt_broker_ip
MQTT_PORT=1883
MQTT_USER=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password
MQTT_TOPIC_PREFIX=homeassistant/

# Meter Configuration (optional - auto-discovery if not set)
METER_IP=your_meter_ip
METER_PORT=8081

# Certificate Paths (optional - defaults to certs/.cert.pem and certs/.key.pem)
CERT_PATH=/opt/xcel_itron2mqtt/certs/.cert.pem
KEY_PATH=/opt/xcel_itron2mqtt/certs/.key.pem

# Logging
LOGLEVEL=INFO
```

**Environment Variable Sources:**

1. **Docker Compose**: Loaded from `.env` file via `env_file: - .env`
2. **Docker CLI**: Passed via `-e` flags
3. **System Environment**: Set in the host system
4. **Container Environment**: Defined in Dockerfile or docker-compose.yaml

**Security Note:**

- The `.env` file is **gitignored** to prevent committing sensitive credentials
- Certificates are stored in the `certs/` directory (also gitignored)
- Always use secure passwords and consider using Docker secrets for production

### **generate_keys.sh Script**

The `generate_keys.sh` script creates SSL certificates for meter authentication:

**Key Functions:**

- **Certificate Generation**: Creates TLS 1.2 certificates with specific parameters
- **LFDI Generation**: Extracts the Logical Field Device Identifier for Xcel registration
- **Certificate Storage**: Saves certificates to `certs/.cert.pem` and `certs/.key.pem`

**Usage:**

```bash
# Generate new certificates
./scripts/generate_keys.sh

# Print existing LFDI
./scripts/generate_keys.sh -p
```

## **Deployment Options:**

1. **Docker Compose** (Recommended): Easy setup with included MQTT broker
2. **Docker CLI**: Manual container management
3. **Development**: Direct Python execution for development/testing

This is essentially a **bridge application** that makes your Xcel smart meter data accessible to your home automation system, allowing you to monitor your energy usage in real-time and integrate it with other smart home devices and automations.
