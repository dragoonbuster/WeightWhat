"""
Weight Comparison API Endpoints

This module implements the main weight comparison endpoints including:
- POST /compare - Primary weight comparison with AI visualization
- GET /compare/{request_id} - Retrieve comparison by request ID
- GET /providers - List available AI providers
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from ...models.requests import WeightComparisonRequest
from ...models.responses import WeightComparisonResponse, ProviderSelectionResponse
from ...models.errors import ErrorCategory, ErrorSeverity
from ...models.weight import ProcessedWeight, WeightProcessor
from ...services.comparison.comparison_service import ComparisonService
from ...core.simple_config import SimpleConfig
from ..main import (
    get_comparison_service,
    get_weight_processor,
    get_config_service,
    get_cache_service,
    get_metrics_service
)

logger = logging.getLogger(__name__)

comparison_router = APIRouter()


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
    from datetime import datetime
    
    return {
        "error_code": error_code,
        "error_category": error_category.value,
        "message": message,
        "details": details or {},
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "severity": severity.value,
        "remediation_hint": remediation_hint
    }


@comparison_router.post(
    "/compare",
    response_model=WeightComparisonResponse,
    status_code=200,
    summary="Compare two items by weight",
    description="Process weight comparison with AI-generated visualizations and detailed analysis",
    responses={
        200: {"description": "Successful comparison"},
        400: {
            "description": "Invalid request data",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "WEIGHT_PARSING_ERROR",
                        "error_category": "business_logic_error",
                        "message": "Unable to parse weight format",
                        "request_id": "req_123456789",
                        "severity": "info",
                        "remediation_hint": "Provide weight in format like '5 kg' or '2.5 pounds'"
                    }
                }
            }
        },
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
        503: {"description": "Service temporarily unavailable"}
    }
)
async def compare_weights(
    request_data: WeightComparisonRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    comparison_service: ComparisonService = Depends(get_comparison_service),
    weight_processor: WeightProcessor = Depends(get_weight_processor),
    cache_service = Depends(get_cache_service),
    metrics_service = Depends(get_metrics_service),
    config_service: SimpleConfig = Depends(get_config_service)
) -> WeightComparisonResponse:
    """
    Compare two items by weight with AI-generated visualizations.
    
    This endpoint processes weight comparison requests by:
    1. Parsing and validating weight inputs
    2. Calculating detailed comparison metrics
    3. Generating AI visualization prompts
    4. Returning comprehensive analysis results
    
    The endpoint integrates with multiple AI providers and includes
    fallback mechanisms for reliability.
    """
    start_time = time.time()
    request_id = str(request_data.request_id)
    
    # Set request context for tracing
    request.state.request_id = request_id
    
    logger.info(
        "Weight comparison request started",
        extra={
            "request_id": request_id,
            "item1": request_data.item1,
            "item2": request_data.item2,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    try:
        # Check cache first for performance optimization
        cache_key = _generate_cache_key(request_data)
        cached_result = await cache_service.get(cache_key)
        
        if cached_result:
            logger.info(
                "Cache hit for weight comparison",
                extra={"request_id": request_id, "cache_key": cache_key}
            )
            # Update request ID and timestamp in cached result
            cached_result["metadata"]["request_id"] = request_id
            cached_result["metadata"]["cache_hit"] = True
            return WeightComparisonResponse(**cached_result)
        
        # Phase 1: Weight Processing
        weight_start = time.time()
        
        try:
            # Process first item weight
            item1_processed = weight_processor.process_weight_input(request_data.item1_weight)
            item1_processed.original_input.source = f"Item: {request_data.item1}"
            
            # Process second item weight  
            item2_processed = weight_processor.process_weight_input(request_data.item2_weight)
            item2_processed.original_input.source = f"Item: {request_data.item2}"
            
        except Exception as e:
            logger.warning(
                "Weight parsing failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "item1_weight": str(request_data.item1_weight.value),
                    "item2_weight": str(request_data.item2_weight.value)
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
                    remediation_hint="Ensure weights are in valid format like '5 kg', '2.5 pounds', or numeric values with units"
                )
            )
        
        weight_processing_time = int((time.time() - weight_start) * 1000)
        
        # Phase 2: Comparison Analysis
        analysis_start = time.time()
        comparison_analysis = weight_processor.calculate_comparison(item1_processed, item2_processed)
        analysis_time = int((time.time() - analysis_start) * 1000)
        
        # Phase 3: AI Visualization Generation (if requested)
        ai_start = time.time()
        visualization_prompt = None
        ai_provider_used = "none"
        ai_processing_time = 0
        
        if request_data.include_visualization:
            try:
                # Create weight input for comparison service
                weight_input = f"{request_data.item1} weighs {item1_processed.display_value}, {request_data.item2} weighs {item2_processed.display_value}"
                
                comparison_response = await comparison_service.create_comparison(
                    weight_input=weight_input,
                    preferred_provider=request_data.preferred_provider if request_data.preferred_provider != "auto" else None,
                    comparison_style=request_data.comparison_type.value,
                    include_visualization=True,
                    user_context={
                        "locale": request_data.locale,
                        "temperature": request_data.ai_temperature,
                        "max_tokens": request_data.max_response_tokens
                    }
                )
                
                if comparison_response and comparison_response.visualization_prompt:
                    from ...models.responses import AIVisualizationPrompt
                    visualization_prompt = AIVisualizationPrompt(
                        prompt_text=comparison_response.visualization_prompt,
                        provider_used=comparison_response.metadata.provider_used,
                        generation_time_ms=comparison_response.metadata.response_time_ms,
                        confidence_score=comparison_response.metadata.confidence_score,
                        fallback_used=comparison_response.metadata.is_fallback if hasattr(comparison_response.metadata, 'is_fallback') else False
                    )
                    ai_provider_used = comparison_response.metadata.provider_used
                
            except Exception as e:
                logger.error(
                    "AI visualization generation failed",
                    extra={
                        "request_id": request_id,
                        "error": str(e),
                        "provider": request_data.preferred_provider
                    }
                )
                # Continue without visualization - not a critical error
                pass
        
        ai_processing_time = int((time.time() - ai_start) * 1000)
        
        # Phase 4: Response Assembly
        total_processing_time = int((time.time() - start_time) * 1000)
        
        # Create analysis response
        from ...models.responses import ComparisonAnalysis, ResponseMetadata
        analysis_response = ComparisonAnalysis(
            weight_ratio=comparison_analysis["weight_ratio"],
            percentage_difference=comparison_analysis["percentage_difference"],
            absolute_difference=comparison_analysis["absolute_difference"],
            heavier_item=comparison_analysis["heavier_item"],
            significance_level=comparison_analysis["significance_level"],
            comparison_category=comparison_analysis.get("comparison_category", "general"),
            equivalent_objects=[]  # Could be populated from comparison service
        )
        
        # Create metadata
        metadata = ResponseMetadata(
            request_id=request_data.request_id,
            processing_time_ms=total_processing_time,
            component_timings={
                "weight_processing": weight_processing_time,
                "analysis": analysis_time,
                "ai_generation": ai_processing_time
            },
            ai_provider_used=ai_provider_used if ai_provider_used != "none" else None,
            ai_response_time_ms=ai_processing_time if ai_processing_time > 0 else None,
            cache_hit=False,
            warnings=[],
            api_version=config_service.get_section("application.version", "1.0.0")
        )
        
        # Create final response
        response = WeightComparisonResponse(
            item1=item1_processed,
            item2=item2_processed,
            analysis=analysis_response,
            visualization=visualization_prompt,
            metadata=metadata
        )
        
        # Cache successful result for future requests
        background_tasks.add_task(
            _cache_response,
            cache_service,
            cache_key,
            response,
            ttl_seconds=3600  # 1 hour cache
        )
        
        # Record metrics
        metrics_service.histogram(
            "comparison.response_time_ms",
            total_processing_time,
            tags={
                "provider": ai_provider_used,
                "cache_hit": "false",
                "include_visualization": str(request_data.include_visualization)
            }
        )
        metrics_service.increment("comparison.requests_total", tags={"status": "success"})
        
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
        
        metrics_service.increment("comparison.requests_total", tags={"status": "error"})
        
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


@comparison_router.get(
    "/compare/{request_id}",
    response_model=WeightComparisonResponse,
    summary="Retrieve comparison by request ID",
    description="Get a previously processed weight comparison by its request ID"
)
async def get_comparison(
    request_id: str,
    cache_service = Depends(get_cache_service)
) -> WeightComparisonResponse:
    """Retrieve a cached comparison result by request ID"""
    
    try:
        # Try to find in cache by request ID
        cache_key = f"comparison_by_id:{request_id}"
        cached_result = await cache_service.get(cache_key)
        
        if not cached_result:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    error_code="COMPARISON_NOT_FOUND",
                    error_category=ErrorCategory.CLIENT_ERROR,
                    message=f"No comparison found with request ID: {request_id}",
                    request_id=request_id,
                    severity=ErrorSeverity.INFO,
                    remediation_hint="Ensure the request ID is correct and the comparison was completed successfully"
                )
            )
        
        return WeightComparisonResponse(**cached_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving comparison {request_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                error_code="RETRIEVAL_ERROR",
                error_category=ErrorCategory.SERVER_ERROR,
                message="Failed to retrieve comparison",
                request_id=request_id,
                severity=ErrorSeverity.WARNING
            )
        )


@comparison_router.get(
    "/providers",
    response_model=Dict[str, Any],
    summary="List available AI providers",
    description="Get information about available AI providers and their current status"
)
async def list_providers(
    comparison_service: ComparisonService = Depends(get_comparison_service)
) -> Dict[str, Any]:
    """List available AI providers and their status"""
    
    try:
        # This would integrate with the AI provider factory to get real status
        # For now, return a mock response
        providers = {
            "available_providers": [
                {
                    "name": "openai",
                    "status": "healthy",
                    "models": ["gpt-4", "gpt-3.5-turbo"],
                    "avg_response_time_ms": 1200,
                    "success_rate": 0.98
                },
                {
                    "name": "anthropic", 
                    "status": "healthy",
                    "models": ["claude-3-sonnet", "claude-3-haiku"],
                    "avg_response_time_ms": 1800,
                    "success_rate": 0.97
                },
                {
                    "name": "xai",
                    "status": "degraded",
                    "models": ["grok-1"],
                    "avg_response_time_ms": 2500,
                    "success_rate": 0.85
                }
            ],
            "default_provider": "auto",
            "selection_strategy": "performance_weighted"
        }
        
        return providers
        
    except Exception as e:
        logger.error(f"Error listing providers: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                error_code="PROVIDER_LISTING_ERROR",
                error_category=ErrorCategory.SERVER_ERROR,
                message="Failed to retrieve provider information",
                request_id=str(uuid.uuid4()),
                severity=ErrorSeverity.WARNING
            )
        )


def _generate_cache_key(request_data: WeightComparisonRequest) -> str:
    """Generate cache key for request"""
    import hashlib
    
    # Create hash from key request components
    key_components = [
        str(request_data.item1_weight.value),
        str(request_data.item1_weight.unit) if request_data.item1_weight.unit else "",
        str(request_data.item2_weight.value), 
        str(request_data.item2_weight.unit) if request_data.item2_weight.unit else "",
        request_data.comparison_type.value,
        str(request_data.include_visualization),
        request_data.preferred_provider or "auto"
    ]
    
    key_string = ":".join(key_components)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"comparison:v1:{key_hash}"


async def _cache_response(
    cache_service,
    cache_key: str,
    response: WeightComparisonResponse,
    ttl_seconds: int
):
    """Cache response in background task"""
    try:
        await cache_service.set(cache_key, response.model_dump(), ttl=ttl_seconds)
        
        # Also cache by request ID for retrieval
        request_id_key = f"comparison_by_id:{response.metadata.request_id}"
        await cache_service.set(request_id_key, response.model_dump(), ttl=ttl_seconds)
        
    except Exception as e:
        logger.warning(f"Failed to cache response: {e}")