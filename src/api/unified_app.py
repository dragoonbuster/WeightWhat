"""
Unified FastAPI Application for SizeComparator

This module provides a unified API application that integrates all comparison services
through intelligent routing based on service mode selection. It supports:

- Unified endpoint architecture with service mode selection
- Backward compatibility with legacy endpoints
- Static file serving for frontend assets
- Intelligent service routing using ComparisonServiceFactory
- Production-ready configuration and error handling

Service Modes:
- MVP: Basic fallback comparisons (always available)
- AI_ENHANCED: AI-powered with fallback (requires AI providers)
- VALIDATED: Full AI validation and quality checks
- FAST_VALIDATED: Optimized AI with <2s response time target
"""

import asyncio
import logging
import time
import os
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, HTTPException, Request, Response, Depends, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..core.environment import EnvironmentManager, EnvironmentType
from ..models.mvp import MVPComparisonRequest, MVPComparisonResponse, MVPErrorResponse
from ..services.shared.service_factory import (
    ComparisonServiceFactory, 
    ServiceRequirements, 
    PerformanceProfile,
    ServiceType
)
from ..services.shared.interfaces import BaseComparisonService

logger = logging.getLogger(__name__)


class ServiceMode(str, Enum):
    """Available service modes for unified API (maps to ServiceType)"""
    BASIC = "basic"                      # Basic fallback service (maps to ServiceType.BASIC)
    FAST_VALIDATION = "fast_validation"  # Fast AI validation (maps to ServiceType.FAST_VALIDATION)
    FULL_VALIDATION = "full_validation"  # Full AI validation (maps to ServiceType.FULL_VALIDATION)
    COMPREHENSIVE = "comprehensive"      # Comprehensive analysis (maps to ServiceType.COMPREHENSIVE)


class UnifiedSizeComparatorApp:
    """Unified SizeComparator application with intelligent service routing"""
    
    def __init__(self, env_manager: Optional[EnvironmentManager] = None):
        """Initialize unified application"""
        self.env_manager = env_manager or EnvironmentManager()
        self.service_factory = ComparisonServiceFactory(self.env_manager)
        self.app = None
        self._service_cache: Dict[ServiceMode, BaseComparisonService] = {}
        self._startup_time = None
        
        # Configuration
        self.config = self._load_app_config()
        
        # Metrics tracking
        self.metrics = {
            "requests_total": 0,
            "requests_by_mode": {mode.value: 0 for mode in ServiceMode},
            "response_times": [],
            "errors_total": 0
        }
        
    def _load_app_config(self) -> Dict[str, Any]:
        """Load application configuration"""
        return {
            "title": "SizeComparator Unified API",
            "description": "Intelligent weight comparison API with multiple service modes",
            "version": "1.0.0",
            "docs_url": "/docs" if self.env_manager.environment != EnvironmentType.PRODUCTION else None,
            "redoc_url": "/redoc" if self.env_manager.environment != EnvironmentType.PRODUCTION else None,
            "openapi_url": "/openapi.json" if self.env_manager.environment != EnvironmentType.PRODUCTION else None,
            
            # Service selection configuration
            "default_service_mode": ServiceMode.FAST_VALIDATION,
            "fallback_service_mode": ServiceMode.BASIC,
            "enable_legacy_endpoints": True,
            
            # Static file configuration
            "serve_frontend": True,
            "frontend_path": self._get_frontend_path(),
            
            # Performance settings
            "request_timeout_seconds": 30,
            "max_concurrent_requests": 100,
            "enable_caching": True,
            
            # CORS settings
            "cors_origins": ["*"] if self.env_manager.environment == EnvironmentType.DEVELOPMENT else [],
            "cors_methods": ["GET", "POST", "OPTIONS"],
            "cors_headers": ["*"]
        }
    
    def _get_frontend_path(self) -> Path:
        """Get path to frontend static files"""
        # Frontend is located relative to the project root
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # src/api/unified_app.py -> project root
        frontend_path = project_root / "frontend"
        
        if not frontend_path.exists():
            logger.warning(f"Frontend path not found: {frontend_path}")
            # Create empty directory to prevent errors
            frontend_path.mkdir(exist_ok=True)
        
        return frontend_path
    
    def create_app(self) -> FastAPI:
        """Create and configure unified FastAPI application"""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan management"""
            # Startup
            logger.info("Starting SizeComparator Unified API")
            self._startup_time = datetime.utcnow()
            
            try:
                # Initialize service factory
                await self._initialize_services()
                
                # Perform startup health check
                health_status = await self._perform_startup_health_check()
                if not health_status["healthy"]:
                    logger.error("Startup health check failed", extra=health_status)
                    raise RuntimeError("Application failed startup health checks")
                
                logger.info("SizeComparator Unified API started successfully")
                
                yield  # Application runs here
                
            finally:
                # Shutdown
                logger.info("Shutting down SizeComparator Unified API")
                await self._cleanup_services()
                logger.info("SizeComparator Unified API shutdown complete")
        
        # Create FastAPI app
        self.app = FastAPI(
            title=self.config["title"],
            description=self.config["description"],
            version=self.config["version"],
            lifespan=lifespan,
            docs_url=self.config["docs_url"],
            redoc_url=self.config["redoc_url"],
            openapi_url=self.config["openapi_url"]
        )
        
        # Setup middleware
        self._setup_middleware()
        
        # Setup routes
        self._setup_routes()
        
        # Setup error handlers
        self._setup_error_handlers()
        
        return self.app
    
    def _setup_middleware(self):
        """Setup middleware for the application"""
        
        # CORS middleware
        if self.config["cors_origins"]:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config["cors_origins"],
                allow_credentials=True,
                allow_methods=self.config["cors_methods"],
                allow_headers=self.config["cors_headers"],
            )
        
        # Request tracking middleware
        @self.app.middleware("http")
        async def track_requests(request: Request, call_next):
            start_time = time.time()
            self.metrics["requests_total"] += 1
            
            response = await call_next(request)
            
            process_time = time.time() - start_time
            self.metrics["response_times"].append(process_time * 1000)
            
            # Keep only recent response times for metrics
            if len(self.metrics["response_times"]) > 1000:
                self.metrics["response_times"] = self.metrics["response_times"][-1000:]
            
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Service-Mode"] = getattr(request.state, "service_mode", "unknown")
            
            return response
    
    def _setup_routes(self):
        """Setup API routes"""
        
        # Static file serving for frontend
        if self.config["serve_frontend"] and self.config["frontend_path"].exists():
            # Mount UI variations directory
            ui_path = self.config["frontend_path"] / "ui"
            if ui_path.exists():
                self.app.mount(
                    "/ui",
                    StaticFiles(directory=str(ui_path), html=True),
                    name="ui"
                )
            
            # Mount CSS directory
            css_path = self.config["frontend_path"] / "css"
            if css_path.exists():
                self.app.mount(
                    "/css",
                    StaticFiles(directory=str(css_path)),
                    name="css"
                )
            
            # Mount JS directory
            js_path = self.config["frontend_path"] / "js"
            if js_path.exists():
                self.app.mount(
                    "/js",
                    StaticFiles(directory=str(js_path)),
                    name="js"
                )
            
            # Mount simple_ui directory
            simple_ui_path = self.config["frontend_path"] / "simple_ui"
            if simple_ui_path.exists():
                self.app.mount(
                    "/simple_ui",
                    StaticFiles(directory=str(simple_ui_path), html=True),
                    name="simple_ui"
                )
            
            # Also mount at /static for backward compatibility
            self.app.mount(
                "/static", 
                StaticFiles(directory=str(self.config["frontend_path"])), 
                name="static"
            )
        
        # Root route - serve frontend index.html
        @self.app.get("/", response_class=HTMLResponse)
        async def serve_frontend():
            """Serve the main frontend application"""
            index_path = self.config["frontend_path"] / "index.html"
            if index_path.exists():
                return HTMLResponse(content=index_path.read_text(), status_code=200)
            else:
                return HTMLResponse(
                    content=self._get_default_homepage(),
                    status_code=200
                )
        
        # Health check endpoint
        @self.app.get("/health")
        async def health_check():
            """Comprehensive health check"""
            return await self._get_health_status()
        
        # Service status endpoint
        @self.app.get("/api/status")
        async def service_status():
            """Get detailed service status"""
            return {
                "service_factory": self.service_factory.get_service_health_status(),
                "app_metrics": self.metrics,
                "startup_time": self._startup_time.isoformat() if self._startup_time else None,
                "uptime_seconds": (datetime.utcnow() - self._startup_time).total_seconds() if self._startup_time else 0
            }
        
        # Main unified comparison endpoint
        @self.app.post("/api/compare", response_model=MVPComparisonResponse)
        async def unified_compare(
            request_data: MVPComparisonRequest,
            request: Request,
            service_mode: Optional[ServiceMode] = Query(None, description="Override service mode"),
            x_service_mode: Optional[ServiceMode] = Header(None, alias="X-Service-Mode"),
            x_performance_profile: Optional[PerformanceProfile] = Header(None, alias="X-Performance-Profile"),
            timeout_ms: Optional[int] = Query(None, description="Request timeout in milliseconds")
        ):
            """
            Unified weight comparison endpoint with intelligent service routing
            
            Service mode selection priority:
            1. Query parameter: ?service_mode=validated
            2. Header: X-Service-Mode: fast_validated  
            3. Environment-based auto-selection
            4. Default configuration
            """
            
            # Determine service mode
            selected_mode = await self._determine_service_mode(
                query_mode=service_mode,
                header_mode=x_service_mode,
                performance_profile=x_performance_profile,
                request_data=request_data,
                timeout_ms=timeout_ms
            )
            
            # Set request state for tracking
            request.state.service_mode = selected_mode.value
            
            # Track metrics
            self.metrics["requests_by_mode"][selected_mode.value] += 1
            
            logger.info(
                f"Processing request with service mode: {selected_mode.value}",
                extra={
                    "service_mode": selected_mode.value,
                    "weight_input": request_data.weight_input,
                    "provider": request_data.provider
                }
            )
            
            try:
                # Get appropriate service
                service = await self._get_service_for_mode(selected_mode)
                
                # Process request
                result = await service.create_comparison(request_data)
                
                return result
                
            except Exception as e:
                self.metrics["errors_total"] += 1
                logger.error(f"Error in unified compare: {e}", exc_info=True)
                
                # Try fallback mode if not already using BASIC
                if selected_mode != ServiceMode.BASIC:
                    logger.warning(f"Falling back to BASIC mode due to error: {e}")
                    try:
                        fallback_service = await self._get_service_for_mode(ServiceMode.BASIC)
                        result = await fallback_service.create_comparison(request_data)
                        result.cached = False  # Mark as fallback
                        return result
                    except Exception as fallback_error:
                        logger.error(f"Fallback also failed: {fallback_error}")
                
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Service temporarily unavailable",
                        "error_code": "SERVICE_ERROR",
                        "service_mode": selected_mode.value,
                        "fallback_attempted": selected_mode != ServiceMode.BASIC
                    }
                )
        
        # Legacy endpoint support
        if self.config["enable_legacy_endpoints"]:
            self._setup_legacy_endpoints()
        
        # Service-specific demo pages
        self._setup_demo_endpoints()
    
    def _setup_legacy_endpoints(self):
        """Setup backward compatibility endpoints"""
        
        @self.app.post("/api/compare/single", response_model=MVPComparisonResponse)
        async def legacy_single_compare(request_data: MVPComparisonRequest):
            """Legacy endpoint: basic comparison (maps to BASIC mode)"""
            service = await self._get_service_for_mode(ServiceMode.BASIC)
            return await service.create_comparison(request_data)
        
        @self.app.post("/api/compare/validated", response_model=MVPComparisonResponse)
        async def legacy_validated_compare(request_data: MVPComparisonRequest):
            """Legacy endpoint: validated comparison (maps to FULL_VALIDATION mode)"""
            service = await self._get_service_for_mode(ServiceMode.FULL_VALIDATION)
            return await service.create_comparison(request_data)
        
        @self.app.post("/api/compare/fast", response_model=MVPComparisonResponse)
        async def legacy_fast_compare(request_data: MVPComparisonRequest):
            """Legacy endpoint: fast comparison (maps to FAST_VALIDATION mode)"""
            service = await self._get_service_for_mode(ServiceMode.FAST_VALIDATION)
            return await service.create_comparison(request_data)
    
    def _setup_demo_endpoints(self):
        """Setup demo endpoints for different service modes"""
        
        @self.app.get("/demo/{mode}", response_class=HTMLResponse)
        async def serve_demo_page(mode: ServiceMode):
            """Serve mode-specific demo page"""
            return HTMLResponse(
                content=self._generate_demo_page(mode),
                status_code=200
            )
        
        @self.app.get("/api/demo")
        async def demo_data():
            """Demo data and examples"""
            return {
                "service_modes": [
                    {
                        "mode": "basic",
                        "name": "Basic Mode", 
                        "description": "Basic fallback comparisons (always available)",
                        "endpoint": "/api/compare?service_mode=basic"
                    },
                    {
                        "mode": "fast_validation",
                        "name": "Fast Validation",
                        "description": "AI-powered with intelligent fallback and fast response",
                        "endpoint": "/api/compare?service_mode=fast_validation"
                    },
                    {
                        "mode": "full_validation", 
                        "name": "Full Validation",
                        "description": "Full AI validation and quality checks",
                        "endpoint": "/api/compare?service_mode=full_validation"
                    },
                    {
                        "mode": "comprehensive",
                        "name": "Comprehensive",
                        "description": "Most comprehensive AI analysis available",
                        "endpoint": "/api/compare?service_mode=comprehensive"
                    }
                ],
                "examples": [
                    {"weight_input": "5 kg", "description": "Medium household object"},
                    {"weight_input": "10 pounds", "description": "Small appliance weight"},
                    {"weight_input": "100 grams", "description": "Small everyday item"},
                    {"weight_input": "2.5 tons", "description": "Vehicle weight"},
                    {"weight_input": "1 ounce", "description": "Very light object"}
                ],
                "performance_profiles": [
                    {"profile": "speed_optimized", "description": "Prioritize fast response"},
                    {"profile": "balanced", "description": "Balance speed and accuracy"},
                    {"profile": "accuracy_optimized", "description": "Prioritize accuracy"}
                ]
            }
    
    def _setup_error_handlers(self):
        """Setup global error handlers"""
        
        @self.app.exception_handler(404)
        async def not_found_handler(request: Request, exc):
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Not found",
                    "error_code": "NOT_FOUND",
                    "path": str(request.url.path),
                    "available_endpoints": [
                        "/api/compare",
                        "/api/status", 
                        "/health",
                        "/demo/{mode}"
                    ]
                }
            )
        
        @self.app.exception_handler(500)
        async def internal_error_handler(request: Request, exc):
            self.metrics["errors_total"] += 1
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "error_code": "INTERNAL_ERROR",
                    "service_mode": getattr(request.state, "service_mode", "unknown")
                }
            )
    
    async def _determine_service_mode(
        self,
        query_mode: Optional[ServiceMode],
        header_mode: Optional[ServiceMode], 
        performance_profile: Optional[PerformanceProfile],
        request_data: MVPComparisonRequest,
        timeout_ms: Optional[int]
    ) -> ServiceMode:
        """Determine optimal service mode based on various inputs"""
        
        # Priority 1: Explicit query parameter
        if query_mode:
            return query_mode
        
        # Priority 2: Header specification
        if header_mode:
            return header_mode
        
        # Priority 3: Intelligent selection based on request characteristics
        if performance_profile or timeout_ms:
            # Use service factory for intelligent selection
            requirements = ServiceRequirements(
                weight_kg=5.0,  # Default weight for selection
                timeout_ms=timeout_ms or 3000,
                performance_profile=performance_profile or PerformanceProfile.BALANCED
            )
            
            optimal_service = self.service_factory.get_optimal_service(requirements)
            
            # Map service types to modes
            service_type_to_mode = {
                ServiceType.BASIC: ServiceMode.BASIC,
                ServiceType.FAST_VALIDATION: ServiceMode.FAST_VALIDATION,
                ServiceType.FULL_VALIDATION: ServiceMode.FULL_VALIDATION,
                ServiceType.COMPREHENSIVE: ServiceMode.COMPREHENSIVE
            }
            
            # Determine service type from factory selection
            for service_type, capabilities in self.service_factory.service_capabilities.items():
                if type(optimal_service).__name__.lower() in capabilities.service_type.value:
                    return service_type_to_mode.get(service_type, ServiceMode.FAST_VALIDATION)
        
        # Priority 4: Application default (environment-aware)
        return self.config["default_service_mode"]
    
    async def _get_service_for_mode(self, mode: ServiceMode) -> BaseComparisonService:
        """Get service instance for specified mode"""
        
        # Check cache first
        if mode in self._service_cache:
            return self._service_cache[mode]
        
        # Create service based on mode - map to ServiceType
        mode_to_service_type = {
            ServiceMode.BASIC: ServiceType.BASIC,
            ServiceMode.FAST_VALIDATION: ServiceType.FAST_VALIDATION,
            ServiceMode.FULL_VALIDATION: ServiceType.FULL_VALIDATION,
            ServiceMode.COMPREHENSIVE: ServiceType.COMPREHENSIVE
        }
        
        target_service_type = mode_to_service_type.get(mode, ServiceType.BASIC)
        
        # Create service based on target type
        if target_service_type == ServiceType.BASIC:
            service = self.service_factory.create_basic_service()
        elif target_service_type == ServiceType.FAST_VALIDATION:
            service = self.service_factory.create_fast_validation_service()
        elif target_service_type == ServiceType.FULL_VALIDATION:
            service = self.service_factory.create_full_validation_service()
        elif target_service_type == ServiceType.COMPREHENSIVE:
            service = self.service_factory.create_comprehensive_service()
        else:
            logger.warning(f"Unknown service type {target_service_type}, using basic")
            service = self.service_factory.create_basic_service()
        
        # Cache the service
        self._service_cache[mode] = service
        
        return service
    
    async def _initialize_services(self):
        """Initialize all services"""
        logger.info("Initializing unified application services")
        
        # Clear service cache
        self._service_cache.clear()
        
        # Pre-warm service factory
        self.service_factory.clear_availability_cache()
        
        logger.info("Services initialized successfully")
    
    async def _cleanup_services(self):
        """Cleanup services on shutdown"""
        logger.info("Cleaning up unified application services")
        
        # Clear service cache
        self._service_cache.clear()
        
        logger.info("Services cleaned up successfully")
    
    async def _perform_startup_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive startup health check"""
        checks = {}
        
        # Check service factory
        try:
            factory_status = self.service_factory.get_service_health_status()
            checks["service_factory"] = factory_status["factory_status"] == "healthy"
        except Exception as e:
            logger.warning(f"Service factory health check failed: {e}")
            checks["service_factory"] = False
        
        # Check each service mode
        for mode in ServiceMode:
            try:
                service = await self._get_service_for_mode(mode)
                checks[f"service_{mode.value}"] = service is not None
            except Exception as e:
                logger.warning(f"Service mode {mode.value} health check failed: {e}")
                checks[f"service_{mode.value}"] = False
        
        # Check frontend
        checks["frontend"] = self.config["frontend_path"].exists()
        
        overall_healthy = checks.get("service_factory", False) and checks.get("service_basic", False)
        
        return {
            "healthy": overall_healthy,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            "status": "healthy",
            "service_factory": self.service_factory.get_service_health_status(),
            "metrics": self.metrics,
            "uptime_seconds": (datetime.utcnow() - self._startup_time).total_seconds() if self._startup_time else 0,
            "version": self.config["version"]
        }
    
    def _get_default_homepage(self) -> str:
        """Generate default homepage when frontend is not available"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SizeComparator Unified API</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .status {{ background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .endpoint {{ background: #f5f5f5; padding: 10px; margin: 5px 0; border-radius: 3px; }}
                code {{ background: #eee; padding: 2px 4px; border-radius: 2px; }}
            </style>
        </head>
        <body>
            <h1>SizeComparator Unified API</h1>
            <p>Intelligent weight comparison API with multiple service modes</p>
            
            <div class="status">
                <h2>Available Endpoints</h2>
                <div class="endpoint"><code>POST /api/compare</code> - Unified comparison with service mode selection</div>
                <div class="endpoint"><code>GET /api/status</code> - Service status and metrics</div>
                <div class="endpoint"><code>GET /health</code> - Health check</div>
                <div class="endpoint"><code>GET /demo/{{mode}}</code> - Mode-specific demo pages</div>
                <div class="endpoint"><code>GET {self.config["docs_url"] or "/docs"}</code> - API Documentation (if enabled)</div>
            </div>
            
            <div class="status">
                <h2>Service Modes</h2>
                <div class="endpoint"><strong>mvp</strong> - Basic fallback (always available)</div>
                <div class="endpoint"><strong>ai_enhanced</strong> - AI-powered with fallback</div>
                <div class="endpoint"><strong>validated</strong> - Full AI validation</div>
                <div class="endpoint"><strong>fast_validated</strong> - Fast AI (&lt;2s target)</div>
            </div>
            
            <div class="status">
                <h2>Example Usage</h2>
                <div class="endpoint">
                    <code>POST /api/compare?service_mode=validated</code><br>
                    <code>{{"weight_input": "5 kg", "style": "creative"}}</code>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_demo_page(self, mode: ServiceMode) -> str:
        """Generate demo page for specific service mode"""
        mode_info = {
            ServiceMode.BASIC: {
                "title": "Basic Mode Demo",
                "description": "Basic weight comparisons with fallback data",
                "color": "#6c757d"
            },
            ServiceMode.FAST_VALIDATION: {
                "title": "Fast Validation Demo", 
                "description": "AI-powered comparisons with fast response",
                "color": "#007bff"
            },
            ServiceMode.FULL_VALIDATION: {
                "title": "Full Validation Demo",
                "description": "Full AI validation and quality checks",
                "color": "#28a745"
            },
            ServiceMode.COMPREHENSIVE: {
                "title": "Comprehensive Demo",
                "description": "Most comprehensive AI analysis available",
                "color": "#ffc107"
            }
        }
        
        info = mode_info.get(mode, mode_info[ServiceMode.BASIC])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{info["title"]} - SizeComparator</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px;
                    background: linear-gradient(135deg, {info["color"]}22 0%, {info["color"]}11 100%);
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                h1 {{ color: {info["color"]}; text-align: center; }}
                .form-group {{ margin: 15px 0; }}
                label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                input, select, button {{
                    width: 100%;
                    padding: 10px;
                    margin: 5px 0;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    box-sizing: border-box;
                }}
                button {{
                    background: {info["color"]};
                    color: white;
                    border: none;
                    cursor: pointer;
                    font-weight: bold;
                }}
                button:hover {{ opacity: 0.9; }}
                #result {{
                    margin-top: 20px;
                    padding: 15px;
                    border-radius: 5px;
                    display: none;
                }}
                .success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
                .error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{info["title"]}</h1>
                <p style="text-align: center; color: #666;">{info["description"]}</p>
                
                <div class="form-group">
                    <label for="weight">Weight Input:</label>
                    <input type="text" id="weight" placeholder="e.g., 5 kg, 10 pounds, 100 grams" />
                </div>
                
                <div class="form-group">
                    <label for="style">Comparison Style:</label>
                    <select id="style">
                        <option value="default">Default</option>
                        <option value="creative">Creative</option>
                        <option value="technical">Technical</option>
                    </select>
                </div>
                
                <button onclick="compareWeight()">Compare Weight ({mode.value} mode)</button>
                
                <div id="result"></div>
            </div>

            <script>
                async function compareWeight() {{
                    const weight = document.getElementById('weight').value.trim();
                    const style = document.getElementById('style').value;
                    const resultDiv = document.getElementById('result');
                    
                    if (!weight) {{
                        alert('Please enter a weight!');
                        return;
                    }}
                    
                    resultDiv.style.display = 'block';
                    resultDiv.className = '';
                    resultDiv.innerHTML = 'Processing...';
                    
                    try {{
                        const response = await fetch('/api/compare?service_mode={mode.value}', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ weight_input: weight, style: style }})
                        }});
                        
                        const data = await response.json();
                        
                        if (response.ok) {{
                            resultDiv.className = 'success';
                            resultDiv.innerHTML = `
                                <h3>Comparison Result:</h3>
                                <p><strong>${{data.comparison_text}}</strong></p>
                                <p><small>Response time: ${{data.response_time_ms}}ms | Provider: ${{data.provider_used}}</small></p>
                            `;
                        }} else {{
                            resultDiv.className = 'error';
                            resultDiv.innerHTML = `<h3>Error:</h3><p>${{data.error || JSON.stringify(data)}}</p>`;
                        }}
                    }} catch (error) {{
                        resultDiv.className = 'error';
                        resultDiv.innerHTML = `<h3>Network Error:</h3><p>${{error.message}}</p>`;
                    }}
                }}
                
                document.getElementById('weight').addEventListener('keypress', function(e) {{
                    if (e.key === 'Enter') compareWeight();
                }});
            </script>
        </body>
        </html>
        """


# Factory function for creating unified app
def create_unified_app(env_manager: Optional[EnvironmentManager] = None) -> FastAPI:
    """Create unified SizeComparator application"""
    app_instance = UnifiedSizeComparatorApp(env_manager)
    return app_instance.create_app()


# Direct execution support
if __name__ == "__main__":
    import uvicorn
    
    # Create environment manager
    env_manager = EnvironmentManager()
    
    # Create application
    app = create_unified_app(env_manager)
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )