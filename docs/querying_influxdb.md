# Querying Data in InfluxDB (FluxDB)

This guide explains how to query your energy monitoring data stored in InfluxDB using the web UI, CLI, and API. All examples are tailored for the Xcel Energy Monitoring Stack.

---

## **1. Using the InfluxDB Web UI (Recommended)**

1. **Open your browser and go to:**
   - [http://localhost:8086](http://localhost:8086)
2. **Log in** with your credentials (default: `admin` / `adminpassword`).
3. **Go to the Data Explorer** (left sidebar).
4. **Select your bucket:**
   - `energy_data`
5. **Build a query** using the UI or enter a Flux query, for example:

   ```flux
   from(bucket: "energy_data")
     |> range(start: -1h)
   ```

6. **Click Submit**. You should see a table or graph with your data.

---

## **2. Using the Influx CLI (in the Docker Container)**

You can run queries directly from the InfluxDB container shell.

### **A. Open a shell in the InfluxDB container:**

```bash
docker-compose exec influxdb bash
```

### **B. Run a Flux query:**

```bash
influx query 'from(bucket:"energy_data") |> range(start: -1h)'
```

### **C. Example: Get the last 10 power usage points**

```bash
influx query 'from(bucket:"energy_data") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "power_usage") |> limit(n:10)'
```

---

## **3. Using the InfluxDB HTTP API**

You can query InfluxDB using its REST API (useful for scripts or external tools).

### **A. Example cURL Query:**

```bash
curl -XPOST "http://localhost:8086/api/v2/query?org=myorg" \
  -H "Authorization: Token my-super-secret-auth-token" \
  -H 'Accept:application/csv' \
  -H 'Content-type:application/vnd.flux' \
  -d 'from(bucket:"energy_data") |> range(start: -1h)'
```

### **B. Example: Query for Energy Consumption**

```bash
curl -XPOST "http://localhost:8086/api/v2/query?org=myorg" \
  -H "Authorization: Token my-super-secret-auth-token" \
  -H 'Accept:application/csv' \
  -H 'Content-type:application/vnd.flux' \
  -d 'from(bucket:"energy_data") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "energy_consumption")'
```

---

## **4. Example Flux Queries for Energy Monitoring**

### **A. Real-time Power Usage (last hour)**

```flux
from(bucket: "energy_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "power_usage")
```

### **B. Energy Consumption (last 24 hours)**

```flux
from(bucket: "energy_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "energy_consumption")
```

### **C. Energy Production (last 24 hours)**

```flux
from(bucket: "energy_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "energy_production")
```

### **D. Hourly Average Power Usage (last 24 hours)**

```flux
from(bucket: "energy_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "power_usage")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> yield(name: "mean")
```

---

## **5. Troubleshooting**

- **No data?**
  - Make sure your simulated meter and Telegraf are running.
  - Check the bucket name and organization in your queries.
  - Use the Data Explorer in the web UI to visually confirm data.
- **See errors?**
  - Check container logs: `docker-compose logs influxdb` and `docker-compose logs telegraf`
  - Make sure your API token and org are correct for API queries.

---

## **6. More Resources**

- [InfluxDB Flux Query Language Docs](https://docs.influxdata.com/influxdb/latest/query-data/flux/)
- [InfluxDB API Reference](https://docs.influxdata.com/influxdb/latest/api-guide/)
- [InfluxDB Data Explorer Guide](https://docs.influxdata.com/influxdb/latest/ui/data-explorer/)

---

This guide should help you quickly verify and explore your energy data in InfluxDB!
