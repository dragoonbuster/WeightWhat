.PHONY: help install dev test lint format clean run docker-build docker-run

# Default target
help:
	@echo "Available commands:"
	@echo "  install     Install production dependencies"
	@echo "  dev         Install development dependencies"
	@echo "  test        Run tests with coverage"
	@echo "  lint        Run code linting"
	@echo "  format      Format code with black and ruff"
	@echo "  clean       Clean build artifacts"
	@echo "  run         Run development server"
	@echo "  docker-build Build Docker image"
	@echo "  docker-run  Run Docker container"

# Install production dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
dev:
	pip install -r requirements.txt
	pre-commit install

# Run tests with coverage
test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Run tests without coverage (faster)
test-fast:
	pytest tests/ -v

# Run specific test file
test-file:
	pytest $(FILE) -v

# Run code linting
lint:
	ruff check src/ tests/
	mypy src/
	black --check src/ tests/

# Format code
format:
	black src/ tests/
	ruff check src/ tests/ --fix

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/

# Run development server
run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run production server
run-prod:
	uvicorn src.main:app --host 0.0.0.0 --port 8000

# Build Docker image
docker-build:
	docker build -t sizecomparator:latest .

# Run Docker container
docker-run:
	docker run -p 8000:8000 --env-file .env sizecomparator:latest

# Run with docker-compose
docker-up:
	docker-compose up --build

# Stop docker-compose
docker-down:
	docker-compose down

# Install pre-commit hooks
pre-commit:
	pre-commit install

# Run pre-commit on all files
pre-commit-all:
	pre-commit run --all-files

# Create new virtual environment
venv:
	python -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

# Update dependencies
update:
	pip install --upgrade pip
	pip install -r requirements.txt --upgrade

# Generate requirements.txt from pyproject.toml (if using poetry)
freeze:
	pip freeze > requirements.txt

# Health check
health:
	curl -f http://localhost:8000/api/v1/health || echo "Service not running"

# Setup development environment
setup: venv dev
	@echo "Development environment setup complete!"
	@echo "1. Activate virtual environment: source venv/bin/activate"
	@echo "2. Copy .env.example to .env and update API keys"
	@echo "3. Run: make run"