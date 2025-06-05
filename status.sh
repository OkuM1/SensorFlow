#!/bin/bash
# SensorFlow Status Check Script

echo "🔍 SensorFlow System Status"
echo "=========================="

# Check Docker containers
echo "📦 Docker Containers:"
docker-compose ps

echo ""
echo "🌐 Service Health Checks:"

# Check API
echo -n "   API (Port 8000): "
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Running"
else
    echo "❌ Not responding"
fi

# Check InfluxDB
echo -n "   InfluxDB (Port 8086): "
if curl -s http://localhost:8086/health > /dev/null; then
    echo "✅ Running"
else
    echo "❌ Not responding"
fi

# Check Grafana
echo -n "   Grafana (Port 3000): "
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Running"
else
    echo "❌ Not responding"
fi

# Check Kafka
echo -n "   Kafka (Port 9092): "
if nc -z localhost 9092 2>/dev/null; then
    echo "✅ Running"
else
    echo "❌ Not responding"
fi

echo ""
echo "📊 Quick Stats:"
curl -s http://localhost:8000/stats | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'   Total Readings: {data[\"total_readings\"]}')
    print(f'   Unique Sensors: {data[\"unique_sensors\"]}')
    if data['latest_reading']:
        latest = data['latest_reading']
        print(f'   Latest: {latest[\"sensor_id\"]} = {latest[\"value\"]} {latest[\"unit\"]}')
except:
    print('   Unable to fetch stats')
"

echo ""
echo "🔗 Access URLs:"
echo "   • API Docs: http://localhost:8000/docs"
echo "   • Grafana: http://localhost:3000 (admin/admin)"
echo "   • InfluxDB: http://localhost:8086"
