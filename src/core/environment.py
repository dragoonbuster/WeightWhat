"""
Environment Variable Management System for SizeComparator

This module provides comprehensive environment variable management with:
- Type-safe loading and validation of all SIZECOMPARATOR_* environment variables
- Secure handling and masking of sensitive configuration data
- Environment-aware behavior (development vs production vs staging)
- Integration with configuration system and all components
- .env file loading with proper precedence
"""

from typing import Optional, Dict, Any, Union, List, TypeVar, Generic, Type, Callable
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
import os
import logging
import re
import json
import hashlib
import hmac
import base64
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from abc import ABC, abstractmethod

# Optional cryptography import for production encryption
try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    Fernet = None

T = TypeVar('T')

# Configure logger
logger = logging.getLogger(__name__)


class EnvironmentType(str, Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"


class ValidationMode(str, Enum):
    """Environment variable validation modes."""
    STRICT = "strict"      # Fail on any validation error
    WARN = "warn"          # Log warnings but continue
    OFF = "off"            # No validation


class SensitivityLevel(str, Enum):
    """Data sensitivity levels for masking."""
    PUBLIC = "public"      # No masking required
    INTERNAL = "internal"  # Mask in logs but not monitoring
    CONFIDENTIAL = "confidential"  # Mask everywhere except secure storage
    SECRET = "secret"      # Full masking and encryption


class ValidationError(Exception):
    """Environment variable validation error."""
    def __init__(self, variable: str, message: str, expected: Any = None, actual: Any = None):
        self.variable = variable
        self.message = message
        self.expected = expected
        self.actual = actual
        super().__init__(f"Validation error for {variable}: {message}")


class EnvironmentVariableSpec(BaseModel):
    """Specification for a single environment variable."""
    name: str = Field(..., description="Environment variable name")
    required: bool = Field(default=False, description="Whether variable is required")
    type: str = Field(..., description="Expected data type")
    default: Optional[Any] = Field(default=None, description="Default value if not set")
    sensitivity: SensitivityLevel = Field(default=SensitivityLevel.PUBLIC)
    
    # Validation rules
    pattern: Optional[str] = Field(default=None, description="Regex pattern validation")
    enum_values: Optional[List[str]] = Field(default=None, description="Allowed enum values")
    min_value: Optional[Union[int, float]] = Field(default=None, description="Minimum numeric value")
    max_value: Optional[Union[int, float]] = Field(default=None, description="Maximum numeric value")
    min_length: Optional[int] = Field(default=None, description="Minimum string length")
    max_length: Optional[int] = Field(default=None, description="Maximum string length")
    
    # Environment-specific rules
    required_in_production: bool = Field(default=False, description="Required only in production")
    development_only: bool = Field(default=False, description="Only used in development")
    
    # Documentation
    description: str = Field(..., description="Human-readable description")
    example: Optional[str] = Field(default=None, description="Example value")
    documentation_url: Optional[str] = Field(default=None, description="Link to documentation")


class EnvironmentVariableRegistry:
    """Central registry for all SIZECOMPARATOR_* environment variables."""
    
    VARIABLES: Dict[str, EnvironmentVariableSpec] = {
        # Core Application Configuration
        "SIZECOMPARATOR_ENV": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_ENV",
            required=True,
            type="enum",
            enum_values=["development", "staging", "production"],
            description="Runtime environment",
            example="production"
        ),
        
        "SIZECOMPARATOR_VERSION": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_VERSION",
            required=False,
            type="string",
            pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$",
            default="1.0.0",
            description="Application version in semver format",
            example="1.2.3"
        ),
        
        "SIZECOMPARATOR_CONFIG_DIR": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_CONFIG_DIR",
            required=False,
            type="path",
            default="/app/config",
            description="Configuration directory path",
            example="/app/config"
        ),
        
        # Configuration System Control
        "SIZECOMPARATOR_CONFIG_VALIDATION": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_CONFIG_VALIDATION",
            required=False,
            type="enum",
            enum_values=["strict", "warn", "off"],
            default="strict",
            description="Configuration validation mode",
            example="strict"
        ),
        
        "SIZECOMPARATOR_HOT_RELOAD": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_HOT_RELOAD",
            required=False,
            type="boolean",
            default=True,
            description="Enable configuration hot reload",
            development_only=True,
            example="true"
        ),
        
        # AI Provider - OpenAI
        "SIZECOMPARATOR_OPENAI_API_KEY": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_OPENAI_API_KEY",
            required=False,  # Conditional based on provider selection
            type="string",
            pattern=r"^sk-[A-Za-z0-9]+$",
            min_length=20,
            max_length=200,
            sensitivity=SensitivityLevel.SECRET,
            required_in_production=True,
            description="OpenAI API key for AI provider authentication",
            example="sk-1234567890abcdef..."
        ),
        
        "SIZECOMPARATOR_OPENAI_ENDPOINT": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_OPENAI_ENDPOINT",
            required=False,
            type="url",
            default="https://api.openai.com/v1",
            pattern=r"^https://",
            description="OpenAI API endpoint URL",
            example="https://api.openai.com/v1"
        ),
        
        "SIZECOMPARATOR_OPENAI_MODEL": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_OPENAI_MODEL",
            required=False,
            type="enum",
            enum_values=["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"],
            default="gpt-4",
            description="OpenAI model to use for comparisons",
            example="gpt-4"
        ),
        
        "SIZECOMPARATOR_OPENAI_TIMEOUT": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_OPENAI_TIMEOUT",
            required=False,
            type="integer",
            min_value=5,
            max_value=300,
            default=30,
            description="OpenAI API timeout in seconds",
            example="30"
        ),
        
        # AI Provider - Anthropic
        "SIZECOMPARATOR_ANTHROPIC_API_KEY": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_ANTHROPIC_API_KEY",
            required=False,
            type="string",
            pattern=r"^sk-ant-[A-Za-z0-9]+$",
            min_length=20,
            max_length=200,
            sensitivity=SensitivityLevel.SECRET,
            description="Anthropic API key for Claude integration",
            example="sk-ant-1234567890abcdef..."
        ),
        
        "SIZECOMPARATOR_ANTHROPIC_ENDPOINT": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_ANTHROPIC_ENDPOINT",
            required=False,
            type="url",
            default="https://api.anthropic.com",
            pattern=r"^https://",
            description="Anthropic API endpoint URL",
            example="https://api.anthropic.com"
        ),
        
        # Cache Configuration - Redis
        "SIZECOMPARATOR_REDIS_HOST": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_REDIS_HOST",
            required=False,
            type="string",
            default="localhost",
            description="Redis server hostname or IP address",
            example="redis.example.com"
        ),
        
        "SIZECOMPARATOR_REDIS_PORT": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_REDIS_PORT",
            required=False,
            type="integer",
            min_value=1,
            max_value=65535,
            default=6379,
            description="Redis server port number",
            example="6379"
        ),
        
        "SIZECOMPARATOR_REDIS_PASSWORD": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_REDIS_PASSWORD",
            required=False,
            type="string",
            min_length=8,
            sensitivity=SensitivityLevel.SECRET,
            description="Redis authentication password",
            example="secure_redis_password"
        ),
        
        "SIZECOMPARATOR_REDIS_TLS": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_REDIS_TLS",
            required=False,
            type="boolean",
            default=False,
            description="Enable TLS encryption for Redis connection",
            example="true"
        ),
        
        "SIZECOMPARATOR_REDIS_DB": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_REDIS_DB",
            required=False,
            type="integer",
            min_value=0,
            max_value=15,
            default=0,
            description="Redis database number",
            example="0"
        ),
        
        # Security Configuration
        "SIZECOMPARATOR_SECRET_KEY": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_SECRET_KEY",
            required=True,
            type="string",
            min_length=32,
            max_length=64,
            sensitivity=SensitivityLevel.SECRET,
            required_in_production=True,
            description="Application secret key for encryption and signing",
            example="super-secret-key-32-characters-long"
        ),
        
        # Monitoring and Logging
        "SIZECOMPARATOR_LOG_LEVEL": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_LOG_LEVEL",
            required=False,
            type="enum",
            enum_values=["debug", "info", "warn", "error"],
            default="info",
            description="Application logging level",
            example="info"
        ),
        
        "SIZECOMPARATOR_LOG_FORMAT": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_LOG_FORMAT",
            required=False,
            type="enum",
            enum_values=["json", "text"],
            default="json",
            description="Log output format",
            example="json"
        ),
        
        "SIZECOMPARATOR_METRICS_ENABLED": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_METRICS_ENABLED",
            required=False,
            type="boolean",
            default=True,
            description="Enable metrics collection and exposure",
            example="true"
        ),
        
        # Feature Flags
        "SIZECOMPARATOR_FEATURE_ENHANCED_VIZ": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_FEATURE_ENHANCED_VIZ",
            required=False,
            type="boolean",
            default=True,
            description="Enable enhanced visualization features",
            example="true"
        ),
        
        "SIZECOMPARATOR_FEATURE_AI_SUGGESTIONS": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_FEATURE_AI_SUGGESTIONS",
            required=False,
            type="boolean",
            default=False,
            description="Enable AI-powered suggestions feature",
            example="false"
        ),
        
        # Service Factory Configuration
        "SIZECOMPARATOR_SERVICE_STRATEGY": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_SERVICE_STRATEGY",
            required=False,
            type="enum",
            enum_values=["smart_routing", "performance_first", "accuracy_first", "basic_only"],
            default="smart_routing",
            description="Service selection strategy for comparison factory",
            example="smart_routing"
        ),
        
        "SIZECOMPARATOR_FORCE_BASIC_SERVICE": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_FORCE_BASIC_SERVICE",
            required=False,
            type="boolean",
            default=False,
            development_only=True,
            description="Force use of basic service only (for development/testing)",
            example="false"
        ),
        
        "SIZECOMPARATOR_REQUIRE_VALIDATION": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_REQUIRE_VALIDATION",
            required=False,
            type="boolean",
            default=True,
            description="Require validation services in production",
            example="true"
        ),
        
        "SIZECOMPARATOR_SERVICE_TIMEOUT_MS": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_SERVICE_TIMEOUT_MS",
            required=False,
            type="integer",
            min_value=1000,
            max_value=30000,
            default=5000,
            description="Default timeout for service operations in milliseconds",
            example="5000"
        ),
        
        # Development and Testing
        "SIZECOMPARATOR_DEBUG": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_DEBUG",
            required=False,
            type="boolean",
            default=False,
            development_only=True,
            description="Enable debug mode with verbose logging",
            example="true"
        ),
        
        "SIZECOMPARATOR_TEST_MODE": EnvironmentVariableSpec(
            name="SIZECOMPARATOR_TEST_MODE",
            required=False,
            type="boolean",
            default=False,
            development_only=True,
            description="Enable test mode with mocked dependencies",
            example="false"
        )
    }
    
    @classmethod
    def get_variable_spec(cls, name: str) -> Optional[EnvironmentVariableSpec]:
        """Get specification for a specific environment variable."""
        return cls.VARIABLES.get(name)
    
    @classmethod
    def get_all_variables(cls) -> Dict[str, EnvironmentVariableSpec]:
        """Get all registered environment variable specifications."""
        return cls.VARIABLES.copy()
    
    @classmethod
    def get_required_variables(cls, environment: EnvironmentType) -> List[str]:
        """Get list of required variables for specific environment."""
        required = []
        for name, spec in cls.VARIABLES.items():
            if spec.required or (environment == EnvironmentType.PRODUCTION and spec.required_in_production):
                required.append(name)
        return required
    
    @classmethod
    def get_sensitive_variables(cls) -> List[str]:
        """Get list of sensitive variables that require masking."""
        return [
            name for name, spec in cls.VARIABLES.items()
            if spec.sensitivity in [SensitivityLevel.CONFIDENTIAL, SensitivityLevel.SECRET]
        ]


class TypeConverter:
    """Type conversion and validation for environment variables."""
    
    @staticmethod
    def convert_string(value: str, spec: EnvironmentVariableSpec) -> str:
        """Convert and validate string type."""
        if spec.min_length and len(value) < spec.min_length:
            raise ValidationError(
                spec.name, 
                f"String too short (minimum {spec.min_length} characters)",
                expected=f">= {spec.min_length} chars",
                actual=f"{len(value)} chars"
            )
        
        if spec.max_length and len(value) > spec.max_length:
            raise ValidationError(
                spec.name,
                f"String too long (maximum {spec.max_length} characters)",
                expected=f"<= {spec.max_length} chars", 
                actual=f"{len(value)} chars"
            )
        
        if spec.pattern and not re.match(spec.pattern, value):
            raise ValidationError(
                spec.name,
                f"String does not match required pattern",
                expected=spec.pattern,
                actual=value
            )
        
        return value
    
    @staticmethod
    def convert_integer(value: str, spec: EnvironmentVariableSpec) -> int:
        """Convert and validate integer type."""
        try:
            int_value = int(value)
        except ValueError:
            raise ValidationError(
                spec.name,
                "Invalid integer format",
                expected="integer",
                actual=value
            )
        
        if spec.min_value is not None and int_value < spec.min_value:
            raise ValidationError(
                spec.name,
                f"Value below minimum",
                expected=f">= {spec.min_value}",
                actual=int_value
            )
        
        if spec.max_value is not None and int_value > spec.max_value:
            raise ValidationError(
                spec.name,
                f"Value above maximum",
                expected=f"<= {spec.max_value}",
                actual=int_value
            )
        
        return int_value
    
    @staticmethod
    def convert_float(value: str, spec: EnvironmentVariableSpec) -> float:
        """Convert and validate float type."""
        try:
            float_value = float(value)
        except ValueError:
            raise ValidationError(
                spec.name,
                "Invalid float format",
                expected="float",
                actual=value
            )
        
        if spec.min_value is not None and float_value < spec.min_value:
            raise ValidationError(
                spec.name,
                f"Value below minimum",
                expected=f">= {spec.min_value}",
                actual=float_value
            )
        
        if spec.max_value is not None and float_value > spec.max_value:
            raise ValidationError(
                spec.name,
                f"Value above maximum", 
                expected=f"<= {spec.max_value}",
                actual=float_value
            )
        
        return float_value
    
    @staticmethod
    def convert_boolean(value: str, spec: EnvironmentVariableSpec) -> bool:
        """Convert and validate boolean type."""
        lower_value = value.lower()
        if lower_value in ("true", "1", "yes", "on", "enabled"):
            return True
        elif lower_value in ("false", "0", "no", "off", "disabled"):
            return False
        else:
            raise ValidationError(
                spec.name,
                "Invalid boolean format",
                expected="true/false, 1/0, yes/no, on/off, enabled/disabled",
                actual=value
            )
    
    @staticmethod
    def convert_enum(value: str, spec: EnvironmentVariableSpec) -> str:
        """Convert and validate enum type."""
        if spec.enum_values and value not in spec.enum_values:
            raise ValidationError(
                spec.name,
                f"Invalid enum value",
                expected=f"one of {spec.enum_values}",
                actual=value
            )
        return value
    
    @staticmethod
    def convert_url(value: str, spec: EnvironmentVariableSpec) -> str:
        """Convert and validate URL type."""
        try:
            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                raise ValidationError(
                    spec.name,
                    "Invalid URL format",
                    expected="valid URL with scheme and netloc",
                    actual=value
                )
        except Exception as e:
            raise ValidationError(
                spec.name,
                f"URL parsing failed: {e}",
                expected="valid URL",
                actual=value
            )
        
        if spec.pattern and not re.match(spec.pattern, value):
            raise ValidationError(
                spec.name,
                "URL does not match required pattern",
                expected=spec.pattern,
                actual=value
            )
        
        return value
    
    @staticmethod
    def convert_path(value: str, spec: EnvironmentVariableSpec) -> str:
        """Convert and validate file path type."""
        path = Path(value)
        
        # Validate path format without requiring existence in all environments
        if not path.is_absolute() and not value.startswith('./'):
            # Allow relative paths starting with ./
            if not value.startswith('/'):
                raise ValidationError(
                    spec.name,
                    "Path must be absolute or start with ./",
                    expected="absolute path or ./relative/path",
                    actual=value
                )
        
        return value
    
    @classmethod
    def convert_value(cls, value: str, spec: EnvironmentVariableSpec) -> Any:
        """Convert string value to appropriate type based on specification."""
        if spec.type == "string":
            return cls.convert_string(value, spec)
        elif spec.type == "integer":
            return cls.convert_integer(value, spec)
        elif spec.type == "float":
            return cls.convert_float(value, spec)
        elif spec.type == "boolean":
            return cls.convert_boolean(value, spec)
        elif spec.type == "enum":
            return cls.convert_enum(value, spec)
        elif spec.type == "url":
            return cls.convert_url(value, spec)
        elif spec.type == "path":
            return cls.convert_path(value, spec)
        else:
            raise ValidationError(
                spec.name,
                f"Unsupported type: {spec.type}",
                expected="string, integer, float, boolean, enum, url, or path",
                actual=spec.type
            )


class SecretManager:
    """Secure handling and masking of sensitive environment variables."""
    
    def __init__(self, master_key: Optional[str] = None):
        """Initialize secret manager with optional master key for encryption."""
        self.master_key = master_key
        self._cipher = None
        if master_key and ENCRYPTION_AVAILABLE:
            self._cipher = Fernet(self._derive_key(master_key))
        elif master_key and not ENCRYPTION_AVAILABLE:
            logger.warning("Encryption requested but cryptography library not available")
    
    def _derive_key(self, master_key: str) -> bytes:
        """Derive encryption key from master key."""
        return base64.urlsafe_b64encode(
            hashlib.pbkdf2_hmac('sha256', master_key.encode(), b'sizecomparator', 100000)[:32]
        )
    
    def mask_sensitive_value(self, value: str, sensitivity: SensitivityLevel, context: str = "default") -> str:
        """Mask sensitive values based on sensitivity level and context."""
        if sensitivity == SensitivityLevel.PUBLIC:
            return value
        
        if sensitivity == SensitivityLevel.INTERNAL:
            if context in ("logs", "debugging"):
                return self._partial_mask(value, show_chars=4)
            return value
        
        if sensitivity == SensitivityLevel.CONFIDENTIAL:
            if context in ("monitoring", "metrics"):
                return self._hash_value(value)
            return self._partial_mask(value, show_chars=2)
        
        if sensitivity == SensitivityLevel.SECRET:
            if context == "secure_storage":
                return self._encrypt_value(value) if self._cipher else self._hash_value(value)
            return "*" * 8  # Complete masking
        
        return value
    
    def _partial_mask(self, value: str, show_chars: int = 4) -> str:
        """Partially mask a value, showing only first/last characters."""
        if len(value) <= show_chars * 2:
            return "*" * len(value)
        
        prefix = value[:show_chars]
        suffix = value[-show_chars:]
        middle = "*" * max(4, len(value) - show_chars * 2)
        return f"{prefix}{middle}{suffix}"
    
    def _hash_value(self, value: str) -> str:
        """Create a hash of the value for identification without exposure."""
        hash_obj = hashlib.sha256(value.encode())
        return f"sha256:{hash_obj.hexdigest()[:16]}"
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a value for secure storage."""
        if not self._cipher:
            raise ValueError("No encryption key available")
        encrypted = self._cipher.encrypt(value.encode())
        return f"enc:{base64.urlsafe_b64encode(encrypted).decode()}"
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt an encrypted value."""
        if not encrypted_value.startswith("enc:"):
            return encrypted_value
        
        if not self._cipher:
            raise ValueError("No decryption key available")
        
        encrypted_data = base64.urlsafe_b64decode(encrypted_value[4:])
        return self._cipher.decrypt(encrypted_data).decode()
    
    def sanitize_for_logging(self, data: Dict[str, Any], registry: EnvironmentVariableRegistry) -> Dict[str, Any]:
        """Sanitize data dictionary for safe logging."""
        sanitized = {}
        
        for key, value in data.items():
            if key.startswith("SIZECOMPARATOR_"):
                spec = registry.get_variable_spec(key)
                if spec:
                    sanitized[key] = self.mask_sensitive_value(str(value), spec.sensitivity, "logs")
                else:
                    # Unknown SIZECOMPARATOR_ variable - treat as confidential
                    sanitized[key] = self._partial_mask(str(value), show_chars=2)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def audit_secret_access(self, variable_name: str, operation: str, user: Optional[str] = None) -> None:
        """Log audit trail for secret access."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "variable": variable_name,
            "operation": operation,
            "user": user or "system",
            "source": "environment_manager"
        }
        
        # Log to audit trail (implementation depends on logging system)
        logging.getLogger("sizecomparator.audit").info(
            "Secret access audit",
            extra=audit_entry
        )


class EnvironmentSecurityPolicy:
    """Security policies based on environment type."""
    
    @staticmethod
    def get_security_policy(environment: EnvironmentType) -> Dict[str, Any]:
        """Get security policy configuration for environment."""
        policies = {
            EnvironmentType.DEVELOPMENT: {
                "require_encryption": False,
                "allow_default_secrets": True,
                "log_secret_access": False,
                "mask_in_logs": False,
                "require_tls": False,
                "audit_level": "basic"
            },
            EnvironmentType.STAGING: {
                "require_encryption": True,
                "allow_default_secrets": False,
                "log_secret_access": True,
                "mask_in_logs": True,
                "require_tls": True,
                "audit_level": "standard"
            },
            EnvironmentType.PRODUCTION: {
                "require_encryption": True,
                "allow_default_secrets": False,
                "log_secret_access": True,
                "mask_in_logs": True,
                "require_tls": True,
                "audit_level": "comprehensive",
                "rotate_secrets": True,
                "validate_secret_strength": True
            }
        }
        
        return policies.get(environment, policies[EnvironmentType.PRODUCTION])
    
    @staticmethod
    def validate_secret_strength(value: str, variable_name: str) -> List[str]:
        """Validate secret strength and return list of issues."""
        issues = []
        
        if len(value) < 16:
            issues.append("Secret too short (minimum 16 characters)")
        
        if len(value) < 32 and variable_name.endswith("_SECRET_KEY"):
            issues.append("Secret key should be at least 32 characters")
        
        if value.isalnum():
            issues.append("Secret should contain special characters")
        
        if re.match(r'^[a-z]+$', value) or re.match(r'^[A-Z]+$', value):
            issues.append("Secret should contain mixed case")
        
        if not re.search(r'\d', value):
            issues.append("Secret should contain numbers")
        
        # Check for common weak patterns
        weak_patterns = [
            r'123+',
            r'password',
            r'secret',
            r'admin',
            r'qwerty',
            r'abcd+'
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, value.lower()):
                issues.append(f"Secret contains weak pattern: {pattern}")
                break
        
        return issues


class DotEnvLoader:
    """Load environment variables from .env files with proper precedence."""
    
    def __init__(self, env_file_paths: Optional[List[str]] = None):
        """Initialize with list of .env file paths in order of precedence."""
        self.env_file_paths = env_file_paths or ['.env.local', '.env']
        self._loaded_variables = {}
    
    def load_env_files(self) -> Dict[str, str]:
        """Load variables from .env files with proper precedence."""
        # System environment variables have highest precedence
        env_vars = dict(os.environ)
        
        # Load .env files in reverse order (lowest precedence first)
        for env_file in reversed(self.env_file_paths):
            if Path(env_file).exists():
                file_vars = self._parse_env_file(env_file)
                # Only set if not already defined
                for key, value in file_vars.items():
                    if key not in env_vars:
                        env_vars[key] = value
                        self._loaded_variables[key] = env_file
                logger.info(f"Loaded {len(file_vars)} variables from {env_file}")
        
        return env_vars
    
    def _parse_env_file(self, file_path: str) -> Dict[str, str]:
        """Parse .env file and return variables."""
        variables = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        
                        # Handle escaped characters
                        value = value.replace('\\n', '\n').replace('\\t', '\t')
                        
                        variables[key] = value
                    else:
                        logger.warning(f"Invalid line format in {file_path}:{line_num}: {line}")
        
        except Exception as e:
            logger.error(f"Error reading .env file {file_path}: {e}")
        
        return variables
    
    def get_source_file(self, variable_name: str) -> Optional[str]:
        """Get the source file for a loaded variable."""
        return self._loaded_variables.get(variable_name)


class EnvironmentManager:
    """Main environment variable manager with environment-aware behavior."""
    
    def __init__(self, 
                 environment: Optional[EnvironmentType] = None, 
                 validation_mode: ValidationMode = ValidationMode.STRICT,
                 env_file_paths: Optional[List[str]] = None,
                 master_key: Optional[str] = None):
        """Initialize environment manager."""
        self.environment = environment or self._detect_environment()
        self.validation_mode = validation_mode
        self.registry = EnvironmentVariableRegistry()
        self.secret_manager = SecretManager(master_key)
        self.security_policy = EnvironmentSecurityPolicy.get_security_policy(self.environment)
        self.dotenv_loader = DotEnvLoader(env_file_paths)
        self._loaded_variables: Dict[str, Any] = {}
        self._validation_errors: List[ValidationError] = []
        self.config_watchers: List[Callable] = []
        
        # Load .env files first to ensure environment variables are available
        self.dotenv_loader.load_env_files()
        
    def _detect_environment(self) -> EnvironmentType:
        """Auto-detect environment from standard variables."""
        env_value = os.getenv("SIZECOMPARATOR_ENV", "development").lower()
        try:
            return EnvironmentType(env_value)
        except ValueError:
            logger.warning(f"Invalid environment value '{env_value}', defaulting to development")
            return EnvironmentType.DEVELOPMENT
    
    def load_all_variables(self) -> Dict[str, Any]:
        """Load and validate all environment variables."""
        loaded = {}
        errors = []
        
        for name, spec in self.registry.get_all_variables().items():
            try:
                value = self.load_variable(name, spec)
                if value is not None:
                    loaded[name] = value
            except ValidationError as e:
                errors.append(e)
                if self.validation_mode == ValidationMode.STRICT:
                    raise
                elif self.validation_mode == ValidationMode.WARN:
                    logger.warning(f"Environment variable validation warning: {e}")
        
        self._loaded_variables = loaded
        self._validation_errors = errors
        
        # Post-load validation for environment-specific requirements
        self._validate_environment_requirements(loaded)
        
        return loaded
    
    def load_variable(self, name: str, spec: Optional[EnvironmentVariableSpec] = None) -> Any:
        """Load and validate a single environment variable."""
        if spec is None:
            spec = self.registry.get_variable_spec(name)
            if spec is None:
                raise ValueError(f"No specification found for variable: {name}")
        
        # Check if variable should be loaded in current environment
        if spec.development_only and self.environment == EnvironmentType.PRODUCTION:
            return None
        
        # Get raw value from environment
        raw_value = os.getenv(name)
        
        # Handle missing required variables
        if raw_value is None:
            if self._is_required_in_environment(spec):
                raise ValidationError(
                    name,
                    f"Required environment variable not set",
                    expected="non-empty value",
                    actual="None"
                )
            
            # Use default if available
            if spec.default is not None:
                return spec.default
            
            return None
        
        # Convert and validate the value
        try:
            converted_value = TypeConverter.convert_value(raw_value, spec)
            
            # Additional security validation for production
            if (self.environment == EnvironmentType.PRODUCTION and 
                spec.sensitivity in [SensitivityLevel.CONFIDENTIAL, SensitivityLevel.SECRET]):
                self._validate_production_secret(converted_value, spec)
            
            # Audit secret access
            if spec.sensitivity in [SensitivityLevel.CONFIDENTIAL, SensitivityLevel.SECRET]:
                self.secret_manager.audit_secret_access(name, "load")
            
            return converted_value
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                name,
                f"Unexpected error during conversion: {e}",
                expected=f"valid {spec.type}",
                actual=raw_value
            )
    
    def _is_required_in_environment(self, spec: EnvironmentVariableSpec) -> bool:
        """Check if variable is required in current environment."""
        if spec.required:
            return True
        
        if spec.required_in_production and self.environment == EnvironmentType.PRODUCTION:
            return True
        
        return False
    
    def _validate_production_secret(self, value: str, spec: EnvironmentVariableSpec) -> None:
        """Additional validation for secrets in production environment."""
        if not self.security_policy.get("validate_secret_strength", False):
            return
        
        issues = EnvironmentSecurityPolicy.validate_secret_strength(value, spec.name)
        if issues:
            raise ValidationError(
                spec.name,
                f"Secret does not meet production security requirements: {'; '.join(issues)}",
                expected="strong secret meeting security policy",
                actual="weak secret"
            )
    
    def _validate_environment_requirements(self, loaded_variables: Dict[str, Any]) -> None:
        """Validate environment-specific requirements."""
        if self.environment == EnvironmentType.PRODUCTION:
            # Ensure TLS is enabled for external connections
            redis_tls = loaded_variables.get("SIZECOMPARATOR_REDIS_TLS", False)
            if not redis_tls and self.security_policy.get("require_tls", False):
                logger.warning("TLS not enabled for Redis in production environment")
        
        # Validate AI provider configuration
        openai_key = loaded_variables.get("SIZECOMPARATOR_OPENAI_API_KEY")
        anthropic_key = loaded_variables.get("SIZECOMPARATOR_ANTHROPIC_API_KEY")
        
        if not openai_key and not anthropic_key:
            raise ValidationError(
                "AI_PROVIDER",
                "At least one AI provider API key must be configured",
                expected="SIZECOMPARATOR_OPENAI_API_KEY or SIZECOMPARATOR_ANTHROPIC_API_KEY",
                actual="neither configured"
            )
    
    def get_variable(self, name: str, default: Any = None, mask_sensitive: bool = True) -> Any:
        """Get a loaded environment variable value."""
        if name not in self._loaded_variables:
            return default
        
        value = self._loaded_variables[name]
        
        # Apply masking if requested and variable is sensitive
        if mask_sensitive:
            spec = self.registry.get_variable_spec(name)
            if spec and spec.sensitivity != SensitivityLevel.PUBLIC:
                return self.secret_manager.mask_sensitive_value(
                    str(value), 
                    spec.sensitivity, 
                    "api_response"
                )
        
        return value
    
    def get_sanitized_config(self) -> Dict[str, Any]:
        """Get configuration with all sensitive values masked for logging."""
        return self.secret_manager.sanitize_for_logging(
            self._loaded_variables, 
            self.registry
        )
    
    def validate_runtime_changes(self, changes: Dict[str, str]) -> List[ValidationError]:
        """Validate proposed runtime configuration changes."""
        errors = []
        
        for name, new_value in changes.items():
            spec = self.registry.get_variable_spec(name)
            if not spec:
                errors.append(ValidationError(
                    name,
                    "Unknown environment variable",
                    expected="registered SIZECOMPARATOR_* variable",
                    actual=name
                ))
                continue
            
            try:
                TypeConverter.convert_value(new_value, spec)
            except ValidationError as e:
                errors.append(e)
        
        return errors
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get comprehensive environment information for debugging."""
        return {
            "environment": self.environment.value,
            "validation_mode": self.validation_mode.value,
            "security_policy": self.security_policy,
            "loaded_variables_count": len(self._loaded_variables),
            "validation_errors_count": len(self._validation_errors),
            "sensitive_variables": self.registry.get_sensitive_variables(),
            "required_variables": self.registry.get_required_variables(self.environment),
            "encryption_available": ENCRYPTION_AVAILABLE
        }
    
    def register_config_watcher(self, callback: Callable) -> None:
        """Register callback for configuration changes."""
        self.config_watchers.append(callback)
    
    def notify_config_change(self, variable_name: str, old_value: Any, new_value: Any) -> None:
        """Notify registered watchers of configuration changes."""
        for watcher in self.config_watchers:
            try:
                watcher(variable_name, old_value, new_value)
            except Exception as e:
                logger.error(f"Config watcher failed: {e}")


# Component Integration Interfaces

class ComponentConfigInterface(ABC):
    """Base interface for component configuration access."""
    
    @abstractmethod
    def get_component_config(self) -> Dict[str, Any]:
        """Get configuration specific to this component."""
        pass
    
    @abstractmethod
    def on_config_change(self, variable_name: str, new_value: Any) -> None:
        """Handle configuration change notifications."""
        pass


class APIProviderConfigInterface(ComponentConfigInterface):
    """Configuration interface for AI provider components."""
    
    def __init__(self, env_manager: EnvironmentManager, provider_name: str):
        self.env_manager = env_manager
        self.provider_name = provider_name
    
    def get_component_config(self) -> Dict[str, Any]:
        """Get AI provider specific configuration."""
        prefix = f"SIZECOMPARATOR_{self.provider_name.upper()}_"
        
        config = {}
        for name, value in self.env_manager._loaded_variables.items():
            if name.startswith(prefix):
                config_key = name[len(prefix):].lower()
                config[config_key] = value
        
        return config
    
    def get_api_key(self) -> Optional[str]:
        """Get API key for provider (unmasked for actual use)."""
        key_name = f"SIZECOMPARATOR_{self.provider_name.upper()}_API_KEY"
        return self.env_manager.get_variable(key_name, mask_sensitive=False)
    
    def get_endpoint_url(self) -> str:
        """Get endpoint URL for provider."""
        endpoint_name = f"SIZECOMPARATOR_{self.provider_name.upper()}_ENDPOINT"
        return self.env_manager.get_variable(endpoint_name)
    
    def on_config_change(self, variable_name: str, new_value: Any) -> None:
        """Handle configuration changes for provider."""
        if variable_name.startswith(f"SIZECOMPARATOR_{self.provider_name.upper()}_"):
            # Reinitialize provider connection with new configuration
            logger.info(f"Reinitializing {self.provider_name} provider due to config change")


class CacheConfigInterface(ComponentConfigInterface):
    """Configuration interface for cache components."""
    
    def __init__(self, env_manager: EnvironmentManager):
        self.env_manager = env_manager
    
    def get_component_config(self) -> Dict[str, Any]:
        """Get cache specific configuration."""
        return {
            "host": self.env_manager.get_variable("SIZECOMPARATOR_REDIS_HOST"),
            "port": self.env_manager.get_variable("SIZECOMPARATOR_REDIS_PORT"),
            "password": self.env_manager.get_variable("SIZECOMPARATOR_REDIS_PASSWORD", mask_sensitive=False),
            "tls_enabled": self.env_manager.get_variable("SIZECOMPARATOR_REDIS_TLS"),
            "database": self.env_manager.get_variable("SIZECOMPARATOR_REDIS_DB", 0)
        }
    
    def on_config_change(self, variable_name: str, new_value: Any) -> None:
        """Handle configuration changes for cache."""
        if variable_name.startswith("SIZECOMPARATOR_REDIS_"):
            logger.info("Cache configuration changed, connection pool will be recreated")


class MonitoringConfigInterface(ComponentConfigInterface):
    """Configuration interface for monitoring components."""
    
    def __init__(self, env_manager: EnvironmentManager):
        self.env_manager = env_manager
    
    def get_component_config(self) -> Dict[str, Any]:
        """Get monitoring specific configuration."""
        return {
            "log_level": self.env_manager.get_variable("SIZECOMPARATOR_LOG_LEVEL"),
            "log_format": self.env_manager.get_variable("SIZECOMPARATOR_LOG_FORMAT"),
            "metrics_enabled": self.env_manager.get_variable("SIZECOMPARATOR_METRICS_ENABLED"),
            "debug_mode": self.env_manager.get_variable("SIZECOMPARATOR_DEBUG", False)
        }
    
    def should_mask_in_logs(self, variable_name: str) -> bool:
        """Check if variable should be masked in logs."""
        spec = self.env_manager.registry.get_variable_spec(variable_name)
        return spec and spec.sensitivity != SensitivityLevel.PUBLIC
    
    def on_config_change(self, variable_name: str, new_value: Any) -> None:
        """Handle configuration changes for monitoring."""
        if variable_name == "SIZECOMPARATOR_LOG_LEVEL":
            logging.getLogger().setLevel(new_value.upper())
            logger.info(f"Log level changed to {new_value}")


class ConfigSystemIntegration:
    """Integration layer between environment manager and configuration system."""
    
    def __init__(self, env_manager: EnvironmentManager):
        self.env_manager = env_manager
    
    def get_config_template_variables(self) -> Dict[str, Any]:
        """Get environment variables for configuration template substitution."""
        # Return all loaded variables with sensitive values masked
        return self.env_manager.get_sanitized_config()
    
    def validate_config_environment_consistency(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate consistency between environment variables and configuration."""
        issues = []
        
        # Check if AI provider configuration matches available API keys
        openai_configured = "openai" in config_data.get("api", {}).get("providers", {})
        openai_key_available = self.env_manager.get_variable("SIZECOMPARATOR_OPENAI_API_KEY") is not None
        
        if openai_configured and not openai_key_available:
            issues.append("OpenAI provider configured but SIZECOMPARATOR_OPENAI_API_KEY not set")
        
        anthropic_configured = "anthropic" in config_data.get("api", {}).get("providers", {})
        anthropic_key_available = self.env_manager.get_variable("SIZECOMPARATOR_ANTHROPIC_API_KEY") is not None
        
        if anthropic_configured and not anthropic_key_available:
            issues.append("Anthropic provider configured but SIZECOMPARATOR_ANTHROPIC_API_KEY not set")
        
        # Check Redis configuration consistency
        redis_configured = config_data.get("cache", {}).get("provider") == "redis"
        redis_host = self.env_manager.get_variable("SIZECOMPARATOR_REDIS_HOST")
        
        if redis_configured and not redis_host:
            issues.append("Redis cache configured but SIZECOMPARATOR_REDIS_HOST not set")
        
        return issues


# Convenience function to create a global environment manager instance
def create_environment_manager(
    environment: Optional[EnvironmentType] = None,
    validation_mode: ValidationMode = ValidationMode.STRICT,
    env_file_paths: Optional[List[str]] = None,
    master_key: Optional[str] = None
) -> EnvironmentManager:
    """Create and initialize environment manager with loaded configuration."""
    env_manager = EnvironmentManager(
        environment=environment,
        validation_mode=validation_mode,
        env_file_paths=env_file_paths,
        master_key=master_key
    )
    env_manager.load_all_variables()
    return env_manager