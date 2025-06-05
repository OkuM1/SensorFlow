.PHONY: help build up down logs test clean simulate

help:
	@echo "SensorFlow - IoT Data Platform"
	@echo "Available commands:"
	@echo "  build     - Build Docker images"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services" 
	@echo "  logs      - Show service logs"
	@echo "  test      - Test API endpoints"
	@echo "  simulate  - Generate test data"
	@echo "  clean     - Clean up containers and volumes"

build:
	docker-compose -f docker-compose-clean.yml build

up:
	docker-compose -f docker-compose-clean.yml up -d
	@echo "Services starting..."
	@echo "API: http://localhost:8000"
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@echo "InfluxDB: http://localhost:8086 (admin/password123)"

down:
	docker-compose -f docker-compose-clean.yml down

logs:
	docker-compose -f docker-compose-clean.yml logs -f

test:
	@echo "Testing API endpoints..."
	curl -s http://localhost:8000/health | jq .
	curl -s http://localhost:8000/sensors | jq .
	curl -s http://localhost:8000/stats | jq .

simulate:
	@echo "Generating test sensor data..."
	python src/data_generator.py

clean:
	docker-compose -f docker-compose-clean.yml down -v
	docker system prune -f
