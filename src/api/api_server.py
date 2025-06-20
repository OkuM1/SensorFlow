#!/usr/bin/env python3
"""
SensorFlow - FastAPI REST API
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import json
import asyncio
import logging
from datetime import datetime, timedelta
from kafka import KafkaConsumer, KafkaProducer
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import redis
import uvicorn
from fastapi.responses import StreamingResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SensorFlow API",
    description="Real-time IoT sensor data management and monitoring platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SensorReading(BaseModel):
    sensor_id: str
    sensor_type: str
    location: str
    timestamp: datetime
    value: float
    unit: str
    status: str
    metadata: Optional[Dict[str, Any]] = {}

class SensorInfo(BaseModel):
    sensor_id: str
    sensor_type: str
    location: str
    last_seen: Optional[datetime] = None
    status: str = "active"
    total_readings: int = 0

class AnomalyAlert(BaseModel):
    alert_id: str
    sensor_id: str
    sensor_type: str
    timestamp: datetime
    value: float
    expected_range: tuple
    severity: str
    message: str

class AggregationQuery(BaseModel):
    sensor_types: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    start_time: datetime
    end_time: datetime
    aggregation_window: str = "1h"

class Config:
    KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
    INFLUXDB_URL = "http://localhost:8086"
    INFLUXDB_TOKEN = "sensorflow-super-secret-token"
    INFLUXDB_ORG = "sensorflow"
    INFLUXDB_BUCKET = "sensors"
    REDIS_URL = "redis://localhost:6379"

config = Config()

kafka_producer = KafkaProducer(
    bootstrap_servers=[config.KAFKA_BOOTSTRAP_SERVERS],
    value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8')
)
influxdb_client = InfluxDBClient(
    url=config.INFLUXDB_URL,
    token=config.INFLUXDB_TOKEN,
    org=config.INFLUXDB_ORG
)
redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)

@app.get("/")
async def root():
    return {
        "service": "SensorFlow API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "sensors": "/sensors",
            "readings": "/readings",
            "anomalies": "/anomalies",
            "aggregations": "/aggregations",
            "stream": "/stream",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    health_status = {"api": "healthy", "timestamp": datetime.now().isoformat()}
    try:
        producer_metadata = kafka_producer.bootstrap_connected()
        health_status["kafka"] = "healthy" if producer_metadata else "unhealthy"
    except Exception as e:
        health_status["kafka"] = f"unhealthy: {str(e)}"
    try:
        health = influxdb_client.health()
        health_status["influxdb"] = health.status
    except Exception as e:
        health_status["influxdb"] = f"unhealthy: {str(e)}"
    try:
        redis_client.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"
    return health_status

@app.get("/sensors", response_model=List[SensorInfo])
async def get_sensors(sensor_type: Optional[str] = None, location: Optional[str] = None):
    try:
        sensor_keys = redis_client.keys("sensor:*")
        sensors = []
        for key in sensor_keys:
            sensor_data = redis_client.hgetall(key)
            if sensor_data:
                sensor = SensorInfo(
                    sensor_id=sensor_data.get("sensor_id"),
                    sensor_type=sensor_data.get("sensor_type"),
                    location=sensor_data.get("location"),
                    last_seen=datetime.fromisoformat(sensor_data.get("last_seen")) if sensor_data.get("last_seen") else None,
                    status=sensor_data.get("status", "unknown"),
                    total_readings=int(sensor_data.get("total_readings", 0))
                )
                if sensor_type and sensor.sensor_type != sensor_type:
                    continue
                if location and sensor.location != location:
                    continue
                sensors.append(sensor)
        return sensors
    except Exception as e:
        logger.error(f"Error fetching sensors: {e}")
        raise HTTPException(status_code=500, detail="Error fetching sensor data")

@app.post("/readings")
async def ingest_reading(reading: SensorReading, background_tasks: BackgroundTasks):
    try:
        topic = f"sensors.{reading.sensor_type}"
        kafka_producer.send(topic, reading.dict())
        background_tasks.add_task(update_sensor_metadata, reading)
        background_tasks.add_task(store_to_influxdb, reading)
        return {"status": "success", "message": "Reading ingested successfully"}
    except Exception as e:
        logger.error(f"Error ingesting reading: {e}")
        raise HTTPException(status_code=500, detail="Error ingesting sensor reading")

@app.get("/readings/{sensor_id}")
async def get_sensor_readings(sensor_id: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, limit: int = 1000):
    try:
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        query = f'''
        from(bucket: "{config.INFLUXDB_BUCKET}")
        |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
        |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
        |> limit(n: {limit})
        '''
        query_api = influxdb_client.query_api()
        result = query_api.query(query, org=config.INFLUXDB_ORG)
        readings = []
        for table in result:
            for record in table.records:
                readings.append({
                    "timestamp": record.get_time(),
                    "sensor_id": record.values.get("sensor_id"),
                    "value": record.get_value(),
                    "sensor_type": record.values.get("sensor_type"),
                    "location": record.values.get("location")
                })
        return {"sensor_id": sensor_id, "readings": readings, "count": len(readings)}
    except Exception as e:
        logger.error(f"Error fetching readings: {e}")
        raise HTTPException(status_code=500, detail="Error fetching sensor readings")

@app.get("/anomalies")
async def get_anomalies(sensor_type: Optional[str] = None, severity: Optional[str] = None, hours: int = 24):
    try:
        start_time = datetime.now() - timedelta(hours=hours)
        anomaly_keys = redis_client.keys("anomaly:*")
        anomalies = []
        for key in anomaly_keys:
            anomaly_data = redis_client.hgetall(key)
            if anomaly_data:
                alert_time = datetime.fromisoformat(anomaly_data.get("timestamp"))
                if alert_time >= start_time:
                    anomaly = AnomalyAlert(
                        alert_id=anomaly_data.get("alert_id"),
                        sensor_id=anomaly_data.get("sensor_id"),
                        sensor_type=anomaly_data.get("sensor_type"),
                        timestamp=alert_time,
                        value=float(anomaly_data.get("value")),
                        expected_range=eval(anomaly_data.get("expected_range", "(0, 100)")),
                        severity=anomaly_data.get("severity"),
                        message=anomaly_data.get("message")
                    )
                    if sensor_type and anomaly.sensor_type != sensor_type:
                        continue
                    if severity and anomaly.severity != severity:
                        continue
                    anomalies.append(anomaly)
        anomalies.sort(key=lambda x: x.timestamp, reverse=True)
        return {"anomalies": anomalies, "count": len(anomalies)}
    except Exception as e:
        logger.error(f"Error fetching anomalies: {e}")
        raise HTTPException(status_code=500, detail="Error fetching anomaly data")

@app.post("/aggregations")
async def get_aggregations(query: AggregationQuery):
    try:
        filters = []
        if query.sensor_types:
            type_filter = " or ".join([f'r["sensor_type"] == "{st}"' for st in query.sensor_types])
            filters.append(f"({type_filter})")
        if query.locations:
            location_filter = " or ".join([f'r["location"] == "{loc}"' for loc in query.locations])
            filters.append(f"({location_filter})")
        filter_clause = " and ".join(filters) if filters else ""
        influx_query = f'''
        from(bucket: "{config.INFLUXDB_BUCKET}")
        |> range(start: {query.start_time.isoformat()}, stop: {query.end_time.isoformat()})
        {f"|> filter(fn: (r) => {filter_clause})" if filter_clause else ""}
        |> aggregateWindow(every: {query.aggregation_window}, fn: mean, createEmpty: false)
        |> yield(name: "mean")
        '''
        query_api = influxdb_client.query_api()
        result = query_api.query(influx_query, org=config.INFLUXDB_ORG)
        aggregations = []
        for table in result:
            for record in table.records:
                aggregations.append({
                    "timestamp": record.get_time(),
                    "sensor_type": record.values.get("sensor_type"),
                    "location": record.values.get("location"),
                    "mean_value": record.get_value(),
                    "window": query.aggregation_window
                })
        return {"aggregations": aggregations, "count": len(aggregations)}
    except Exception as e:
        logger.error(f"Error getting aggregations: {e}")
        raise HTTPException(status_code=500, detail="Error calculating aggregations")

@app.get("/stream")
async def stream_sensor_data():
    async def event_generator():
        consumer = KafkaConsumer(
            'sensors.temperature', 'sensors.vibration', 'sensors.pressure', 'sensors.humidity',
            bootstrap_servers=[config.KAFKA_BOOTSTRAP_SERVERS],
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=1000
        )
        try:
            for message in consumer:
                data = message.value
                yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            consumer.close()
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

async def update_sensor_metadata(reading: SensorReading):
    try:
        key = f"sensor:{reading.sensor_id}"
        sensor_data = {
            "sensor_id": reading.sensor_id,
            "sensor_type": reading.sensor_type,
            "location": reading.location,
            "last_seen": reading.timestamp.isoformat(),
            "status": reading.status
        }
        current_count = redis_client.hget(key, "total_readings")
        sensor_data["total_readings"] = int(current_count or 0) + 1
        redis_client.hset(key, mapping=sensor_data)
    except Exception as e:
        logger.error(f"Error updating sensor metadata: {e}")

async def store_to_influxdb(reading: SensorReading):
    try:
        point = Point("sensor_reading") \
            .tag("sensor_id", reading.sensor_id) \
            .tag("sensor_type", reading.sensor_type) \
            .tag("location", reading.location) \
            .tag("status", reading.status) \
            .field("value", reading.value) \
            .time(reading.timestamp)
        write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=config.INFLUXDB_BUCKET, org=config.INFLUXDB_ORG, record=point)
    except Exception as e:
        logger.error(f"Error storing to InfluxDB: {e}")

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
