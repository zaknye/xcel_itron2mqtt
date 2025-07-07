#!/bin/bash

# =============================================================================
# XCEL ITRON2MQTT - ENVIRONMENT SETUP SCRIPT
# =============================================================================
# This script helps you set up your .env file securely
# =============================================================================

set -e

echo "🔐 XCEL ITRON2MQTT - ENVIRONMENT SETUP"
echo "========================================"

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled. Your existing .env file is preserved."
        exit 1
    fi
fi

# Copy template to .env
if [ -f "env.template" ]; then
    cp env.template .env
    echo "✅ Created .env file from template"
else
    echo "❌ Error: env.template not found!"
    exit 1
fi

echo ""
echo "🔧 ENVIRONMENT VARIABLES SETUP"
echo "==============================="
echo ""

# Function to prompt for secure input
prompt_secure() {
    local var_name=$1
    local default_value=$2
    local description=$3
    
    echo "📝 $description"
    if [ -n "$default_value" ]; then
        echo "   Default: $default_value"
        read -p "   Enter new value (or press Enter to keep default): " value
        if [ -z "$value" ]; then
            value="$default_value"
        fi
    else
        read -s -p "   Enter value: " value
        echo
    fi
    
    # Update .env file
    sed -i.bak "s/^${var_name}=.*/${var_name}=${value}/" .env
    rm -f .env.bak
}

# Prompt for InfluxDB credentials
echo "🗄️  INFLUXDB CONFIGURATION"
echo "---------------------------"
prompt_secure "INFLUXDB_INIT_USERNAME" "admin" "InfluxDB admin username"
prompt_secure "INFLUXDB_INIT_PASSWORD" "adminpassword" "InfluxDB admin password"
prompt_secure "INFLUXDB_INIT_ORG" "myorg" "InfluxDB organization name"
prompt_secure "INFLUXDB_INIT_BUCKET" "energy_data" "InfluxDB bucket name"

# Generate a secure token for InfluxDB
echo "🔑 Generating secure InfluxDB admin token..."
INFLUXDB_TOKEN=$(openssl rand -hex 32)
sed -i.bak "s/^INFLUXDB_INIT_ADMIN_TOKEN=.*/INFLUXDB_INIT_ADMIN_TOKEN=${INFLUXDB_TOKEN}/" .env
rm -f .env.bak
echo "   ✅ Generated secure token"

echo ""
echo "📊 GRAFANA CONFIGURATION"
echo "------------------------"
prompt_secure "GRAFANA_ADMIN_USER" "admin" "Grafana admin username"
prompt_secure "GRAFANA_ADMIN_PASSWORD" "admin" "Grafana admin password"

echo ""
echo "📡 MQTT CONFIGURATION"
echo "---------------------"
prompt_secure "MQTT_SERVER" "mqtt" "MQTT server hostname"
prompt_secure "MQTT_PORT" "1883" "MQTT server port"
echo "   Note: MQTT_USER and MQTT_PASSWORD are optional (leave empty for no auth)"

echo ""
echo "⚙️  APPLICATION CONFIGURATION"
echo "----------------------------"
prompt_secure "METER_PORT" "8081" "Meter communication port"
prompt_secure "LOGLEVEL" "INFO" "Logging level (DEBUG, INFO, WARNING, ERROR)"

echo ""
echo "✅ ENVIRONMENT SETUP COMPLETE!"
echo "=============================="
echo ""
echo "🔒 Security Notes:"
echo "   • Your .env file contains sensitive data"
echo "   • It's already in .gitignore and won't be committed"
echo "   • Change default passwords in production"
echo "   • Consider using a secrets manager for production"
echo ""
echo "🚀 Next Steps:"
echo "   1. Review your .env file: cat .env"
echo "   2. Start the stack: docker-compose up -d"
echo "   3. Access Grafana: http://localhost:3000"
echo "   4. Access InfluxDB: http://localhost:8086"
echo ""
echo "📚 For more information, see the README.md" 