"""
Simplified API for SizeComparator.
Uses the three core services for all functionality.
"""

import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..core_services import WeightProcessor, ComparisonEngine, CacheManager

logger = logging.getLogger(__name__)

# Request/Response models
class ComparisonRequest(BaseModel):
    weight_input: str = Field(..., min_length=1, max_length=100)
    style: str = Field(default="default", pattern="^(default|creative|technical)$")

class ComparisonResponse(BaseModel):
    comparison_text: str
    original_input: str
    weight_display: str
    processing_time_ms: int
    used_ai: bool = False

class CounterResponse(BaseModel):
    count: int
    timestamp: float

# Global instances
weight_processor = WeightProcessor()
comparison_engine = ComparisonEngine()
cache_manager = CacheManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Starting SizeComparator API")
    yield
    logger.info("Shutting down SizeComparator API")

# Create FastAPI app
app = FastAPI(
    title="SizeComparator API",
    description="Simple weight comparison API",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    # Mount directories
    for subdir in ["css", "js", "ui"]:
        path = frontend_path / subdir
        if path.exists():
            app.mount(f"/{subdir}", StaticFiles(directory=str(path)), name=subdir)
    
    # Mount root static files
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve frontend."""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>SizeComparator API</h1><p>Frontend not found</p>")

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "sizecomparator"}

@app.post("/api/compare", response_model=ComparisonResponse)
async def compare_weight(request: ComparisonRequest):
    """Generate weight comparison."""
    start_time = time.time()
    
    # Process weight
    weight_data = weight_processor.process(request.weight_input)
    if not weight_data:
        raise HTTPException(status_code=400, detail="Invalid weight format")
    
    # Check cache
    cache_key = cache_manager.build_cache_key(weight_data['weight_kg'], request.style)
    cached = cache_manager.get(cache_key)
    
    if cached:
        comparison_text = cached
        used_ai = False
    else:
        # Generate comparison
        category = weight_processor.get_weight_category(weight_data['weight_kg'])
        comparison_text = comparison_engine.generate_comparison(
            weight_data['weight_kg'],
            category,
            request.style
        )
        used_ai = True
        
        # Cache result
        cache_manager.set(cache_key, comparison_text, ttl=3600)
    
    # Increment counter
    cache_manager.increment_counter()
    
    # Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    return ComparisonResponse(
        comparison_text=comparison_text,
        original_input=request.weight_input,
        weight_display=weight_data['display'],
        processing_time_ms=processing_time_ms,
        used_ai=used_ai
    )

@app.get("/api/counter", response_model=CounterResponse)
async def get_counter():
    """Get global counter."""
    return CounterResponse(
        count=cache_manager.get_counter(),
        timestamp=time.time()
    )

# Legacy endpoint support
@app.post("/api/compare/single")
async def legacy_single(request: ComparisonRequest):
    """Legacy endpoint - redirects to main compare."""
    return await compare_weight(request)

@app.post("/api/compare/fast")
async def legacy_fast(request: ComparisonRequest):
    """Legacy endpoint - redirects to main compare."""
    return await compare_weight(request)

@app.post("/api/compare/validated")
async def legacy_validated(request: ComparisonRequest):
    """Legacy endpoint - redirects to main compare."""
    return await compare_weight(request)

# Error handlers
@app.exception_handler(400)
async def bad_request_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc.detail) if hasattr(exc, 'detail') else "Bad request"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )