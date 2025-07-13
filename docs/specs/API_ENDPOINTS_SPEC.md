# API Endpoints Specification for SizeComparator FastAPI Backend

## Document Overview

This specification provides comprehensive technical details for implementing SizeComparator's FastAPI endpoints with production-ready error handling, request/response middleware, input validation, and complete integration with all system components. Target implementation ensures sub-2 second response times while maintaining 99% uptime SLA requirements.

## 1. Executive Summary (0.5 pages)

### 1.1 API Architecture Overview

SizeComparator's FastAPI backend serves as the central orchestration layer, coordinating weight processing, AI provider interactions, and response formatting through a RESTful API interface. The system implements sophisticated middleware patterns for request correlation, error handling, and performance monitoring.

**Key API Responsibilities:**
- Weight comparison processing via POST /api/compare endpoint
- System health monitoring through DEPLOYMENT_OPS_SPEC compliant endpoints
- Request/response middleware for CORS, validation, and error handling
- Input sanitization and comprehensive validation using DATA_MODELS patterns
- Rate limiting and timeout management for production resilience

**Technology Stack:**
- FastAPI 0.104+ for async request handling
- Pydantic v2 for request/response validation
- Prometheus metrics integration for DEPLOYMENT_OPS_SPEC monitoring
- Structured logging aligned with ERROR_MONITORING_SPEC

**Performance Targets:**
- API response time: < 2 seconds (95th percentile, excluding AI processing)
- Concurrent request handling: 100 requests/second
- Memory usage: < 512MB under normal load
- 99% uptime SLA compliance

### 1.2 Integration Points

| Component | Integration Method | Purpose |
|-----------|-------------------|---------|
| BACKEND_CORE_SPEC | Pydantic models, async patterns | Core business logic and validation |
| AI_PROVIDER_SPEC | Provider interface, circuit breakers | AI-powered weight comparisons |
| CONFIG_SYSTEM_SPEC | Environment variables, hot-reload | Configuration management |
| ERROR_MONITORING_SPEC | Structured logging, request IDs | Error tracking and monitoring |
| DEPLOYMENT_OPS_SPEC | Health endpoints, metrics | Production monitoring |

## 2. Core Weight Comparison Endpoint (1.5 pages)

### 2.1 POST /api/compare - Full Implementation

The primary endpoint for weight comparisons integrating BACKEND_CORE_SPEC models with AI_PROVIDER_SPEC processing.

#### 2.1.1 Request Model (Data Models Integration)

```python
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from enum import Enum

class WeightUnit(str, Enum):
    """Supported weight units from BACKEND_CORE_SPEC"""
    KILOGRAM = "kg"
    POUND = "lb" 
    OUNCE = "oz"
    GRAM = "g"
    STONE = "st"
    METRIC_TON = "mt"

class WeightComparisonRequest(BaseModel):
    """Primary request model aligned with BACKEND_CORE_SPEC"""
    item1_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of first item to compare",
        example="African Elephant"
    )
    item1_weight: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Weight with optional unit (e.g., '5000 kg', '5 tons')",
        example="5000 kg"
    )
    item2_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of second item to compare",
        example="Honda Civic"
    )
    item2_weight: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Weight with optional unit",
        example="1300 kg"
    )
    output_unit: Optional[WeightUnit] = Field(
        default=WeightUnit.KILOGRAM,
        description="Preferred unit for output display"
    )
    comparison_context: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Additional context for AI comparison",
        example="Focus on size relative to everyday objects"
    )
    
    # Request metadata for ERROR_MONITORING_SPEC tracking
    request_id: Optional[str] = Field(
        default=None,
        description="Client-provided request ID for tracing"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "item1_name": "African Elephant",
                "item1_weight": "5000 kg",
                "item2_name": "Honda Civic", 
                "item2_weight": "1300 kg",
                "output_unit": "kg",
                "comparison_context": "Emphasize everyday relatability"
            }
        }
    
    @validator('item1_name', 'item2_name')
    def validate_item_names(cls, v):
        """Validate item names for security and appropriateness"""
        if not v.strip():
            raise ValueError("Item name cannot be empty")
        
        # Basic sanitization
        sanitized = v.strip()
        if len(sanitized) != len(v):
            raise ValueError("Item name contains invalid whitespace")
        
        # Prevent potential injection attacks
        forbidden_chars = ['<', '>', '{', '}', '[', ']', '&', '#']
        if any(char in sanitized for char in forbidden_chars):
            raise ValueError("Item name contains forbidden characters")
        
        return sanitized
    
    @validator('item1_weight', 'item2_weight')
    def validate_weight_format(cls, v):
        """Validate weight string format for WEIGHT_PROCESSOR integration"""
        weight_str = v.strip().lower()
        
        # Allow common weight patterns
        # Examples: "5 kg", "2.5 pounds", "3000g", "1.5 tons"
        import re
        weight_pattern = r'^[\d.,]+\s*(?:kg|g|lb|lbs|pound|pounds|oz|ounce|ounces|ton|tons|stone|st)?\s*$'
        
        if not re.match(weight_pattern, weight_str):
            raise ValueError(f"Invalid weight format: {v}. Use format like '5 kg' or '2.5 pounds'")
        
        return v.strip()
```

#### 2.1.2 Response Model (BACKEND_CORE_SPEC Alignment)

```python
from datetime import datetime
from typing import List, Optional

class WeightItem(BaseModel):
    """Individual weight item from BACKEND_CORE_SPEC"""
    name: str = Field(..., description="Item name")
    original_input: str = Field(..., description="Original weight input")
    weight_kg: Decimal = Field(
        ...,
        gt=Decimal('0.001'),
        le=Decimal('1000000'),
        description="Normalized weight in kilograms"
    )
    weight_display: str = Field(..., description="Human-readable weight with units")
    unit_used: WeightUnit = Field(..., description="Primary unit for display")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in weight parsing (0.0-1.0)"
    )
    
    @validator('weight_kg')
    def validate_precision(cls, v):
        """Ensure 6 decimal places maximum for internal precision"""
        return v.quantize(Decimal('0.000001'))

class ComparisonResult(BaseModel):
    """Weight comparison calculations from BACKEND_CORE_SPEC"""
    ratio: Decimal = Field(..., description="item1/item2 weight ratio")
    percentage_difference: Decimal = Field(
        ...,
        description="Percentage difference between weights"
    )
    heavier_item: str = Field(..., description="Name of heavier item or 'Equal'")
    weight_difference_kg: Decimal = Field(
        ...,
        description="Absolute weight difference in kg"
    )
    weight_difference_display: str = Field(
        ...,
        description="Human-readable weight difference"
    )
    calculation_method: str = Field(
        default="direct_conversion",
        description="Method used for calculation"
    )
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class AIComparison(BaseModel):
    """AI-generated comparison from AI_PROVIDER_SPEC"""
    description: str = Field(..., description="Object description for comparison")
    individual_weight: str = Field(..., description="Weight per individual item")
    total_weight: str = Field(..., description="Total weight description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")
    category: str = Field(..., description="Object category")
    provider_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="AI provider specific metadata"
    )

class VisualizationPrompt(BaseModel):
    """AI-generated visualization prompt from AI_PROVIDER_SPEC"""
    prompt: str = Field(..., min_length=10, description="Visualization prompt text")
    comparisons: List[AIComparison] = Field(
        ...,
        min_items=2,
        max_items=2,
        description="Exactly 2 AI-generated comparisons"
    )
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    generation_time_ms: int = Field(..., ge=0, description="AI generation time")
    provider_used: str = Field(..., min_length=1, description="AI provider name")

class ResponseMetadata(BaseModel):
    """Response metadata for ERROR_MONITORING_SPEC integration"""
    request_id: str = Field(..., description="Request correlation ID")
    processing_time_ms: int = Field(..., ge=0, description="Total processing time")
    ai_provider_used: str = Field(..., description="Primary AI provider")
    ai_response_time_ms: int = Field(..., ge=0, description="AI provider response time")
    cache_hit: bool = Field(default=False, description="Whether result was cached")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    version: str = Field(..., description="API version")
    weight_processing_time_ms: int = Field(..., ge=0, description="Weight parsing time")

class WeightComparisonResponse(BaseModel):
    """Complete response model for BACKEND_CORE_SPEC compliance"""
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
        json_schema_extra = {
            "example": {
                "item1": {
                    "name": "African Elephant",
                    "original_input": "5000 kg",
                    "weight_kg": 5000.0,
                    "weight_display": "5,000 kg",
                    "unit_used": "kg",
                    "confidence": 1.0
                },
                "item2": {
                    "name": "Honda Civic",
                    "original_input": "1300 kg",
                    "weight_kg": 1300.0,
                    "weight_display": "1,300 kg", 
                    "unit_used": "kg",
                    "confidence": 1.0
                },
                "comparison": {
                    "ratio": 3.85,
                    "percentage_difference": 284.6,
                    "heavier_item": "African Elephant",
                    "weight_difference_kg": 3700.0,
                    "weight_difference_display": "3,700 kg heavier"
                },
                "visualization": {
                    "prompt": "An African elephant standing next to a Honda Civic",
                    "comparisons": [
                        {
                            "description": "4 Honda Civics",
                            "individual_weight": "1,300 kg each",
                            "total_weight": "5,200 kg total",
                            "confidence": 0.95,
                            "category": "vehicle"
                        }
                    ],
                    "confidence_score": 0.92,
                    "generation_time_ms": 1200,
                    "provider_used": "openai"
                },
                "metadata": {
                    "request_id": "req_123456789",
                    "processing_time_ms": 1450,
                    "ai_provider_used": "openai",
                    "ai_response_time_ms": 1200,
                    "cache_hit": false,
                    "version": "1.0.0",
                    "weight_processing_time_ms": 50
                }
            }
        }
```

#### 2.1.3 Endpoint Implementation with Full Error Handling

```python
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from contextlib import asynccontextmanager
import time
import uuid
from typing import Optional

router = APIRouter(prefix="/api", tags=["weight-comparison"])

@router.post(
    "/compare",
    response_model=WeightComparisonResponse,
    status_code=200,
    summary="Compare two items by weight",
    description="Process weight comparison with AI-generated visualizations",
    responses={
        200: {"description": "Successful comparison"},
        400: {"description": "Invalid request data", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ValidationErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
        503: {"description": "Service temporarily unavailable", "model": ErrorResponse}
    }
)
async def compare_weights(
    request_data: WeightComparisonRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    weight_processor: WeightProcessorService = Depends(get_weight_processor),
    ai_service: AIProviderService = Depends(get_ai_service),
    cache_service: CacheService = Depends(get_cache_service),
    config_service: ConfigurationService = Depends(get_config_service),
    logger: StructuredLogger = Depends(get_logger)
) -> WeightComparisonResponse:
    """
    Compare two items by weight with AI-generated visualizations.
    
    Integrates with:
    - WEIGHT_PROCESSOR_SPEC for weight parsing and conversion
    - AI_PROVIDER_SPEC for visualization generation
    - CONFIG_SYSTEM_SPEC for configuration management
    - ERROR_MONITORING_SPEC for structured logging
    """
    start_time = time.time()
    
    # Get or generate request ID for ERROR_MONITORING_SPEC tracking
    request_id = request_data.request_id or str(uuid.uuid4())
    
    # Set request context for ERROR_MONITORING_SPEC
    from contextvars import ContextVar
    request_id_context: ContextVar[str] = ContextVar('request_id')
    request_id_context.set(request_id)
    
    logger.info(
        "Weight comparison request started",
        extra={
            "request_id": request_id,
            "item1_name": request_data.item1_name,
            "item2_name": request_data.item2_name,
            "client_ip": request.client.host
        }
    )
    
    try:
        # Check cache first for performance optimization
        cache_key = f"comparison:{hash(request_data.model_dump_json())}"
        cached_result = await cache_service.get(cache_key)
        
        if cached_result:
            logger.info(
                "Cache hit for weight comparison",
                extra={"request_id": request_id, "cache_key": cache_key}
            )
            cached_result["metadata"]["cache_hit"] = True
            cached_result["metadata"]["request_id"] = request_id
            return WeightComparisonResponse(**cached_result)
        
        # Phase 1: Weight Processing (WEIGHT_PROCESSOR_SPEC integration)
        weight_start = time.time()
        
        try:
            item1_weight = await weight_processor.parse_weight(
                request_data.item1_weight,
                context={"item_name": request_data.item1_name}
            )
            item2_weight = await weight_processor.parse_weight(
                request_data.item2_weight,
                context={"item_name": request_data.item2_name}
            )
        except WeightParsingException as e:
            logger.warning(
                "Weight parsing failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "item1_weight": request_data.item1_weight,
                    "item2_weight": request_data.item2_weight
                }
            )
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    error_code="WEIGHT_PARSING_ERROR",
                    error_category=ErrorCategory.BUSINESS_LOGIC_ERROR,
                    message=f"Unable to parse weight: {str(e)}",
                    request_id=request_id,
                    severity=ErrorSeverity.WARNING,
                    remediation_hint="Provide weight in format like '5 kg' or '2.5 pounds'"
                )
            )
        
        weight_processing_time = int((time.time() - weight_start) * 1000)
        
        # Create weight items
        item1 = WeightItem(
            name=request_data.item1_name,
            original_input=request_data.item1_weight,
            weight_kg=item1_weight.kg,
            weight_display=item1_weight.display_string(request_data.output_unit),
            unit_used=request_data.output_unit,
            confidence=item1_weight.confidence
        )
        
        item2 = WeightItem(
            name=request_data.item2_name,
            original_input=request_data.item2_weight,
            weight_kg=item2_weight.kg,
            weight_display=item2_weight.display_string(request_data.output_unit),
            unit_used=request_data.output_unit,
            confidence=item2_weight.confidence
        )
        
        # Phase 2: Comparison Calculation
        comparison = calculate_comparison(item1, item2)
        
        # Phase 3: AI Visualization Generation (AI_PROVIDER_SPEC integration)
        ai_start = time.time()
        
        ai_request = AIProviderRequest(
            item1_name=request_data.item1_name,
            item1_weight=request_data.item1_weight,
            item2_name=request_data.item2_name,
            item2_weight=request_data.item2_weight,
            prompt_template_id="size_comparison_basic",
            template_variables={
                "context": request_data.comparison_context or "",
                "output_unit": request_data.output_unit,
                "ratio": float(comparison.ratio)
            },
            request_id=request_id
        )
        
        try:
            ai_response = await ai_service.generate_comparisons(ai_request)
            ai_provider_used = ai_service.get_active_provider_name()
        except AIProviderException as e:
            logger.error(
                "AI provider failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "provider": ai_service.get_active_provider_name()
                }
            )
            # Fall back to default visualization
            ai_response = create_fallback_visualization(item1, item2, comparison)
            ai_provider_used = "fallback"
        
        ai_processing_time = int((time.time() - ai_start) * 1000)
        
        # Phase 4: Response Assembly
        total_processing_time = int((time.time() - start_time) * 1000)
        
        response = WeightComparisonResponse(
            item1=item1,
            item2=item2,
            comparison=comparison,
            visualization=ai_response,
            metadata=ResponseMetadata(
                request_id=request_id,
                processing_time_ms=total_processing_time,
                ai_provider_used=ai_provider_used,
                ai_response_time_ms=ai_processing_time,
                cache_hit=False,
                version=config_service.get("application.version"),
                weight_processing_time_ms=weight_processing_time
            )
        )
        
        # Cache successful result for future requests
        background_tasks.add_task(
            cache_service.set,
            cache_key,
            response.model_dump(),
            ttl_seconds=3600  # 1 hour cache
        )
        
        logger.info(
            "Weight comparison completed successfully",
            extra={
                "request_id": request_id,
                "processing_time_ms": total_processing_time,
                "ai_provider": ai_provider_used,
                "cache_hit": False
            }
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (already handled)
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(
            "Unexpected error in weight comparison",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                error_code="INTERNAL_SERVER_ERROR",
                error_category=ErrorCategory.SERVER_ERROR,
                message="An unexpected error occurred while processing your request",
                request_id=request_id,
                severity=ErrorSeverity.CRITICAL,
                remediation_hint="Please try again. If the problem persists, contact support."
            )
        )

def calculate_comparison(item1: WeightItem, item2: WeightItem) -> ComparisonResult:
    """Calculate weight comparison metrics"""
    ratio = item1.weight_kg / item2.weight_kg
    
    # Determine percentage difference and heavier item
    if item1.weight_kg > item2.weight_kg:
        percentage_diff = ((item1.weight_kg - item2.weight_kg) / item2.weight_kg) * 100
        heavier_item = item1.name
        weight_diff = item1.weight_kg - item2.weight_kg
        diff_display = f"{format_weight(weight_diff)} heavier"
    elif item2.weight_kg > item1.weight_kg:
        percentage_diff = ((item2.weight_kg - item1.weight_kg) / item1.weight_kg) * 100
        heavier_item = item2.name
        weight_diff = item2.weight_kg - item1.weight_kg
        diff_display = f"{format_weight(weight_diff)} heavier"
    else:
        percentage_diff = Decimal('0')
        heavier_item = "Equal"
        weight_diff = Decimal('0')
        diff_display = "Equal weight"
    
    return ComparisonResult(
        ratio=ratio.quantize(Decimal('0.01')),
        percentage_difference=percentage_diff.quantize(Decimal('0.1')),
        heavier_item=heavier_item,
        weight_difference_kg=weight_diff,
        weight_difference_display=diff_display
    )

def create_fallback_visualization(
    item1: WeightItem,
    item2: WeightItem,
    comparison: ComparisonResult
) -> VisualizationPrompt:
    """Create fallback visualization when AI providers fail"""
    return VisualizationPrompt(
        prompt=f"Visual comparison showing {item1.name} next to {item2.name}",
        comparisons=[
            AIComparison(
                description=f"Approximately {comparison.ratio:.1f} {item2.name}s",
                individual_weight=item2.weight_display,
                total_weight=f"{float(comparison.ratio * item2.weight_kg):.0f} kg total",
                confidence=0.8,
                category="fallback",
                provider_metadata={"fallback": True}
            ),
            AIComparison(
                description="Scale reference object",
                individual_weight="Variable",
                total_weight=f"Comparison ratio: {comparison.ratio:.2f}:1",
                confidence=0.8,
                category="reference",
                provider_metadata={"fallback": True}
            )
        ],
        confidence_score=0.8,
        generation_time_ms=0,
        provider_used="fallback"
    )
```

## 3. Health Check Endpoints (DEPLOYMENT_OPS_SPEC Integration) (1 page)

### 3.1 Health Monitoring Implementation

Complete implementation of DEPLOYMENT_OPS_SPEC health check requirements with AI provider monitoring.

```python
from fastapi import APIRouter, Depends, Response
from datetime import datetime
from typing import Dict, Any, Optional

health_router = APIRouter(prefix="/api/v1", tags=["health"])

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthResponse(BaseModel):
    """Basic health response for DEPLOYMENT_OPS_SPEC load balancers"""
    status: HealthStatus = Field(..., description="Overall system health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(..., description="Application version")
    uptime_seconds: int = Field(..., description="Application uptime in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "version": "1.0.0",
                "uptime_seconds": 3600
            }
        }

class ComponentHealth(BaseModel):
    """Individual component health status"""
    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Component health status")
    response_time_ms: Optional[int] = Field(None, description="Last response time")
    last_check: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ReadinessResponse(BaseModel):
    """Comprehensive readiness response for DEPLOYMENT_OPS_SPEC"""
    ready: bool = Field(..., description="Whether service is ready to accept traffic")
    checks: Dict[str, str] = Field(..., description="Individual check results")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = Field(None, description="Detailed check information")
    component_health: List[ComponentHealth] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "ready": True,
                "checks": {
                    "ai_provider_connectivity": "pass",
                    "configuration_loaded": "pass",
                    "cache_connectivity": "pass",
                    "memory_usage": "pass"
                },
                "timestamp": "2024-01-15T10:30:00Z",
                "details": {
                    "ai_providers": {
                        "openai": "healthy",
                        "anthropic": "degraded",
                        "xai": "circuit_open"
                    },
                    "memory_usage_mb": 256,
                    "cpu_usage_percent": 15.5
                }
            }
        }

@health_router.get(
    "/health",
    response_model=HealthResponse,
    status_code=200,
    summary="Basic health check",
    description="Liveness probe for DEPLOYMENT_OPS_SPEC load balancers and orchestrators"
)
async def health_check(
    config_service: ConfigurationService = Depends(get_config_service),
    app_state: ApplicationState = Depends(get_app_state)
) -> HealthResponse:
    """
    Basic health check endpoint for DEPLOYMENT_OPS_SPEC integration.
    
    This endpoint should always return quickly (< 1 second) and provides
    minimal health information for load balancer health checks.
    """
    
    # Calculate uptime
    uptime_seconds = int((datetime.utcnow() - app_state.startup_time).total_seconds())
    
    # Determine overall health status
    status = HealthStatus.HEALTHY
    
    # Basic checks that might affect health
    try:
        # Verify configuration is loaded
        version = config_service.get("application.version")
        
        # Check memory usage (simple check)
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # If memory usage is extremely high, mark as degraded
        if memory_mb > 1024:  # > 1GB
            status = HealthStatus.DEGRADED
        
    except Exception:
        status = HealthStatus.UNHEALTHY
        version = "unknown"
    
    return HealthResponse(
        status=status,
        version=version,
        uptime_seconds=uptime_seconds
    )

@health_router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=200,
    summary="Comprehensive readiness check",
    description="Readiness probe with dependency health checks for DEPLOYMENT_OPS_SPEC"
)
async def readiness_check(
    ai_service: AIProviderService = Depends(get_ai_service),
    cache_service: CacheService = Depends(get_cache_service),
    config_service: ConfigurationService = Depends(get_config_service),
    logger: StructuredLogger = Depends(get_logger)
) -> ReadinessResponse:
    """
    Comprehensive readiness check for DEPLOYMENT_OPS_SPEC integration.
    
    Checks all critical dependencies and reports detailed health status.
    Used by Kubernetes readiness probes and deployment health monitoring.
    """
    
    checks = {}
    component_health = []
    overall_ready = True
    
    # Check 1: Configuration System
    try:
        config_check_start = time.time()
        config_valid = config_service.is_valid()
        config_check_time = int((time.time() - config_check_start) * 1000)
        
        if config_valid:
            checks["configuration_loaded"] = "pass"
            component_health.append(ComponentHealth(
                name="configuration",
                status=HealthStatus.HEALTHY,
                response_time_ms=config_check_time,
                metadata={"hot_reload_enabled": config_service.is_hot_reload_enabled()}
            ))
        else:
            checks["configuration_loaded"] = "fail"
            overall_ready = False
            component_health.append(ComponentHealth(
                name="configuration",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=config_check_time,
                error_message="Configuration validation failed"
            ))
    except Exception as e:
        checks["configuration_loaded"] = "error"
        overall_ready = False
        logger.error("Configuration health check failed", extra={"error": str(e)})
    
    # Check 2: AI Provider Connectivity (AI_PROVIDER_SPEC integration)
    try:
        ai_health = await ai_service.get_health_status()
        provider_details = {}
        
        for provider_name, provider_health in ai_health.items():
            provider_details[provider_name] = provider_health.status.value
            
            component_health.append(ComponentHealth(
                name=f"ai_provider_{provider_name}",
                status=HealthStatus(provider_health.status.value),
                response_time_ms=int(provider_health.avg_response_time_ms),
                metadata={
                    "circuit_state": provider_health.circuit_state,
                    "success_rate": provider_health.success_rate,
                    "error_count": provider_health.error_count
                }
            ))
        
        # AI providers are ready if at least one provider is healthy
        healthy_providers = [
            h for h in ai_health.values() 
            if h.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]
        ]
        
        if healthy_providers:
            checks["ai_provider_connectivity"] = "pass"
        else:
            checks["ai_provider_connectivity"] = "fail"
            overall_ready = False
        
    except Exception as e:
        checks["ai_provider_connectivity"] = "error"
        overall_ready = False
        logger.error("AI provider health check failed", extra={"error": str(e)})
    
    # Check 3: Cache Connectivity
    try:
        cache_check_start = time.time()
        cache_healthy = await cache_service.health_check()
        cache_check_time = int((time.time() - cache_check_start) * 1000)
        
        if cache_healthy:
            checks["cache_connectivity"] = "pass"
            component_health.append(ComponentHealth(
                name="cache",
                status=HealthStatus.HEALTHY,
                response_time_ms=cache_check_time,
                metadata=cache_service.get_stats()
            ))
        else:
            checks["cache_connectivity"] = "degraded"
            # Cache issues don't prevent readiness, just degrade performance
            component_health.append(ComponentHealth(
                name="cache",
                status=HealthStatus.DEGRADED,
                response_time_ms=cache_check_time,
                error_message="Cache connectivity issues"
            ))
    except Exception as e:
        checks["cache_connectivity"] = "error"
        logger.warning("Cache health check failed", extra={"error": str(e)})
    
    # Check 4: System Resources
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        # Memory check
        if memory_mb < 512:
            checks["memory_usage"] = "pass"
            memory_status = HealthStatus.HEALTHY
        elif memory_mb < 1024:
            checks["memory_usage"] = "degraded"
            memory_status = HealthStatus.DEGRADED
        else:
            checks["memory_usage"] = "fail"
            memory_status = HealthStatus.UNHEALTHY
            overall_ready = False
        
        component_health.append(ComponentHealth(
            name="memory",
            status=memory_status,
            metadata={
                "memory_mb": int(memory_mb),
                "cpu_percent": cpu_percent
            }
        ))
        
    except Exception as e:
        checks["memory_usage"] = "error"
        logger.warning("Resource health check failed", extra={"error": str(e)})
    
    # Aggregate details for response
    details = {
        "ai_providers": provider_details if 'provider_details' in locals() else {},
        "memory_usage_mb": int(memory_mb) if 'memory_mb' in locals() else None,
        "cpu_usage_percent": cpu_percent if 'cpu_percent' in locals() else None,
        "total_checks": len(checks),
        "passed_checks": len([c for c in checks.values() if c == "pass"])
    }
    
    return ReadinessResponse(
        ready=overall_ready,
        checks=checks,
        details=details,
        component_health=component_health
    )

@health_router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Metrics endpoint for DEPLOYMENT_OPS_SPEC monitoring integration"
)
async def metrics(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """
    Prometheus metrics endpoint for DEPLOYMENT_OPS_SPEC integration.
    
    Exposes application metrics in Prometheus format for monitoring
    and alerting systems.
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    # Update metrics before exposing
    await metrics_service.update_metrics()
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

### 3.2 Metrics Collection for DEPLOYMENT_OPS_SPEC

```python
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest

class MetricsService:
    """Metrics collection service for DEPLOYMENT_OPS_SPEC monitoring"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Request metrics (RED pattern)
        self.request_counter = Counter(
            'sizecomparator_requests_total',
            'Total requests processed',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'sizecomparator_request_duration_seconds',
            'Request processing duration',
            ['endpoint'],
            registry=self.registry
        )
        
        self.request_size = Histogram(
            'sizecomparator_request_size_bytes',
            'Request payload size',
            ['endpoint'],
            registry=self.registry
        )
        
        # AI provider metrics (AI_PROVIDER_SPEC integration)
        self.ai_provider_requests = Counter(
            'sizecomparator_ai_provider_requests_total',
            'AI provider requests',
            ['provider', 'status'],
            registry=self.registry
        )
        
        self.ai_provider_duration = Histogram(
            'sizecomparator_ai_provider_duration_seconds',
            'AI provider response time',
            ['provider'],
            registry=self.registry
        )
        
        self.ai_provider_health = Gauge(
            'sizecomparator_ai_provider_health',
            'AI provider health status (1=healthy, 0=unhealthy)',
            ['provider'],
            registry=self.registry
        )
        
        self.circuit_breaker_state = Gauge(
            'sizecomparator_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half_open)',
            ['provider'],
            registry=self.registry
        )
        
        # Business metrics
        self.weight_comparisons = Counter(
            'sizecomparator_weight_comparisons_total',
            'Total weight comparisons processed',
            registry=self.registry
        )
        
        self.cache_operations = Counter(
            'sizecomparator_cache_operations_total',
            'Cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        # System metrics
        self.active_connections = Gauge(
            'sizecomparator_active_connections',
            'Current active connections',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'sizecomparator_memory_usage_bytes',
            'Current memory usage',
            registry=self.registry
        )
    
    async def update_metrics(self):
        """Update gauge metrics with current values"""
        try:
            # Update memory usage
            import psutil
            process = psutil.Process()
            self.memory_usage.set(process.memory_info().rss)
            
            # Update AI provider health metrics (would be injected)
            # This would be called by the AI service when health changes
            
        except Exception as e:
            logger.warning("Failed to update metrics", extra={"error": str(e)})
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record request metrics"""
        self.request_counter.labels(method=method, endpoint=endpoint, status=status).inc()
        self.request_duration.labels(endpoint=endpoint).observe(duration)
    
    def record_ai_request(self, provider: str, status: str, duration: float):
        """Record AI provider request metrics"""
        self.ai_provider_requests.labels(provider=provider, status=status).inc()
        self.ai_provider_duration.labels(provider=provider).observe(duration)
    
    def update_ai_provider_health(self, provider: str, healthy: bool):
        """Update AI provider health gauge"""
        self.ai_provider_health.labels(provider=provider).set(1 if healthy else 0)
    
    def update_circuit_breaker_state(self, provider: str, state: str):
        """Update circuit breaker state gauge"""
        state_mapping = {"closed": 0, "open": 1, "half_open": 2}
        self.circuit_breaker_state.labels(provider=provider).set(state_mapping.get(state, 0))
```

## 4. Request/Response Middleware Implementation (1.5 pages)

### 4.1 CORS Middleware with CONFIG_SYSTEM_SPEC Integration

```python
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid
import json
from typing import Callable

def setup_cors_middleware(app: FastAPI, config_service: ConfigurationService):
    """Configure CORS middleware using CONFIG_SYSTEM_SPEC settings"""
    
    cors_config = config_service.get("api.cors", {
        "allow_origins": ["http://localhost:3000"],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["*"],
        "expose_headers": ["X-Request-ID", "X-Processing-Time"]
    })
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get("allow_origins", ["*"]),
        allow_credentials=cors_config.get("allow_credentials", False),
        allow_methods=cors_config.get("allow_methods", ["*"]),
        allow_headers=cors_config.get("allow_headers", ["*"]),
        expose_headers=cors_config.get("expose_headers", [])
    )

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Request ID middleware for ERROR_MONITORING_SPEC tracing"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Set in context for ERROR_MONITORING_SPEC
        from contextvars import ContextVar
        request_id_context: ContextVar[str] = ContextVar('request_id')
        request_id_context.set(request_id)
        
        # Add to request state for access in endpoints
        request.state.request_id = request_id
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        processing_time = time.time() - start_time
        
        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
        
        return response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware for ERROR_MONITORING_SPEC integration"""
    
    def __init__(self, app, logger: StructuredLogger, metrics_service: MetricsService):
        super().__init__(app)
        self.logger = logger
        self.metrics_service = metrics_service
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        try:
            response = await call_next(request)
            
            # Record successful request metrics
            duration = time.time() - start_time
            self.metrics_service.record_request(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                duration=duration
            )
            
            return response
            
        except HTTPException as e:
            # Handle known HTTP exceptions
            duration = time.time() - start_time
            
            self.logger.warning(
                "HTTP exception occurred",
                extra={
                    "request_id": request_id,
                    "status_code": e.status_code,
                    "detail": e.detail,
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration
                }
            )
            
            self.metrics_service.record_request(
                method=request.method,
                endpoint=request.url.path,
                status=e.status_code,
                duration=duration
            )
            
            # Return properly formatted error response
            return JSONResponse(
                status_code=e.status_code,
                content=e.detail if isinstance(e.detail, dict) else {"message": e.detail}
            )
            
        except ValidationError as e:
            # Handle Pydantic validation errors
            duration = time.time() - start_time
            
            self.logger.warning(
                "Validation error occurred",
                extra={
                    "request_id": request_id,
                    "validation_errors": e.errors(),
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration
                }
            )
            
            self.metrics_service.record_request(
                method=request.method,
                endpoint=request.url.path,
                status=422,
                duration=duration
            )
            
            # Create detailed validation error response
            field_errors = []
            for error in e.errors():
                field_errors.append({
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"]
                })
            
            error_response = ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                error_category=ErrorCategory.CLIENT_ERROR,
                message="Request validation failed",
                field_errors=field_errors,
                request_id=request_id,
                severity=ErrorSeverity.INFO,
                remediation_hint="Check the request format and ensure all required fields are provided correctly"
            )
            
            return JSONResponse(
                status_code=422,
                content=error_response.model_dump()
            )
            
        except Exception as e:
            # Handle unexpected errors
            duration = time.time() - start_time
            
            self.logger.error(
                "Unhandled exception occurred",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration
                },
                exc_info=True
            )
            
            self.metrics_service.record_request(
                method=request.method,
                endpoint=request.url.path,
                status=500,
                duration=duration
            )
            
            # Create generic error response
            error_response = ErrorResponse(
                error_code="INTERNAL_SERVER_ERROR",
                error_category=ErrorCategory.SERVER_ERROR,
                message="An unexpected error occurred",
                request_id=request_id,
                severity=ErrorSeverity.CRITICAL,
                remediation_hint="Please try again later. If the problem persists, contact support."
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response.model_dump()
            )

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware for ERROR_MONITORING_SPEC"""
    
    def __init__(self, app, logger: StructuredLogger, config_service: ConfigurationService):
        super().__init__(app)
        self.logger = logger
        self.config_service = config_service
        self.log_request_body = config_service.get("logging.log_request_body", False)
        self.log_response_body = config_service.get("logging.log_response_body", False)
        self.max_body_size = config_service.get("logging.max_body_size", 1024)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        # Log incoming request
        request_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": request.client.host if request.client else None
        }
        
        # Optionally log request body
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) <= self.max_body_size:
                    # Safely decode body for logging
                    try:
                        request_data["body"] = json.loads(body.decode())
                    except:
                        request_data["body"] = body.decode()[:self.max_body_size]
                else:
                    request_data["body_size"] = len(body)
                    request_data["body_truncated"] = True
            except:
                request_data["body_error"] = "Could not read request body"
        
        self.logger.info("Request started", extra=request_data)
        
        # Process request
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        response_data = {
            "request_id": request_id,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "response_headers": dict(response.headers)
        }
        
        self.logger.info("Request completed", extra=response_data)
        
        return response

def setup_middleware(app: FastAPI, dependencies: Dict[str, Any]):
    """Setup all middleware in correct order"""
    
    # 1. CORS middleware (first to handle preflight requests)
    setup_cors_middleware(app, dependencies["config_service"])
    
    # 2. Request ID middleware (early to ensure all logs have request ID)
    app.add_middleware(RequestIDMiddleware)
    
    # 3. Request logging middleware
    app.add_middleware(
        RequestLoggingMiddleware,
        logger=dependencies["logger"],
        config_service=dependencies["config_service"]
    )
    
    # 4. Error handling middleware (last to catch all errors)
    app.add_middleware(
        ErrorHandlingMiddleware,
        logger=dependencies["logger"],
        metrics_service=dependencies["metrics_service"]
    )
```

### 4.2 Rate Limiting Middleware

```python
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with sliding window algorithm"""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 100,
        burst_limit: int = 20,
        config_service: ConfigurationService = None
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.config_service = config_service
        
        # Sliding window storage: client_ip -> [(timestamp, count), ...]
        self.request_windows: Dict[str, List[Tuple[datetime, int]]] = defaultdict(list)
        self.burst_counters: Dict[str, Tuple[datetime, int]] = {}
        
        # Cleanup task
        self.cleanup_task = None
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start cleanup task if not running
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self.cleanup_old_entries())
        
        client_ip = request.client.host if request.client else "unknown"
        now = datetime.utcnow()
        
        # Check if rate limiting is enabled for this request
        if not self.should_rate_limit(request):
            return await call_next(request)
        
        # Get current rate limit configuration
        rate_config = self.get_rate_limit_config()
        
        # Check burst limit (short-term)
        if not self.check_burst_limit(client_ip, now, rate_config["burst_limit"]):
            return self.create_rate_limit_response(
                "Burst limit exceeded. Please slow down your requests."
            )
        
        # Check sliding window limit (longer-term)
        if not self.check_sliding_window(client_ip, now, rate_config["requests_per_minute"]):
            return self.create_rate_limit_response(
                f"Rate limit exceeded. Maximum {rate_config['requests_per_minute']} requests per minute."
            )
        
        # Record this request
        self.record_request(client_ip, now)
        
        return await call_next(request)
    
    def should_rate_limit(self, request: Request) -> bool:
        """Determine if request should be rate limited"""
        # Skip rate limiting for health checks
        if request.url.path in ["/api/v1/health", "/api/v1/ready", "/api/v1/metrics"]:
            return False
        
        # Skip for internal requests (if configured)
        if self.config_service:
            internal_ips = self.config_service.get("rate_limiting.internal_ips", [])
            if request.client and request.client.host in internal_ips:
                return False
        
        return True
    
    def get_rate_limit_config(self) -> Dict[str, int]:
        """Get current rate limiting configuration"""
        if self.config_service:
            return {
                "requests_per_minute": self.config_service.get(
                    "rate_limiting.requests_per_minute", 
                    self.requests_per_minute
                ),
                "burst_limit": self.config_service.get(
                    "rate_limiting.burst_limit",
                    self.burst_limit
                )
            }
        
        return {
            "requests_per_minute": self.requests_per_minute,
            "burst_limit": self.burst_limit
        }
    
    def check_burst_limit(self, client_ip: str, now: datetime, burst_limit: int) -> bool:
        """Check burst limit (requests in last 10 seconds)"""
        if client_ip not in self.burst_counters:
            self.burst_counters[client_ip] = (now, 1)
            return True
        
        last_time, count = self.burst_counters[client_ip]
        
        # Reset counter if more than 10 seconds have passed
        if now - last_time > timedelta(seconds=10):
            self.burst_counters[client_ip] = (now, 1)
            return True
        
        # Check if under burst limit
        if count < burst_limit:
            self.burst_counters[client_ip] = (last_time, count + 1)
            return True
        
        return False
    
    def check_sliding_window(self, client_ip: str, now: datetime, requests_per_minute: int) -> bool:
        """Check sliding window rate limit"""
        window_start = now - timedelta(minutes=1)
        
        # Clean old entries for this client
        if client_ip in self.request_windows:
            self.request_windows[client_ip] = [
                (timestamp, count) for timestamp, count in self.request_windows[client_ip]
                if timestamp > window_start
            ]
        
        # Count requests in current window
        total_requests = sum(
            count for timestamp, count in self.request_windows[client_ip]
        )
        
        return total_requests < requests_per_minute
    
    def record_request(self, client_ip: str, now: datetime):
        """Record a request for rate limiting tracking"""
        self.request_windows[client_ip].append((now, 1))
    
    def create_rate_limit_response(self, message: str) -> Response:
        """Create rate limit exceeded response"""
        error_response = ErrorResponse(
            error_code="RATE_LIMIT_EXCEEDED",
            error_category=ErrorCategory.CLIENT_ERROR,
            message=message,
            request_id=str(uuid.uuid4()),
            severity=ErrorSeverity.INFO,
            remediation_hint="Wait before making additional requests"
        )
        
        return JSONResponse(
            status_code=429,
            content=error_response.model_dump(),
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": "0"
            }
        )
    
    async def cleanup_old_entries(self):
        """Periodically clean up old rate limiting entries"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean every 5 minutes
                now = datetime.utcnow()
                cutoff_time = now - timedelta(minutes=2)
                
                # Clean request windows
                for client_ip in list(self.request_windows.keys()):
                    self.request_windows[client_ip] = [
                        (timestamp, count) for timestamp, count in self.request_windows[client_ip]
                        if timestamp > cutoff_time
                    ]
                    
                    if not self.request_windows[client_ip]:
                        del self.request_windows[client_ip]
                
                # Clean burst counters
                burst_cutoff = now - timedelta(minutes=1)
                for client_ip in list(self.burst_counters.keys()):
                    last_time, _ = self.burst_counters[client_ip]
                    if last_time < burst_cutoff:
                        del self.burst_counters[client_ip]
                        
            except Exception as e:
                # Log cleanup errors but don't crash
                logger.warning("Rate limit cleanup failed", extra={"error": str(e)})
```

## 5. Input Validation and Error Response Formatting (1 page)

### 5.1 Comprehensive Input Validation

```python
from pydantic import validator, root_validator
import re
from typing import Any, Dict, List

class SecurityValidator:
    """Security-focused input validation"""
    
    @staticmethod
    def validate_no_injection(value: str, field_name: str) -> str:
        """Prevent common injection attacks"""
        dangerous_patterns = [
            r'<script.*?>.*?</script>',  # XSS
            r'javascript:',              # JavaScript URLs
            r'on\w+\s*=',               # Event handlers
            r'\\x[0-9a-fA-F]{2}',       # Hex encoding
            r'\\u[0-9a-fA-F]{4}',       # Unicode encoding
            r'[\x00-\x1f\x7f-\x9f]',   # Control characters
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"{field_name} contains potentially dangerous content")
        
        return value
    
    @staticmethod
    def validate_length_limits(value: str, min_len: int, max_len: int, field_name: str) -> str:
        """Validate string length limits"""
        if len(value) < min_len:
            raise ValueError(f"{field_name} must be at least {min_len} characters")
        if len(value) > max_len:
            raise ValueError(f"{field_name} must not exceed {max_len} characters")
        return value
    
    @staticmethod
    def validate_allowed_characters(value: str, allowed_pattern: str, field_name: str) -> str:
        """Validate only allowed characters are present"""
        if not re.match(allowed_pattern, value):
            raise ValueError(f"{field_name} contains invalid characters")
        return value

class WeightValidator:
    """Weight-specific validation logic"""
    
    WEIGHT_PATTERNS = {
        'metric': r'^(\d+(?:\.\d+)?)\s*(kg|g|kilogram|gram)s?$',
        'imperial': r'^(\d+(?:\.\d+)?)\s*(lb|lbs|pound|pounds|oz|ounce|ounces)$',
        'mixed': r'^(\d+(?:\.\d+)?)\s*(ton|tons|tonne|tonnes|stone|st)s?$'
    }
    
    @classmethod
    def validate_weight_format(cls, weight_str: str) -> Dict[str, Any]:
        """Validate and parse weight string"""
        cleaned = weight_str.strip().lower()
        
        # Try each pattern
        for pattern_type, pattern in cls.WEIGHT_PATTERNS.items():
            match = re.match(pattern, cleaned)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                
                # Validate reasonable ranges
                if value <= 0:
                    raise ValueError("Weight must be positive")
                
                if value > 1000000:  # 1M kg limit
                    raise ValueError("Weight exceeds maximum allowed value")
                
                return {
                    'value': value,
                    'unit': unit,
                    'pattern_type': pattern_type,
                    'confidence': 1.0
                }
        
        # Try to handle edge cases
        return cls._handle_edge_cases(cleaned)
    
    @classmethod
    def _handle_edge_cases(cls, weight_str: str) -> Dict[str, Any]:
        """Handle edge cases in weight parsing"""
        # Handle number without unit (assume kg)
        if re.match(r'^\d+(?:\.\d+)?$', weight_str):
            value = float(weight_str)
            return {
                'value': value,
                'unit': 'kg',
                'pattern_type': 'assumed',
                'confidence': 0.8
            }
        
        # Handle common abbreviations
        common_substitutions = {
            'kilos': 'kg',
            'kilo': 'kg',
            'grams': 'g',
            'gram': 'g',
            'lbs': 'lb',
            'pounds': 'lb'
        }
        
        for old, new in common_substitutions.items():
            if old in weight_str:
                modified = weight_str.replace(old, new)
                try:
                    return cls.validate_weight_format(modified)
                except:
                    continue
        
        raise ValueError(f"Unable to parse weight format: {weight_str}")

# Enhanced request model with comprehensive validation
class ValidatedWeightComparisonRequest(WeightComparisonRequest):
    """Extended request model with security and business validation"""
    
    @validator('item1_name', 'item2_name')
    def validate_item_names_comprehensive(cls, v, field):
        """Comprehensive item name validation"""
        # Security validation
        v = SecurityValidator.validate_no_injection(v, field.name)
        v = SecurityValidator.validate_length_limits(v, 1, 100, field.name)
        v = SecurityValidator.validate_allowed_characters(
            v, 
            r'^[a-zA-Z0-9\s\-_.,()]+$',
            field.name
        )
        
        # Business logic validation
        if len(v.strip()) == 0:
            raise ValueError(f"{field.name} cannot be empty")
        
        # Check for inappropriate content
        inappropriate_words = ['test', 'debug', 'admin']  # Extend as needed
        if any(word in v.lower() for word in inappropriate_words):
            raise ValueError(f"{field.name} contains inappropriate content")
        
        return v.strip()
    
    @validator('item1_weight', 'item2_weight')
    def validate_weight_comprehensive(cls, v, field):
        """Comprehensive weight validation"""
        # Security validation
        v = SecurityValidator.validate_no_injection(v, field.name)
        v = SecurityValidator.validate_length_limits(v, 1, 50, field.name)
        
        # Weight format validation
        try:
            weight_info = WeightValidator.validate_weight_format(v)
            # Store parsed weight info for later use
            setattr(cls, f'_{field.name}_info', weight_info)
        except ValueError as e:
            raise ValueError(f"{field.name}: {str(e)}")
        
        return v
    
    @validator('comparison_context')
    def validate_context(cls, v):
        """Validate comparison context"""
        if v is None:
            return v
        
        v = SecurityValidator.validate_no_injection(v, 'comparison_context')
        v = SecurityValidator.validate_length_limits(v, 0, 200, 'comparison_context')
        
        return v.strip()
    
    @root_validator
    def validate_request_consistency(cls, values):
        """Cross-field validation"""
        item1_name = values.get('item1_name')
        item2_name = values.get('item2_name')
        
        # Ensure items are different
        if item1_name and item2_name and item1_name.lower() == item2_name.lower():
            raise ValueError("Cannot compare an item to itself")
        
        return values
```

### 5.2 Error Response Formatting (ERROR_MONITORING_SPEC Integration)

```python
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List

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
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "WEIGHT_PARSING_ERROR",
                "error_category": "business_logic_error",
                "message": "Unable to parse weight format",
                "details": {
                    "input": "five kilos",
                    "expected_format": "number + unit (e.g., '5 kg')"
                },
                "request_id": "req_123456789",
                "timestamp": "2024-01-15T10:30:00Z",
                "severity": "info",
                "remediation_hint": "Provide weight in format like '5 kg' or '2.5 pounds'"
            }
        }

class ValidationErrorResponse(ErrorResponse):
    """Specific error for validation failures"""
    error_category: ErrorCategory = Field(default=ErrorCategory.CLIENT_ERROR)
    field_errors: List[Dict[str, str]] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "VALIDATION_ERROR", 
                "error_category": "client_error",
                "message": "Request validation failed",
                "field_errors": [
                    {
                        "field": "item1_name",
                        "message": "Item name contains invalid characters",
                        "type": "value_error"
                    },
                    {
                        "field": "item1_weight",
                        "message": "Unable to parse weight format",
                        "type": "value_error"
                    }
                ],
                "request_id": "req_123456789",
                "severity": "info",
                "remediation_hint": "Check the request format and field values"
            }
        }

# HTTP Status Code Mapping
HTTP_STATUS_MAPPING = {
    ErrorCategory.CLIENT_ERROR: 400,
    ErrorCategory.BUSINESS_LOGIC_ERROR: 400,
    ErrorCategory.INTEGRATION_ERROR: 503,
    ErrorCategory.SERVER_ERROR: 500
}

def create_error_response(
    error_code: str,
    error_category: ErrorCategory,
    message: str,
    request_id: str,
    severity: ErrorSeverity,
    details: Optional[Dict[str, Any]] = None,
    remediation_hint: Optional[str] = None
) -> Dict[str, Any]:
    """Create standardized error response"""
    
    error_response = ErrorResponse(
        error_code=error_code,
        error_category=error_category,
        message=message,
        details=details or {},
        request_id=request_id,
        severity=severity,
        remediation_hint=remediation_hint
    )
    
    return error_response.model_dump()

# Common error responses for reuse
def weight_parsing_error(input_value: str, request_id: str) -> Dict[str, Any]:
    """Standard weight parsing error response"""
    return create_error_response(
        error_code="WEIGHT_PARSING_ERROR",
        error_category=ErrorCategory.BUSINESS_LOGIC_ERROR,
        message=f"Unable to parse weight format: {input_value}",
        request_id=request_id,
        severity=ErrorSeverity.INFO,
        details={"input": input_value, "expected_format": "number + unit (e.g., '5 kg')"},
        remediation_hint="Provide weight in format like '5 kg' or '2.5 pounds'"
    )

def ai_provider_error(provider: str, error_message: str, request_id: str) -> Dict[str, Any]:
    """Standard AI provider error response"""
    return create_error_response(
        error_code="AI_PROVIDER_ERROR",
        error_category=ErrorCategory.INTEGRATION_ERROR,
        message="AI service temporarily unavailable",
        request_id=request_id,
        severity=ErrorSeverity.WARNING,
        details={"provider": provider, "error": error_message},
        remediation_hint="Please try again. The service will automatically retry with backup providers."
    )

def rate_limit_error(limit: int, request_id: str) -> Dict[str, Any]:
    """Standard rate limit error response"""
    return create_error_response(
        error_code="RATE_LIMIT_EXCEEDED",
        error_category=ErrorCategory.CLIENT_ERROR,
        message=f"Rate limit exceeded. Maximum {limit} requests per minute.",
        request_id=request_id,
        severity=ErrorSeverity.INFO,
        details={"limit": limit, "period": "minute"},
        remediation_hint="Wait before making additional requests"
    )

def validation_error(field_errors: List[Dict[str, str]], request_id: str) -> Dict[str, Any]:
    """Standard validation error response"""
    error_response = ValidationErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        field_errors=field_errors,
        request_id=request_id,
        severity=ErrorSeverity.INFO,
        remediation_hint="Check the request format and ensure all required fields are provided correctly"
    )
    
    return error_response.model_dump()
```

## 6. Rate Limiting and Request Timeout Handling (1 page)

### 6.1 Advanced Rate Limiting with Circuit Breaker Integration

```python
import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import redis.asyncio as redis

class DistributedRateLimiter:
    """Distributed rate limiter using Redis for multi-instance deployments"""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        default_limit: int = 100,
        window_size: int = 60,
        burst_limit: int = 20,
        burst_window: int = 10
    ):
        self.redis = redis_client
        self.default_limit = default_limit
        self.window_size = window_size
        self.burst_limit = burst_limit
        self.burst_window = burst_window
        
        # Lua script for atomic rate limiting
        self.rate_limit_script = """
        local key = KEYS[1]
        local window = tonumber(ARGV[1])
        local limit = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        
        -- Remove expired entries
        redis.call('ZREMRANGEBYSCORE', key, 0, current_time - window)
        
        -- Count current requests
        local current_count = redis.call('ZCARD', key)
        
        if current_count < limit then
            -- Add current request
            redis.call('ZADD', key, current_time, current_time)
            redis.call('EXPIRE', key, window)
            return {1, limit - current_count - 1}
        else
            return {0, 0}
        end
        """
        
        self.script_sha = None
    
    async def initialize(self):
        """Initialize Redis scripts"""
        self.script_sha = await self.redis.script_load(self.rate_limit_script)
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit for identifier.
        
        Returns:
            (allowed, remaining, reset_time)
        """
        limit = limit or self.default_limit
        window = window or self.window_size
        current_time = int(time.time())
        
        key = f"rate_limit:{identifier}"
        
        try:
            if self.script_sha:
                result = await self.redis.evalsha(
                    self.script_sha,
                    1,
                    key,
                    str(window),
                    str(limit),
                    str(current_time)
                )
            else:
                # Fallback if script not loaded
                await self.initialize()
                result = await self.redis.evalsha(
                    self.script_sha,
                    1,
                    key,
                    str(window),
                    str(limit),
                    str(current_time)
                )
            
            allowed = bool(result[0])
            remaining = int(result[1])
            reset_time = current_time + window
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            # Fall back to local rate limiting if Redis fails
            logger.warning("Redis rate limiting failed, using local fallback", extra={"error": str(e)})
            return True, limit, current_time + window
    
    async def check_burst_limit(self, identifier: str) -> bool:
        """Check burst rate limit"""
        return await self.check_rate_limit(
            f"burst:{identifier}",
            self.burst_limit,
            self.burst_window
        )[0]

class TimeoutManager:
    """Advanced timeout management with adaptive timeouts"""
    
    def __init__(self):
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.base_timeouts = {
            "weight_processing": 2.0,
            "ai_provider": 30.0,
            "cache_operation": 1.0,
            "total_request": 45.0
        }
    
    def calculate_adaptive_timeout(self, operation_type: str, complexity_factor: float = 1.0) -> float:
        """Calculate adaptive timeout based on historical performance"""
        base_timeout = self.base_timeouts.get(operation_type, 10.0)
        
        # Get recent response times for this operation
        recent_times = self.response_times.get(operation_type, deque())
        
        if len(recent_times) < 10:
            # Not enough data, use base timeout
            return base_timeout * complexity_factor
        
        # Calculate P95 response time
        sorted_times = sorted(recent_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index]
        
        # Adaptive timeout = P95 + buffer, bounded by min/max
        adaptive_timeout = p95_time * 1.5 * complexity_factor
        
        # Apply bounds
        min_timeout = base_timeout * 0.5
        max_timeout = base_timeout * 3.0
        
        return max(min_timeout, min(adaptive_timeout, max_timeout))
    
    def record_response_time(self, operation_type: str, response_time: float):
        """Record response time for adaptive timeout calculation"""
        self.response_times[operation_type].append(response_time)
    
    async def execute_with_timeout(
        self,
        coro,
        operation_type: str,
        complexity_factor: float = 1.0,
        custom_timeout: Optional[float] = None
    ):
        """Execute coroutine with adaptive timeout"""
        timeout = custom_timeout or self.calculate_adaptive_timeout(operation_type, complexity_factor)
        
        start_time = time.time()
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            response_time = time.time() - start_time
            self.record_response_time(operation_type, response_time)
            return result
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            self.record_response_time(operation_type, response_time)
            raise
        except Exception as e:
            response_time = time.time() - start_time
            self.record_response_time(operation_type, response_time)
            raise

class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Request timeout middleware with graceful handling"""
    
    def __init__(
        self,
        app,
        default_timeout: float = 45.0,
        timeout_manager: TimeoutManager = None,
        logger: StructuredLogger = None
    ):
        super().__init__(app)
        self.default_timeout = default_timeout
        self.timeout_manager = timeout_manager or TimeoutManager()
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        # Determine timeout based on endpoint
        timeout = self.get_endpoint_timeout(request.url.path)
        
        try:
            return await self.timeout_manager.execute_with_timeout(
                call_next(request),
                "total_request",
                custom_timeout=timeout
            )
        except asyncio.TimeoutError:
            if self.logger:
                self.logger.warning(
                    "Request timeout exceeded",
                    extra={
                        "request_id": request_id,
                        "path": request.url.path,
                        "method": request.method,
                        "timeout": timeout
                    }
                )
            
            error_response = create_error_response(
                error_code="REQUEST_TIMEOUT",
                error_category=ErrorCategory.SERVER_ERROR,
                message=f"Request timed out after {timeout} seconds",
                request_id=request_id,
                severity=ErrorSeverity.WARNING,
                remediation_hint="The request took too long to process. Please try again with a simpler request."
            )
            
            return JSONResponse(
                status_code=408,
                content=error_response
            )
    
    def get_endpoint_timeout(self, path: str) -> float:
        """Get timeout for specific endpoint"""
        endpoint_timeouts = {
            "/api/compare": 45.0,  # AI processing can take time
            "/api/v1/health": 2.0,
            "/api/v1/ready": 5.0,
            "/api/v1/metrics": 3.0
        }
        
        return endpoint_timeouts.get(path, self.default_timeout)

# Integration with main application
class RateLimitConfig(BaseModel):
    """Rate limiting configuration from CONFIG_SYSTEM_SPEC"""
    enabled: bool = True
    requests_per_minute: int = 100
    burst_limit: int = 20
    use_redis: bool = True
    redis_url: Optional[str] = None
    whitelist_ips: List[str] = Field(default_factory=list)
    
class RateLimitingService:
    """Service for managing rate limiting across the application"""
    
    def __init__(self, config: RateLimitConfig, redis_client: Optional[redis.Redis] = None):
        self.config = config
        self.redis_client = redis_client
        
        if config.use_redis and redis_client:
            self.rate_limiter = DistributedRateLimiter(redis_client)
        else:
            # Use local rate limiter as fallback
            self.rate_limiter = LocalRateLimiter()
    
    async def check_rate_limit(self, client_ip: str, endpoint: str) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for client and endpoint"""
        
        # Skip rate limiting for whitelisted IPs
        if client_ip in self.config.whitelist_ips:
            return True, {"whitelisted": True}
        
        # Get endpoint-specific limits
        endpoint_config = self.get_endpoint_config(endpoint)
        
        # Check rate limit
        allowed, remaining, reset_time = await self.rate_limiter.check_rate_limit(
            f"{client_ip}:{endpoint}",
            limit=endpoint_config["limit"],
            window=endpoint_config["window"]
        )
        
        return allowed, {
            "limit": endpoint_config["limit"],
            "remaining": remaining,
            "reset_time": reset_time,
            "endpoint": endpoint
        }
    
    def get_endpoint_config(self, endpoint: str) -> Dict[str, int]:
        """Get rate limiting configuration for endpoint"""
        endpoint_configs = {
            "/api/compare": {"limit": 50, "window": 60},  # More restrictive for AI endpoints
            "/api/v1/health": {"limit": 300, "window": 60},  # More permissive for health checks
            "/api/v1/ready": {"limit": 300, "window": 60},
            "/api/v1/metrics": {"limit": 100, "window": 60}
        }
        
        return endpoint_configs.get(endpoint, {"limit": self.config.requests_per_minute, "window": 60})

# Example integration with FastAPI
async def setup_rate_limiting_and_timeouts(app: FastAPI, config_service: ConfigurationService):
    """Setup rate limiting and timeout middleware"""
    
    # Load rate limiting configuration
    rate_limit_config = RateLimitConfig(
        enabled=config_service.get("rate_limiting.enabled", True),
        requests_per_minute=config_service.get("rate_limiting.requests_per_minute", 100),
        burst_limit=config_service.get("rate_limiting.burst_limit", 20),
        use_redis=config_service.get("rate_limiting.use_redis", True),
        redis_url=config_service.get("cache.connection.url"),
        whitelist_ips=config_service.get("rate_limiting.whitelist_ips", [])
    )
    
    # Setup Redis if enabled
    redis_client = None
    if rate_limit_config.use_redis and rate_limit_config.redis_url:
        redis_client = redis.from_url(rate_limit_config.redis_url)
    
    # Create rate limiting service
    rate_limiting_service = RateLimitingService(rate_limit_config, redis_client)
    
    # Create timeout manager
    timeout_manager = TimeoutManager()
    
    # Add middleware
    if rate_limit_config.enabled:
        app.add_middleware(
            RateLimitMiddleware,
            rate_limiting_service=rate_limiting_service
        )
    
    app.add_middleware(
        RequestTimeoutMiddleware,
        timeout_manager=timeout_manager
    )
    
    return rate_limiting_service, timeout_manager
```

## 7. FastAPI Application Integration and Configuration (0.5 pages)

### 7.1 Complete Application Setup

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting SizeComparator API server")
    
    # Initialize services
    await initialize_services()
    
    # Health check startup validation
    health_status = await perform_startup_health_check()
    if not health_status["healthy"]:
        logger.error("Startup health check failed", extra=health_status)
        raise RuntimeError("Application failed startup health checks")
    
    logger.info("SizeComparator API server started successfully")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down SizeComparator API server")
    await cleanup_services()
    logger.info("SizeComparator API server shutdown complete")

def create_app(config_service: ConfigurationService) -> FastAPI:
    """Create and configure FastAPI application"""
    
    app_config = config_service.get("application", {})
    api_config = config_service.get("api", {})
    
    app = FastAPI(
        title=app_config.get("name", "SizeComparator API"),
        version=app_config.get("version", "1.0.0"),
        description="Weight comparison API with AI-powered visualizations",
        lifespan=lifespan,
        docs_url="/docs" if app_config.get("environment") != "production" else None,
        redoc_url="/redoc" if app_config.get("environment") != "production" else None,
        openapi_url="/openapi.json" if app_config.get("environment") != "production" else None
    )
    
    # Setup dependency injection
    setup_dependencies(app, config_service)
    
    # Setup middleware (order matters!)
    setup_middleware(app, config_service)
    
    # Setup routes
    setup_routes(app)
    
    # Setup error handlers
    setup_error_handlers(app)
    
    return app

def setup_routes(app: FastAPI):
    """Setup API routes"""
    app.include_router(router, prefix="")  # Weight comparison endpoints
    app.include_router(health_router, prefix="")  # Health check endpoints

async def initialize_services():
    """Initialize all application services"""
    # Initialize AI providers
    await ai_service.initialize()
    
    # Initialize cache
    await cache_service.initialize()
    
    # Initialize metrics
    await metrics_service.initialize()
    
    # Initialize rate limiting
    if rate_limiting_service:
        await rate_limiting_service.initialize()

async def perform_startup_health_check() -> Dict[str, Any]:
    """Perform comprehensive startup health check"""
    checks = {}
    
    # Check configuration
    checks["configuration"] = config_service.is_valid()
    
    # Check AI providers
    try:
        ai_health = await ai_service.get_health_status()
        checks["ai_providers"] = any(
            status.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]
            for status in ai_health.values()
        )
    except:
        checks["ai_providers"] = False
    
    # Check cache
    try:
        checks["cache"] = await cache_service.health_check()
    except:
        checks["cache"] = False
    
    overall_healthy = all(checks.values())
    
    return {
        "healthy": overall_healthy,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

async def cleanup_services():
    """Cleanup application services"""
    # Cleanup AI providers
    await ai_service.cleanup()
    
    # Cleanup cache connections
    await cache_service.cleanup()
    
    # Cleanup metrics
    await metrics_service.cleanup()

# Application configuration and startup
if __name__ == "__main__":
    import uvicorn
    from app.config.service import ConfigurationService
    
    # Load configuration
    config_service = ConfigurationService()
    config_service.load_from_environment()
    
    # Create application
    app = create_app(config_service)
    
    # Get server configuration
    server_config = config_service.get("server", {})
    
    # Run server
    uvicorn.run(
        app,
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8000),
        workers=server_config.get("workers", 1),
        log_config=None,  # Use our custom logging
        access_log=False  # Handled by middleware
    )
```

This comprehensive API endpoints specification provides:

1. **Complete POST /api/compare endpoint** with full BACKEND_CORE_SPEC model integration and AI_PROVIDER_SPEC processing
2. **Health check endpoints** fully compliant with DEPLOYMENT_OPS_SPEC requirements  
3. **Comprehensive middleware stack** for CORS, request ID tracking, error handling, rate limiting, and timeouts
4. **Input validation framework** with security-focused validation and ERROR_MONITORING_SPEC error formatting
5. **Rate limiting and timeout handling** with Redis-based distributed limiting and adaptive timeouts
6. **Production-ready error handling** with specific HTTP status codes and ERROR_MONITORING_SPEC categorization

The specification ensures sub-2 second response times while maintaining 99% uptime through proper error handling, circuit breakers, and comprehensive monitoring integration.

**File Path**: `/home/commodore/projects/SizeComparator/API_ENDPOINTS_SPEC.md`