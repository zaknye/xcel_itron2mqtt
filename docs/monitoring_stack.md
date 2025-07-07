# Xcel Energy Monitoring Stack

## **Overview**

This monitoring stack provides a complete real-time energy monitoring solution using simulated Xcel smart meter data. The stack includes:

- **MQTT Broker** (Mosquitto) - Message routing
- **InfluxDB** - Time-series data storage
- **Telegraf** - Data collection from MQTT
- **Grafana** - Real-time visualization dashboard
- **Simulated Meter** - Test data generator

## **Architecture**

```
Simulated Meter → MQTT Broker → Telegraf → InfluxDB → Grafana
```

### **Data Flow**

1. **Simulated Meter** generates realistic energy data every 5 seconds
2. **MQTT Broker** receives and routes messages to subscribers
3. **Telegraf** collects data from MQTT topics and sends to InfluxDB
4. **InfluxDB** stores time-series data for historical analysis
5. **Grafana** visualizes real-time and historical data

## **Quick Start**

### **1. Start the Monitoring Stack**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### **2. Access the Dashboard**

- **Grafana**: http://localhost:3000

  - Username: `admin`
  - Password: `admin`
  - Dashboard: "Xcel Energy Monitoring Dashboard"

- **InfluxDB**: http://localhost:8086
  - Username: `admin`
  - Password: `adminpassword`
  - Organization: `myorg`
  - Bucket: `energy_data`

### **3. Test Data Generation**

The simulated meter automatically starts and generates data. You can also run it manually:

```bash
# Run simulated meter locally
./scripts/run_simulated_meter.sh

# Or run the MQTT subscriber to see data
./scripts/run_subscriber.sh
```

## **Services Configuration**

### **MQTT Broker (Mosquitto)**

- **Port**: 1883 (MQTT), 9001 (WebSocket)
- **Configuration**: `mosquitto/config/mosquitto.conf`
- **Features**: Anonymous access, persistence, logging

### **InfluxDB**

- **Port**: 8086
- **Database**: Time-series database
- **Organization**: `myorg`
- **Bucket**: `energy_data`
- **Token**: `my-super-secret-auth-token`

### **Telegraf**

- **Configuration**: `telegraf/telegraf.conf`
- **Input**: MQTT topics
- **Output**: InfluxDB
- **Collection Interval**: 10 seconds

### **Grafana**

- **Port**: 3000
- **Admin**: admin/admin
- **Datasource**: InfluxDB (auto-configured)
- **Dashboard**: Auto-loaded energy monitoring dashboard

## **Data Types**

### **Power Usage (Instantaneous Demand)**

- **Unit**: Watts (W)
- **Update Frequency**: Every 5 seconds
- **Pattern**: Realistic hourly usage patterns
- **Range**: 100-8000W

### **Energy Consumption (Summation Received)**

- **Unit**: Watt-hours (Wh)
- **Pattern**: Accumulating consumption over time
- **Use Case**: Total energy consumed from grid

### **Energy Production (Summation Delivered)**

- **Unit**: Watt-hours (Wh)
- **Pattern**: Solar production (daytime only)
- **Use Case**: Energy delivered back to grid

## **Dashboard Features**

### **Real-time Panels**

1. **Real-time Power Usage**

   - Live power consumption graph
   - Updates every 5 seconds
   - Shows current demand in Watts

2. **Energy Consumption**

   - Cumulative energy consumption over time
   - Historical tracking
   - kWh conversion

3. **Energy Production (Solar)**

   - Solar panel production simulation
   - Daytime-only production
   - Grid feedback tracking

4. **Hourly Power Usage**
   - Bar chart of hourly averages
   - Usage pattern analysis
   - Peak demand identification

### **Summary Panels**

1. **Current Power Usage**

   - Real-time power reading
   - Large display for monitoring

2. **Total Energy Consumed**

   - Cumulative consumption
   - kWh display

3. **Total Energy Produced**

   - Solar production total
   - kWh display

4. **Energy Self-Sufficiency**
   - Production vs consumption ratio
   - Percentage calculation

## **Simulated Data Patterns**

### **Hourly Usage Patterns**

The simulated meter generates realistic data based on typical household patterns:

- **Night (12 AM - 6 AM)**: Low usage (200-800W)
- **Morning (6 AM - 9 AM)**: Rising usage (800-2000W)
- **Day (9 AM - 5 PM)**: Medium usage (1000-3000W)
- **Evening (5 PM - 9 PM)**: Peak usage (2000-6000W)
- **Late Evening (9 PM - 12 AM)**: Declining usage (1000-3000W)

### **Solar Production Simulation**

- **Daytime (6 AM - 6 PM)**: Variable production (0-3000W)
- **Night**: No production (0W)
- **Weather Variation**: Random factors affect production

### **Energy Accumulation**

- **Consumption**: Gradually increases over time
- **Production**: Accumulates during daylight hours
- **Realistic Growth**: Simulates actual meter behavior

## **Customization**

### **Modify Data Patterns**

Edit `xcel_itron2mqtt/simulated_meter.py`:

```python
# Adjust hourly patterns
self.hourly_patterns = {
    0: 0.3,   # 3 AM - low usage
    1: 0.2,   # 4 AM - very low
    # ... customize patterns
}

# Modify base values
self.base_energy_received = 12345678  # Wh
self.base_power_demand = 2500          # W
```

### **Add New Metrics**

1. **Add to Telegraf config** (`telegraf/telegraf.conf`)
2. **Update simulated meter** to generate new data
3. **Create Grafana panels** for visualization

### **Modify Dashboard**

1. **Access Grafana** at http://localhost:3000
2. **Edit dashboard** or create new panels
3. **Export configuration** to `grafana/dashboards/`

## **Troubleshooting**

### **Common Issues**

#### **No Data in Grafana**

1. Check if simulated meter is running: `docker-compose ps`
2. Verify MQTT messages: `docker-compose logs simulated_meter`
3. Check Telegraf logs: `docker-compose logs telegraf`
4. Verify InfluxDB connection: `docker-compose logs influxdb`

#### **Dashboard Not Loading**

1. Check Grafana logs: `docker-compose logs grafana`
2. Verify datasource connection
3. Check InfluxDB token and organization

#### **MQTT Connection Issues**

1. Check Mosquitto logs: `docker-compose logs mqtt`
2. Verify network connectivity between containers
3. Check MQTT topic structure

### **Useful Commands**

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f simulated_meter
docker-compose logs -f telegraf
docker-compose logs -f grafana

# Restart specific service
docker-compose restart simulated_meter

# Access container shell
docker-compose exec grafana bash
docker-compose exec influxdb bash

# Check data in InfluxDB
docker-compose exec influxdb influx query 'from(bucket:"energy_data") |> range(start: -1h)'
```

## **Production Considerations**

### **Security**

- Enable MQTT authentication
- Use strong passwords
- Configure SSL/TLS
- Restrict network access

### **Performance**

- Adjust Telegraf collection intervals
- Optimize InfluxDB retention policies
- Monitor resource usage
- Scale services as needed

### **Monitoring**

- Add health checks
- Configure alerts
- Monitor disk space
- Set up backups

## **Next Steps**

1. **Replace simulated data** with real meter when available
2. **Add alerts** for high usage or anomalies
3. **Implement data retention** policies
4. **Add more metrics** (voltage, current, power factor)
5. **Create mobile dashboard** for remote monitoring

This monitoring stack provides a complete foundation for real-time energy monitoring and can be easily extended for production use with real smart meter data.
