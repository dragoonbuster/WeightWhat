"""
FastAPI API Package for SizeComparator

This package contains the FastAPI application and all API endpoints for the SizeComparator service.
Provides RESTful API for weight comparisons with AI-powered visualizations.
"""

__version__ = "1.0.0"

from .main import create_app

__all__ = ["create_app"]