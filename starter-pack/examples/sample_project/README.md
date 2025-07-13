# Task Management API

A modern, scalable REST API for task and project management built with FastAPI and PostgreSQL.

## Features

- **Task Management**: Create, update, and track tasks with priorities and deadlines
- **Project Organization**: Group tasks into projects with customizable workflows  
- **Team Collaboration**: Assign tasks, manage permissions, and track progress
- **Real-time Updates**: WebSocket support for live notifications (coming soon)
- **Rich API**: Comprehensive REST API with OpenAPI documentation
- **Secure**: JWT authentication with role-based access control

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+ (for caching)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sample_project
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the development server:
```bash
uvicorn app.main:app --reload
```

7. Access the API documentation at `http://localhost:8000/docs`

## API Overview

### Authentication
- `POST /api/v1/auth/register` - Create new account
- `POST /api/v1/auth/login` - Get access token
- `POST /api/v1/auth/refresh` - Refresh access token

### Tasks
- `GET /api/v1/tasks` - List tasks (with filtering)
- `POST /api/v1/tasks` - Create new task
- `GET /api/v1/tasks/{id}` - Get task details
- `PUT /api/v1/tasks/{id}` - Update task
- `DELETE /api/v1/tasks/{id}` - Delete task

### Projects
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}/tasks` - Get project tasks

See full API documentation at `/docs` when running the server.

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_tasks.py
```

### Code Style
```bash
# Format code
black .

# Lint code
flake8

# Type checking
mypy .
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

## Project Structure

```
sample_project/
├── app/                  # Application code
│   ├── api/             # API endpoints
│   ├── core/            # Core utilities
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   └── services/        # Business logic
├── tests/               # Test suite
├── docs/                # Documentation
│   └── specs/          # Technical specifications
├── scripts/             # Utility scripts
└── alembic/             # Database migrations
```

## Documentation

- [API Specification](docs/specs/API_SPEC.md) - Detailed API documentation
- [Architecture Guide](docs/architecture/README.md) - System design and decisions
- [Development Guide](docs/DEVELOPMENT.md) - Setup and contribution guidelines
- [AI Context](CLAUDE.md) - Context for AI assistants

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please read our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: See `/docs` directory
- API Issues: Create an issue on GitHub
- Security: Email security@example.com

## Acknowledgments

- FastAPI for the excellent web framework
- PostgreSQL for the robust database
- The Python community for amazing tools