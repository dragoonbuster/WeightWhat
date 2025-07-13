# Task Management API - AI Assistant Context

Last Updated: 2025-07-13

## Project Overview

Task Management API is a RESTful web service that provides comprehensive task and project management capabilities. Users can create projects, manage tasks with priorities and deadlines, assign tasks to team members, and track progress through customizable workflows.

### Core Value Proposition
- **Simple yet powerful** - Clean API design that scales from personal to enterprise use
- **Real-time collaboration** - WebSocket support for live updates
- **Flexible workflows** - Customizable task states and transitions
- **Rich integrations** - Webhook support for external tools

## Current Implementation Status (July 2025)

### Completed Features
- **Core API Infrastructure**
  - FastAPI framework with async support
  - PostgreSQL database with SQLAlchemy ORM
  - JWT authentication with role-based access control
  - Comprehensive OpenAPI documentation

- **Task Management**
  - CRUD operations for tasks and projects
  - Priority levels (critical, high, medium, low)
  - Due date tracking with reminder system
  - Task assignment and ownership

- **User System**
  - User registration and authentication
  - Team creation and management
  - Role-based permissions (admin, member, viewer)
  - User profile management

### In Progress
- WebSocket implementation for real-time updates
- Advanced search and filtering
- Task templates and recurring tasks
- Email notification system

### Planned (Not Started)
- Mobile API optimizations
- Bulk operations endpoints
- Analytics and reporting API
- Third-party integrations (Slack, GitHub)

### Known Issues
- Pagination performance degrades with large datasets
- WebSocket connection handling needs improvement
- Some edge cases in permission checking
- Task history tracking incomplete

## Recent Changes (July 10-13, 2025)

1. **Performance Improvements**
   - Optimized database queries with eager loading
   - Added Redis caching for frequently accessed data
   - Implemented connection pooling

2. **API Enhancements**
   - Added bulk task creation endpoint
   - Improved error messages and status codes
   - Enhanced filtering capabilities

3. **Security Updates**
   - Implemented rate limiting
   - Added API key authentication option
   - Enhanced input validation

4. **Bug Fixes**
   - Fixed task assignment notification bug
   - Resolved timezone handling issues
   - Fixed pagination edge cases

## Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use type hints throughout
- Write descriptive variable and function names
- Keep functions small and focused
- Document complex logic inline

### API Design Principles
- RESTful conventions strictly followed
- Consistent response formats
- Meaningful HTTP status codes
- Clear and descriptive error messages
- Version API endpoints when breaking changes occur

### Git Commit Standards
- Use conventional commits format
- Prefix: feat, fix, docs, style, refactor, test, chore
- Subject line: 50 characters max
- Body: Explain what and why, not how

### Testing Requirements
- Minimum 80% test coverage
- Unit tests for all business logic
- Integration tests for API endpoints
- Performance tests for critical paths

## Technical Architecture

### Database Schema
- Projects -> Tasks (one-to-many)
- Users -> Tasks (many-to-many through assignments)
- Teams -> Users (many-to-many through memberships)
- Audit log for all changes

### API Structure
```
/api/v1/
  /auth/          # Authentication endpoints
  /users/         # User management
  /teams/         # Team operations
  /projects/      # Project CRUD
  /tasks/         # Task management
  /search/        # Advanced search
  /webhooks/      # Webhook configuration
```

### Security Model
- JWT tokens with 1-hour expiration
- Refresh tokens with 30-day expiration
- Row-level security for data isolation
- API rate limiting per user/IP

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker (optional)

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd sample_project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
alembic upgrade head

# Run development server
uvicorn app.main:app --reload
```

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@localhost/taskdb
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
```

## Testing

### Run Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_tasks.py

# Integration tests only
pytest tests/integration/
```

### Performance Testing
```bash
# Load testing with locust
locust -f tests/performance/locustfile.py
```

## API Examples

### Create a Task
```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement caching",
    "description": "Add Redis caching layer",
    "priority": "high",
    "project_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

### Get Project Tasks
```bash
curl http://localhost:8000/api/v1/projects/{project_id}/tasks \
  -H "Authorization: Bearer <token>"
```

## Deployment

### Production Checklist
- Set strong SECRET_KEY
- Enable HTTPS only
- Configure proper CORS
- Set up monitoring
- Enable structured logging
- Configure backups
- Set up CI/CD pipeline

### Docker Deployment
```bash
# Build image
docker build -t task-api .

# Run container
docker run -p 8000:8000 --env-file .env task-api
```

## Project Structure
```
sample_project/
├── app/
│   ├── api/              # API endpoints
│   │   ├── v1/           # Version 1 endpoints
│   │   └── deps.py       # Common dependencies
│   ├── core/             # Core configuration
│   │   ├── config.py     # Settings
│   │   └── security.py   # Auth utilities
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── main.py           # Application entry
├── tests/                # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── conftest.py       # Test fixtures
├── scripts/              # Utility scripts
├── docs/                 # Documentation
│   ├── specs/            # Technical specifications
│   └── architecture/     # Architecture decisions
├── alembic/              # Database migrations
├── requirements.txt      # Python dependencies
├── Dockerfile            # Container definition
└── .env.example          # Environment template
```

## Important Context for AI Assistants

### When Working on This Project:
1. **API First**: All features must be accessible via API
2. **Test Coverage**: Never merge code below 80% coverage
3. **Performance**: Consider scaling from day one
4. **Security**: Assume all input is malicious
5. **Documentation**: Update API docs with changes

### Common Pitfalls:
- Not handling pagination properly
- Forgetting to validate permissions
- Missing database indexes
- Not considering timezone issues
- Inadequate error handling

### Design Decisions:
- FastAPI chosen for async support and auto-documentation
- PostgreSQL for JSONB support and full-text search
- Redis for caching and real-time features
- JWT for stateless authentication

## Next Major Milestones

1. **v1.1 Release** (August 2025)
   - WebSocket support
   - Advanced search
   - Bulk operations

2. **v1.2 Release** (September 2025)
   - Mobile optimizations
   - Analytics API
   - Webhook improvements

3. **v2.0 Planning** (Q4 2025)
   - GraphQL API
   - Microservices split
   - Enterprise features

## Remember
- **API consistency** is paramount
- **Performance** matters at scale
- **Security** is not optional
- **Tests** prevent regressions
- **Documentation** helps everyone
- Keep commits atomic and meaningful
- Review your own code first
- Ask for help when stuck