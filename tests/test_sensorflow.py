#!/usr/bin/env python3
"""
SensorFlow Test Suite
Comprehensive testing for the SensorFlow platform
"""

import pytest
import json
import time
import asyncio
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from kafka import KafkaProducer, KafkaConsumer
import requests

# Test imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_generators.sensor_simulator import SensorSimulator, SensorReading
from ml_models.anomaly_detection import SensorAnomalyDetector

class TestSensorSimulator:
    """Test the sensor data simulator"""
    
    def test_sensor_initialization(self):
        """Test sensor configuration initialization"""
        simulator = SensorSimulator()
        
        # Check that sensors are initialized
        assert len(simulator.sensor_configs) > 0
        
        # Check sensor types
        sensor_types = {sensor['type'] for sensor in simulator.sensor_configs}
        expected_types = {'temperature', 'vibration', 'pressure', 'humidity'}
        assert sensor_types == expected_types
    
    def test_sensor_reading_generation(self):
        """Test individual sensor reading generation"""
        simulator = SensorSimulator()
        sensor_config = simulator.sensor_configs[0]
        
        reading = simulator.generate_reading(sensor_config)
        
        # Validate reading structure
        assert isinstance(reading, SensorReading)
        assert reading.sensor_id == sensor_config['id']
        assert reading.sensor_type == sensor_config['type']
        assert reading.unit == sensor_config['unit']
        assert isinstance(reading.value, float)
        assert reading.status in ['NORMAL', 'HIGH_ALARM', 'LOW_ALARM']
    
    def test_anomaly_generation(self):
        """Test that anomalies are generated at expected rate"""
        simulator = SensorSimulator()
        
        # Use a sensor with high failure rate for testing
        test_sensor = {
            "id": "TEST_001",
            "type": "test",
            "location": "test",
            "normal_range": (0.0, 100.0),
            "unit": "test",
            "failure_rate": 0.5,  # 50% anomaly rate
            "drift_factor": 10.0
        }
        
        # Generate many readings
        anomaly_count = 0
        total_readings = 1000
        
        for _ in range(total_readings):
            reading = simulator.generate_reading(test_sensor)
            if reading.status in ['HIGH_ALARM', 'LOW_ALARM']:
                anomaly_count += 1
        
        anomaly_rate = anomaly_count / total_readings
        
        # Should be approximately 50% with some tolerance
        assert 0.4 <= anomaly_rate <= 0.6

class TestAnomalyDetection:
    """Test ML anomaly detection models"""
    
    def setup_method(self):
        """Setup test data"""
        self.detector = SensorAnomalyDetector()
        
        # Create synthetic training data
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=1000, freq='1min')
        
        self.normal_data = pd.DataFrame({
            'sensor_id': ['TEST_001'] * 1000,
            'sensor_type': ['temperature'] * 1000,
            'timestamp': dates,
            'value': np.random.normal(22, 2, 1000),  # Normal temperature
            'location': ['test'] * 1000
        })
        
        # Add some clear anomalies
        anomaly_indices = np.random.choice(1000, 50, replace=False)
        self.normal_data.loc[anomaly_indices, 'value'] += np.random.normal(15, 5, 50)
    
    def test_feature_engineering(self):
        """Test feature preparation"""
        features = self.detector.prepare_features(self.normal_data)
        
        # Check that new features are created
        expected_features = [
            'hour', 'day_of_week', 'month',
            'rolling_mean_5', 'rolling_std_5',
            'value_diff', 'z_score_5'
        ]
        
        for feature in expected_features:
            assert feature in features.columns
        
        # Check no NaN values
        assert not features.isnull().any().any()
    
    def test_isolation_forest_training(self):
        """Test Isolation Forest model training"""
        model, scaler = self.detector.train_isolation_forest('temperature', self.normal_data)
        
        # Check model is trained
        assert model is not None
        assert scaler is not None
        assert 'temperature_isolation' in self.detector.models
        assert 'temperature_isolation' in self.detector.scalers
    
    def test_anomaly_prediction(self):
        """Test anomaly prediction"""
        # Train model first
        self.detector.train_isolation_forest('temperature', self.normal_data)
        
        # Create test data with obvious anomalies
        test_data = self.normal_data.tail(100).copy()
        test_data.loc[test_data.index[-10:], 'value'] = 100  # Clear anomalies
        
        predictions = self.detector.predict_anomalies('temperature', test_data)
        
        # Should detect the anomalies we added
        assert 'isolation_forest' in predictions
        anomaly_count = np.sum(predictions['isolation_forest']['anomalies'])
        assert anomaly_count > 0

class TestAPIEndpoints:
    """Test API functionality"""
    
    def setup_method(self):
        """Setup for API tests"""
        self.base_url = "http://localhost:8000"
        
    def test_health_endpoint(self):
        """Test API health check"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            assert response.status_code == 200
            
            health_data = response.json()
            assert 'services' in health_data
            assert 'api' in health_data['services']
            assert health_data['services']['api'] == 'running'
        except requests.RequestException:
            pytest.skip("API not available for testing")
    
    def test_sensors_endpoint(self):
        """Test sensors listing endpoint"""
        try:
            response = requests.get(f"{self.base_url}/sensors", timeout=5)
            assert response.status_code == 200
            
            sensors = response.json()
            assert isinstance(sensors, list)
        except requests.RequestException:
            pytest.skip("API not available for testing")
    
    def test_reading_ingestion(self):
        """Test sensor reading ingestion"""
        try:
            reading_data = {
                "sensor_id": "TEST_001",
                "sensor_type": "temperature",
                "location": "test_location",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "value": 22.5,
                "unit": "°C",
                "status": "NORMAL",
                "metadata": {"test": "true"}
            }
            
            response = requests.post(
                f"{self.base_url}/readings",
                json=reading_data,
                timeout=5
            )
            assert response.status_code == 200
            
            result = response.json()
            assert result['status'] == 'success'
        except requests.RequestException:
            pytest.skip("API not available for testing")

class TestIntegration:
    """Integration tests for the complete pipeline"""
    
    @pytest.mark.integration
    def test_end_to_end_pipeline(self):
        """Test complete data flow from generation to storage"""
        # This test requires all services to be running
        pytest.skip("Integration test - requires full service stack")
    
    @pytest.mark.integration 
    def test_kafka_producer_consumer(self):
        """Test Kafka message flow"""
        try:
            # Test producer
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9092'],
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            
            test_message = {
                "sensor_id": "TEST_001",
                "value": 25.0,
                "timestamp": datetime.now().isoformat()
            }
            
            producer.send('test.topic', test_message)
            producer.flush()
            producer.close()
            
            # Test consumer
            consumer = KafkaConsumer(
                'test.topic',
                bootstrap_servers=['localhost:9092'],
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                consumer_timeout_ms=5000
            )
            
            messages = []
            for message in consumer:
                messages.append(message.value)
                break  # Just get one message
            
            consumer.close()
            
            assert len(messages) > 0
            assert messages[0]['sensor_id'] == 'TEST_001'
            
        except Exception:
            pytest.skip("Kafka not available for testing")

class TestPerformance:
    """Performance and load testing"""
    
    def test_simulator_performance(self):
        """Test simulator can handle high message rates"""
        simulator = SensorSimulator()
        
        start_time = time.time()
        reading_count = 0
        
        # Generate readings for 5 seconds
        while time.time() - start_time < 5:
            sensor_config = simulator.sensor_configs[0]
            reading = simulator.generate_reading(sensor_config)
            reading_count += 1
        
        rate = reading_count / (time.time() - start_time)
        
        # Should be able to generate at least 1000 readings/second
        assert rate > 1000
    
    def test_anomaly_detection_performance(self):
        """Test ML model performance on large datasets"""
        detector = SensorAnomalyDetector()
        
        # Create large dataset
        large_data = pd.DataFrame({
            'sensor_id': ['TEST_001'] * 10000,
            'sensor_type': ['temperature'] * 10000,
            'timestamp': pd.date_range('2024-01-01', periods=10000, freq='1min'),
            'value': np.random.normal(22, 2, 10000),
            'location': ['test'] * 10000
        })
        
        start_time = time.time()
        detector.train_isolation_forest('temperature', large_data)
        training_time = time.time() - start_time
        
        start_time = time.time()
        predictions = detector.predict_anomalies('temperature', large_data.tail(1000))
        prediction_time = time.time() - start_time
        
        # Training should complete in reasonable time
        assert training_time < 30  # seconds
        assert prediction_time < 5  # seconds

if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing"
    ])
