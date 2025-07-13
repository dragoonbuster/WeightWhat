# SizeComparator System Specification

Last Updated: 2025-07-13

## 1. Executive Summary & Architecture Overview

### Project Purpose

SizeComparator is a lightweight web application that transforms weight inputs into relatable object comparisons using AI providers. Users enter a weight value (lbs or kg) and receive two AI-generated comparison suggestions that help visualize the weight using common objects.

**Example Interaction**:
- Input: "24 lbs"
- Output: "Four medium chickens (6 lbs each)" + "One car tire (24 lbs total)"

The system emphasizes simplicity, reliability, and maintainability while providing consistent, high-quality comparisons through intelligent AI provider management.

### Key Architectural Decisions

| Decision Area | Choice | Rationale |
|--------------|---------|-----------|
| Frontend | Vanilla HTML/CSS/JS | Zero dependencies, fast loading, universal compatibility |
| Backend | Python FastAPI | Lightweight, excellent typing, async support |
| AI Integration | Provider abstraction with fallback | Reliability through redundancy, easy provider swapping |
| Storage | File-based configuration | No database overhead, simple deployment |
| Deployment | Single container | Minimal infrastructure, easy scaling |

### Success Criteria

- **Performance**: Sub-2 second response times for weight comparisons
- **Reliability**: 99% uptime with graceful AI provider failures
- **Maintainability**: Zero-maintenance deployment with configuration-driven prompts
- **Extensibility**: Easy addition of new AI providers without code changes

### System Architecture Overview

```
User Browser
     ↓
Static Frontend (HTML/CSS/JS)
     ↓
FastAPI Backend
     ↓
AI Provider Manager ← → Prompt Templates
     ↓                      ↓
Multiple AI Providers  Configuration Files
(OpenAI, Anthropic, X.ai)
```

## 2. System Architecture & Component Design

### High-Level Architecture

The system follows a clean separation of concerns with four primary layers:

**Presentation Layer**: Vanilla frontend with theme management
**API Layer**: FastAPI with async request handling
**Business Logic Layer**: Weight processing and AI orchestration
**Integration Layer**: AI provider abstraction with fallback mechanisms

### Core Components

**Weight Parser**
- Validates user input (positive numbers, supported units)
- Converts between lbs/kg using standard conversion rates
- Enforces reasonable weight limits (0.1 - 1,000,000 units)
- Returns normalized Weight objects for consistent processing

**AI Provider Manager**
- Implements provider abstraction pattern for pluggable AI services
- Manages provider health status and automatic failover
- Handles rate limiting with exponential backoff
- Coordinates parallel requests to multiple providers for redundancy

**Prompt Template System**
- Configuration-driven prompt management without code deployment
- Template validation and variable substitution
- Provider-specific prompt optimization
- A/B testing support for prompt effectiveness

**Response Validator**
- Validates AI responses against quality criteria
- Ensures exactly 2 comparisons per response
- Checks for realistic weight relationships
- Filters inappropriate or nonsensical suggestions

**Theme Manager**
- Persistent light/dark mode selection using localStorage
- CSS custom property updates for instant theme switching
- System preference detection and automatic theme selection

### Data Flow

1. **Input Processing**: User input → Weight Parser → Validated Weight object
2. **AI Orchestration**: Weight object → AI Provider Manager → Parallel AI calls
3. **Response Processing**: AI responses → Response Validator → Quality-checked comparisons
4. **Output Formatting**: Validated responses → Response Formatter → User display

### Key Design Patterns

**Provider Pattern**: Standardized interface for AI services enables easy swapping and testing
**Template Method**: Consistent AI interaction flow across different providers
**Circuit Breaker**: Automatic provider failure detection and recovery
**Configuration Strategy**: Runtime behavior modification through file-based configuration

## 3. AI Provider Integration Framework

### Provider Interface Design

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class AIProvider(ABC):
    """Abstract base class for AI comparison providers."""
    
    @abstractmethod
    async def generate_comparisons(self, weight: Weight, context: Dict) -> List[Comparison]:
        """Generate weight comparisons using provider-specific API."""
        pass
    
    @abstractmethod
    def validate_response(self, response: Any) -> bool:
        """Validate provider response format and content."""
        pass
    
    @abstractmethod
    def get_health_status(self) -> ProviderHealth:
        """Return current provider health and availability."""
        pass
```

### Supported Providers Configuration

| Provider | API Type | Rate Limits | Fallback Priority | Est. Cost/Request | Response Time |
|----------|----------|-------------|------------------|------------------|---------------|
| OpenAI GPT-4 | REST | 3,500 RPM | 1 (Primary) | $0.03 | 800ms avg |
| Anthropic Claude | REST | 1,000 RPM | 2 (Secondary) | $0.015 | 1200ms avg |
| X.ai Grok | REST | 500 RPM | 3 (Tertiary) | $0.01 | 1500ms avg |

### Retry & Fallback Strategy

**Provider Selection Logic**:
- Primary provider available → Use immediately
- Primary provider down → Automatic secondary attempt within 100ms
- All providers down → Return cached response or graceful error message
- Rate limit exceeded → Exponential backoff with provider rotation

**Error Handling Flow**:
```python
async def get_comparison_with_fallback(weight: Weight) -> ComparisonResponse:
    for provider in provider_priority_list:
        try:
            if provider.is_healthy():
                return await provider.generate_comparisons(weight)
        except RateLimitError:
            await backoff_delay(provider)
            continue
        except ProviderError:
            mark_provider_unhealthy(provider)
            continue
    
    return fallback_response(weight)
```

### Prompt Template System

**Configuration Structure**:
```python
WEIGHT_COMPARISON_PROMPT = {
    "system_message": "You are a weight comparison expert that helps people understand weights through familiar objects.",
    "user_template": "Convert {weight} {unit} into exactly 2 different relatable object comparisons. Format each as 'Number + Object type (individual weight)'. Use common household items, animals, or everyday objects.",
    "validation_rules": [
        "must_have_exactly_2_comparisons",
        "realistic_weight_relationships", 
        "common_recognizable_objects",
        "avoid_inappropriate_content"
    ],
    "max_tokens": 150,
    "temperature": 0.7,
    "stop_sequences": ["\n\n"]
}
```

**Provider-Specific Optimizations**:
- OpenAI: Structured output format with JSON mode
- Anthropic: Explicit instruction formatting with examples
- X.ai: Simplified prompts optimized for Grok's response style

## 4. Frontend Implementation & Theme System

### Minimal Frontend Architecture

The frontend uses vanilla HTML/CSS/JS to eliminate build dependencies and ensure universal compatibility:

**Single Page Structure**:
- Semantic HTML5 markup for accessibility
- CSS Grid layout with mobile-first responsive design
- Progressive enhancement with JavaScript for better UX
- No external dependencies or CDN requirements

### Theme System Implementation

```javascript
const ThemeManager = {
    THEMES: { LIGHT: 'light', DARK: 'dark' },
    STORAGE_KEY: 'sizecomparator-theme',
    
    init() {
        const saved = localStorage.getItem(this.STORAGE_KEY);
        const system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        const theme = saved || system;
        this.apply(theme);
        this.setupToggle();
    },
    
    toggle() {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'light' ? 'dark' : 'light';
        this.apply(next);
        localStorage.setItem(this.STORAGE_KEY, next);
    },
    
    apply(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.updateToggleButton(theme);
    }
};
```

### User Interface Components

| Component | Functionality | Implementation Details |
|-----------|--------------|----------------------|
| Weight Input | Number input with unit selection | HTML5 number input with min/max validation |
| Unit Selector | lbs/kg radio buttons | Styled radio group with clear visual feedback |
| Submit Button | Trigger comparison request | Disabled during loading, shows spinner |
| Results Display | Show 2 comparison cards | CSS Grid layout with smooth animations |
| Theme Toggle | Light/dark mode switch | Icon-based toggle in header corner |
| Error Display | User-friendly error messages | Conditional visibility with fade transitions |

### API Communication Pattern

```javascript
class ComparisonAPI {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
    }
    
    async getComparisons(weight, unit) {
        try {
            const response = await fetch(`${this.baseURL}/compare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ weight: parseFloat(weight), unit })
            });
            
            if (!response.ok) {
                throw new Error(`API Error: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Comparison request failed:', error);
            return { 
                error: 'Service temporarily unavailable. Please try again.' 
            };
        }
    }
}
```

## 5. Backend API & Request Processing

### FastAPI Application Structure

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import asyncio
from typing import List, Optional

app = FastAPI(title="SizeComparator API", version="1.0.0")

class WeightRequest(BaseModel):
    weight: float
    unit: str
    
    @validator('weight')
    def weight_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Weight must be positive')
        if v > 1000000:
            raise ValueError('Weight too large for comparison')
        return v
    
    @validator('unit')
    def unit_must_be_supported(cls, v):
        if v.lower() not in ['lbs', 'kg']:
            raise ValueError('Unit must be lbs or kg')
        return v.lower()

@app.post("/api/compare")
async def compare_weight(request: WeightRequest) -> ComparisonResponse:
    try:
        # Parse and normalize weight
        weight = Weight(value=request.weight, unit=request.unit)
        
        # Get AI-generated comparisons with fallback
        comparisons = await ai_manager.get_comparisons(weight)
        
        # Format and return response
        return ComparisonResponse(
            comparisons=comparisons,
            total_weight=f"{weight.value} {weight.unit}",
            response_time_ms=measure_response_time()
        )
        
    except WeightValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AIProviderError as e:
        raise HTTPException(status_code=503, detail="Comparison service temporarily unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Request/Response Contracts

**Request Format**:
```json
{
    "weight": 24.5,
    "unit": "lbs"
}
```

**Success Response Format**:
```json
{
    "comparisons": [
        {
            "description": "Four medium chickens",
            "individual_weight": "6 lbs each",
            "total_weight": "24 lbs",
            "confidence": 0.9,
            "category": "animals"
        },
        {
            "description": "One car tire",
            "individual_weight": "24 lbs total", 
            "total_weight": "24 lbs",
            "confidence": 0.8,
            "category": "objects"
        }
    ],
    "request_weight": "24 lbs",
    "response_time_ms": 1250,
    "provider_used": "openai"
}
```

**Error Response Format**:
```json
{
    "error": {
        "code": "INVALID_WEIGHT",
        "message": "Weight must be a positive number",
        "details": {
            "field": "weight",
            "value": -5,
            "constraint": "positive_number"
        }
    }
}
```

### Weight Processing Logic

**Validation Pipeline**:
1. Type validation (numeric input)
2. Range validation (0.1 to 1,000,000)
3. Unit validation (lbs or kg only)
4. Precision normalization (2 decimal places)

**Unit Conversion**:
```python
class Weight:
    CONVERSION_RATE = 2.20462  # kg to lbs
    
    def to_lbs(self) -> float:
        if self.unit == 'kg':
            return self.value * self.CONVERSION_RATE
        return self.value
    
    def to_kg(self) -> float:
        if self.unit == 'lbs':
            return self.value / self.CONVERSION_RATE
        return self.value
```

## 6. Configuration Management & Error Handling

### Configuration Structure

```python
# config/application.yaml
ai_providers:
  enabled: ["openai", "anthropic", "xai"]
  timeout_seconds: 10
  max_retries: 2
  fallback_enabled: true
  
  openai:
    model: "gpt-4"
    max_tokens: 150
    temperature: 0.7
    
  anthropic:
    model: "claude-3-sonnet-20240229"
    max_tokens: 150
    temperature: 0.7
    
  xai:
    model: "grok-beta"
    max_tokens: 150
    temperature: 0.7

prompt_templates:
  comparison_prompt: "prompts/weight_comparison.txt"
  validation_rules:
    - "exactly_two_comparisons"
    - "realistic_weights"
    - "common_objects"
    - "appropriate_content"

application:
  max_weight_lbs: 1000000
  max_weight_kg: 453592
  supported_units: ["lbs", "kg"]
  cache_ttl_seconds: 300
  request_timeout_seconds: 30
  
logging:
  level: "INFO"
  format: "json"
  include_request_id: true
```

### Error Handling Strategy

| Error Type | HTTP Status | User Message | Logging Level | Retry Logic |
|------------|-------------|--------------|---------------|-------------|
| Invalid Weight | 400 | "Please enter a valid weight" | INFO | None |
| Unsupported Unit | 400 | "Please use lbs or kg" | INFO | None |
| AI Provider Down | 503 | "Service temporarily unavailable" | ERROR | Auto-failover |
| Rate Limited | 429 | "Please try again in a moment" | WARNING | Exponential backoff |
| Malformed AI Response | 500 | "Unexpected error occurred" | ERROR | Retry once |
| Timeout | 504 | "Request timed out, please try again" | WARNING | Retry with backoff |

### Graceful Degradation

**Fallback Mechanisms**:
- All AI providers down → Static comparison database lookup
- Partial AI failure → Mix AI and static responses
- Slow AI response → Return cached recent comparisons
- Invalid AI response → Retry with simplified prompt

**Circuit Breaker Implementation**:
```python
class ProviderCircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, provider_func, *args):
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError()
        
        try:
            result = await provider_func(*args)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

## 7. Development Workflow & Parallel Implementation

### Parallel Development Strategy

**Phase 1: Foundation (Parallel Development)**
```
Developer A: Frontend UI Components
- HTML structure and responsive CSS
- Theme system implementation  
- Form validation and user feedback
- API communication layer

Developer B: AI Provider Interfaces
- Abstract provider base class
- OpenAI, Anthropic, X.ai implementations
- Provider health monitoring
- Retry/fallback logic

Developer C: Core Backend Logic
- FastAPI application setup
- Weight parsing and validation
- Configuration management
- Error handling framework
```

**Phase 2: Integration (Sequential)**
- API endpoint integration and testing
- End-to-end user workflow validation
- Error handling verification across components
- Performance optimization and monitoring setup

**Phase 3: Polish & Deployment (Parallel)**
```
Developer A: Performance & Monitoring
- Response time optimization
- Logging and metrics implementation
- Health check endpoints

Developer B: Documentation & Testing
- API documentation generation
- Integration test suite
- Load testing scenarios

Developer C: Deployment & Infrastructure
- Docker containerization
- CI/CD pipeline setup
- Production configuration
```

### Testing Strategy

**Unit Testing**:
- Weight parser validation logic
- AI provider response validation
- Configuration loading and validation
- Theme system functionality

**Integration Testing**:
- API endpoints with mock AI providers
- Error handling across component boundaries
- Provider failover scenarios
- Response formatting and validation

**End-to-End Testing**:
- Complete user workflows
- Cross-browser compatibility
- Mobile responsiveness
- Performance under load

### Deployment Approach

**Containerization**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Health Checks**:
- Application startup verification
- AI provider connectivity tests
- Configuration validation
- Memory and CPU usage monitoring

## 8. Implementation Guidelines & Quality Standards

### Code Quality Standards

**Python Backend Requirements**:
- Type hints for all function parameters and return values
- Async/await for all I/O operations (API calls, file reads)
- Comprehensive error handling with specific exception types
- Configuration-driven behavior with no hardcoded values
- Clean separation of concerns between business logic and infrastructure

**Frontend Requirements**:
- Semantic HTML5 markup for accessibility
- CSS custom properties for theme management
- Progressive enhancement with feature detection
- Error boundary handling for API failures
- Responsive design with mobile-first approach

### Security Considerations

**Input Validation**:
- Server-side validation for all user inputs
- SQL injection prevention (though no database used)
- XSS prevention through proper output encoding
- Request size limiting to prevent DoS attacks

**API Security**:
- Rate limiting per client IP address
- CORS configuration for production domains
- Secure API key management using environment variables
- No sensitive data exposure in error messages or logs

**Infrastructure Security**:
- Container security scanning in CI/CD
- Least-privilege principles for service accounts
- Regular dependency updates and vulnerability scanning
- Secure communication using HTTPS in production

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time | < 2 seconds (95th percentile) | Server-side timing |
| Frontend Load Time | < 500ms | Browser performance API |
| AI Provider Timeout | 10 seconds maximum | Provider-specific timing |
| Memory Usage | < 512MB per container | Runtime monitoring |
| Concurrent Users | 100+ simultaneous | Load testing |
| Uptime | 99%+ availability | Health check monitoring |

### Monitoring & Observability

**Logging Strategy**:
- Structured JSON logging for easy parsing
- Request ID tracking across components
- AI provider response time and success rate logging
- Error aggregation and alerting

**Metrics Collection**:
- Request rate and response time percentiles
- AI provider health and failover frequency
- Theme usage statistics
- Error rate by type and component

This specification provides a complete implementation guide for building a production-ready weight comparison system that emphasizes simplicity, reliability, and maintainability while handling the complexities of AI service integration.