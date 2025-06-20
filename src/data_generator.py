"""
SensorFlow Data Generator - Simulates IoT Sensor Data
"""
import random
import time
import requests
from datetime import datetime
from faker import Faker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SensorDataGenerator:
    """Generates realistic sensor data for testing."""
    
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.fake = Faker()
        self.sensor_configs = {
            "temperature": {
                "min_value": 15.0,
                "max_value": 35.0,
                "unit": "°C",
                "anomaly_threshold": 45.0
            },
            "pressure": {
                "min_value": 0.8,
                "max_value": 2.5,
                "unit": "bar",
                "anomaly_threshold": 3.0
            },
            "vibration": {
                "min_value": 0.1,
                "max_value": 2.0,
                "unit": "m/s²",
                "anomaly_threshold": 5.0
            },
            "humidity": {
                "min_value": 30.0,
                "max_value": 70.0,
                "unit": "%",
                "anomaly_threshold": 90.0
            }
        }
    
    def generate_reading(self, sensor_type="temperature", sensor_id=None, anomaly_chance=0.05):
        """Generate a single sensor reading."""
        if sensor_id is None:
            sensor_id = f"{sensor_type}_sensor_{random.randint(1, 5):02d}"
        
        config = self.sensor_configs[sensor_type]
        
        # Generate normal or anomalous value
        if random.random() < anomaly_chance:
            # Generate anomaly
            value = random.uniform(config["anomaly_threshold"], config["anomaly_threshold"] * 1.2)
        else:
            # Generate normal value
            value = random.uniform(config["min_value"], config["max_value"])
        
        return {
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "value": round(value, 2),
            "unit": config["unit"],
            "timestamp": datetime.now().isoformat(),
            "location": f"Factory Floor {random.randint(1, 5)}"
        }
    
    def send_reading(self, reading):
        """Send reading to the API."""
        try:
            response = requests.post(f"{self.api_url}/readings", json=reading)
            if response.status_code == 200:
                logger.info(f"Sent: {reading['sensor_id']} = {reading['value']} {reading['unit']}")
                return True
            else:
                logger.error(f"Failed to send reading: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending reading: {e}")
            return False
    
    def run_simulation(self, duration_minutes=10, readings_per_minute=6):
        """Run continuous data generation simulation."""
        logger.info(f"Starting sensor simulation for {duration_minutes} minutes")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        sensor_types = list(self.sensor_configs.keys())
        
        while time.time() < end_time:
            # Generate readings for different sensor types
            for _ in range(readings_per_minute):
                sensor_type = random.choice(sensor_types)
                reading = self.generate_reading(sensor_type)
                self.send_reading(reading)
                
                time.sleep(60 / readings_per_minute)  # Distribute readings evenly
        
        logger.info("Simulation completed")

def main():
    """Main function to run the data generator."""
    generator = SensorDataGenerator()
    
    # Test API connection
    try:
        response = requests.get(f"{generator.api_url}/health")
        if response.status_code == 200:
            logger.info("API connection successful")
        else:
            logger.error("API connection failed")
            return
    except Exception as e:
        logger.error(f"Cannot connect to API: {e}")
        return
    
    # Generate some initial data
    logger.info("Generating initial sensor data...")
    for sensor_type in generator.sensor_configs.keys():
        for _ in range(3):  # 3 readings per sensor type
            reading = generator.generate_reading(sensor_type)
            generator.send_reading(reading)
    
    logger.info("Initial data generation complete")

if __name__ == "__main__":
    main()
