"""
Configuration models and validation helpers for SizeComparator.

This module contains all configuration-related models matching CONFIG_SYSTEM_SPEC
requirements for validation, hot-reload, and template management.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union, Literal, Annotated
from datetime import datetime
from enum import Enum
import re


class ConfigurationError(BaseModel):
    """Configuration validation error."""
    config_path: str = Field(
        ...,
        description="Configuration path with error",
        examples=["api.providers.openai.timeout_seconds", "cache.settings.ttl"]
    )
    error_type: str = Field(
        ...,
        description="Type of configuration error",
        examples=["missing_required", "invalid_type", "out_of_range", "unknown_field"]
    )
    error_message: str = Field(
        ...,
        description="Detailed error message"
    )
    current_value: Optional[Any] = Field(
        None,
        description="Current invalid value"
    )
    expected_type: Optional[str] = Field(
        None,
        description="Expected type or format"
    )
    suggested_value: Optional[Any] = Field(
        None,
        description="Suggested correct value"
    )
    schema_constraint: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON Schema constraint that failed"
    )


class TemplateType(str, Enum):
    """Types of templates supported."""
    COMPARISON_PROMPT = "comparison_prompt"
    VISUALIZATION_PROMPT = "visualization_prompt"
    ERROR_MESSAGE = "error_message"
    NOTIFICATION = "notification"


class TemplateValidationResult(BaseModel):
    """Template validation result for CONFIG_SYSTEM_SPEC."""
    template_id: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Template identifier"
    )
    valid: bool = Field(
        ...,
        description="Template validation status"
    )
    syntax_errors: List[str] = Field(
        default_factory=list,
        max_items=50,
        description="Template syntax errors"
    )
    variable_errors: List[str] = Field(
        default_factory=list,
        max_items=50,
        description="Template variable errors"
    )
    required_variables: List[str] = Field(
        default_factory=list,
        description="Required template variables"
    )
    optional_variables: List[str] = Field(
        default_factory=list,
        description="Optional template variables"
    )
    provider_compatibility: Dict[str, bool] = Field(
        default_factory=dict,
        description="Provider compatibility status"
    )
    example_output: Optional[str] = Field(
        None,
        max_length=1000,
        description="Example rendered output"
    )


class TemplateConfig(BaseModel):
    """Configuration for a prompt template."""
    template_id: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Unique template identifier"
    )
    template_type: TemplateType = Field(
        ...,
        description="Type of template"
    )
    template_content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Template content with variables"
    )
    description: str = Field(
        ...,
        max_length=500,
        description="Template description"
    )
    required_variables: List[str] = Field(
        default_factory=list,
        description="Required template variables"
    )
    optional_variables: List[str] = Field(
        default_factory=list,
        description="Optional template variables"
    )
    supported_providers: List[str] = Field(
        default_factory=list,
        description="AI providers that support this template"
    )
    version: str = Field(
        ...,
        pattern=r'^\d+\.\d+\.\d+$',
        description="Template version"
    )
    enabled: bool = Field(
        True,
        description="Whether template is enabled"
    )
    priority: Annotated[int, Field(ge=1, le=10)] = Field(
        5,
        description="Template priority (1=highest)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional template metadata"
    )
    
    @field_validator('template_content')
    @classmethod
    def validate_template_syntax(cls, v: str) -> str:
        """Validate template syntax for variable placeholders."""
        # Check for balanced braces
        brace_count = 0
        for char in v:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count < 0:
                    raise ValueError("Unmatched closing brace in template")
        
        if brace_count != 0:
            raise ValueError("Unmatched opening brace in template")
        
        # Check for valid variable names
        variable_pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        variables = re.findall(variable_pattern, v)
        
        # Check for invalid variable references
        invalid_pattern = r'\{[^a-zA-Z_][^}]*\}'
        if re.search(invalid_pattern, v):
            raise ValueError("Invalid variable name in template")
        
        return v


class APIConfiguration(BaseModel):
    """API server configuration."""
    host: str = Field(
        "0.0.0.0",
        description="API server host"
    )
    port: Annotated[int, Field(ge=1, le=65535)] = Field(
        8000,
        description="API server port"
    )
    workers: Annotated[int, Field(ge=1, le=32)] = Field(
        4,
        description="Number of worker processes"
    )
    timeout_seconds: Annotated[float, Field(ge=1.0, le=300.0)] = Field(
        30.0,
        description="Request timeout"
    )
    max_request_size_mb: Annotated[int, Field(ge=1, le=100)] = Field(
        10,
        description="Maximum request size in MB"
    )
    cors_enabled: bool = Field(
        True,
        description="Whether CORS is enabled"
    )
    cors_origins: List[str] = Field(
        default_factory=list,
        description="Allowed CORS origins"
    )
    rate_limiting_enabled: bool = Field(
        True,
        description="Whether rate limiting is enabled"
    )
    rate_limit_requests_per_minute: Annotated[int, Field(ge=1, le=10000)] = Field(
        100,
        description="Rate limit per minute per client"
    )


class CacheConfiguration(BaseModel):
    """Cache configuration."""
    enabled: bool = Field(
        True,
        description="Whether caching is enabled"
    )
    backend: Literal["memory", "redis"] = Field(
        "memory",
        description="Cache backend type"
    )
    ttl_seconds: Annotated[int, Field(ge=1, le=86400)] = Field(
        3600,
        description="Default TTL in seconds"
    )
    max_size_mb: Annotated[int, Field(ge=1, le=1024)] = Field(
        100,
        description="Maximum cache size in MB"
    )
    redis_url: Optional[str] = Field(
        None,
        description="Redis connection URL if using Redis backend"
    )
    compression_enabled: bool = Field(
        True,
        description="Whether to compress cached data"
    )


class LoggingConfiguration(BaseModel):
    """Logging configuration."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO",
        description="Logging level"
    )
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    file_enabled: bool = Field(
        True,
        description="Whether to log to file"
    )
    file_path: Optional[str] = Field(
        None,
        description="Log file path"
    )
    max_file_size_mb: Annotated[int, Field(ge=1, le=1000)] = Field(
        50,
        description="Maximum log file size in MB"
    )
    backup_count: Annotated[int, Field(ge=1, le=10)] = Field(
        5,
        description="Number of backup log files"
    )
    json_format: bool = Field(
        True,
        description="Whether to use JSON format for structured logging"
    )


class MonitoringConfiguration(BaseModel):
    """Monitoring and metrics configuration."""
    metrics_enabled: bool = Field(
        True,
        description="Whether metrics collection is enabled"
    )
    metrics_endpoint: str = Field(
        "/metrics",
        description="Prometheus metrics endpoint"
    )
    health_check_endpoint: str = Field(
        "/health",
        description="Health check endpoint"
    )
    readiness_endpoint: str = Field(
        "/ready",
        description="Readiness check endpoint"
    )
    error_tracking_enabled: bool = Field(
        True,
        description="Whether error tracking is enabled"
    )
    performance_tracking_enabled: bool = Field(
        True,
        description="Whether performance tracking is enabled"
    )
    sample_rate: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        1.0,
        description="Sampling rate for traces"
    )


class SecurityConfiguration(BaseModel):
    """Security configuration."""
    api_key_required: bool = Field(
        False,
        description="Whether API key is required"
    )
    api_key_header: str = Field(
        "X-API-Key",
        description="API key header name"
    )
    allowed_hosts: List[str] = Field(
        default_factory=list,
        description="Allowed host headers"
    )
    max_requests_per_minute: Annotated[int, Field(ge=1, le=10000)] = Field(
        1000,
        description="Global rate limit per minute"
    )
    request_size_limit_mb: Annotated[int, Field(ge=1, le=100)] = Field(
        10,
        description="Request size limit in MB"
    )
    sensitive_data_masking: bool = Field(
        True,
        description="Whether to mask sensitive data in logs"
    )


class ApplicationConfiguration(BaseModel):
    """Main application configuration."""
    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid'
    )
    
    # Application metadata
    name: str = Field(
        "SizeComparator",
        description="Application name"
    )
    version: str = Field(
        ...,
        pattern=r'^\d+\.\d+\.\d+$',
        description="Application version"
    )
    environment: Literal["development", "staging", "production"] = Field(
        ...,
        description="Deployment environment"
    )
    debug: bool = Field(
        False,
        description="Whether debug mode is enabled"
    )
    
    # Component configurations
    api: APIConfiguration = Field(
        default_factory=APIConfiguration,
        description="API server configuration"
    )
    cache: CacheConfiguration = Field(
        default_factory=CacheConfiguration,
        description="Cache configuration"
    )
    logging: LoggingConfiguration = Field(
        default_factory=LoggingConfiguration,
        description="Logging configuration"
    )
    monitoring: MonitoringConfiguration = Field(
        default_factory=MonitoringConfiguration,
        description="Monitoring configuration"
    )
    security: SecurityConfiguration = Field(
        default_factory=SecurityConfiguration,
        description="Security configuration"
    )
    
    # AI providers
    providers: Dict[str, Any] = Field(
        default_factory=dict,
        description="AI provider configurations"
    )
    
    # Templates
    templates: List[TemplateConfig] = Field(
        default_factory=list,
        description="Prompt templates"
    )
    
    # Feature flags
    features: Dict[str, bool] = Field(
        default_factory=dict,
        description="Feature flags"
    )
    
    # Custom settings
    custom: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom application settings"
    )


class ConfigurationValidator:
    """Validator for configuration data."""
    
    @staticmethod
    def validate_configuration(config: Dict[str, Any]) -> List[ConfigurationError]:
        """Validate complete configuration."""
        errors = []
        
        try:
            # Attempt to parse as ApplicationConfiguration
            ApplicationConfiguration(**config)
        except Exception as e:
            # Parse validation errors
            if hasattr(e, 'errors'):
                for error in e.errors():
                    config_path = '.'.join(str(p) for p in error['loc'])
                    errors.append(ConfigurationError(
                        config_path=config_path,
                        error_type=error['type'],
                        error_message=error['msg'],
                        current_value=error.get('input'),
                        constraint_violated=error.get('ctx', {}).get('constraint')
                    ))
            else:
                errors.append(ConfigurationError(
                    config_path="root",
                    error_type="validation_error",
                    error_message=str(e)
                ))
        
        return errors
    
    @staticmethod
    def validate_template(template: TemplateConfig) -> TemplateValidationResult:
        """Validate a single template."""
        result = TemplateValidationResult(
            template_id=template.template_id,
            valid=True
        )
        
        try:
            # Extract variables from template
            variable_pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
            found_variables = set(re.findall(variable_pattern, template.template_content))
            
            # Check required variables are present
            missing_required = set(template.required_variables) - found_variables
            if missing_required:
                result.valid = False
                result.variable_errors.append(
                    f"Missing required variables: {', '.join(missing_required)}"
                )
            
            # Check for undefined variables
            undefined_variables = found_variables - set(template.required_variables) - set(template.optional_variables)
            if undefined_variables:
                result.variable_errors.append(
                    f"Undefined variables: {', '.join(undefined_variables)}"
                )
            
            result.required_variables = list(found_variables & set(template.required_variables))
            result.optional_variables = list(found_variables & set(template.optional_variables))
            
        except Exception as e:
            result.valid = False
            result.syntax_errors.append(str(e))
        
        return result


class CachedConfig(BaseModel):
    """Cached configuration entry."""
    type: str = Field(
        ...,
        description="Configuration type"
    )
    version: str = Field(
        ...,
        description="Configuration version"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Configuration data"
    )
    cached_at: datetime = Field(
        ...,
        description="When configuration was cached"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="When configuration expires"
    )