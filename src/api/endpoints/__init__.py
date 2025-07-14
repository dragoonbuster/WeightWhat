"""
API Endpoints Package for SizeComparator

This package contains all FastAPI endpoint routers for the SizeComparator service:
- comparison: Main weight comparison endpoints
- health: Health check endpoints for monitoring
- metrics: Prometheus metrics endpoints
"""

from .comparison import comparison_router
from .health import health_router
from .metrics import metrics_router

__all__ = ["comparison_router", "health_router", "metrics_router"]