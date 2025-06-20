#!/usr/bin/env python3
"""
SensorFlow - Industrial Sensor Data Simulator
"""
import json
import time
import random
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from dataclasses import dataclass, asdict
from kafka import KafkaProducer
from faker import Faker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
fake = Faker()

@dataclass
class SensorReading:
    sensor_id: str
    sensor_type: str
    location: str
    timestamp: str
    value: float
    unit: str
    status: str
    metadata: Dict[str, Any]

class SensorSimulator:
    def __init__(self, kafka_bootstrap_servers: str = "localhost:9092"):
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_bootstrap_servers],
            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            key_serializer=lambda x: x.encode('utf-8') if x else None
        )
        self.sensor_configs = self._initialize_sensors()
    def _initialize_sensors(self):
        locations = [
            "Building-A-Floor-1", "Building-A-Floor-2", "Building-A-Floor-3",
            "Building-B-Floor-1", "Building-B-Floor-2", 
            "Warehouse-Zone-1", "Warehouse-Zone-2", "Warehouse-Zone-3",
            "Production-Line-1", "Production-Line-2", "Production-Line-3"
        ]
        sensors = []
        for i in range(50):
            sensors.append({
                "id": f"TEMP_{i:03d}",
                "type": "temperature",
                "location": random.choice(locations),
                "normal_range": (18.0, 25.0),
                "unit": "°C",
                "failure_rate": 0.02,
                "drift_factor": 0.1
            })
        for i in range(30):
            sensors.append({
                "id": f"VIB_{i:03d}",
                "type": "vibration",
                "location": random.choice(locations),
                "normal_range": (0.0, 50.0),
                "unit": "Hz",
                "failure_rate": 0.05,
                "drift_factor": 2.0
            })
        for i in range(25):
            sensors.append({
                "id": f"PRES_{i:03d}",
                "type": "pressure",
                "location": random.choice(locations),
                "normal_range": (50.0, 200.0),
                "unit": "PSI",
                "failure_rate": 0.03,
                "drift_factor": 5.0
            })
        for i in range(20):
            sensors.append({
                "id": f"HUM_{i:03d}",
                "type": "humidity",
                "location": random.choice(locations),
                "normal_range": (40.0, 60.0),
                "unit": "%RH",
                "failure_rate": 0.01,
                "drift_factor": 1.0
            })
        return sensors
    def _generate_sensor_value(self, sensor_config):
        min_val, max_val = sensor_config["normal_range"]
        is_anomaly = random.random() < sensor_config["failure_rate"]
        if is_anomaly:
            if random.choice([True, False]):
                value = max_val + random.uniform(0, sensor_config["drift_factor"] * (max_val - min_val))
                status = "HIGH_ALARM"
            else:
                value = min_val - random.uniform(0, sensor_config["drift_factor"] * (max_val - min_val))
                status = "LOW_ALARM"
        else:
            center = (min_val + max_val) / 2
            noise = random.gauss(0, (max_val - min_val) * 0.05)
            value = center + noise
            value = max(min_val * 0.8, min(max_val * 1.2, value))
            status = "NORMAL"
        return round(value, 2), status
    def generate_reading(self, sensor_config):
        value, status = self._generate_sensor_value(sensor_config)
        return SensorReading(
            sensor_id=sensor_config["id"],
            sensor_type=sensor_config["type"],
            location=sensor_config["location"],
            timestamp=datetime.now(timezone.utc).isoformat(),
            value=value,
            unit=sensor_config["unit"],
            status=status,
            metadata={
                "batch_id": fake.uuid4(),
                "firmware_version": f"v{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,9)}",
                "battery_level": random.randint(20, 100),
                "signal_strength": random.randint(-80, -20)
            }
        )
    def start_simulation(self, messages_per_second: int = 100, duration_seconds: int = None):
        logger.info(f"Starting SensorFlow simulation: {messages_per_second} msg/sec")
        logger.info(f"Total sensors: {len(self.sensor_configs)}")
        message_count = 0
        start_time = time.time()
        try:
            while True:
                batch_start = time.time()
                for _ in range(messages_per_second):
                    sensor_config = random.choice(self.sensor_configs)
                    reading = self.generate_reading(sensor_config)
                    topic = f"sensors.{reading.sensor_type}"
                    self.producer.send(
                        topic=topic,
                        key=reading.sensor_id,
                        value=asdict(reading)
                    )
                    message_count += 1
                    if message_count % 1000 == 0:
                        elapsed = time.time() - start_time
                        rate = message_count / elapsed
                        logger.info(f"Sent {message_count} messages | Rate: {rate:.1f} msg/sec")
                batch_duration = time.time() - batch_start
                sleep_time = max(0, 1.0 - batch_duration)
                time.sleep(sleep_time)
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break
        except KeyboardInterrupt:
            logger.info("Simulation stopped by user")
        finally:
            self.producer.flush()
            self.producer.close()
            elapsed = time.time() - start_time
            logger.info(f"Simulation completed: {message_count} messages in {elapsed:.1f}s")
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SensorFlow Data Simulator")
    parser.add_argument("--kafka-servers", default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--rate", type=int, default=100, help="Messages per second")
    parser.add_argument("--duration", type=int, help="Duration in seconds (infinite if not specified)")
    args = parser.parse_args()
    simulator = SensorSimulator(kafka_bootstrap_servers=args.kafka_servers)
    simulator.start_simulation(messages_per_second=args.rate, duration_seconds=args.duration)
if __name__ == "__main__":
    main()
