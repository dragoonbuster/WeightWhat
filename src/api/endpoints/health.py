"""
Health Check API Endpoints

This module implements health monitoring endpoints for DEPLOYMENT_OPS_SPEC compliance:
- GET /health - Basic liveness probe
- GET /ready - Comprehensive readiness probe with dependency checks
- GET /health/detailed - Detailed health information for debugging
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
import psutil

from ...models.responses import HealthCheckResponse, ReadinessResponse, ReadinessCheck
from ...core.simple_config import SimpleConfig
from ..main import (
    get_app_state,
    get_config_service,
    get_cache_service,
    get_comparison_service,
    get_ai_provider_factory,
    app_state
)

logger = logging.getLogger(__name__)

health_router = APIRouter()


@health_router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=200,
    summary="Basic health check",
    description="Liveness probe for load balancers and orchestrators. Returns quickly with minimal health information.",
    responses={
        200: {"description": "Service is alive"},
        503: {"description": "Service is unhealthy"}
    }
)
async def health_check(
    config_service: SimpleConfig = Depends(get_config_service)
) -> HealthCheckResponse:
    """
    Basic health check endpoint for liveness probes.
    
    This endpoint should always return quickly (< 1 second) and provides
    minimal health information for load balancer health checks.
    """
    
    try:
        # Calculate uptime
        startup_time = app_state.get("startup_time")
        if startup_time:
            uptime_seconds = int((datetime.utcnow() - startup_time).total_seconds())
        else:
            uptime_seconds = 0
        
        # Get basic configuration
        version = config_service.get_section("application.version", "1.0.0")
        environment = config_service.get_section("application.environment", "development")
        
        # Perform minimal health checks
        status = "healthy"
        components = {}
        
        # Check memory usage (simple check)
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > 1024:  # > 1GB
                status = "degraded"
                
            components["memory"] = {
                "name": "memory",
                "status": "healthy" if memory_mb <= 1024 else "degraded",
                "last_check": datetime.utcnow().isoformat(),
                "metadata": {"memory_mb": int(memory_mb)}
            }
        except Exception as e:
            logger.warning(f"Memory check failed: {e}")
            status = "degraded"
            components["memory"] = {
                "name": "memory", 
                "status": "degraded",
                "last_check": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        
        # Check if critical services are initialized
        if not app_state.get("comparison_service"):
            status = "unhealthy"
            components["core_services"] = {
                "name": "core_services",
                "status": "unhealthy", 
                "last_check": datetime.utcnow().isoformat(),
                "error": "Core services not initialized"
            }
        else:
            components["core_services"] = {
                "name": "core_services",
                "status": "healthy",
                "last_check": datetime.utcnow().isoformat()
            }
        
        response = HealthCheckResponse(
            status=status,
            version=version,
            environment=environment,
            uptime_seconds=uptime_seconds,
            components=components
        )
        
        # Set appropriate HTTP status based on health
        if status == "unhealthy":
            raise HTTPException(
                status_code=503,
                detail=response.model_dump()
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        # Return unhealthy status
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "version": "unknown",
                "environment": "unknown", 
                "uptime_seconds": 0,
                "components": {
                    "health_check": {
                        "name": "health_check",
                        "status": "unhealthy",
                        "last_check": datetime.utcnow().isoformat(),
                        "error": str(e)
                    }
                }
            }
        )


@health_router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=200,
    summary="Comprehensive readiness check",
    description="Readiness probe with dependency health checks. Used by Kubernetes and monitoring systems.",
    responses={
        200: {"description": "Service is ready"},
        503: {"description": "Service is not ready"}
    }
)
async def readiness_check(
    cache_service = Depends(get_cache_service),
    config_service: SimpleConfig = Depends(get_config_service),
    ai_provider_factory = Depends(get_ai_provider_factory)
) -> ReadinessResponse:
    """
    Comprehensive readiness check for deployment orchestrators.
    
    Checks all critical dependencies and reports detailed health status.
    Used by Kubernetes readiness probes and deployment health monitoring.
    """
    
    checks = {}
    overall_ready = True
    start_time = time.time()
    
    # Check 1: Configuration System
    config_check_start = time.time()
    try:
        config_valid = config_service is not None
        config_version = config_service.get_section("application.version", "unknown") if config_service else "unknown"
        config_check_time = int((time.time() - config_check_start) * 1000)
        
        if config_valid and config_version != "unknown":
            checks["configuration"] = ReadinessCheck(
                check_name="configuration",
                status="pass",
                message="Configuration loaded successfully",
                duration_ms=config_check_time,
                required=True
            )
        else:
            checks["configuration"] = ReadinessCheck(
                check_name="configuration",
                status="fail",
                message="Configuration not properly loaded",
                duration_ms=config_check_time,
                required=True
            )
            overall_ready = False
            
    except Exception as e:
        config_check_time = int((time.time() - config_check_start) * 1000)
        checks["configuration"] = ReadinessCheck(
            check_name="configuration",
            status="fail",
            message=f"Configuration check failed: {str(e)}",
            duration_ms=config_check_time,
            required=True
        )
        overall_ready = False
        logger.error("Configuration readiness check failed", extra={"error": str(e)})
    
    # Check 2: Cache Connectivity
    cache_check_start = time.time()
    try:
        if cache_service:
            test_key = f"readiness_check_{int(time.time())}"
            await cache_service.set(test_key, "ok", ttl=10)
            result = await cache_service.get(test_key)
            cache_check_time = int((time.time() - cache_check_start) * 1000)
            
            if result == "ok":
                checks["cache"] = ReadinessCheck(
                    check_name="cache",
                    status="pass",
                    message="Cache connectivity verified",
                    duration_ms=cache_check_time,
                    required=False,  # Cache failure doesn't prevent readiness
                    threshold={"max_response_time_ms": 1000}
                )
            else:
                checks["cache"] = ReadinessCheck(
                    check_name="cache",
                    status="warn",
                    message="Cache test failed",
                    duration_ms=cache_check_time,
                    required=False
                )
        else:
            cache_check_time = int((time.time() - cache_check_start) * 1000)
            checks["cache"] = ReadinessCheck(
                check_name="cache",
                status="fail",
                message="Cache service not initialized",
                duration_ms=cache_check_time,
                required=False
            )
            
    except Exception as e:
        cache_check_time = int((time.time() - cache_check_start) * 1000)
        checks["cache"] = ReadinessCheck(
            check_name="cache",
            status="warn", 
            message=f"Cache check failed: {str(e)}",
            duration_ms=cache_check_time,
            required=False
        )
        logger.warning("Cache readiness check failed", extra={"error": str(e)})
    
    # Check 3: AI Provider Connectivity
    ai_check_start = time.time()
    try:
        if ai_provider_factory:
            # Check if any providers are available
            available_providers = await ai_provider_factory.get_available_providers()
            ai_check_time = int((time.time() - ai_check_start) * 1000)
            
            if available_providers and len(available_providers) > 0:
                checks["ai_providers"] = ReadinessCheck(
                    check_name="ai_providers",
                    status="pass",
                    message=f"Found {len(available_providers)} available AI providers",
                    duration_ms=ai_check_time,
                    required=True,
                    threshold={"min_providers": 1}
                )
            else:
                checks["ai_providers"] = ReadinessCheck(
                    check_name="ai_providers",
                    status="fail",
                    message="No AI providers available",
                    duration_ms=ai_check_time,
                    required=True
                )
                overall_ready = False
        else:
            ai_check_time = int((time.time() - ai_check_start) * 1000)
            checks["ai_providers"] = ReadinessCheck(
                check_name="ai_providers",
                status="fail",
                message="AI provider factory not initialized",
                duration_ms=ai_check_time,
                required=True
            )
            overall_ready = False
            
    except Exception as e:
        ai_check_time = int((time.time() - ai_check_start) * 1000)
        checks["ai_providers"] = ReadinessCheck(
            check_name="ai_providers",
            status="fail",
            message=f"AI provider check failed: {str(e)}",
            duration_ms=ai_check_time,
            required=True
        )
        overall_ready = False
        logger.error("AI provider readiness check failed", extra={"error": str(e)})
    
    # Check 4: System Resources
    resource_check_start = time.time()
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        resource_check_time = int((time.time() - resource_check_start) * 1000)
        
        # Memory thresholds
        if memory_mb < 512:
            memory_status = "pass"
            memory_message = f"Memory usage normal: {memory_mb:.1f} MB"
        elif memory_mb < 1024:
            memory_status = "warn"
            memory_message = f"Memory usage elevated: {memory_mb:.1f} MB"
        else:
            memory_status = "fail"
            memory_message = f"Memory usage critical: {memory_mb:.1f} MB"
            overall_ready = False
        
        checks["memory"] = ReadinessCheck(
            check_name="memory",
            status=memory_status,
            message=memory_message,
            duration_ms=resource_check_time,
            required=True,
            threshold={
                "warning_mb": 512,
                "critical_mb": 1024,
                "current_mb": int(memory_mb)
            }
        )
        
    except Exception as e:
        resource_check_time = int((time.time() - resource_check_start) * 1000)
        checks["memory"] = ReadinessCheck(
            check_name="memory",
            status="warn",
            message=f"Resource check failed: {str(e)}",
            duration_ms=resource_check_time,
            required=False
        )
        logger.warning("Resource readiness check failed", extra={"error": str(e)})
    
    # Check 5: Core Services
    service_check_start = time.time()
    try:
        comparison_service = app_state.get("comparison_service")
        weight_processor = app_state.get("weight_processor")
        service_check_time = int((time.time() - service_check_start) * 1000)
        
        if comparison_service and weight_processor:
            checks["core_services"] = ReadinessCheck(
                check_name="core_services", 
                status="pass",
                message="All core services initialized",
                duration_ms=service_check_time,
                required=True
            )
        else:
            missing_services = []
            if not comparison_service:
                missing_services.append("comparison_service")
            if not weight_processor:
                missing_services.append("weight_processor")
                
            checks["core_services"] = ReadinessCheck(
                check_name="core_services",
                status="fail",
                message=f"Missing services: {', '.join(missing_services)}",
                duration_ms=service_check_time,
                required=True
            )
            overall_ready = False
            
    except Exception as e:
        service_check_time = int((time.time() - service_check_start) * 1000)
        checks["core_services"] = ReadinessCheck(
            check_name="core_services",
            status="fail",
            message=f"Service check failed: {str(e)}",
            duration_ms=service_check_time,
            required=True
        )
        overall_ready = False
    
    # Calculate summary statistics
    total_check_time = int((time.time() - start_time) * 1000)
    passed_checks = sum(1 for c in checks.values() if c.status == "pass")
    total_checks = len(checks)
    
    # Create response
    response = ReadinessResponse(
        ready=overall_ready,
        checks=checks,
        total_check_time_ms=total_check_time,
        details={
            "checks_passed": passed_checks,
            "total_checks": total_checks,
            "success_rate": passed_checks / total_checks if total_checks > 0 else 0,
            "environment": config_service.get_section("application.environment", "unknown") if config_service else "unknown",
            "startup_time": app_state.get("startup_time").isoformat() if app_state.get("startup_time") else None
        }
    )
    
    # Set appropriate HTTP status
    if not overall_ready:
        raise HTTPException(
            status_code=503,
            detail=response.model_dump()
        )
    
    return response


@health_router.get(
    "/health/detailed",
    response_model=Dict[str, Any],
    summary="Detailed health information",
    description="Comprehensive health information for debugging and monitoring dashboards"
)
async def detailed_health_check(
    cache_service = Depends(get_cache_service),
    config_service: SimpleConfig = Depends(get_config_service),
    ai_provider_factory = Depends(get_ai_provider_factory)
) -> Dict[str, Any]:
    """
    Detailed health check with comprehensive system information.
    
    This endpoint provides extensive health and performance metrics
    for debugging and monitoring dashboards.
    """
    
    try:
        # Gather comprehensive system information
        start_time = time.time()
        
        # System metrics
        process = psutil.Process()
        system_info = {
            "memory": {
                "rss_mb": process.memory_info().rss / 1024 / 1024,
                "vms_mb": process.memory_info().vms / 1024 / 1024,
                "percent": process.memory_percent()
            },
            "cpu": {
                "percent": process.cpu_percent(),
                "num_threads": process.num_threads()
            },
            "process": {
                "pid": process.pid,
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
                "status": process.status()
            }
        }
        
        # Application state
        app_info = {
            "startup_time": app_state.get("startup_time").isoformat() if app_state.get("startup_time") else None,
            "uptime_seconds": int((datetime.utcnow() - app_state["startup_time"]).total_seconds()) if app_state.get("startup_time") else 0,
            "services_initialized": {
                "config_service": app_state.get("config_service") is not None,
                "comparison_service": app_state.get("comparison_service") is not None,
                "weight_processor": app_state.get("weight_processor") is not None,
                "cache_service": app_state.get("cache_service") is not None,
                "ai_provider_factory": app_state.get("ai_provider_factory") is not None,
                "metrics_service": app_state.get("metrics_service") is not None
            }
        }
        
        # Configuration info
        config_info = {}
        if config_service:
            config_info = {
                "version": config_service.get_section("application.version", "unknown"),
                "environment": config_service.get_section("application.environment", "unknown"),
                "log_level": config_service.get_section("logging.level", "unknown")
            }
        
        # Cache status
        cache_info = {"status": "not_available"}
        if cache_service:
            try:
                test_start = time.time()
                await cache_service.set("health_test", "ok", ttl=10)
                result = await cache_service.get("health_test")
                cache_response_time = int((time.time() - test_start) * 1000)
                
                cache_info = {
                    "status": "healthy" if result == "ok" else "degraded",
                    "response_time_ms": cache_response_time,
                    "type": type(cache_service).__name__
                }
            except Exception as e:
                cache_info = {
                    "status": "unhealthy",
                    "error": str(e),
                    "type": type(cache_service).__name__
                }
        
        # AI provider status
        ai_info = {"status": "not_available"}
        if ai_provider_factory:
            try:
                available_providers = await ai_provider_factory.get_available_providers()
                ai_info = {
                    "status": "healthy" if available_providers else "degraded",
                    "available_providers": list(available_providers.keys()) if available_providers else [],
                    "provider_count": len(available_providers) if available_providers else 0
                }
            except Exception as e:
                ai_info = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        # Calculate total response time
        total_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": "detailed_health_check",
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": total_time_ms,
            "system": system_info,
            "application": app_info,
            "configuration": config_info,
            "cache": cache_info,
            "ai_providers": ai_info
        }
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Detailed health check failed",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )