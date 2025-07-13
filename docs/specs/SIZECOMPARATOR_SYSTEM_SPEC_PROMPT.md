# SizeComparator System Specification Prompt (Optimized)

Create a focused SIZECOMPARATOR_SYSTEM_SPEC.md specification for a lightweight weight comparison web application. This specification should be **10 pages maximum** and serve as a comprehensive implementation guide for senior developers building an AI-powered comparison system.

## Context

SizeComparator is a minimalist web application that converts weight inputs (lbs/kg) into relatable object comparisons using AI providers (OpenAI, Anthropic, X.ai). The system emphasizes simplicity, reliability, and extensibility while avoiding complex dependencies and integration challenges. This is designed for rapid development with AI-assisted coding while maintaining production-quality architecture.

## Document Requirements

- **Target Length**: 10 pages maximum
- **Focus**: Lightweight architecture with robust AI integration patterns
- **Format**: Tables, bullet points, and essential code examples only
- **Approach**: Senior dev + PM methodology with parallel development support

## Core Sections (with page allocations)

### 1. Executive Summary & Architecture Overview (1.5 pages)

**Project Purpose**:
- Transform weight inputs into two AI-generated comparison suggestions
- Example: "24 lbs" → "four chickens (6 lbs each)" + "one car tire (24 lbs)"
- Emphasis on simplicity, reliability, and maintainability

**Key Architectural Decisions**:
- Frontend: Vanilla HTML/CSS/JS (no frameworks)
- Backend: Python FastAPI with async AI provider management
- AI Integration: Provider abstraction pattern with fallback/retry logic
- Storage: File-based configuration (no database overhead)
- Deployment: Single container or serverless functions

**Success Criteria**:
- Sub-2 second response times for weight comparisons
- 99% uptime with graceful AI provider failures
- Zero-maintenance deployment with configuration-driven prompts
- Easy addition of new AI providers without code changes

### 2. System Architecture & Component Design (2 pages)

**High-Level Architecture** (text-based diagram):
```
[Browser] → [Static Frontend] → [FastAPI Backend] → [AI Provider Manager]
                                       ↓                      ↓
                                 [Weight Parser]    [Multiple AI Providers]
                                       ↓                      ↓
                                [Response Formatter] ← [Prompt Templates]
```

**Core Components**:
- **Weight Parser**: Input validation and unit conversion
- **AI Provider Manager**: Abstract provider interface with retry/fallback
- **Prompt Template System**: Configuration-driven prompt management
- **Response Validator**: AI output validation and formatting
- **Theme Manager**: Light/dark mode state management

**Data Flow**:
1. User Input → Weight Parser (validation + normalization)
2. Normalized Weight → AI Provider Manager (parallel AI calls)
3. AI Responses → Response Validator (quality checks)
4. Validated Responses → Response Formatter (user display)

**Key Design Patterns**:
- **Provider Pattern**: Pluggable AI services
- **Template Method**: Standardized AI interaction flow
- **Circuit Breaker**: AI provider failure handling
- **Configuration Strategy**: Runtime behavior modification

### 3. AI Provider Integration Framework (2 pages)

**Provider Interface Design**:
```python
class AIProvider(ABC):
    @abstractmethod
    async def generate_comparisons(self, weight: Weight, context: Dict) -> List[Comparison]:
        """Generate weight comparisons using provider-specific API."""
        pass
    
    @abstractmethod
    def validate_response(self, response: Any) -> bool:
        """Validate provider response format and content."""
        pass
```

**Supported Providers Configuration Table**:
| Provider | API Type | Rate Limits | Fallback Priority | Cost/Request |
|----------|----------|-------------|------------------|--------------|
| OpenAI GPT-4 | REST | 3,500 RPM | 1 (Primary) | $0.03 |
| Anthropic Claude | REST | 1,000 RPM | 2 (Secondary) | $0.015 |
| X.ai Grok | REST | 500 RPM | 3 (Tertiary) | $0.01 |

**Retry & Fallback Strategy**:
- Primary provider failure → Immediate secondary attempt
- All providers down → Cached response or user-friendly error
- Rate limit hit → Exponential backoff with provider rotation
- Malformed response → Retry once, then fallback

**Prompt Template System**:
```python
# Configuration-driven prompts with validation
WEIGHT_COMPARISON_PROMPT = {
    "system": "You are a weight comparison expert...",
    "user_template": "Convert {weight} {unit} into exactly 2 relatable object comparisons...",
    "validation_rules": ["must_have_2_comparisons", "realistic_weights", "common_objects"],
    "max_tokens": 150,
    "temperature": 0.7
}
```

### 4. Frontend Implementation & Theme System (1.5 pages)

**Minimal Frontend Architecture**:
- Single HTML page with embedded CSS and JavaScript
- No build process or bundlers required
- Progressive enhancement for better UX
- Responsive design with CSS Grid/Flexbox

**Theme System Implementation**:
```javascript
// Light/dark mode with localStorage persistence
const ThemeManager = {
    init() { /* Load saved theme, set initial state */ },
    toggle() { /* Switch themes, save preference */ },
    apply(theme) { /* Update CSS custom properties */ }
};
```

**User Interface Components Table**:
| Component | Functionality | Implementation |
|-----------|--------------|-----------------|
| Weight Input | Number + unit selection | HTML5 input with validation |
| Submit Button | Trigger comparison | Async fetch with loading state |
| Results Display | Show 2 comparisons | Dynamic DOM updates |
| Theme Toggle | Light/dark switch | CSS custom properties |
| Error Display | User-friendly errors | Conditional visibility |

**API Communication Pattern**:
```javascript
// Robust API calls with error handling
async function getComparisons(weight, unit) {
    try {
        const response = await fetch('/api/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ weight, unit })
        });
        return await response.json();
    } catch (error) {
        return { error: 'Service temporarily unavailable' };
    }
}
```

### 5. Backend API & Request Processing (1.5 pages)

**FastAPI Application Structure**:
```python
# Core API endpoint with comprehensive error handling
@app.post("/api/compare")
async def compare_weight(request: WeightRequest) -> ComparisonResponse:
    try:
        weight = parse_and_validate_weight(request)
        comparisons = await ai_manager.get_comparisons(weight)
        return format_response(comparisons)
    except WeightValidationError as e:
        raise HTTPException(400, str(e))
    except AIProviderError as e:
        raise HTTPException(503, "Comparison service temporarily unavailable")
```

**Request/Response Contracts**:
```json
// Request format
{
    "weight": 24,
    "unit": "lbs"
}

// Response format
{
    "comparisons": [
        {
            "description": "Four medium chickens",
            "individual_weight": "6 lbs each",
            "confidence": 0.9
        },
        {
            "description": "One car tire",
            "individual_weight": "24 lbs total",
            "confidence": 0.8
        }
    ],
    "total_weight": "24 lbs",
    "response_time_ms": 1250
}
```

**Weight Processing Logic**:
- Input validation (positive numbers, supported units)
- Unit conversion to standardized format
- Range validation (reasonable weight limits)
- Precision handling for display

### 6. Configuration Management & Error Handling (1 page)

**Configuration Structure**:
```python
# File-based configuration for zero-deployment updates
CONFIG = {
    "ai_providers": {
        "enabled": ["openai", "anthropic", "xai"],
        "timeout_seconds": 10,
        "max_retries": 2
    },
    "prompt_templates": {
        "comparison_prompt": "path/to/prompt.txt",
        "validation_rules": ["realistic", "common_objects"]
    },
    "application": {
        "max_weight": 1000000,
        "supported_units": ["lbs", "kg"],
        "cache_ttl_seconds": 300
    }
}
```

**Error Handling Strategy Table**:
| Error Type | Response | User Message | Logging |
|------------|----------|--------------|---------|
| Invalid Weight | 400 Bad Request | "Please enter a valid weight" | Info |
| AI Provider Down | 503 Service Unavailable | "Service temporarily unavailable" | Error |
| Rate Limited | 429 Too Many Requests | "Please try again in a moment" | Warning |
| Malformed Response | 500 Internal Error | "Unexpected error occurred" | Error |

### 7. Development Workflow & Parallel Implementation (1 page)

**Parallel Development Strategy**:
```
Phase 1 (Parallel):
- Frontend UI components (Developer A)
- AI provider interfaces (Developer B) 
- Weight parsing logic (Developer C)

Phase 2 (Integration):
- API endpoint integration
- End-to-end testing
- Error handling verification

Phase 3 (Polish):
- Performance optimization
- Documentation updates
- Deployment preparation
```

**Testing Strategy**:
- Unit tests for weight parsing and validation
- Integration tests with mock AI providers
- E2E tests for complete user workflows
- Load testing for AI provider failover

**Deployment Approach**:
- Single Docker container with health checks
- Environment-based configuration
- Graceful shutdown handling
- Log aggregation for monitoring

### 8. Implementation Guidelines & Quality Standards (0.5 pages)

**Code Quality Standards**:
- Type hints throughout Python codebase
- Async/await for all I/O operations
- Comprehensive error handling with user-friendly messages
- Configuration-driven behavior (no hardcoded values)
- Clean separation of concerns between components

**Security Considerations**:
- Input validation and sanitization
- API rate limiting per client
- Secure API key management
- CORS configuration for production
- No sensitive data in logs

**Performance Targets**:
- API response time: < 2 seconds (95th percentile)
- Frontend load time: < 500ms
- AI provider timeout: 10 seconds maximum
- Memory usage: < 512MB container

## Deliverable Requirements

Create a SIZECOMPARATOR_SYSTEM_SPEC.md that:
1. Provides clear implementation guidance for senior developers
2. Emphasizes lightweight, maintainable architecture
3. Details AI integration patterns with fallback strategies
4. Includes specific configuration examples and error handling
5. Focuses on parallel development opportunities
6. Addresses common pitfalls in AI-driven applications

## What to Exclude

- Detailed AI prompt engineering (separate specification)
- Comprehensive deployment procedures (operations guide)
- Multiple implementation alternatives (focus on recommended approach)
- Extensive code examples beyond interface definitions
- Historical context or alternative architectures considered

## Writing Style

- Use imperative mood for requirements and guidelines
- Prefer tables and structured lists over prose
- Include minimal, essential code examples
- Focus on architectural decisions and patterns
- Emphasize robustness and simplicity over complexity

## Project-Specific Context

**Key Success Factors**:
- Minimal dependencies for easy maintenance
- Robust error handling for AI service integration
- Configuration-driven prompts for easy updates
- Clean separation between frontend and AI logic
- Parallel-friendly architecture for rapid development

**Common Pitfalls to Address**:
- AI provider rate limiting and failures
- Inconsistent response formats from different providers
- Frontend/backend coupling issues
- Configuration management complexity
- Error state handling in user interface

The specification should serve as a complete implementation guide that enables experienced developers to build a production-ready weight comparison system efficiently while avoiding common AI integration challenges.