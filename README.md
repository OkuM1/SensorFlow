# SensorFlow

A practical IoT data platform that collects, processes, and visualizes sensor data in real-time. Built for demonstrating modern data engineering patterns with Docker, Python, and time-series databases.

## Overview

SensorFlow simulates industrial IoT sensors and processes their data through a complete pipeline. You can use it to understand how sensor data flows from collection to visualization, or as a starting point for your own IoT projects.

The platform generates realistic sensor readings for temperature, pressure, vibration, and humidity from multiple factory locations, then stores and visualizes this data using industry-standard tools.

## Getting Started

You need Docker and Docker Compose installed on your system.

**Clone and start:**
```bash
git clone https://github.com/yourusername/SensorFlow.git
cd SensorFlow
docker-compose up -d
```

**Access the interfaces:**
- API docs: http://localhost:8000/docs
- Grafana dashboards: http://localhost:3000 (admin/admin)
- InfluxDB interface: http://localhost:8086 (admin/password123)

**Run the demo:**
```bash
python3 demo_script.py
```

This generates sample data and shows you how the system works.

## What's Inside

**Core Components:**
- FastAPI service for data ingestion and retrieval
- InfluxDB for time-series data storage  
- Grafana for data visualization
- Apache Kafka for message streaming
- Python scripts that simulate IoT sensors

**API Endpoints:**
- `GET /` - Basic API information
- `GET /health` - Service health status
- `GET /sensors` - List active sensors
- `GET /readings` - Retrieve sensor data
- `POST /readings` - Submit new readings
- `POST /simulate` - Generate test data
- `GET /stats` - System statistics

## Example Data

The sensor simulator creates data that looks like real industrial equipment:

```json
{
  "sensor_id": "TEMP_001", 
  "sensor_type": "temperature",
  "value": 23.4,
  "unit": "celsius",
  "location": "Factory_Floor_A",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

Sensor types include temperature (15-50°C), pressure (1-5 bar), vibration (0-2 m/s²), and humidity (20-80%).

## Architecture

```
Sensor Simulator → FastAPI → InfluxDB → Grafana
                      ↓
                   Kafka Queue
```

Data flows from simulated sensors through the API into InfluxDB for storage. Grafana reads from InfluxDB to create dashboards. Kafka handles message queuing for reliable data processing.

## Development

**Run locally:**
```bash
pip install -r requirements.txt
cd src
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Generate test data:**
```bash
python3 src/data_generator.py
```

**Check system status:**
```bash
./status.sh
```

## Project Structure

```
SensorFlow/
├── src/
│   ├── api/main.py         # REST API server
│   └── data_generator.py   # Sensor simulation
├── docker-compose.yml      # Service definitions  
├── Dockerfile             # API container
├── requirements.txt       # Python packages
├── demo_script.py        # Demo automation
└── status.sh            # Health monitoring
```

## Testing the System

**Health check:**
```bash
curl http://localhost:8000/health
```

**List sensors:**
```bash
curl http://localhost:8000/sensors
```

**Generate sample data:**
```bash
curl -X POST http://localhost:8000/simulate?count=100
```

**View statistics:**
```bash
curl http://localhost:8000/stats
```

## Useful Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services  
docker-compose down

# Clean up data
docker-compose down -v

# Rebuild containers
docker-compose build --no-cache
```

## Why This Project

I built SensorFlow to demonstrate practical data engineering concepts without the complexity of enterprise systems. It shows how to:

- Handle time-series data at scale
- Build REST APIs for data ingestion
- Use Docker for service orchestration  
- Create monitoring and visualization
- Simulate realistic IoT scenarios

The code is straightforward and well-documented, making it useful for learning or as a foundation for larger projects.

## Extending the Platform

Ready to add more features? Consider:

- Connect real sensor hardware via GPIO or serial interfaces
- Add authentication and user management
- Implement alerting for anomaly detection
- Scale with Kubernetes deployment
- Add data retention policies
- Create custom Grafana dashboards
- Integrate machine learning models

## License

Released under the MIT License. See LICENSE file for details.
