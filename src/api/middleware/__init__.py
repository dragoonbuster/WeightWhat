"""
Middleware Package for SizeComparator FastAPI Application

This package contains all middleware components for request/response processing:
- request_id: Request ID tracking for distributed tracing
- cors: CORS configuration for frontend integration
- error_handler: Global error handling and formatting
"""

from .request_id import RequestIDMiddleware
from .cors import setup_cors_middleware
from .error_handler import ErrorHandlingMiddleware

__all__ = [
    "RequestIDMiddleware",
    "setup_cors_middleware", 
    "ErrorHandlingMiddleware"
]