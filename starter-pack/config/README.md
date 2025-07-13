# Configuration Templates for TickerTape

This directory contains essential configuration file templates for the TickerTape project.

## Files Included

### .env.example
Environment configuration template with all available settings:
- Database connections (PostgreSQL/SQLite)
- API configuration
- Security keys
- External service credentials
- Feature flags
- Email settings
- Logging configuration

**Usage:**
```bash
cp .env.example .env
# Edit .env with your actual values
```

### .gitignore
Comprehensive gitignore file covering:
- Python artifacts
- Node.js artifacts
- Virtual environments
- IDE settings
- OS files
- Sensitive files
- Database files
- Logs and temporary files

**Usage:**
```bash
cp .gitignore ../../.gitignore
```

### docker-compose.yml
Main Docker Compose configuration including:
- Web application service
- PostgreSQL database
- Redis cache
- Celery worker and beat
- Nginx (production profile)
- pgAdmin and Redis Commander (development profile)

**Usage:**
```bash
# Development
docker-compose up

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

### docker-compose.dev.yml
Development-specific overrides:
- Debug mode enabled
- Volume mounts for hot reloading
- Additional development tools (Mailhog, docs server)
- Exposed ports for debugging

### docker-compose.prod.yml
Production-specific overrides:
- Optimized settings
- Resource limits
- Monitoring stack (Prometheus/Grafana)
- Backup service
- Multiple replicas

### pytest.ini
Testing configuration with:
- Parallel test execution
- Coverage reporting (80% minimum)
- Test markers for organization
- Comprehensive output options
- Async support

**Usage:**
```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run without slow tests
pytest -m "not slow"

# Run with specific coverage
pytest --cov-fail-under=90
```

## Quick Start

1. Copy all configuration files to project root:
```bash
cp .env.example ../../.env
cp .gitignore ../../.gitignore
cp docker-compose*.yml ../../
cp pytest.ini ../../
```

2. Update .env with your values:
```bash
# Generate secure keys
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

3. Start development environment:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

4. Run tests:
```bash
pytest
```

## Security Notes

- Never commit .env files
- Always use strong, unique keys in production
- Rotate keys regularly
- Use environment-specific configurations
- Enable HTTPS in production

## Docker Profiles

- **default**: Core services only
- **development**: Includes pgAdmin, Redis Commander, Mailhog
- **production**: Includes Nginx, backup service
- **monitoring**: Includes Prometheus and Grafana