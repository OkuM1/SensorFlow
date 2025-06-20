# SensorFlow

A practical IoT data platform that collects, processes, and visualizes sensor data in real-time. Built for demonstrating modern data engineering patterns with Docker, Python, and time-series databases.

## Overview

SensorFlow simulates industrial IoT sensors and processes their data through a complete pipeline. You can use it to understand how sensor data flows from collection to visualization, or as a starting point for your own IoT projects.

The platform generates realistic sensor readings for temperature, pressure, vibration, and humidity from multiple factory locations, then stores and visualizes this data using industry-standard tools.

## Architecture

```
Sensor Simulator → FastAPI (PostgreSQL) → Grafana
                      ↓
                FastAPI (Kafka/InfluxDB/Redis)
                      ↓
                   InfluxDB
```

- **Sensor Simulator**: Generates realistic industrial sensor data and sends it to Kafka.
- **FastAPI (PostgreSQL)**: REST API for CRUD operations on sensor readings, backed by PostgreSQL.
- **FastAPI (Kafka/InfluxDB/Redis)**: Advanced API for streaming, analytics, and time-series storage.
- **InfluxDB**: Stores time-series sensor data for analytics and visualization.
- **Grafana**: Visualizes sensor data from InfluxDB.
- **Kafka**: Message queue for real-time data ingestion and streaming.
- **PostgreSQL**: Relational database for persistent sensor readings (used by the main API).

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

**Run the sensor simulator:**
```bash
python3 src/data_generators/sensor_simulator.py --rate 10 --duration 10
```

**Run the demo script:**
```bash
python3 demo_script.py
```

## Database Configuration

- **PostgreSQL**: Used by the main FastAPI app (`src/api/main.py`).
  - Connection string: `postgresql://sensorflow:password@localhost:5432/sensorflow`
  - Data is persisted in the Docker volume `postgres_data`.
- **InfluxDB**: Used for time-series data and analytics by the advanced API (`src/api/api_server.py`).

## API Endpoints (PostgreSQL-backed API)
- `GET /` - Basic API information
- `GET /health` - Service health status
- `GET /sensors` - List active sensors
- `GET /readings` - List sensor data
- `POST /readings` - Submit new readings
- `GET /readings/{id}` - Retrieve a single reading
- `PUT /readings/{id}` - Update a reading
- `DELETE /readings/{id}` - Delete a reading
- `POST /simulate` - Generate test data
- `GET /stats` - System statistics

## API Endpoints (Kafka/InfluxDB/Redis-backed API)
- `GET /sensors` - List all sensors
- `POST /readings` - Ingest a new reading
- `GET /readings/{sensor_id}` - Get historical readings
- `GET /anomalies` - List anomaly alerts
- `POST /aggregations` - Get aggregated data
- `GET /stream` - Real-time event stream

## Example Data

The sensor simulator creates data that looks like real industrial equipment:

```json
{
  "sensor_id": "TEMP_001", 
  "sensor_type": "temperature",
  "value": 23.4,
  "unit": "°C",
  "location": "Factory_Floor_A",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Project Structure

```
SensorFlow/
├── src/
│   ├── api/main.py               # REST API (PostgreSQL)
│   ├── api/api_server.py         # Advanced API (Kafka/InfluxDB/Redis)
│   ├── data_generators/sensor_simulator.py  # Sensor simulation
│   ├── ml_models/anomaly_detection.py       # ML anomaly detection
│   └── processing/spark_streaming.py        # Spark streaming processor
├── docker-compose.yml            # Service definitions  
├── Dockerfile                    # API container
├── requirements.txt              # Python packages
├── demo_script.py                # Demo automation
├── status.sh                     # Health monitoring
└── dashboards/                   # Grafana dashboards and provisioning
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

**Read a specific entry:**
```bash
curl http://localhost:8000/readings/1
```

**Update an entry:**
```bash
curl -X PUT -H "Content-Type: application/json" \
     -d '{"sensor_id":"temp_sensor_01","sensor_type":"temperature","value":22.5,"unit":"°C","timestamp":"2024-01-01T00:00:00","location":"Floor 1"}' \
     http://localhost:8000/readings/1
```

**Delete an entry:**
```bash
curl -X DELETE http://localhost:8000/readings/1
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

SensorFlow demonstrates practical data engineering concepts:
- Handle time-series data at scale
- Build REST APIs for data ingestion
- Use Docker for service orchestration  
- Create monitoring and visualization
- Simulate realistic IoT scenarios

## License

Released under the MIT License. See LICENSE file for details.
