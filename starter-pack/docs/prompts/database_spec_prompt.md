# Database Schema Specification Prompt (Generic Template)

You are a database architect with expertise in schema design. Create a focused specification document titled "DATABASE_SCHEMA.md" in the docs/specs/ directory for [PROJECT_NAME]'s database schema and relationships.

## Context
[PROJECT_NAME] uses [ORM_FRAMEWORK] with support for multiple database backends (PostgreSQL, MySQL, SQLite). The system [BRIEF_DESCRIPTION_OF_CORE_FUNCTIONALITY].

## Document Requirements

Target Length: **8-10 pages**
Focus: Schema design, relationships, and key constraints
Implementation: Reference patterns only, defer details to implementation specs

## Core Sections

### 1. Executive Summary (1 page)
- Database architecture overview in 3-4 paragraphs
- Key design decisions table (decision, rationale)
- Technology stack: [PRIMARY_DB] primary, [SECONDARY_DB] development
- Performance targets summary

### 2. Entity Relationship Design (2 pages)

#### 2.1 Complete ERD
Provide a Mermaid diagram showing all entities and relationships

#### 2.2 Core Table Groups
**Authentication System**: users, sessions, permissions, roles
**[CORE_ENTITY_1] System**: [entity], [entity_history], [entity_metadata]
**[CORE_ENTITY_2] System**: [entity], [entity_relationships]
**[BUSINESS_LOGIC] System**: [relevant_tables]
**System Tables**: audit_logs, background_jobs, system_events

### 3. Schema Definitions (3-4 pages)

Use condensed table format focusing on key fields:

```markdown
## Core Tables

### users
- id: [UUID/BIGINT] (PK)
- username: VARCHAR(50) UNIQUE
- email: VARCHAR(255) UNIQUE
- hashed_password: VARCHAR(255)
- is_active, email_verified: BOOLEAN
- created_at, updated_at: TIMESTAMP
- Indexes: username, email, (is_active, created_at)

### [core_entity]
- id: [UUID/BIGINT] (PK)
- user_id: [UUID/BIGINT] (FK users)
- name, description: TEXT
- status: ENUM([status_values])
- metadata: JSON/JSONB
- [domain_specific_fields]
- Indexes: user_id, status, created_at

[Continue for all tables...]
```

Include only:
- Primary keys and foreign keys
- Unique constraints
- Critical business fields
- Key indexes

### 4. Relationships and Constraints (1-2 pages)

#### 4.1 Foreign Key Relationships
Table format: Parent -> Child (constraint type, cascade behavior)

Example:
| Parent | Child | Constraint | On Delete | On Update |
|--------|-------|------------|-----------|-----------|
| users | sessions | user_id FK | CASCADE | CASCADE |
| users | [entity] | user_id FK | CASCADE | CASCADE |

#### 4.2 Business Constraints
- Check constraints for enums and ranges
- Unique composite keys
- Conditional unique indexes
- Domain-specific validation rules

#### 4.3 Data Integrity Rules
- Required vs optional relationships
- Cascade vs restrict behaviors
- Orphan prevention strategies
- Referential integrity patterns

### 5. Index Strategy (1 page)

#### 5.1 Index Categories
- Primary/Foreign keys (automatic)
- Query optimization indexes
- Full-text search indexes
- JSON/JSONB GIN indexes (PostgreSQL)
- Covering indexes for read-heavy queries

#### 5.2 Key Index Patterns
Show 3-4 critical examples only:
```sql
-- High-frequency user queries
CREATE INDEX idx_[entity]_user_recent 
ON [entity](user_id, created_at DESC) 
WHERE is_active = true;

-- Text search optimization
CREATE INDEX idx_[entity]_search 
ON [entity] USING gin(to_tsvector('english', name || ' ' || description));

-- JSON field queries (PostgreSQL)
CREATE INDEX idx_[entity]_metadata 
ON [entity] USING gin(metadata);
```

### 6. Database-Specific Considerations (1 page)

#### 6.1 Cross-Database Compatibility
Quick reference table:
| Feature | PostgreSQL | MySQL | SQLite |
|---------|------------|--------|---------|
| UUID | Native UUID | CHAR(36) | TEXT(36) |
| Arrays | ARRAY type | JSON | JSON |
| JSON | JSONB | JSON | JSON |
| Full-text | tsvector | FULLTEXT | FTS5 |
| Enums | CREATE TYPE | ENUM() | CHECK |

#### 6.2 Migration Strategy
- Schema versioning approach
- Forward/backward compatibility
- Zero-downtime migration patterns
- Rollback procedures

### 7. Performance and Monitoring (1 page)

#### 7.1 Query Performance Targets
- Simple lookups: < 10ms
- List/filter queries: < 50ms
- Dashboard aggregations: < 200ms
- Complex reports: < 1000ms

#### 7.2 Scaling Considerations
- Partition strategy for large tables
- Archive policy for historical data
- Read replica requirements
- Connection pooling guidelines

#### 7.3 Monitoring Requirements
- Slow query logging thresholds
- Index usage tracking
- Table size monitoring
- Vacuum/analyze schedule (PostgreSQL)

## Writing Guidelines

1. **Use Tables Over Prose**: Convert descriptions to structured tables
2. **Visual First**: Include ERD diagrams for all relationships
3. **Focus on Structure**: Schema and relationships over implementation
4. **Compress Examples**: Show patterns, not every variation
5. **Database Agnostic**: Design for portability where possible

## Common Patterns to Consider

### Authentication & Authorization
- User registration and login
- Session management
- Role-based permissions
- API key management

### Audit & Compliance
- Change tracking (who, what, when)
- Soft deletes vs hard deletes
- Data retention policies
- PII handling

### Multi-tenancy (if applicable)
- Tenant isolation strategy
- Cross-tenant queries
- Data segregation

### Time-series Data (if applicable)
- Partitioning strategy
- Data retention
- Aggregation tables

## Excluded Topics (Reference Other Specs)
- ORM implementation details → BACKEND_IMPLEMENTATION
- API query patterns → API_SPECIFICATION
- Caching strategy → PERFORMANCE_OPTIMIZATION
- Backup procedures → OPERATIONS_GUIDE
- Security implementation → SECURITY_SPECIFICATION

## Key Deliverables
1. Complete ERD diagram with all entities
2. All table definitions (condensed format)
3. Relationship mapping with constraints
4. Critical indexes for performance
5. Cross-database compatibility matrix
6. Migration strategy overview

## Placeholder Instructions
Replace the following placeholders with project-specific information:
- [PROJECT_NAME]: Your project name
- [ORM_FRAMEWORK]: e.g., SQLAlchemy, Django ORM, Prisma, TypeORM
- [PRIMARY_DB]: e.g., PostgreSQL, MySQL, MongoDB
- [SECONDARY_DB]: e.g., SQLite, H2, In-memory DB
- [BRIEF_DESCRIPTION_OF_CORE_FUNCTIONALITY]: 1-2 sentences about what the system does
- [CORE_ENTITY_1], [CORE_ENTITY_2]: Your main business entities
- [BUSINESS_LOGIC]: Core business domain (e.g., e-commerce, content management, analytics)

The specification should be a concise reference for schema structure and relationships, with implementation details deferred to specialized documents.