.PHONY: help install dev test lint format clean run migrate shell docs

# Default target
help:
	@echo "Task Management API - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install    Install dependencies"
	@echo "  make dev        Set up development environment"
	@echo ""
	@echo "Development:"
	@echo "  make run        Run development server"
	@echo "  make shell      Open Python shell with app context"
	@echo "  make migrate    Run database migrations"
	@echo "  make seed       Seed sample data"
	@echo ""
	@echo "Testing:"
	@echo "  make test       Run all tests"
	@echo "  make test-unit  Run unit tests only"
	@echo "  make test-cov   Run tests with coverage"
	@echo "  make test-watch Run tests in watch mode"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint       Run linters"
	@echo "  make format     Format code"
	@echo "  make type       Run type checking"
	@echo "  make quality    Run all quality checks"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs       Build documentation"
	@echo "  make docs-serve Serve documentation locally"
	@echo ""
	@echo "Database:"
	@echo "  make db-upgrade    Apply migrations"
	@echo "  make db-downgrade  Rollback last migration"
	@echo "  make db-reset      Reset database"
	@echo "  make db-revision   Create new migration"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-run    Run in Docker"
	@echo "  make docker-test   Run tests in Docker"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean      Remove generated files"

# Setup commands
install:
	pip install -r requirements.txt

dev: install
	cp .env.example .env
	@echo "Environment file created. Please update .env with your settings."
	pre-commit install
	@echo "Development environment ready!"

# Development commands
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

shell:
	python -c "from app.main import app; from app.core.database import SessionLocal; import IPython; IPython.embed()"

migrate:
	alembic upgrade head

seed:
	python scripts/seed_data.py

# Testing commands
test:
	pytest

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

test-watch:
	ptw -- --testmon

# Code quality commands
lint:
	flake8 app tests
	mypy app

format:
	black app tests
	isort app tests

type:
	mypy app

quality: lint type test

# Documentation commands
docs:
	mkdocs build

docs-serve:
	mkdocs serve

# Database commands
db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-reset:
	alembic downgrade base
	alembic upgrade head

db-revision:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

# Docker commands
docker-build:
	docker build -f docker/Dockerfile.dev -t task-api:dev .

docker-run:
	docker-compose up

docker-test:
	docker-compose run --rm api pytest

docker-down:
	docker-compose down

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".tox" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +

# Production commands
prod-build:
	docker build -f docker/Dockerfile.prod -t task-api:latest .

prod-deploy:
	@echo "Deploy command should be configured for your infrastructure"

# Performance testing
perf-test:
	locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Security
security-check:
	bandit -r app
	safety check

# Git hooks
pre-commit:
	pre-commit run --all-files