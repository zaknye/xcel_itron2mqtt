# MQTT to Home Assistant Integration Guide

## **Overview**

This document explains how the Xcel Itron2MQTT application automatically creates sensors in Home Assistant using the **MQTT Discovery** protocol. This integration enables seamless monitoring of your Xcel smart meter data without any manual Home Assistant configuration.

## **How MQTT Discovery Works**

### **Home Assistant MQTT Discovery Protocol**

Home Assistant supports automatic device discovery through MQTT using a specific topic structure and JSON payload format. The Xcel Itron2MQTT application leverages this protocol to automatically register sensors with Home Assistant.

### **Two-Phase Integration Process**

#### **Phase 1: Configuration Messages (One-time Setup)**

When the application starts, it sends **configuration messages** to Home Assistant that define what sensors should be created. These messages are sent to specific MQTT topics with JSON payloads containing sensor definitions.

**Configuration Message Example:**

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

#### **Phase 2: State Messages (Continuous Updates)**

After sensors are created, the application continuously sends **state messages** with actual meter readings to the corresponding state topics.

**State Message Example:**

```
1234
```

_(Simple numeric value representing power in Watts)_

## **MQTT Topic Structure**

### **Topic Format**

The application uses this hierarchical topic structure for Home Assistant discovery:

```
homeassistant/{entity_type}/{device_name}/{sensor_name}/{config|state}
```

### **Configuration Topics**

These topics receive the sensor configuration messages:

- `homeassistant/sensor/xcel_itron_5/Instantaneous_Demand/config`
- `homeassistant/sensor/xcel_itron_5/Current_Summation_Received/config`
- `homeassistant/sensor/xcel_itron_5/Current_Summation_Delivered/config`

### **State Topics**

These topics receive the actual sensor data:

- `homeassistant/sensor/xcel_itron_5/Instantaneous_Demand/state`
- `homeassistant/sensor/xcel_itron_5/Current_Summation_Received/state`
- `homeassistant/sensor/xcel_itron_5/Current_Summation_Delivered/state`

### **Device Information Topic**

- `homeassistant/device/energy/xcel_itron_5`

## **Automatically Created Sensors**

### **Power Sensors**

#### **Instantaneous Demand**

- **Purpose**: Real-time power usage monitoring
- **Device Class**: `power`
- **Unit**: `W` (Watts)
- **Update Frequency**: Every 5 seconds
- **Use Case**: Monitor current power consumption

### **Energy Sensors**

#### **Current Summation Received**

- **Purpose**: Total energy received from the grid
- **Device Class**: `energy`
- **Unit**: `Wh` (Watt-hours)
- **State Class**: `total`
- **Use Case**: Track total energy consumption over time

#### **Current Summation Delivered**

- **Purpose**: Total energy delivered back to the grid
- **Device Class**: `energy`
- **Unit**: `Wh` (Watt-hours)
- **State Class**: `total`
- **Use Case**: Monitor solar panel energy production

### **Time Period Sensors**

#### **Duration**

- **Purpose**: Billing period duration
- **Device Class**: `duration`
- **Unit**: `s` (seconds)
- **Use Case**: Track billing cycle duration

#### **Start Time**

- **Purpose**: Billing period start timestamp
- **Device Class**: `timestamp`
- **Use Case**: Monitor billing cycle start times

### **Time-of-Use (TOU) Sensors**

#### **TOU Tier**

- **Purpose**: Current pricing tier information
- **Device Class**: `sensor`
- **Use Case**: Monitor time-of-use pricing periods

## **Device Information Integration**

### **Device Entity Creation**

The application creates a **device entity** in Home Assistant that groups all the sensors together:

```json
{
  "name": "Xcel Itron 5",
  "device_class": "energy",
  "state_topic": "homeassistant/device/energy/xcel_itron_5",
  "unique_id": "1234567890123456789012345678901234567890",
  "device": {
    "identifiers": ["1234567890123456789012345678901234567890"],
    "name": "Xcel Itron 5",
    "model": "Itron",
    "sw_version": "3.2.39"
  }
}
```

### **Device Information Sources**

- **Name**: Set to "Xcel Itron 5"
- **Model**: Extracted from meter hardware info (`mfID`)
- **Software Version**: Extracted from meter firmware (`swVer`)
- **Unique ID**: LFDI (Logical Field Device Identifier) from meter

## **Configuration from YAML Files**

### **Endpoint Configuration**

Sensor configurations are defined in YAML files (`endpoints_default.yaml` and `endpoints_3_2_39.yaml`):

```yaml
- Instantaneous Demand:
    url: "/upt/1/mr/1/r"
    tags:
      value:
        entity_type: sensor
        device_class: power
        unit_of_measurement: W
```

### **Automatic Configuration Generation**

The YAML configuration automatically generates:

- **Sensor Name**: "Xcel Itron 5 Instantaneous Demand"
- **Device Class**: `power`
- **Unit of Measurement**: `W`
- **State Topic**: `homeassistant/sensor/xcel_itron_5/Instantaneous_Demand/state`
- **Unique ID**: `xcel_itron_5_instantaneous_demand_instantaneous_demand`

## **Retention and Persistence**

### **Message Retention Settings**

- **Configuration Messages**: Sent with `retain=True`

  - Ensures Home Assistant receives configuration even if it starts after the application
  - Persists across Home Assistant restarts
  - Allows for automatic sensor recreation

- **State Messages**: Sent with `retain=False`
  - Real-time data is not retained
  - Prevents old data from being displayed after restarts
  - Maintains current state accuracy

### **Unique ID Persistence**

- **Unique IDs**: Generated based on device name and sensor name
- **Persistence**: Sensors maintain their entity IDs across Home Assistant restarts
- **Avoidance**: Prevents duplicate sensor creation

## **Home Assistant Integration Benefits**

### **Automatic Sensor Creation**

Once the application is running, sensors automatically appear in Home Assistant with:

- **Proper device classes** for correct UI representation
- **Units of measurement** for proper formatting
- **Historical data tracking** for energy sensors
- **Device grouping** for organization
- **Automatic entity IDs** for scripting and automation

### **Real-time Updates**

The sensors receive continuous updates every 5 seconds:

- **Power readings** update in real-time
- **Energy totals** accumulate over time
- **Time periods** update with billing cycles
- **TOU tiers** change based on time-of-use pricing

### **Home Assistant Features**

#### **Dashboard Integration**

- Sensors automatically appear in Home Assistant dashboards
- Proper icons and units are displayed
- Historical graphs are available for energy sensors

#### **Automation Support**

- Sensors can be used in Home Assistant automations
- Entity IDs are automatically generated
- State changes can trigger automations

#### **Scripting Support**

- Sensors can be referenced in Home Assistant scripts
- Current values can be accessed via templates
- Historical data is available for analysis

## **Troubleshooting**

### **Common Issues**

#### **Sensors Not Appearing**

1. Check MQTT connection status
2. Verify configuration messages are being sent
3. Check Home Assistant MQTT integration is enabled
4. Review logs for MQTT errors

#### **Sensors Not Updating**

1. Verify state messages are being sent
2. Check MQTT topic structure
3. Review application logs for errors
4. Confirm meter connectivity

#### **Duplicate Sensors**

1. Check unique ID generation
2. Verify device identifiers
3. Clear retained MQTT messages if needed
4. Restart Home Assistant if necessary

### **Debugging Steps**

1. **Enable Debug Logging**

   ```bash
   LOGLEVEL=DEBUG
   ```

2. **Check MQTT Topics**

   - Use MQTT client to monitor topics
   - Verify configuration messages are sent
   - Check state message frequency

3. **Review Home Assistant Logs**
   - Check for MQTT integration errors
   - Verify sensor discovery messages
   - Monitor entity creation

## **Advanced Configuration**

### **Custom Topic Prefix**

You can customize the MQTT topic prefix:

```bash
MQTT_TOPIC_PREFIX=custom/prefix/
```

### **Custom Sensor Names**

Modify the YAML configuration to change sensor names:

```yaml
- Custom Power Sensor:
    url: "/upt/1/mr/1/r"
    tags:
      value:
        entity_type: sensor
        device_class: power
        unit_of_measurement: W
```

### **Additional Sensor Types**

Add new sensor types by extending the YAML configuration:

```yaml
- New Sensor Type:
    url: "/custom/endpoint"
    tags:
      custom_value:
        entity_type: sensor
        device_class: measurement
        unit_of_measurement: custom_unit
```

## **Integration Examples**

### **Home Assistant Automation Example**

```yaml
automation:
  - alias: "High Power Usage Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.xcel_itron_5_instantaneous_demand
      above: 5000
    action:
      - service: notify.mobile_app
        data:
          message: "High power usage detected: {{ states('sensor.xcel_itron_5_instantaneous_demand') }}W"
```

### **Dashboard Configuration**

```yaml
# Example dashboard card configuration
type: entities
title: Energy Monitoring
entities:
  - entity: sensor.xcel_itron_5_instantaneous_demand
    name: Current Power Usage
  - entity: sensor.xcel_itron_5_current_summation_received
    name: Total Energy Consumed
  - entity: sensor.xcel_itron_5_current_summation_delivered
    name: Total Energy Produced
```

This MQTT to Home Assistant integration provides a seamless way to monitor your Xcel smart meter data with full Home Assistant functionality, including dashboards, automations, and historical tracking.
