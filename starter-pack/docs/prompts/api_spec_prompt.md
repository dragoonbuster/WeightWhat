# API Contracts Specification Prompt (Generic Template)

Create a focused API_CONTRACTS.md specification for [PROJECT_NAME] that establishes contract-driven development principles and patterns. This specification should be **8-10 pages** and serve as a concise guide for API design consistency across all endpoints.

## Context
[PROJECT_NAME] requires a consistent API design that supports [LIST_CLIENT_TYPES: e.g., web, mobile, desktop] and enables parallel development through clear contracts. The specification should establish patterns once and apply them universally.

## Document Requirements
- **Target Length**: 8-10 pages maximum
- **Focus**: Design patterns and principles over exhaustive endpoint documentation
- **Format**: Tables, bullet points, and concise examples
- **References**: Link to OpenAPI schemas for detailed endpoint specifications

## Core Sections (with page allocations)

### 1. API Design Principles (1 page)
Establish foundational principles in a concise table format:
- RESTful resource design patterns
- Statelessness and idempotency requirements
- Performance guidelines (response times, payload limits)
- Security-first approach
- HATEOAS implementation strategy (if applicable)

### 2. Contract Standards (2 pages)
Define the contract methodology and patterns:

**2.1 OpenAPI Specification Standards**
- Version: OpenAPI 3.1
- File organization pattern
- Schema reuse strategy
- Example of ONE complete resource definition ([PRIMARY_RESOURCE_NAME]):
  ```yaml
  components:
    schemas:
      [ResourceName]:
        type: object
        required: [id, field1, field2]
        # Show pattern once, apply everywhere
  ```

**2.2 Universal Patterns**
Table format showing patterns applied to ALL resources:
| Pattern | Implementation | Example |
|---------|---------------|---------|
| Pagination | [PAGINATION_STYLE: cursor/offset] | `?cursor=xyz&limit=20` |
| Filtering | field-based | `?status=active&[field]=[value]` |
| Sorting | multi-field | `?sort=-created_at,name` |
| Field selection | sparse fieldsets | `?fields=id,name,status` |

### 3. Versioning & Evolution (1 page)
Concise versioning strategy:
- Versioning approach ([VERSIONING_STRATEGY: URL path/header/query])
- Breaking change definition (bullet list)
- Deprecation timeline (simple table)
- Version discovery endpoint specification

### 4. Authentication & Authorization (1.5 pages)
Single, comprehensive authentication pattern:
- [AUTH_METHOD: JWT/OAuth2/API Key] flow (one diagram)
- Token/credential lifecycle table
- Authorization matrix for resource access
- Example authorization header usage

### 5. Request/Response Contracts (1.5 pages)
Universal patterns for all endpoints:

**5.1 Standard Request Format**
```json
{
  "data": { /* resource data */ },
  "meta": { /* request metadata */ }
}
```

**5.2 Standard Response Format**
```json
{
  "data": { /* resource or collection */ },
  "meta": { /* pagination, etc */ },
  "links": { /* HATEOAS links */ }
}
```

**5.3 Error Response Format**
Single, consistent error structure for ALL errors:
```json
{
  "error": {
    "code": "STANDARD_ERROR_CODE",
    "message": "Human readable message",
    "details": { /* context specific */ },
    "request_id": "req_123"
  }
}
```

### 6. Standard Operations (1 page)
Matrix showing standard operations for ALL resources:
| Operation | Method | Path | Status | Response |
|-----------|--------|------|--------|----------|
| List | GET | /resources | 200 | Collection |
| Create | POST | /resources | 201 | Resource + Location |
| Read | GET | /resources/:id | 200 | Resource |
| Update | PUT | /resources/:id | 200 | Resource |
| Patch | PATCH | /resources/:id | 200 | Resource |
| Delete | DELETE | /resources/:id | 204 | Empty |

### 7. Testing & Mocking (1 page)
Contract testing approach:
- Consumer-driven contract pattern
- Mock server configuration ([MOCK_TOOL: Prism/WireMock/etc])
- Contract test example (one [TEST_FRAMEWORK: Pact/Spring Cloud Contract] test)
- CI/CD integration checklist

### 8. Implementation Guidelines (1 page)
Quick reference for developers:

**8.1 Naming Conventions Table**
| Element | Convention | Example |
|---------|------------|---------|
| Resources | [RESOURCE_NAMING: plural/singular] nouns | `/resources` |
| Query params | [PARAM_CASE: camelCase/snake_case] | `paramName` |
| Response fields | [FIELD_CASE: snake_case/camelCase] | `field_name` |
| Headers | [HEADER_CASE: Kebab-Case/Title-Case] | `X-Header-Name` |

**8.2 Status Code Quick Reference**
Group by category with clear use cases:
- 2xx: Success patterns
- 4xx: Client error patterns
- 5xx: Server error patterns

## Deliverable Requirements

Create an API_CONTRACTS.md that:
1. Establishes patterns ONCE and references them throughout
2. Uses tables and matrices to compress information
3. Shows complete examples only where patterns are introduced
4. References external OpenAPI files for detailed schemas
5. Focuses on the "why" of decisions, not just the "what"
6. Includes a one-page quick reference card for developers

## What to Exclude
- Individual endpoint documentation (use OpenAPI files)
- Repetitive examples of the same pattern
- Implementation code (reference pattern libraries)
- Verbose explanations where tables suffice
- Historical decisions or alternatives considered

## Writing Style
- Use imperative mood ("Use JWT tokens" not "We will use JWT tokens")
- Prefer tables over prose for specifications
- Show patterns through minimal, clear examples
- Group related concepts to avoid repetition
- Focus on rules and exceptions, not edge cases

## Project-Specific Placeholders Guide

When using this template, replace the following placeholders:
- `[PROJECT_NAME]`: Your project name
- `[LIST_CLIENT_TYPES]`: Supported client types (e.g., "web, mobile, CLI")
- `[PRIMARY_RESOURCE_NAME]`: Main resource for examples (e.g., "User", "Product")
- `[PAGINATION_STYLE]`: Choose cursor-based or offset-based
- `[VERSIONING_STRATEGY]`: Choose URL path, header, or query parameter
- `[AUTH_METHOD]`: Your authentication method (JWT, OAuth2, API Key, etc.)
- `[MOCK_TOOL]`: Your preferred mock server tool
- `[TEST_FRAMEWORK]`: Your contract testing framework
- `[RESOURCE_NAMING]`: plural or singular convention
- `[PARAM_CASE]`: camelCase or snake_case for query parameters
- `[FIELD_CASE]`: snake_case or camelCase for response fields
- `[HEADER_CASE]`: Kebab-Case or Title-Case for headers

The final document should be a practical reference that developers can quickly scan to understand API patterns and make consistent implementation decisions without reading extensive documentation.