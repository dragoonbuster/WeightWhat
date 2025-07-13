# Backend Core System Specification for SizeComparator

## Document Overview
Create a technical specification document (8-10 pages) for the SizeComparator backend core system focusing on the FastAPI application structure and weight processing logic. This specification should provide practical implementation guidance for developers building the core API service.

## 1. Executive Summary (0.5 pages)
- Brief overview of the backend core system's role in SizeComparator
- Key responsibilities: weight processing, validation, API exposure
- Technology stack: FastAPI, Python 3.11+, Pydantic
- Performance target: Sub-2 second response times for all endpoints

## 2. FastAPI Application Structure (1.5 pages)

### 2.1 Project Layout
Directory structure aligned with all specification requirements:
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization
│   ├── config/
│   │   ├── __init__.py
│   │   ├── service.py       # CONFIG_SYSTEM_SPEC implementation
│   │   └── settings.py      # Environment-specific settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── weight.py    # Weight comparison endpoints
│   │   │   └── health.py    # DEPLOYMENT_OPS_SPEC health endpoints
│   │   └── dependencies.py  # Shared dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── weight_processor.py  # Weight parsing and conversion
│   │   ├── validators.py        # Input validation logic
│   │   └── ai_interface.py      # AI_PROVIDER_SPEC integration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py      # Pydantic request models
│   │   ├── responses.py     # TESTING_SPEC-ready response models
│   │   ├── ai_models.py     # AI_PROVIDER_SPEC models
│   │   └── errors.py        # ERROR_MONITORING_SPEC error models
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── logging.py       # ERROR_MONITORING_SPEC logging
│   │   └── metrics.py       # Prometheus metrics
│   └── utils/
│       ├── __init__.py
│       └── exceptions.py    # Custom exception classes
├── config/                  # CONFIG_SYSTEM_SPEC configuration files
│   ├── base/
│   │   ├── app.yaml
│   │   └── prompts.yaml
│   ├── environments/
│   │   ├── development.yaml
│   │   ├── staging.yaml
│   │   └── production.yaml
│   └── schema/
│       └── app.schema.json
├── tests/                   # TESTING_SPEC test structure
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── fixtures/
│   └── mocks/
├── Dockerfile               # DEPLOYMENT_OPS_SPEC container
├── docker-compose.yml       # Local development
├── requirements.txt
└── .github/
    └── workflows/           # DEPLOYMENT_OPS_SPEC CI/CD
        └── test-deploy.yml
```

### 2.2 Application Initialization
Application initialization must follow CONFIG_SYSTEM_SPEC.md patterns:

```python
from app.config import ConfigurationService
from app.core.exceptions import ConfigurationError

def create_app() -> FastAPI:
    # Load configuration using CONFIG_SYSTEM_SPEC interface
    config_service = ConfigurationService()
    config_service.load_from_environment()
    
    app = FastAPI(
        title=config_service.get("application.name"),
        version=config_service.get("application.version"),
        **config_service.get("api.fastapi_config", {})
    )
    
    # CORS middleware from config
    app.add_middleware(
        CORSMiddleware,
        **config_service.get("api.cors", {})
    )
    
    # Exception handler registration
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    
    # Hot-reload configuration support
    config_service.enable_hot_reload()
    config_service.on_config_change(handle_config_change)
    
    return app
```

- FastAPI app configuration loaded from CONFIG_SYSTEM_SPEC hierarchy
- Environment variable resolution using config service
- Hot-reload support for runtime configuration changes
- Startup/shutdown event handlers for resource management

### 2.3 Async/Await Pattern Usage
- Guidelines for async endpoint implementation
- When to use sync vs async functions
- Proper async context management

## 3. Weight Processing Core Logic (2 pages)

### 3.1 Weight Parsing Engine
Detailed specification for parsing various weight formats:
- Natural language inputs: "5 pounds", "2.5kg", "3 lbs 4 oz"
- Numeric inputs with implicit units
- Mixed unit formats
- Edge cases and ambiguous inputs

### 3.2 Unit Conversion System
```python
class WeightUnit(Enum):
    KILOGRAM = "kg"
    POUND = "lb"
    OUNCE = "oz"
    GRAM = "g"
    STONE = "st"
    METRIC_TON = "mt"
    
class WeightConverter:
    """Handles all weight unit conversions with high precision"""
    # Conversion factors stored as Decimal for precision
    # All conversions go through base unit (grams)
```

### 3.3 Validation Rules
- Minimum weight: 0.001 kg (1 gram)
- Maximum weight: 1,000,000 kg (1000 metric tons)
- Precision: 3 decimal places for display
- Internal precision: Use Python Decimal with 6 decimal places

### 3.4 Float Precision Handling
- Use `decimal.Decimal` for all internal calculations
- Rounding strategies for different contexts
- Avoiding floating-point arithmetic errors

## 4. Pydantic Models and Validation (1.5 pages)

### 4.1 Request Models
```python
class WeightComparisonRequest(BaseModel):
    item1_name: str = Field(..., min_length=1, max_length=100)
    item1_weight: str = Field(..., description="Weight with optional unit")
    item2_name: str = Field(..., min_length=1, max_length=100)
    item2_weight: str = Field(..., description="Weight with optional unit")
    output_unit: Optional[WeightUnit] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "item1_name": "Elephant",
                "item1_weight": "5000 kg",
                "item2_name": "Car",
                "item2_weight": "3000 pounds"
            }
        }
```

### 4.2 Response Models
Complete Pydantic models for TESTING_SPEC mocking:

```python
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

class WeightUnit(str, Enum):
    KILOGRAM = "kg"
    POUND = "lb"
    OUNCE = "oz"
    GRAM = "g"
    STONE = "st"
    METRIC_TON = "mt"

class WeightItem(BaseModel):
    """Core weight item model for TESTING_SPEC mocking"""
    name: str = Field(..., min_length=1, max_length=100)
    original_input: str = Field(..., min_length=1)
    weight_kg: Decimal = Field(..., gt=Decimal('0.001'), le=Decimal('1000000'))
    weight_display: str = Field(..., min_length=1)
    unit_used: WeightUnit
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    @validator('weight_kg')
    def validate_precision(cls, v):
        """Ensure 6 decimal places maximum for internal precision"""
        return v.quantize(Decimal('0.000001'))

class ComparisonResult(BaseModel):
    """Comparison calculation results for TESTING_SPEC"""
    ratio: Decimal = Field(..., description="item1/item2 ratio")
    percentage_difference: Decimal = Field(..., description="Percentage difference")
    heavier_item: str = Field(..., description="Name of heavier item")
    weight_difference_kg: Decimal = Field(..., description="Absolute difference")
    calculation_method: str = Field(default="direct_conversion")
    
class VisualizationPrompt(BaseModel):
    """AI-generated visualization for TESTING_SPEC mocking"""
    prompt: str = Field(..., min_length=10)
    comparisons: List[Comparison] = Field(..., min_items=2, max_items=2)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    generation_time_ms: int = Field(..., ge=0)
    provider_used: str = Field(..., min_length=1)

class ResponseMetadata(BaseModel):
    """Response metadata for debugging and monitoring"""
    request_id: str = Field(..., description="Correlation ID")
    processing_time_ms: int = Field(..., ge=0)
    ai_provider_used: str = Field(..., min_length=1)
    ai_response_time_ms: int = Field(..., ge=0)
    cache_hit: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(..., description="API version")

class WeightComparisonResponse(BaseModel):
    """Complete response model for TESTING_SPEC mocking"""
    item1: WeightItem
    item2: WeightItem
    comparison: ComparisonResult
    visualization: VisualizationPrompt
    metadata: ResponseMetadata
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "item1": {
                    "name": "Elephant",
                    "original_input": "5000 kg",
                    "weight_kg": 5000.0,
                    "weight_display": "5,000 kg",
                    "unit_used": "kg",
                    "confidence": 1.0
                },
                "item2": {
                    "name": "Car", 
                    "original_input": "3000 pounds",
                    "weight_kg": 1360.777,
                    "weight_display": "3,000 lbs (1,361 kg)",
                    "unit_used": "lb",
                    "confidence": 1.0
                }
            }
        }

# Health check models for DEPLOYMENT_OPS_SPEC
class HealthResponse(BaseModel):
    """Basic health response for load balancers"""
    status: str = Field(..., pattern="^(healthy|unhealthy)$")
    timestamp: datetime
    version: str

class ReadinessResponse(BaseModel):
    """Readiness response with dependency checks"""
    ready: bool
    checks: Dict[str, bool]
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
```

### 4.3 Validation Decorators and Custom Validators
- Field-level validators for weight strings
- Model-level validators for business logic
- Custom error messages for validation failures

## 5. API Endpoints Specification (1.5 pages)

### 5.1 Core Endpoints

#### POST /api/v1/compare
- Purpose: Compare two items by weight
- Request body: `WeightComparisonRequest`
- Response: `WeightComparisonResponse`
- Status codes: 200, 400, 422, 500

#### GET /api/v1/health
- Purpose: Basic health check for DEPLOYMENT_OPS_SPEC
- Response: Simple health status
- Used by: Load balancers and orchestrators

#### GET /api/v1/ready
- Purpose: Readiness check for DEPLOYMENT_OPS_SPEC
- Response: Service readiness with dependency status
- Include: AI provider connectivity, configuration validation

#### GET /api/v1/metrics
- Purpose: Prometheus metrics for monitoring
- Response: Metrics in Prometheus format
- Include: Request rates, error rates, latency percentiles

```python
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Liveness probe for DEPLOYMENT_OPS_SPEC"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=config.get("application.version")
    )

@router.get("/ready", response_model=ReadinessResponse)  
async def readiness_check(
    ai_service: AIService = Depends(get_ai_service),
    config_service: ConfigurationService = Depends(get_config_service)
):
    """Readiness probe for DEPLOYMENT_OPS_SPEC"""
    checks = {
        "ai_providers": await ai_service.health_check(),
        "configuration": config_service.is_valid()
    }
    
    all_healthy = all(checks.values())
    
    return ReadinessResponse(
        ready=all_healthy,
        checks=checks,
        timestamp=datetime.utcnow()
    )

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint for DEPLOYMENT_OPS_SPEC"""
    from prometheus_client import generate_latest
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### 5.2 Request/Response Contracts
Detailed examples of all request/response scenarios including:
- Successful comparisons
- Validation errors
- Parser failures
- System errors

### 5.3 Error Response Format
Error responses must align with ERROR_MONITORING_SPEC.md categories:

```python
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ErrorCategory(Enum):
    """Error categories from ERROR_MONITORING_SPEC"""
    CLIENT_ERROR = "client_error"          # 4xx errors
    SERVER_ERROR = "server_error"          # 5xx errors  
    INTEGRATION_ERROR = "integration_error" # External API failures
    BUSINESS_LOGIC_ERROR = "business_logic_error" # Validation failures

class ErrorSeverity(Enum):
    """Severity levels from ERROR_MONITORING_SPEC"""
    CRITICAL = "critical"  # System outage, page immediately
    WARNING = "warning"    # Degraded performance, notify on-call
    INFO = "info"         # Anomalies worth investigating

class ErrorResponse(BaseModel):
    """Standardized error response matching ERROR_MONITORING_SPEC"""
    error_code: str = Field(..., description="Unique error identifier")
    error_category: ErrorCategory = Field(..., description="Error classification")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    request_id: str = Field(..., description="Correlation ID for tracing")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: ErrorSeverity = Field(..., description="Alert severity level")
    remediation_hint: Optional[str] = Field(None, description="Suggested fix")
    
class ValidationErrorResponse(ErrorResponse):
    """Specific error for validation failures"""
    error_category: ErrorCategory = Field(default=ErrorCategory.CLIENT_ERROR)
    field_errors: List[Dict[str, str]] = Field(default_factory=list)

# Error mapping from exceptions to categories
ERROR_CATEGORY_MAPPING = {
    ValidationException: ErrorCategory.CLIENT_ERROR,
    WeightParsingException: ErrorCategory.BUSINESS_LOGIC_ERROR,
    AIProviderException: ErrorCategory.INTEGRATION_ERROR,
    InternalServerError: ErrorCategory.SERVER_ERROR,
}
```

## 6. AI Provider Interface (1.5 pages)

### 6.1 Exact AI Provider Response Interface
The backend must implement the exact interface defined in AI_PROVIDER_SPEC.md to handle AI provider responses:

```python
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum

class ProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CIRCUIT_OPEN = "circuit_open"

class Comparison(BaseModel):
    """Exact model from AI_PROVIDER_SPEC that backend must handle"""
    description: str = Field(..., description="Object description")
    individual_weight: str = Field(..., description="Weight per item")
    total_weight: str = Field(..., description="Total weight")
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: str = Field(..., description="Object category")
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)

class ComparisonRequest(BaseModel):
    """Request format for AI providers"""
    weight: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1)
    prompt_template: str = Field(..., min_length=1)
    max_tokens: int = Field(default=500, ge=50, le=2000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=60.0)

class ProviderHealth(BaseModel):
    """Health status from AI providers"""
    status: ProviderStatus
    success_rate: float = Field(..., ge=0.0, le=1.0)
    avg_response_time_ms: float = Field(..., ge=0.0)
    error_count: int = Field(..., ge=0)
    last_error: Optional[str] = None
    circuit_state: str = Field(..., pattern="^(CLOSED|OPEN|HALF_OPEN)$")

class AIProviderInterface(ABC):
    @abstractmethod
    async def generate_comparisons(
        self, 
        request: ComparisonRequest
    ) -> List[Comparison]:
        """Generate exactly 2 weight comparisons"""
        pass
    
    @abstractmethod
    def validate_response(self, response: Any) -> bool:
        """Validate provider-specific response format"""
        pass
    
    @abstractmethod
    def parse_response(self, response: Any) -> List[Comparison]:
        """Parse provider response into Comparison models"""
        pass
    
    @abstractmethod
    def get_health_status(self) -> ProviderHealth:
        """Return current provider health metrics"""
        pass
```

### 6.2 Response Validation
Backend must validate AI provider responses against the exact schema:

```python
class AIResponseValidator:
    def validate_comparison_list(self, comparisons: List[Comparison]) -> ValidationResult:
        """Validate list of comparisons from AI provider"""
        errors = []
        
        if len(comparisons) != 2:
            errors.append("Must have exactly 2 comparisons")
        
        for i, comp in enumerate(comparisons):
            try:
                # Pydantic validation happens automatically
                comp.model_validate(comp.model_dump())
            except ValidationError as e:
                errors.append(f"Comparison {i+1}: {e}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

### 6.3 Integration Points
- Async method calls to AI services with exact contract compliance
- Timeout handling (30-second maximum from ComparisonRequest)
- Retry logic with exponential backoff for rate limits and timeouts
- Fallback strategies using provider health status
- Circuit breaker integration based on ProviderHealth metrics

### 6.4 Response Caching
- Cache successful Comparison objects for identical ComparisonRequest inputs
- TTL: 24 hours
- Cache key generation from request hash

## 7. Performance and Concurrency (1 page)

### 7.1 Performance Requirements
- API response time: < 2 seconds (excluding AI generation)
- Concurrent request handling: 100 requests/second
- Memory usage: < 512MB under normal load

### 7.2 Concurrent Request Handling
- FastAPI's async capabilities
- Connection pooling for external services
- Request queuing strategies
- Rate limiting implementation

### 7.3 Performance Monitoring
- Request/response time logging
- Memory usage tracking
- Error rate monitoring
- Slow query identification

## 8. Error Handling and Edge Cases (1.5 pages)

### 8.1 Error Classification per ERROR_MONITORING_SPEC
All errors must be classified according to ERROR_MONITORING_SPEC categories:

```python
class WeightParsingException(Exception):
    """Business logic error for invalid weight formats"""
    category = ErrorCategory.BUSINESS_LOGIC_ERROR
    severity = ErrorSeverity.WARNING

class AIProviderException(Exception):
    """Integration error for AI service failures"""
    category = ErrorCategory.INTEGRATION_ERROR
    severity = ErrorSeverity.CRITICAL

class ValidationException(Exception):
    """Client error for request validation failures"""
    category = ErrorCategory.CLIENT_ERROR
    severity = ErrorSeverity.INFO

def map_exception_to_error_response(exc: Exception, request_id: str) -> ErrorResponse:
    """Convert exceptions to standardized error responses"""
    category = getattr(exc.__class__, 'category', ErrorCategory.SERVER_ERROR)
    severity = getattr(exc.__class__, 'severity', ErrorSeverity.WARNING)
    
    return ErrorResponse(
        error_code=f"{category.value}_{exc.__class__.__name__}",
        error_category=category,
        message=str(exc),
        request_id=request_id,
        severity=severity,
        remediation_hint=get_remediation_hint(exc.__class__)
    )
```

### 8.2 Common Error Scenarios with Monitoring
- **Invalid weight format**: "five and a half kilos" → BUSINESS_LOGIC_ERROR
- **Out of range values**: negative weights, extreme values → CLIENT_ERROR  
- **Ambiguous units**: "5" without unit specification → CLIENT_ERROR
- **Malformed JSON requests**: → CLIENT_ERROR
- **AI provider timeouts**: → INTEGRATION_ERROR with circuit breaker activation
- **Configuration errors**: → SERVER_ERROR with immediate alerting

### 8.3 Error Handling Strategy with Request Correlation
- Graceful degradation with fallback responses
- User-friendly error messages with error codes
- Structured logging with request ID propagation (ERROR_MONITORING_SPEC)
- Automatic retry for transient errors
- Circuit breaker activation for provider failures

### 8.4 Unit Conversion Edge Cases
- Precision loss in conversions (log as warnings)
- Rounding errors accumulation (use Decimal throughout)
- Mixed unit handling (e.g., "5kg 200g") with validation
- Locale-specific decimal separators (normalize input)

### 8.5 Request ID Propagation
```python
import uuid
from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar('request_id')

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_context.set(request_id)
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

## 9. Security Considerations (0.5 pages)

### 9.1 Input Sanitization
- SQL injection prevention (though no direct DB access)
- XSS prevention in string inputs
- Request size limits
- Rate limiting per IP

### 9.2 API Security
- API key authentication for future versions
- HTTPS enforcement
- CORS configuration
- Request validation middleware

## Cross-Component Integration References

### Required Specification Compliance
- **AI_PROVIDER_SPEC.md**: Implement exact `Comparison`, `ComparisonRequest`, and `ProviderHealth` models
- **CONFIG_SYSTEM_SPEC.md**: Use `IConfigurationService` interface for all configuration loading
- **ERROR_MONITORING_SPEC.md**: Align all error responses with `ErrorCategory` and `ErrorSeverity` enums
- **DEPLOYMENT_OPS_SPEC.md**: Provide `/health`, `/ready`, and `/metrics` endpoints with specified schemas
- **TESTING_SPEC.md**: Design all Pydantic models to support comprehensive mocking patterns

### Implementation Contracts
1. **AI Provider Integration**: Must handle all `ProviderStatus` states and implement circuit breaker patterns
2. **Configuration Management**: Must support hot-reload and environment variable templating
3. **Error Classification**: All exceptions must map to ERROR_MONITORING_SPEC categories
4. **Health Monitoring**: Health checks must report AI provider connectivity and configuration validity
5. **Testing Support**: All models must be mockable with realistic test data generation

### External Documentation
- FastAPI Documentation: https://fastapi.tiangolo.com/
- Pydantic V2 Documentation: https://docs.pydantic.dev/latest/
- Prometheus Python Client: https://github.com/prometheus/client_python

## Appendices

### A. Sample Weight Parsing Test Cases
Provide 20+ examples of weight inputs and expected outputs

### B. Performance Benchmarks
Target metrics for various operations

### C. Error Code Reference
Complete list of error codes and their meanings

## 10. Cross-Component Integration Validation (1 page)

### 10.1 AI Provider Contract Validation
Backend must validate AI provider responses against exact schema:

```python
async def validate_ai_provider_integration():
    """Startup validation of AI provider contracts"""
    test_request = ComparisonRequest(
        weight=100.0,
        unit="kg",
        prompt_template="test prompt",
        max_tokens=100,
        temperature=0.7,
        timeout_seconds=10.0
    )
    
    for provider in ai_providers:
        try:
            # Test exact interface compliance
            health = provider.get_health_status()
            assert isinstance(health, ProviderHealth)
            assert health.status in ProviderStatus
            
            # Test response format
            comparisons = await provider.generate_comparisons(test_request)
            assert len(comparisons) == 2
            for comp in comparisons:
                assert isinstance(comp, Comparison)
                assert 0.0 <= comp.confidence <= 1.0
                
        except Exception as e:
            logger.error(f"Provider {provider.name} failed contract validation: {e}")
            raise ConfigurationError(f"AI provider contract violation: {e}")
```

### 10.2 Configuration Service Integration
Validate CONFIG_SYSTEM_SPEC compliance at startup:

```python
def validate_configuration_integration():
    """Validate configuration service contract compliance"""
    config_service = ConfigurationService()
    
    # Test required configuration paths
    required_paths = [
        "application.name",
        "application.version", 
        "api.cors.allow_origins",
        "ai_providers.selection_strategy",
        "comparison.max_objects"
    ]
    
    for path in required_paths:
        if not config_service.has(path):
            raise ConfigurationError(f"Missing required configuration: {path}")
    
    # Test hot-reload capability
    config_service.enable_hot_reload()
    assert callable(config_service.on_config_change)
```

### 10.3 Health Check Contract Compliance
Ensure DEPLOYMENT_OPS_SPEC health endpoints work correctly:

```python
@pytest.mark.integration
async def test_deployment_health_contracts():
    """Test health endpoints meet DEPLOYMENT_OPS_SPEC requirements"""
    
    # Test /health endpoint
    health_response = await client.get("/api/v1/health")
    assert health_response.status_code == 200
    health_data = health_response.json()
    assert health_data["status"] in ["healthy", "unhealthy"]
    assert "timestamp" in health_data
    assert "version" in health_data
    
    # Test /ready endpoint  
    ready_response = await client.get("/api/v1/ready")
    ready_data = ready_response.json()
    assert "ready" in ready_data
    assert "checks" in ready_data
    assert "ai_providers" in ready_data["checks"]
    assert "configuration" in ready_data["checks"]
    
    # Test /metrics endpoint
    metrics_response = await client.get("/api/v1/metrics")
    assert metrics_response.status_code == 200
    assert "text/plain" in metrics_response.headers["content-type"]
```

### 10.4 Error Response Contract Testing
Validate ERROR_MONITORING_SPEC compliance:

```python
@pytest.mark.integration  
async def test_error_monitoring_contracts():
    """Test error responses meet ERROR_MONITORING_SPEC format"""
    
    # Test validation error
    response = await client.post("/api/v1/compare", json={"invalid": "data"})
    assert response.status_code == 400
    error_data = response.json()
    
    # Validate error response structure
    assert "error_code" in error_data
    assert "error_category" in error_data
    assert error_data["error_category"] == "client_error"
    assert "request_id" in error_data
    assert "severity" in error_data
    assert "timestamp" in error_data
```

### 10.5 Testing Model Contract
Ensure all models support TESTING_SPEC mocking patterns:

```python
def test_model_mocking_compatibility():
    """Verify all models support comprehensive mocking"""
    
    # Test WeightItem mocking
    mock_weight = WeightItem(
        name="Test Object",
        original_input="100 kg", 
        weight_kg=Decimal("100.000000"),
        weight_display="100 kg",
        unit_used=WeightUnit.KILOGRAM,
        confidence=0.95
    )
    assert mock_weight.model_validate(mock_weight.dict())
    
    # Test complex response mocking
    mock_response = WeightComparisonResponse(
        item1=mock_weight,
        item2=mock_weight,
        comparison=ComparisonResult(
            ratio=Decimal("1.0"),
            percentage_difference=Decimal("0.0"),
            heavier_item="Equal",
            weight_difference_kg=Decimal("0.0")
        ),
        visualization=VisualizationPrompt(
            prompt="Mock prompt",
            comparisons=[],
            confidence_score=0.9,
            generation_time_ms=100,
            provider_used="mock"
        ),
        metadata=ResponseMetadata(
            request_id="test-123",
            processing_time_ms=50,
            ai_provider_used="mock",
            ai_response_time_ms=100,
            version="1.0.0"
        )
    )
    
    # Verify JSON serialization works for testing
    json_data = mock_response.model_dump()
    reconstructed = WeightComparisonResponse.model_validate(json_data)
    assert reconstructed == mock_response
```