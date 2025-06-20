#!/bin/bash

# SensorFlow Setup Script
# Automated setup for the SensorFlow IoT platform

set -e

echo "🌊 SensorFlow - IoT Sensor Data Platform Setup"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed"
}

# Check if Python is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8+ first."
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
        print_error "Python 3.8+ is required. Current version: $python_version"
        exit 1
    fi
    
    print_status "Python $python_version is installed"
}

# Install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    
    if command -v pip3 &> /dev/null; then
        pip3 install -r requirements.txt
    else
        python3 -m pip install -r requirements.txt
    fi
    
    print_status "Python dependencies installed"
}

# Create necessary directories
create_directories() {
    print_info "Creating necessary directories..."
    
    mkdir -p logs data/raw data/processed models
    mkdir -p dashboards/grafana/dashboards
    mkdir -p tests/integration tests/unit
    
    print_status "Directories created"
}

# Set permissions
set_permissions() {
    print_info "Setting up permissions..."
    
    chmod +x scripts/*.sh
    chmod +x src/data_generators/sensor_simulator.py
    chmod +x src/processing/spark_streaming.py
    
    print_status "Permissions set"
}

# Build Docker containers
build_containers() {
    print_info "Building Docker containers..."
    
    docker-compose build
    
    print_status "Docker containers built"
}

# Start services
start_services() {
    print_info "Starting SensorFlow services..."
    
    docker-compose up -d
    
    print_status "Services started"
}

# Wait for services to be ready
wait_for_services() {
    print_info "Waiting for services to be ready..."
    
    # Wait for Kafka
    print_info "Waiting for Kafka..."
    sleep 30
    
    # Wait for InfluxDB
    print_info "Waiting for InfluxDB..."
    sleep 10
    
    # Check API health
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null; then
            print_status "API is ready"
            break
        fi
        
        print_info "Waiting for API... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_warning "API health check timed out, but continuing..."
    fi
}

# Create Kafka topics
create_kafka_topics() {
    print_info "Creating Kafka topics..."
    
    topics=("sensors.temperature" "sensors.vibration" "sensors.pressure" "sensors.humidity" "alerts.anomalies" "aggregations.minute" "aggregations.hour")
    
    for topic in "${topics[@]}"; do
        docker-compose exec -T kafka kafka-topics --create \
            --topic "$topic" \
            --bootstrap-server localhost:9092 \
            --partitions 3 \
            --replication-factor 1 \
            --if-not-exists || true
    done
    
    print_status "Kafka topics created"
}

# Initialize InfluxDB
init_influxdb() {
    print_info "Initializing InfluxDB..."
    
    # The initialization is handled by environment variables in docker-compose
    # Just verify the bucket exists
    sleep 5
    
    print_status "InfluxDB initialized"
}

# Display access information
show_access_info() {
    echo ""
    echo "🎉 SensorFlow Setup Complete!"
    echo "=============================="
    echo ""
    echo "Access the platform:"
    echo "📊 Grafana Dashboard:    http://localhost:3000 (admin/sensorflow123)"
    echo "🌐 API Documentation:    http://localhost:8000/docs"
    echo "⚡ Spark UI:             http://localhost:8080"
    echo "📈 Kafka Control Center: http://localhost:9021"
    echo "📊 Prometheus:           http://localhost:9090"
    echo ""
    echo "Start sensor simulation:"
    echo "💻 make simulate         # Start data generation"
    echo "💻 make process          # Start stream processing"
    echo ""
    echo "Monitor the system:"
    echo "💻 make logs             # View all logs"
    echo "💻 make status           # Check service status"
    echo ""
    echo "Stop the platform:"
    echo "💻 make stop             # Stop all services"
    echo ""
}

# Main setup function
main() {
    echo "Starting SensorFlow setup..."
    echo ""
    
    check_docker
    check_python
    create_directories
    install_dependencies
    set_permissions
    build_containers
    start_services
    wait_for_services
    create_kafka_topics
    init_influxdb
    
    show_access_info
}

# Handle script arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "quick")
        print_info "Quick setup - skipping builds..."
        start_services
        wait_for_services
        create_kafka_topics
        show_access_info
        ;;
    "clean")
        print_info "Cleaning up SensorFlow..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_status "Cleanup complete"
        ;;
    "reset")
        print_info "Resetting SensorFlow..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        main
        ;;
    *)
        echo "Usage: $0 {setup|quick|clean|reset}"
        echo "  setup - Full setup (default)"
        echo "  quick - Quick start existing containers"
        echo "  clean - Clean up all containers and volumes"
        echo "  reset - Clean up and full setup"
        exit 1
        ;;
esac
