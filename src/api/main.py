"""
SensorFlow API - Main FastAPI Application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import logging
from datetime import datetime
import json
import asyncio
import random
import os
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SensorFlow API",
    description="Real-time IoT Sensor Data Platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class SensorReading(BaseModel):
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: datetime
    location: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: dict

# Database connection settings
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sensorflow")

@app.on_event("startup")
async def startup_event():
    """Create database connection pool and ensure table exists."""
    app.state.pool = await asyncpg.create_pool(dsn=DATABASE_URL)
    create_table = """
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id SERIAL PRIMARY KEY,
            sensor_id TEXT NOT NULL,
            sensor_type TEXT NOT NULL,
            value DOUBLE PRECISION NOT NULL,
            unit TEXT NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            location TEXT
        );
    """
    async with app.state.pool.acquire() as conn:
        await conn.execute(create_table)

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection pool."""
    await app.state.pool.close()

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "SensorFlow API",
        "version": "1.0.0",
        "description": "Real-time IoT Sensor Data Platform",
        "endpoints": {
            "health": "/health",
            "sensors": "/sensors",
            "readings": "/readings",
            "simulate": "/simulate"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        services={
            "api": "running",
            "kafka": "simulated",
            "influxdb": "simulated"
        }
    )

@app.get("/sensors", response_model=List[str])
async def get_sensors():
    """Get list of available sensors."""
    return [
        "temp_sensor_01",
        "pressure_sensor_01", 
        "vibration_sensor_01",
        "humidity_sensor_01"
    ]

@app.get("/readings", response_model=List[SensorReading])
async def get_readings(limit: int = 100):
    """Get recent sensor readings."""
    query = """SELECT sensor_id, sensor_type, value, unit, timestamp, location
               FROM sensor_readings
               ORDER BY id DESC
               LIMIT $1"""
    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch(query, limit)
    return [SensorReading(**dict(r)) for r in rows]


@app.post("/readings", response_model=dict)
async def add_reading(reading: SensorReading):
    """Add a new sensor reading."""
    query = """INSERT INTO sensor_readings
               (sensor_id, sensor_type, value, unit, timestamp, location)
               VALUES ($1, $2, $3, $4, $5, $6)"""
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            query,
            reading.sensor_id,
            reading.sensor_type,
            reading.value,
            reading.unit,
            reading.timestamp,
            reading.location,
        )
    logger.info(
        f"Added reading from {reading.sensor_id}: {reading.value} {reading.unit}"
    )
    return {"status": "success", "message": "Reading added"}


@app.get("/readings/{reading_id}", response_model=SensorReading)
async def get_reading(reading_id: int):
    """Retrieve a single sensor reading by ID."""
    query = """SELECT sensor_id, sensor_type, value, unit, timestamp, location
               FROM sensor_readings WHERE id=$1"""
    async with app.state.pool.acquire() as conn:
        row = await conn.fetchrow(query, reading_id)
    if not row:
        raise HTTPException(status_code=404, detail="Reading not found")
    return SensorReading(**dict(row))


@app.put("/readings/{reading_id}", response_model=SensorReading)
async def update_reading(reading_id: int, reading: SensorReading):
    """Update an existing sensor reading."""
    query = """UPDATE sensor_readings SET
                sensor_id=$1,
                sensor_type=$2,
                value=$3,
                unit=$4,
                timestamp=$5,
                location=$6
                WHERE id=$7
                RETURNING sensor_id, sensor_type, value, unit, timestamp, location"""
    async with app.state.pool.acquire() as conn:
        row = await conn.fetchrow(
            query,
            reading.sensor_id,
            reading.sensor_type,
            reading.value,
            reading.unit,
            reading.timestamp,
            reading.location,
            reading_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Reading not found")
    return SensorReading(**dict(row))


@app.delete("/readings/{reading_id}", response_model=dict)
async def delete_reading(reading_id: int):
    """Delete a sensor reading by ID."""
    query = "DELETE FROM sensor_readings WHERE id=$1"
    async with app.state.pool.acquire() as conn:
        result = await conn.execute(query, reading_id)
    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Reading not found")
    return {"status": "success", "message": "Reading deleted"}

@app.post("/simulate", response_model=dict)
async def simulate_data(count: int = 10):
    """Simulate sensor data for demo purposes."""
    sensor_types = ["temperature", "pressure", "vibration", "humidity"]
    units = {"temperature": "°C", "pressure": "bar", "vibration": "m/s²", "humidity": "%"}

    for _ in range(count):
        sensor_type = random.choice(sensor_types)
        reading = SensorReading(
            sensor_id=f"{sensor_type}_sensor_0{random.randint(1,3)}",
            sensor_type=sensor_type,
            value=round(random.uniform(10, 100), 2),
            unit=units[sensor_type],
            timestamp=datetime.now(),
            location=f"Factory Floor {random.randint(1,5)}",
        )
        await add_reading(reading)

    return {"status": "success", "message": f"Generated {count} sensor readings"}

@app.get("/stats", response_model=dict)
async def get_statistics():
    """Get basic statistics about sensor data."""
    async with app.state.pool.acquire() as conn:
        total_readings = await conn.fetchval(
            "SELECT COUNT(*) FROM sensor_readings"
        )
        sensor_rows = await conn.fetch(
            "SELECT DISTINCT sensor_id FROM sensor_readings"
        )
        latest = await conn.fetchrow(
            "SELECT sensor_id, sensor_type, value, unit, timestamp, location\n"
            "FROM sensor_readings ORDER BY timestamp DESC LIMIT 1"
        )

    sensors = [r["sensor_id"] for r in sensor_rows]
    latest_reading = SensorReading(**dict(latest)).dict() if latest else None

    return {
        "total_readings": total_readings,
        "unique_sensors": len(sensors),
        "sensors": sensors,
        "latest_reading": latest_reading,
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
