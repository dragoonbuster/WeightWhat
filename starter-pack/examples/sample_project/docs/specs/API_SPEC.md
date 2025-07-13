# Task Management API Specification

Version: 1.0.0  
Last Updated: 2025-07-13

## Overview

The Task Management API provides a comprehensive RESTful interface for managing tasks, projects, teams, and users. This specification defines all endpoints, request/response formats, authentication requirements, and error handling.

## Base URL

```
Production: https://api.taskmanager.com
Staging: https://staging-api.taskmanager.com
Development: http://localhost:8000
```

## Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Token Lifecycle
- Access tokens expire after 1 hour
- Refresh tokens expire after 30 days
- Use the refresh endpoint to get new access tokens

## Common Headers

| Header | Required | Description |
|--------|----------|-------------|
| Authorization | Yes* | Bearer token for authenticated endpoints |
| Content-Type | Yes | application/json for all requests with body |
| X-API-Version | No | API version (defaults to latest) |
| X-Request-ID | No | Unique request identifier for tracing |

*Not required for auth endpoints

## Response Format

All responses follow a consistent format:

### Success Response
```json
{
  "status": "success",
  "data": {
    // Response data
  },
  "meta": {
    "timestamp": "2025-07-13T10:00:00Z",
    "version": "1.0.0"
  }
}
```

### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "title",
        "message": "Title is required"
      }
    ]
  },
  "meta": {
    "timestamp": "2025-07-13T10:00:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Pagination

List endpoints support pagination:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| limit | integer | 20 | Items per page (max 100) |
| sort | string | -created_at | Sort field and direction |

Response includes pagination metadata:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

## API Endpoints

### Authentication

#### Register User
```
POST /api/v1/auth/register
```

Request:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe"
}
```

Response:
```json
{
  "status": "success",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "John Doe",
      "created_at": "2025-07-13T10:00:00Z"
    },
    "tokens": {
      "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "token_type": "bearer",
      "expires_in": 3600
    }
  }
}
```

#### Login
```
POST /api/v1/auth/login
```

Request:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

Response: Same as register

#### Refresh Token
```
POST /api/v1/auth/refresh
```

Request:
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Response:
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

### Tasks

#### List Tasks
```
GET /api/v1/tasks
```

Query Parameters:
- `project_id` - Filter by project
- `assigned_to` - Filter by assignee user ID
- `status` - Filter by status (todo, in_progress, done)
- `priority` - Filter by priority (low, medium, high, critical)
- `due_before` - Filter by due date (ISO 8601)
- `due_after` - Filter by due date (ISO 8601)
- `search` - Full-text search in title and description

Response:
```json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Implement user authentication",
      "description": "Add JWT authentication to the API",
      "status": "in_progress",
      "priority": "high",
      "due_date": "2025-07-20T23:59:59Z",
      "project": {
        "id": "660e8400-e29b-41d4-a716-446655440000",
        "name": "API Development"
      },
      "assignee": {
        "id": "770e8400-e29b-41d4-a716-446655440000",
        "full_name": "Jane Smith"
      },
      "created_by": {
        "id": "880e8400-e29b-41d4-a716-446655440000",
        "full_name": "John Doe"
      },
      "created_at": "2025-07-13T10:00:00Z",
      "updated_at": "2025-07-13T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "pages": 3
  }
}
```

#### Create Task
```
POST /api/v1/tasks
```

Request:
```json
{
  "title": "Implement user authentication",
  "description": "Add JWT authentication to the API",
  "project_id": "660e8400-e29b-41d4-a716-446655440000",
  "priority": "high",
  "due_date": "2025-07-20T23:59:59Z",
  "assigned_to": "770e8400-e29b-41d4-a716-446655440000",
  "tags": ["backend", "security"]
}
```

Response:
```json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Implement user authentication",
    "description": "Add JWT authentication to the API",
    "status": "todo",
    "priority": "high",
    "due_date": "2025-07-20T23:59:59Z",
    "project_id": "660e8400-e29b-41d4-a716-446655440000",
    "assigned_to": "770e8400-e29b-41d4-a716-446655440000",
    "created_by": "880e8400-e29b-41d4-a716-446655440000",
    "tags": ["backend", "security"],
    "created_at": "2025-07-13T10:00:00Z"
  }
}
```

#### Get Task
```
GET /api/v1/tasks/{task_id}
```

Response: Same as create task response

#### Update Task
```
PUT /api/v1/tasks/{task_id}
```

Request: Same as create (all fields optional)

Response: Updated task object

#### Delete Task
```
DELETE /api/v1/tasks/{task_id}
```

Response:
```json
{
  "status": "success",
  "data": {
    "message": "Task deleted successfully"
  }
}
```

#### Update Task Status
```
PATCH /api/v1/tasks/{task_id}/status
```

Request:
```json
{
  "status": "in_progress"
}
```

Response: Updated task object

### Projects

#### List Projects
```
GET /api/v1/projects
```

Query Parameters:
- `team_id` - Filter by team
- `owned_by` - Filter by owner user ID
- `search` - Search in name and description

Response:
```json
{
  "status": "success",
  "data": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "name": "API Development",
      "description": "Core API development project",
      "color": "#3B82F6",
      "owner": {
        "id": "880e8400-e29b-41d4-a716-446655440000",
        "full_name": "John Doe"
      },
      "team": {
        "id": "990e8400-e29b-41d4-a716-446655440000",
        "name": "Backend Team"
      },
      "task_count": 25,
      "completed_task_count": 10,
      "created_at": "2025-07-01T10:00:00Z"
    }
  ]
}
```

#### Create Project
```
POST /api/v1/projects
```

Request:
```json
{
  "name": "API Development",
  "description": "Core API development project",
  "color": "#3B82F6",
  "team_id": "990e8400-e29b-41d4-a716-446655440000"
}
```

Response: Created project object

#### Get Project Tasks
```
GET /api/v1/projects/{project_id}/tasks
```

Query Parameters: Same as list tasks

Response: List of tasks for the project

### Teams

#### List Teams
```
GET /api/v1/teams
```

Response:
```json
{
  "status": "success",
  "data": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440000",
      "name": "Backend Team",
      "description": "API and backend development",
      "member_count": 5,
      "project_count": 3,
      "created_at": "2025-06-15T10:00:00Z"
    }
  ]
}
```

#### Create Team
```
POST /api/v1/teams
```

Request:
```json
{
  "name": "Backend Team",
  "description": "API and backend development"
}
```

Response: Created team object

#### Add Team Member
```
POST /api/v1/teams/{team_id}/members
```

Request:
```json
{
  "user_id": "770e8400-e29b-41d4-a716-446655440000",
  "role": "member"
}
```

Response:
```json
{
  "status": "success",
  "data": {
    "message": "Member added successfully"
  }
}
```

### Users

#### Get Current User
```
GET /api/v1/users/me
```

Response:
```json
{
  "status": "success",
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "avatar_url": "https://api.taskmanager.com/avatars/user.jpg",
    "created_at": "2025-07-13T10:00:00Z",
    "preferences": {
      "notifications_enabled": true,
      "theme": "light",
      "timezone": "UTC"
    }
  }
}
```

#### Update User Profile
```
PUT /api/v1/users/me
```

Request:
```json
{
  "full_name": "John Doe",
  "avatar_url": "https://api.taskmanager.com/avatars/user.jpg",
  "preferences": {
    "notifications_enabled": true,
    "theme": "dark",
    "timezone": "America/New_York"
  }
}
```

Response: Updated user object

### Search

#### Global Search
```
GET /api/v1/search
```

Query Parameters:
- `q` - Search query (required)
- `type` - Filter by type (task, project, user)
- `limit` - Results per type (default 5)

Response:
```json
{
  "status": "success",
  "data": {
    "tasks": [...],
    "projects": [...],
    "users": [...]
  }
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| UNAUTHORIZED | 401 | Missing or invalid authentication |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| VALIDATION_ERROR | 400 | Invalid input data |
| DUPLICATE_ENTRY | 409 | Resource already exists |
| RATE_LIMITED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |

## Rate Limiting

- 100 requests per minute for authenticated users
- 20 requests per minute for unauthenticated users
- Headers included in response:
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

## Webhooks

Configure webhooks to receive real-time notifications:

### Webhook Events
- `task.created`
- `task.updated`
- `task.deleted`
- `task.status_changed`
- `project.created`
- `project.updated`
- `team.member_added`
- `team.member_removed`

### Webhook Payload
```json
{
  "event": "task.created",
  "timestamp": "2025-07-13T10:00:00Z",
  "data": {
    // Event-specific data
  }
}
```

## SDK Examples

### Python
```python
from taskmanager import Client

client = Client(api_key="your-api-key")

# Create a task
task = client.tasks.create(
    title="New feature",
    project_id="project-id",
    priority="high"
)

# List tasks
tasks = client.tasks.list(status="todo", limit=10)
```

### JavaScript
```javascript
const TaskManager = require('taskmanager-js');

const client = new TaskManager({ apiKey: 'your-api-key' });

// Create a task
const task = await client.tasks.create({
  title: 'New feature',
  projectId: 'project-id',
  priority: 'high'
});

// List tasks
const tasks = await client.tasks.list({ 
  status: 'todo', 
  limit: 10 
});
```

## Changelog

### Version 1.0.0 (2025-07-13)
- Initial API release
- Core task management functionality
- Team collaboration features
- JWT authentication
- Webhook support