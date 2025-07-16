"""
CORS Middleware Configuration for Frontend Integration

This module configures Cross-Origin Resource Sharing (CORS) for the FastAPI application:
- Configurable origins based on environment
- Support for credentials and cookies
- Custom headers for API communication
- Preflight request handling
"""

import logging
from typing import List, Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...core.simple_config import SimpleConfig

logger = logging.getLogger(__name__)


def setup_cors_middleware(app: FastAPI, config_loader: SimpleConfig):
    """
    Configure CORS middleware using CONFIG_SYSTEM_SPEC settings.
    
    This function sets up CORS based on the current environment and
    configuration settings, providing secure defaults while allowing
    necessary frontend integration.
    """
    
    # Get CORS configuration
    cors_config = config_loader.get_section("api.cors", {})
    environment = config_loader.get_section("application.environment", "development")
    
    # Determine allowed origins based on environment
    allowed_origins = _get_allowed_origins(cors_config, environment)
    
    # Determine allowed methods
    allowed_methods = cors_config.get("allow_methods", [
        "GET",
        "POST", 
        "PUT",
        "DELETE",
        "OPTIONS",
        "HEAD",
        "PATCH"
    ])
    
    # Determine allowed headers
    allowed_headers = cors_config.get("allow_headers", [
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "X-Correlation-ID",
        "X-API-Key",
        "X-Client-Version",
        "Cache-Control"
    ])
    
    # Determine exposed headers (headers that frontend can access)
    exposed_headers = cors_config.get("expose_headers", [
        "X-Request-ID",
        "X-Processing-Time",
        "X-Processing-Time-Ms", 
        "X-Response-Timestamp",
        "X-Rate-Limit-Remaining",
        "X-Rate-Limit-Reset",
        "Cache-Control",
        "ETag"
    ])
    
    # Determine credential settings
    allow_credentials = cors_config.get("allow_credentials", _should_allow_credentials(environment))
    
    # Maximum age for preflight cache
    max_age = cors_config.get("max_age", 86400)  # 24 hours
    
    # Log CORS configuration for debugging
    logger.info(
        "Configuring CORS middleware",
        extra={
            "environment": environment,
            "allowed_origins": allowed_origins if isinstance(allowed_origins, list) else "all",
            "allow_credentials": allow_credentials,
            "allowed_methods_count": len(allowed_methods),
            "allowed_headers_count": len(allowed_headers)
        }
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
        expose_headers=exposed_headers,
        max_age=max_age
    )
    
    logger.info("CORS middleware configured successfully")


def _get_allowed_origins(cors_config: dict, environment: str) -> Union[List[str], List[str]]:
    """Get allowed origins based on environment and configuration"""
    
    # Check for explicit origins in config
    if "allow_origins" in cors_config:
        origins = cors_config["allow_origins"]
        if isinstance(origins, str):
            if origins == "*":
                return ["*"]
            else:
                return [origins]
        elif isinstance(origins, list):
            return origins
    
    # Environment-based defaults
    if environment == "production":
        # Production: only allow specific domains
        return _get_production_origins(cors_config)
    elif environment == "staging":
        # Staging: allow staging and development domains
        return _get_staging_origins(cors_config)
    elif environment == "development":
        # Development: allow common development URLs
        return _get_development_origins(cors_config)
    else:
        # Unknown environment: restrictive defaults
        logger.warning(f"Unknown environment '{environment}', using restrictive CORS policy")
        return ["http://localhost:3000"]


def _get_production_origins(cors_config: dict) -> List[str]:
    """Get production-safe CORS origins"""
    
    # Get from config or use secure defaults
    production_origins = cors_config.get("production_origins", [])
    
    if not production_origins:
        # If no production origins specified, log warning and use restrictive policy
        logger.warning("No production CORS origins specified, using restrictive policy")
        return []
    
    # Validate production origins (must be HTTPS)
    validated_origins = []
    for origin in production_origins:
        if origin.startswith("https://") or origin.startswith("http://localhost"):
            validated_origins.append(origin)
        else:
            logger.warning(f"Rejecting non-HTTPS production origin: {origin}")
    
    return validated_origins


def _get_staging_origins(cors_config: dict) -> List[str]:
    """Get staging environment CORS origins"""
    
    staging_origins = cors_config.get("staging_origins", [
        "https://staging.sizecomparator.com",
        "https://staging-api.sizecomparator.com",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080"
    ])
    
    # Add development origins for testing
    staging_origins.extend(_get_development_origins(cors_config))
    
    return list(set(staging_origins))  # Remove duplicates


def _get_development_origins(cors_config: dict) -> List[str]:
    """Get development environment CORS origins"""
    
    return cors_config.get("development_origins", [
        "http://localhost:3000",   # React dev server
        "http://localhost:3001",   # Alternative React port
        "http://localhost:5173",   # Vite dev server
        "http://localhost:8080",   # Vue dev server
        "http://localhost:4200",   # Angular dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:3000",
        # Allow local network access for mobile testing
        "http://192.168.1.100:3000",
        "http://10.0.0.100:3000"
    ])


def _should_allow_credentials(environment: str) -> bool:
    """Determine if credentials should be allowed based on environment"""
    
    # In production, only allow credentials if origins are explicitly set
    # In development, allow for easier testing
    return environment in ["development", "staging"]


def validate_cors_configuration(config_loader: SimpleConfig) -> dict:
    """
    Validate CORS configuration and return validation results.
    
    This function can be called during startup to ensure CORS
    configuration is valid and secure.
    """
    
    results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "configuration": {}
    }
    
    cors_config = config_loader.get_section("api.cors", {})
    environment = config_loader.get_section("application.environment", "development")
    
    # Check for wildcard origins in production
    allowed_origins = _get_allowed_origins(cors_config, environment)
    if environment == "production" and "*" in allowed_origins:
        results["errors"].append("Wildcard origins (*) not allowed in production")
        results["valid"] = False
    
    # Check for HTTP origins in production
    if environment == "production":
        for origin in allowed_origins:
            if origin.startswith("http://") and not origin.startswith("http://localhost"):
                results["warnings"].append(f"HTTP origin in production: {origin}")
    
    # Check credentials with wildcard origins
    allow_credentials = cors_config.get("allow_credentials", _should_allow_credentials(environment))
    if allow_credentials and "*" in allowed_origins:
        results["errors"].append("Cannot use credentials with wildcard origins")
        results["valid"] = False
    
    # Check for overly permissive headers
    allowed_headers = cors_config.get("allow_headers", [])
    if "*" in allowed_headers:
        results["warnings"].append("Wildcard headers (*) may be overly permissive")
    
    # Store configuration summary
    results["configuration"] = {
        "environment": environment,
        "allowed_origins": allowed_origins,
        "allow_credentials": allow_credentials,
        "allowed_methods": cors_config.get("allow_methods", []),
        "allowed_headers_count": len(allowed_headers),
        "max_age": cors_config.get("max_age", 86400)
    }
    
    return results


# Example CORS configurations for different environments
EXAMPLE_CORS_CONFIGS = {
    "development": {
        "api": {
            "cors": {
                "allow_origins": [
                    "http://localhost:3000",
                    "http://localhost:5173"
                ],
                "allow_credentials": True,
                "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "max_age": 86400
            }
        }
    },
    "production": {
        "api": {
            "cors": {
                "allow_origins": [
                    "https://sizecomparator.com",
                    "https://www.sizecomparator.com"
                ],
                "allow_credentials": False,
                "allow_methods": ["GET", "POST", "OPTIONS"],
                "expose_headers": [
                    "X-Request-ID",
                    "X-Processing-Time"
                ],
                "max_age": 86400
            }
        }
    }
}