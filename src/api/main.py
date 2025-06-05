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

# In-memory storage for demo (in production, use a real database)
sensor_readings: List[SensorReading] = []

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
    return sensor_readings[-limit:]

@app.post("/readings", response_model=dict)
async def add_reading(reading: SensorReading):
    """Add a new sensor reading."""
    sensor_readings.append(reading)
    logger.info(f"Added reading from {reading.sensor_id}: {reading.value} {reading.unit}")
    return {"status": "success", "message": "Reading added"}

@app.post("/simulate", response_model=dict)
async def simulate_data(count: int = 10):
    """Simulate sensor data for demo purposes."""
    sensor_types = ["temperature", "pressure", "vibration", "humidity"]
    units = {"temperature": "°C", "pressure": "bar", "vibration": "m/s²", "humidity": "%"}
    
    for i in range(count):
        sensor_type = random.choice(sensor_types)
        reading = SensorReading(
            sensor_id=f"{sensor_type}_sensor_0{random.randint(1,3)}",
            sensor_type=sensor_type,
            value=round(random.uniform(10, 100), 2),
            unit=units[sensor_type],
            timestamp=datetime.now(),
            location=f"Factory Floor {random.randint(1,5)}"
        )
        sensor_readings.append(reading)
    
    return {"status": "success", "message": f"Generated {count} sensor readings"}

@app.get("/stats", response_model=dict)
async def get_statistics():
    """Get basic statistics about sensor data."""
    if not sensor_readings:
        return {"total_readings": 0, "sensors": [], "latest_reading": None}
    
    sensor_ids = list(set([r.sensor_id for r in sensor_readings]))
    latest_reading = sensor_readings[-1] if sensor_readings else None
    
    return {
        "total_readings": len(sensor_readings),
        "unique_sensors": len(sensor_ids),
        "sensors": sensor_ids,
        "latest_reading": latest_reading.dict() if latest_reading else None
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
