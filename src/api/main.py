"""
FastAPI Application Setup for SizeComparator

This module creates and configures the FastAPI application with:
- Dependency injection
- Middleware setup
- Error handling
- Lifespan management
- Route configuration
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..core.simple_config import get_config, SimpleConfig
from ..models.errors import ErrorCategory, ErrorSeverity
from ..services.comparison.comparison_service import ComparisonService, create_comparison_service
from ..services.weight_processor import WeightProcessor
from ..providers.factory import ProviderFactory
from ..services.cache.redis_cache import RedisCache
from ..services.cache.memory_cache import MemoryCache

# Import middleware
from .middleware.request_id import RequestIDMiddleware
from .middleware.cors import setup_cors_middleware
from .middleware.error_handler import ErrorHandlingMiddleware

logger = logging.getLogger(__name__)

# Global application state
app_state = {
    "startup_time": None,
    "config_service": None,
    "comparison_service": None,
    "weight_processor": None,
    "ai_provider_factory": None,
    "cache_service": None,
    "metrics_service": None,
    "rate_limiting_service": None,
}


class MetricsService:
    """Simple metrics service for tracking application metrics"""
    
    def __init__(self):
        self.counters = {}
        self.histograms = {}
        self.gauges = {}
        
    def increment(self, metric: str, tags: Dict[str, str] = None):
        """Increment counter metric"""
        key = f"{metric}:{':'.join(f'{k}={v}' for k, v in (tags or {}).items())}"
        self.counters[key] = self.counters.get(key, 0) + 1
        
    def histogram(self, metric: str, value: float, tags: Dict[str, str] = None):
        """Record histogram metric"""
        key = f"{metric}:{':'.join(f'{k}={v}' for k, v in (tags or {}).items())}"
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
        
    def set_gauge(self, metric: str, value: float, tags: Dict[str, str] = None):
        """Set gauge metric"""
        key = f"{metric}:{':'.join(f'{k}={v}' for k, v in (tags or {}).items())}"
        self.gauges[key] = value
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        return {
            "counters": self.counters,
            "histograms": self.histograms,
            "gauges": self.gauges
        }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting SizeComparator API server")
    app_state["startup_time"] = datetime.utcnow()
    
    try:
        # Initialize services
        await initialize_services()
        
        # Perform startup health check
        health_status = await perform_startup_health_check()
        if not health_status["healthy"]:
            logger.error("Startup health check failed", extra=health_status)
            raise RuntimeError("Application failed startup health checks")
        
        logger.info("SizeComparator API server started successfully")
        
        yield  # Application runs here
        
    finally:
        # Shutdown
        logger.info("Shutting down SizeComparator API server")
        await cleanup_services()
        logger.info("SizeComparator API server shutdown complete")


async def initialize_services():
    """Initialize all application services"""
    # Initialize configuration
    config_loader = get_config()
    app_state["config_service"] = config_loader
    
    # Initialize metrics
    metrics_service = MetricsService()
    app_state["metrics_service"] = metrics_service
    
    # Initialize cache service
    cache_config = config_loader.get_cache_config()
    if cache_config.get("provider") == "redis":
        cache_service = RedisCache(
            host=cache_config.get("host", "localhost"),
            port=cache_config.get("port", 6379),
            db=cache_config.get("db", 0),
            password=cache_config.get("password")
        )
    else:
        cache_service = MemoryCache(
            max_size=cache_config.get("max_size", 1000),
            default_ttl=cache_config.get("default_ttl", 3600)
        )
    
    await cache_service.initialize()
    app_state["cache_service"] = cache_service
    
    # Initialize weight processor
    weight_processor = WeightProcessor()
    app_state["weight_processor"] = weight_processor
    
    # Initialize AI provider factory
    ai_provider_factory = ProviderFactory()
    app_state["ai_provider_factory"] = ai_provider_factory
    
    # Initialize comparison service
    comparison_service = create_comparison_service(
        weight_processor=weight_processor,
        provider_factory=ai_provider_factory,
        cache_service=cache_service,
        config=config_loader,
        metrics=metrics_service,
        logger=logger
    )
    app_state["comparison_service"] = comparison_service


async def perform_startup_health_check() -> Dict[str, Any]:
    """Perform comprehensive startup health check"""
    checks = {}
    
    # Check configuration
    checks["configuration"] = app_state["config_service"] is not None
    
    # Check cache
    try:
        if app_state["cache_service"]:
            await app_state["cache_service"].set("health_check", "ok", ttl=10)
            result = await app_state["cache_service"].get("health_check")
            checks["cache"] = result == "ok"
        else:
            checks["cache"] = False
    except Exception as e:
        logger.warning(f"Cache health check failed: {e}")
        checks["cache"] = False
    
    # Check AI providers
    try:
        if app_state["ai_provider_factory"]:
            providers = app_state["ai_provider_factory"].registry.list_providers()
            checks["ai_providers"] = len(providers) > 0
        else:
            checks["ai_providers"] = False
    except Exception as e:
        logger.warning(f"AI provider health check failed: {e}")
        checks["ai_providers"] = False
    
    overall_healthy = all(checks.values())
    
    return {
        "healthy": overall_healthy,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


async def cleanup_services():
    """Cleanup application services"""
    try:
        # Cleanup cache
        if app_state["cache_service"]:
            await app_state["cache_service"].cleanup()
        
        # Cleanup AI providers
        if app_state["ai_provider_factory"]:
            await app_state["ai_provider_factory"].shutdown_all()
            
    except Exception as e:
        logger.error(f"Error during service cleanup: {e}")


def create_app(config_loader: Optional[SimpleConfig] = None) -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Use provided config or create new one
    if config_loader is None:
        config_loader = get_config()
    
    app_config = config_loader.get_all()
    api_config = config_loader.get_api_config()
    
    # Create FastAPI app
    app = FastAPI(
        title=app_config.get("name", "SizeComparator API"),
        version=app_config.get("version", "1.0.0"),
        description="Weight comparison API with AI-powered visualizations",
        lifespan=lifespan,
        docs_url="/docs" if app_config.get("environment") != "production" else None,
        redoc_url="/redoc" if app_config.get("environment") != "production" else None,
        openapi_url="/openapi.json" if app_config.get("environment") != "production" else None
    )
    
    # Setup middleware (order matters!)
    setup_middleware(app, config_loader)
    
    # Setup dependency injection
    setup_dependencies(app)
    
    # Setup routes
    setup_routes(app)
    
    # Setup error handlers
    setup_error_handlers(app)
    
    return app


def setup_middleware(app: FastAPI, config_loader: SimpleConfig):
    """Setup middleware in correct order"""
    
    # 1. CORS middleware (first to handle preflight requests)
    setup_cors_middleware(app, config_loader)
    
    # 2. Request ID middleware (early to ensure all logs have request ID)
    app.add_middleware(RequestIDMiddleware)
    
    # 3. Error handling middleware (last to catch all errors)
    app.add_middleware(
        ErrorHandlingMiddleware,
        config_loader=config_loader
    )


def setup_dependencies(app: FastAPI):
    """Setup dependency injection"""
    
    # Store app state for dependency injection
    app.state.app_state = app_state


def setup_routes(app: FastAPI):
    """Setup API routes"""
    
    # Import routers here to avoid circular imports
    from .endpoints.comparison import comparison_router
    from .endpoints.health import health_router
    from .endpoints.metrics import metrics_router
    
    # Health endpoints (no prefix)
    app.include_router(health_router, prefix="", tags=["health"])
    
    # Metrics endpoint (no prefix)
    app.include_router(metrics_router, prefix="", tags=["metrics"])
    
    # Main API endpoints
    app.include_router(comparison_router, prefix="/api/v1", tags=["comparison"])


def setup_error_handlers(app: FastAPI):
    """Setup global error handlers"""
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Handle 404 errors"""
        return JSONResponse(
            status_code=404,
            content={
                "error_code": "NOT_FOUND",
                "error_category": ErrorCategory.CLIENT_ERROR.value,
                "message": "The requested resource was not found",
                "request_id": getattr(request.state, "request_id", "unknown"),
                "timestamp": datetime.utcnow().isoformat(),
                "severity": ErrorSeverity.INFO.value
            }
        )
    
    @app.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc):
        """Handle 405 errors"""
        return JSONResponse(
            status_code=405,
            content={
                "error_code": "METHOD_NOT_ALLOWED",
                "error_category": ErrorCategory.CLIENT_ERROR.value,
                "message": f"Method {request.method} not allowed for this endpoint",
                "request_id": getattr(request.state, "request_id", "unknown"),
                "timestamp": datetime.utcnow().isoformat(),
                "severity": ErrorSeverity.INFO.value
            }
        )


# Dependency injection functions
def get_app_state():
    """Get application state (for dependency injection)"""
    return app_state


def get_config_service():
    """Get configuration service (for dependency injection)"""
    return app_state["config_service"]


def get_comparison_service():
    """Get comparison service (for dependency injection)"""
    return app_state["comparison_service"]


def get_weight_processor():
    """Get weight processor service (for dependency injection)"""
    return app_state["weight_processor"]


def get_cache_service():
    """Get cache service (for dependency injection)"""
    return app_state["cache_service"]


def get_metrics_service():
    """Get metrics service (for dependency injection)"""
    return app_state["metrics_service"]


def get_ai_provider_factory():
    """Get AI provider factory (for dependency injection)"""
    return app_state["ai_provider_factory"]


# Application startup for direct execution
if __name__ == "__main__":
    import uvicorn
    
    # Load configuration
    config_loader = get_config()
    
    # Create application
    app = create_app(config_loader)
    
    # Get server configuration
    server_config = config_loader.get_api_config()
    
    # Run server
    uvicorn.run(
        app,
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8000),
        workers=server_config.get("workers", 1),
        log_config=None,  # Use our custom logging
        access_log=False  # Handled by middleware
    )