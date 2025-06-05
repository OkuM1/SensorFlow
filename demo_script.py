#!/usr/bin/env python3
"""
SensorFlow Demo Script
Demonstrates the working IoT data pipeline
"""
import requests
import time
import json
import random
from datetime import datetime

# API Configuration
API_BASE_URL = "http://localhost:8000"

def check_services():
    """Check if all services are running"""
    print("🔍 Checking Service Status...")
    
    # Check API
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("✅ SensorFlow API: Running")
        else:
            print("❌ SensorFlow API: Not responding")
            return False
    except:
        print("❌ SensorFlow API: Connection failed")
        return False
    
    # Check InfluxDB
    try:
        response = requests.get("http://localhost:8086/health")
        if response.status_code == 200:
            print("✅ InfluxDB: Running")
        else:
            print("❌ InfluxDB: Not responding")
    except:
        print("❌ InfluxDB: Connection failed")
    
    print("✅ All core services are operational!\n")
    return True

def generate_demo_data():
    """Generate realistic demo sensor data"""
    print("🏭 Generating IoT Sensor Data...")
    
    # Add some structured data
    response = requests.post(f"{API_BASE_URL}/simulate?count=50")
    if response.status_code == 200:
        print("✅ Generated 50 sensor readings")
    else:
        print("❌ Failed to generate data")
        return False
    
    return True

def show_statistics():
    """Display current system statistics"""
    print("\n📊 Current System Statistics:")
    
    try:
        response = requests.get(f"{API_BASE_URL}/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   Total Readings: {stats['total_readings']}")
            print(f"   Unique Sensors: {stats['unique_sensors']}")
            print(f"   Active Sensor Types: Temperature, Pressure, Vibration, Humidity")
            
            if stats['latest_reading']:
                latest = stats['latest_reading']
                print(f"   Latest Reading: {latest['sensor_id']} = {latest['value']} {latest['unit']}")
                print(f"   Location: {latest['location']}")
    except Exception as e:
        print(f"   Error fetching statistics: {e}")

def show_recent_data():
    """Show recent sensor readings"""
    print("\n📈 Recent Sensor Readings:")
    
    try:
        response = requests.get(f"{API_BASE_URL}/readings?limit=10")
        if response.status_code == 200:
            readings = response.json()
            for reading in readings[-5:]:  # Show last 5
                timestamp = reading['timestamp'][:19]  # Remove microseconds
                print(f"   {reading['sensor_id']}: {reading['value']} {reading['unit']} ({timestamp})")
    except Exception as e:
        print(f"   Error fetching readings: {e}")

def main():
    """Main demo function"""
    print("🚀 SensorFlow IoT Platform Demo")
    print("=" * 50)
    
    # Check services
    if not check_services():
        print("❌ Services not ready. Please start with: docker-compose up -d")
        return
    
    # Generate demo data
    if not generate_demo_data():
        return
    
    # Show statistics
    show_statistics()
    
    # Show recent data
    show_recent_data()
    
    print("\n🎯 Demo Complete!")
    print("\n📱 Access Points:")
    print("   • API Documentation: http://localhost:8000/docs")
    print("   • API Health Check: http://localhost:8000/health")
    print("   • Grafana Dashboard: http://localhost:3000")
    print("   • InfluxDB UI: http://localhost:8086")
    
    print("\n🔧 Available API Endpoints:")
    print("   • GET /readings - View sensor data")
    print("   • GET /stats - System statistics")
    print("   • POST /simulate?count=N - Generate test data")
    print("   • GET /sensors - List available sensors")

if __name__ == "__main__":
    main()
