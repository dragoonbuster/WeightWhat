# Task Management API - Directory Structure

```
sample_project/
├── app/                        # Application source code
│   ├── __init__.py
│   ├── main.py                # FastAPI application entry point
│   ├── api/                   # API endpoints
│   │   ├── __init__.py
│   │   ├── deps.py           # Common dependencies
│   │   └── v1/               # API version 1
│   │       ├── __init__.py
│   │       ├── auth.py       # Authentication endpoints
│   │       ├── tasks.py      # Task management endpoints
│   │       ├── projects.py   # Project endpoints
│   │       ├── teams.py      # Team endpoints
│   │       └── users.py      # User endpoints
│   ├── core/                  # Core application components
│   │   ├── __init__.py
│   │   ├── config.py         # Application configuration
│   │   ├── security.py       # Security utilities
│   │   ├── database.py       # Database connection
│   │   └── exceptions.py     # Custom exceptions
│   ├── models/                # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py          # User model
│   │   ├── task.py          # Task model
│   │   ├── project.py       # Project model
│   │   └── team.py          # Team model
│   ├── schemas/               # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py          # User schemas
│   │   ├── task.py          # Task schemas
│   │   ├── project.py       # Project schemas
│   │   └── team.py          # Team schemas
│   ├── services/              # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication service
│   │   ├── task.py          # Task service
│   │   ├── project.py       # Project service
│   │   ├── notification.py  # Notification service
│   │   └── search.py        # Search service
│   └── utils/                 # Utility functions
│       ├── __init__.py
│       ├── pagination.py    # Pagination helpers
│       ├── validators.py    # Custom validators
│       └── email.py         # Email utilities
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── conftest.py           # Pytest configuration
│   ├── unit/                 # Unit tests
│   │   ├── __init__.py
│   │   ├── test_auth.py
│   │   ├── test_models.py
│   │   └── test_services.py
│   ├── integration/          # Integration tests
│   │   ├── __init__.py
│   │   ├── test_api_auth.py
│   │   ├── test_api_tasks.py
│   │   └── test_api_projects.py
│   └── performance/          # Performance tests
│       ├── __init__.py
│       └── locustfile.py
├── alembic/                   # Database migrations
│   ├── alembic.ini
│   ├── env.py
│   ├── script.py.mako
│   └── versions/             # Migration files
│       └── .gitkeep
├── scripts/                   # Utility scripts
│   ├── create_admin.py       # Create admin user
│   ├── seed_data.py          # Seed sample data
│   └── backup_db.sh          # Database backup
├── docs/                      # Documentation
│   ├── api/                  # API documentation
│   │   └── openapi.json     # OpenAPI spec
│   ├── specs/                # Technical specifications
│   │   └── API_SPEC.md      # API specification
│   ├── architecture/         # Architecture docs
│   │   ├── README.md        # Architecture overview
│   │   └── decisions/       # ADRs
│   └── guides/               # User guides
│       ├── setup.md         # Setup guide
│       └── deployment.md    # Deployment guide
├── .github/                   # GitHub configuration
│   ├── workflows/            # GitHub Actions
│   │   ├── test.yml         # Test workflow
│   │   └── deploy.yml       # Deploy workflow
│   └── ISSUE_TEMPLATE/       # Issue templates
├── docker/                    # Docker files
│   ├── Dockerfile.dev        # Development image
│   └── Dockerfile.prod       # Production image
├── .env.example              # Environment template
├── .gitignore                # Git ignore file
├── .pre-commit-config.yaml   # Pre-commit hooks
├── CLAUDE.md                 # AI assistant context
├── README.md                 # Project documentation
├── TASK_LIST.md              # Development tasks
├── DIRECTORY_STRUCTURE.md    # This file
├── alembic.ini               # Alembic configuration
├── docker-compose.yml        # Docker compose
├── Makefile                  # Common commands
├── pyproject.toml            # Python project config
└── requirements.txt          # Python dependencies
```

## Key Directories

### `/app` - Application Code
Contains all the application source code organized by responsibility:
- `api/` - RESTful API endpoints
- `core/` - Core utilities and configuration
- `models/` - Database models
- `schemas/` - Request/response schemas
- `services/` - Business logic
- `utils/` - Helper functions

### `/tests` - Test Suite
Comprehensive test coverage:
- `unit/` - Isolated unit tests
- `integration/` - API integration tests
- `performance/` - Load and performance tests

### `/docs` - Documentation
All project documentation:
- `specs/` - Technical specifications
- `architecture/` - Design decisions
- `guides/` - User and developer guides

### `/scripts` - Utilities
Helpful scripts for development:
- Database management
- Data seeding
- Admin tasks

### `/alembic` - Migrations
Database schema version control:
- Migration scripts
- Version history

## File Naming Conventions

- Python files: `snake_case.py`
- Test files: `test_*.py`
- Documentation: `UPPER_CASE.md` for top-level, `lower_case.md` for subdirs
- Config files: `.lowercase` or `lowercase.ext`

## Import Structure

```python
# Absolute imports from app
from app.core.config import settings
from app.models.task import Task
from app.schemas.task import TaskCreate
from app.services.task import TaskService

# Relative imports within module
from .deps import get_current_user
from ..core.security import verify_password
```