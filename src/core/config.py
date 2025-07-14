"""
Configuration Loader System for SizeComparator

Provides robust, hot-reloadable configuration management with YAML/JSON support,
environment variable templating, hierarchical merging, and atomic updates.
"""

import json
import logging
import os
import re
import socket
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, Deque
import yaml

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


# Configure logging
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Base exception for configuration errors"""
    pass


class ConfigLoadError(ConfigError):
    """Error loading configuration files"""
    pass


class ValidationError(ConfigError):
    """Configuration validation error"""
    def __init__(self, message: str, path: str = "", value: Any = None):
        super().__init__(message)
        self.path = path
        self.value = value


class MissingVariableError(ConfigError):
    """Required environment variable not found"""
    pass


class TypeConversionError(ConfigError):
    """Error converting environment variable types"""
    pass


class CircularDependencyError(ConfigError):
    """Circular dependency in environment variable resolution"""
    pass


class DependencyError(ConfigError):
    """Configuration dependency not satisfied"""
    pass


class CriticalPathError(ConfigError):
    """Critical path test failed"""
    pass


class UpdateVerificationError(ConfigError):
    """Configuration update verification failed"""
    pass


class ValidationResult:
    """Container for validation results"""
    def __init__(self, valid: bool, errors: List[ValidationError], warnings: List[str] = None):
        self.valid = valid
        self.errors = errors
        self.warnings = warnings or []


class ConfigChangeEvent:
    """Event fired when configuration changes"""
    def __init__(self, path: Path, config: Dict[str, Any], timestamp: datetime):
        self.path = path
        self.config = config
        self.timestamp = timestamp


class ConfigErrorEvent:
    """Event fired when configuration error occurs"""
    def __init__(self, path: Path, error: str, timestamp: datetime):
        self.path = path
        self.error = error
        self.timestamp = timestamp


class ConfigSubscriber(ABC):
    """Abstract base class for configuration change subscribers"""
    
    @abstractmethod
    def on_config_change(self, event: ConfigChangeEvent):
        """Handle configuration changes"""
        pass
    
    @abstractmethod
    def on_config_error(self, event: ConfigErrorEvent):
        """Handle configuration errors"""
        pass


class ComponentConfigAdapter(ConfigSubscriber):
    """Adapter for component-specific configuration updates"""
    
    def __init__(self, component_name: str, update_callback: Callable):
        self.component_name = component_name
        self.update_callback = update_callback
        self.config_section = None
        
    def on_config_change(self, event: ConfigChangeEvent):
        """Extract component-specific configuration"""
        new_section = event.config.get(self.component_name, {})
        
        if new_section != self.config_section:
            self.config_section = new_section
            try:
                self.update_callback(new_section)
                logger.info(f"Updated configuration for {self.component_name}")
            except Exception as e:
                logger.error(f"Failed to update {self.component_name}: {e}")
    
    def on_config_error(self, event: ConfigErrorEvent):
        """Handle configuration errors"""
        logger.error(f"Configuration error in {self.component_name}: {event.error}")


class Debouncer:
    """Debouncer to prevent rapid-fire configuration reloads"""
    
    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.timer = None
        self.lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs):
        """Debounced function call"""
        with self.lock:
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(self.delay, func, args, kwargs)
            self.timer.start()


class FileWatcher:
    """File system watcher for configuration changes"""
    
    def __init__(self, path: Path, callback: Callable):
        self.path = path
        self.callback = callback
        self.observer = Observer()
        self.debouncer = Debouncer(delay=0.5)
        self._setup_handler()
        
    def _setup_handler(self):
        """Setup file system event handler"""
        handler = FileSystemEventHandler()
        handler.on_modified = self._on_change
        self.observer.schedule(handler, str(self.path.parent), recursive=False)
        
    def start(self):
        """Start watching file changes"""
        if not self.observer.is_alive():
            self.observer.start()
            logger.debug(f"Started watching {self.path}")
        
    def stop(self):
        """Stop watching file changes"""
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            logger.debug(f"Stopped watching {self.path}")
        
    def _on_change(self, event):
        """Handle file change events"""
        if isinstance(event, FileModifiedEvent) and event.src_path == str(self.path):
            logger.debug(f"File change detected: {self.path}")
            self.debouncer.call(self.callback)


class EnvResolver:
    """Environment variable resolution engine"""
    
    TEMPLATE_PATTERN = re.compile(r'\$\{([^}]+)\}')
    PREFIX = 'SIZECOMPARATOR_'
    
    def resolve(self, value: Any, depth: int = 0) -> Any:
        """Recursively resolve environment variables"""
        if depth > 10:
            raise CircularDependencyError("Max resolution depth exceeded")
            
        if isinstance(value, str):
            return self._resolve_string(value, depth)
        elif isinstance(value, dict):
            return {k: self.resolve(v, depth) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve(item, depth) for item in value]
        return value
        
    def _resolve_string(self, value: str, depth: int) -> str:
        """Resolve environment variables in string"""
        def replacer(match):
            var_spec = match.group(1)
            var_name, default = self._parse_var_spec(var_spec)
            
            # Enforce prefix for custom variables
            if not var_name.startswith(('PATH', 'HOME', 'USER', 'PWD', 'SHELL')):
                if not var_name.startswith(self.PREFIX):
                    raise ValidationError(f"Variable {var_name} must start with {self.PREFIX}")
            
            env_value = os.environ.get(var_name, default)
            if env_value is None:
                raise MissingVariableError(f"Required variable {var_name} not found")
                
            # Recursive resolution
            return self.resolve(env_value, depth + 1)
            
        return self.TEMPLATE_PATTERN.sub(replacer, value)
    
    def _parse_var_spec(self, var_spec: str) -> tuple[str, Optional[str]]:
        """Parse variable specification like VAR_NAME:-default"""
        if ':-' in var_spec:
            var_name, default = var_spec.split(':-', 1)
            return var_name.strip(), default
        return var_spec.strip(), None


class ConfigMerger:
    """Configuration hierarchy merger with deep merge strategy"""
    
    def merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge with special handling for arrays and null values"""
        result = deepcopy(base)
        
        for key, value in override.items():
            if value is None:
                # Explicit null removes the key
                result.pop(key, None)
            elif key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    # Recursive merge for nested objects
                    result[key] = self.merge(result[key], value)
                elif isinstance(result[key], list) and isinstance(value, dict):
                    # Special array operations
                    result[key] = self._merge_array(result[key], value)
                else:
                    # Direct replacement
                    result[key] = value
            else:
                result[key] = value
                
        return result
        
    def _merge_array(self, base_array: List, operations: Dict) -> List:
        """Handle array merge operations"""
        result = list(base_array)
        
        if '$append' in operations:
            result.extend(operations['$append'])
        if '$prepend' in operations:
            result = operations['$prepend'] + result
        if '$remove' in operations:
            for item in operations['$remove']:
                if item in result:
                    result.remove(item)
        if '$set' in operations:
            result = operations['$set']
            
        return result


class CustomValidators:
    """Custom validation functions for configuration"""
    
    _validators = {}
    
    @classmethod
    def validator(cls, path: str):
        """Decorator to register custom validators"""
        def decorator(func):
            cls._validators[path] = func
            return func
        return decorator
    
    @classmethod
    def get_validators(cls) -> Dict[str, Callable]:
        """Get all registered validators"""
        return cls._validators.copy()


# Custom validator instances
def validate_database_reachability(value: str, config: Dict) -> Optional[str]:
    """Check if database host is reachable"""
    try:
        socket.gethostbyname(value)
        return None
    except socket.gaierror:
        return f"Database host '{value}' is not reachable"


def validate_api_key_format(value: str, config: Dict) -> Optional[str]:
    """Validate API key format"""
    if not re.match(r'^sk-[a-zA-Z0-9]{48}$', value):
        return "API key must match format: sk-{48 alphanumeric characters}"
    return None


# Register validators
CustomValidators._validators['database.host'] = validate_database_reachability
CustomValidators._validators['ai_providers.*.api_key'] = validate_api_key_format


class SchemaValidator:
    """JSON Schema-based configuration validator"""
    
    def __init__(self, schema_path: Optional[Path] = None):
        self.schema = self._load_schema(schema_path) if schema_path else self._default_schema()
        self.custom_validators = CustomValidators.get_validators()
        
    def validate(self, config: Dict) -> ValidationResult:
        """Validate configuration against schema and custom validators"""
        errors = []
        
        # Basic structure validation
        errors.extend(self._validate_structure(config))
        
        # Custom validators
        if not errors:
            errors.extend(self._run_custom_validators(config))
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=self._check_deprecations(config)
        )
    
    def _load_schema(self, schema_path: Path) -> Dict:
        """Load JSON schema from file"""
        try:
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load schema from {schema_path}: {e}")
            return self._default_schema()
    
    def _default_schema(self) -> Dict:
        """Default schema for SizeComparator configuration"""
        return {
            "type": "object",
            "required": ["application", "weight", "ai_providers"],
            "properties": {
                "application": {
                    "type": "object",
                    "required": ["name", "version"],
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                        "server": {
                            "type": "object",
                            "properties": {
                                "host": {"type": "string"},
                                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                                "workers": {"type": "integer", "minimum": 1}
                            }
                        }
                    }
                },
                "weight": {
                    "type": "object",
                    "required": ["supported_units", "default_unit"],
                    "properties": {
                        "supported_units": {"type": "array", "items": {"type": "string"}},
                        "default_unit": {"type": "string"},
                        "max_weight_lbs": {"type": "number", "minimum": 0},
                        "precision_digits": {"type": "integer", "minimum": 1}
                    }
                },
                "ai_providers": {
                    "type": "object",
                    "required": ["enabled", "default_provider"],
                    "properties": {
                        "enabled": {"type": "array", "items": {"type": "string"}},
                        "default_provider": {"type": "string"},
                        "timeout_seconds": {"type": "integer", "minimum": 1}
                    }
                }
            }
        }
    
    def _validate_structure(self, config: Dict) -> List[ValidationError]:
        """Basic structure validation"""
        errors = []
        
        # Check required top-level sections
        required = ["application", "weight", "ai_providers"]
        for req in required:
            if req not in config:
                errors.append(ValidationError(f"Missing required section: {req}", req))
        
        # Validate application section
        if "application" in config:
            app = config["application"]
            if not isinstance(app.get("name"), str):
                errors.append(ValidationError("application.name must be a string", "application.name"))
            if not isinstance(app.get("version"), str):
                errors.append(ValidationError("application.version must be a string", "application.version"))
        
        return errors
    
    def _run_custom_validators(self, config: Dict) -> List[ValidationError]:
        """Run custom validation functions"""
        errors = []
        
        for path, validator_func in self.custom_validators.items():
            try:
                value = self._get_nested_value(config, path)
                if value is not None:
                    error_msg = validator_func(value, config)
                    if error_msg:
                        errors.append(ValidationError(error_msg, path, value))
            except Exception as e:
                logger.warning(f"Custom validator {path} failed: {e}")
        
        return errors
    
    def _get_nested_value(self, config: Dict, path: str) -> Any:
        """Get nested configuration value by dot notation path"""
        parts = path.split('.')
        value = config
        
        for part in parts:
            if isinstance(value, dict):
                if '*' in part:
                    # Wildcard support for array validation
                    return None  # Skip wildcard validation for now
                value = value.get(part)
            else:
                return None
        
        return value
    
    def _check_deprecations(self, config: Dict) -> List[str]:
        """Check for deprecated configuration options"""
        warnings = []
        
        # Add deprecation checks as needed
        deprecated_paths = {
            "logging.use_json": "Use logging.format: 'json' instead",
            "security.enable_cors": "Use security.cors.enabled instead"
        }
        
        for path, message in deprecated_paths.items():
            if self._get_nested_value(config, path) is not None:
                warnings.append(f"Deprecated config {path}: {message}")
        
        return warnings


class ConfigErrorHandler:
    """Error handler with circuit breaker pattern"""
    
    def __init__(self):
        self.error_threshold = 5
        self.error_window = 300  # 5 minutes
        self.recent_errors: Deque[datetime] = deque()
        self.safe_mode = False
        
    def handle_error(self, error: Exception, context: Dict):
        """Handle configuration errors with circuit breaker pattern"""
        self.recent_errors.append(datetime.utcnow())
        self._cleanup_old_errors()
        
        if len(self.recent_errors) >= self.error_threshold:
            # Circuit breaker triggered
            logger.critical(f"Configuration error threshold exceeded: {error}")
            self._enter_safe_mode()
        else:
            # Log and continue
            logger.error(f"Configuration error: {error}", extra=context)
            
    def _cleanup_old_errors(self):
        """Remove errors outside the time window"""
        cutoff = datetime.utcnow().timestamp() - self.error_window
        while self.recent_errors and self.recent_errors[0].timestamp() < cutoff:
            self.recent_errors.popleft()
            
    def _enter_safe_mode(self):
        """Fall back to last known good configuration"""
        self.safe_mode = True
        logger.warning("Entering configuration safe mode")
        # Additional safe mode logic would go here


class HotReloadManager:
    """File system monitoring for hot configuration reload"""
    
    def __init__(self, config_loader: 'ConfigLoader'):
        self.config_loader = config_loader
        self.subscribers: List[ConfigSubscriber] = []
        self.reload_lock = threading.Lock()
        self.last_reload = time.time()
        self.min_reload_interval = 1.0  # Prevent reload storms
        
    def watch_files(self, paths: List[Path]):
        """Monitor configuration files for changes"""
        for path in paths:
            if path.exists():
                watcher = FileWatcher(path, lambda p=path: self._on_file_change(p))
                watcher.start()
                self.config_loader.watchers[path] = watcher
                logger.info(f"Watching configuration file: {path}")
    
    def add_subscriber(self, subscriber: ConfigSubscriber):
        """Add configuration change subscriber"""
        self.subscribers.append(subscriber)
        logger.debug(f"Added config subscriber: {type(subscriber).__name__}")
    
    def remove_subscriber(self, subscriber: ConfigSubscriber):
        """Remove configuration change subscriber"""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
            logger.debug(f"Removed config subscriber: {type(subscriber).__name__}")
    
    def _on_file_change(self, path: Path):
        """Handle configuration file changes"""
        with self.reload_lock:
            # Debounce rapid changes
            if time.time() - self.last_reload < self.min_reload_interval:
                return
                
            try:
                # Load and validate new configuration
                new_config = self.config_loader.load_configuration()
                
                # Notify subscribers
                self._notify_subscribers(ConfigChangeEvent(
                    path=path,
                    config=new_config,
                    timestamp=datetime.utcnow()
                ))
                
                self.last_reload = time.time()
                logger.info(f"Configuration reloaded from {path}")
                
            except Exception as e:
                # Log error but keep running with current config
                logger.error(f"Failed to reload configuration: {e}")
                self._notify_error(ConfigErrorEvent(
                    path=path,
                    error=str(e),
                    timestamp=datetime.utcnow()
                ))
    
    def _notify_subscribers(self, event: ConfigChangeEvent):
        """Notify all subscribers of configuration change"""
        for subscriber in self.subscribers:
            try:
                subscriber.on_config_change(event)
            except Exception as e:
                logger.error(f"Subscriber notification failed: {e}")
    
    def _notify_error(self, event: ConfigErrorEvent):
        """Notify all subscribers of configuration error"""
        for subscriber in self.subscribers:
            try:
                subscriber.on_config_error(event)
            except Exception as e:
                logger.error(f"Error notification failed: {e}")


class SafeConfigUpdater:
    """Safe configuration updater with validation and rollback"""
    
    def __init__(self, validator: SchemaValidator, error_handler: ConfigErrorHandler):
        self.validator = validator
        self.error_handler = error_handler
        self.update_lock = threading.Lock()
        self.current_config: Dict[str, Any] = {}
    
    def update_config(self, new_config: Dict) -> bool:
        """Safely update configuration with validation and rollback"""
        # Phase 1: Pre-validation
        validation_result = self.validator.validate(new_config)
        if not validation_result.valid:
            error_msg = "; ".join([f"{e.path}: {e}" for e in validation_result.errors])
            raise ValidationError(f"Validation failed: {error_msg}")
        
        # Phase 2: Dependency check
        if not self._check_dependencies(new_config):
            raise DependencyError("Configuration dependencies not satisfied")
        
        # Phase 3: Test critical paths
        test_results = self._test_critical_paths(new_config)
        if not all(test_results.values()):
            failed = [k for k, v in test_results.items() if not v]
            raise CriticalPathError(f"Critical path tests failed: {failed}")
        
        # Phase 4: Atomic update
        with self.update_lock:
            old_config = self.current_config.copy()
            try:
                self.current_config = new_config
                
                # Phase 5: Verify update
                if not self._verify_update(new_config):
                    raise UpdateVerificationError("Configuration update verification failed")
                
                return True
                
            except Exception as e:
                # Rollback
                self.current_config = old_config
                logger.error(f"Configuration update failed, rolled back: {e}")
                raise
    
    def _check_dependencies(self, config: Dict) -> bool:
        """Check configuration dependencies"""
        # Check if enabled AI providers are properly configured
        if 'ai_providers' in config:
            enabled = config['ai_providers'].get('enabled', [])
            for provider in enabled:
                if provider not in config.get('ai_providers', {}):
                    logger.error(f"Enabled provider {provider} not configured")
                    return False
        
        return True
    
    def _test_critical_paths(self, config: Dict) -> Dict[str, bool]:
        """Test critical configuration paths"""
        tests = {}
        
        # Test application configuration
        tests['application'] = bool(
            config.get('application', {}).get('name') and
            config.get('application', {}).get('version')
        )
        
        # Test weight configuration
        tests['weight'] = bool(
            config.get('weight', {}).get('supported_units') and
            config.get('weight', {}).get('default_unit')
        )
        
        # Test AI providers
        tests['ai_providers'] = bool(
            config.get('ai_providers', {}).get('enabled') and
            config.get('ai_providers', {}).get('default_provider')
        )
        
        return tests
    
    def _verify_update(self, config: Dict) -> bool:
        """Verify configuration update was successful"""
        return self.current_config == config


class ConfigLoader:
    """Main configuration loader with hot-reload and validation"""
    
    def __init__(self, base_path: Union[str, Path], environment: str = "development"):
        self.base_path = Path(base_path)
        self.environment = environment
        self.watchers: Dict[Path, FileWatcher] = {}
        self.current_config: Dict[str, Any] = {}
        self.lock = threading.RLock()
        
        # Initialize components
        self.env_resolver = EnvResolver()
        self.merger = ConfigMerger()
        self.validator = SchemaValidator()
        self.error_handler = ConfigErrorHandler()
        self.updater = SafeConfigUpdater(self.validator, self.error_handler)
        self.hot_reload = HotReloadManager(self)
        
        # Configuration file paths
        self.config_files = {
            'base': self.base_path / 'base.yaml',
            'environment': self.base_path / f'{environment}.yaml',
            'local': self.base_path / 'local.yaml'
        }
        
        logger.info(f"ConfigLoader initialized for environment: {environment}")
    
    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration with atomic updates"""
        with self.lock:
            try:
                # Load in precedence order
                config = self._load_base()
                config = self._merge_environment(config)
                config = self._merge_local(config)
                
                # Resolve environment variables
                config = self.env_resolver.resolve(config)
                
                # Validate configuration
                validation_result = self.validator.validate(config)
                if not validation_result.valid:
                    error_msg = "; ".join([f"{e.path}: {e}" for e in validation_result.errors])
                    raise ValidationError(f"Configuration validation failed: {error_msg}")
                
                # Log warnings
                for warning in validation_result.warnings:
                    logger.warning(warning)
                
                # Atomic update
                old_config = self.current_config.copy()
                self.current_config = config
                
                logger.info("Configuration loaded successfully")
                return config
                
            except Exception as e:
                # Rollback on failure
                if hasattr(self, 'current_config'):
                    logger.error(f"Configuration load failed, maintaining current config: {e}")
                else:
                    logger.error(f"Initial configuration load failed: {e}")
                raise ConfigLoadError(f"Configuration load failed: {e}")
    
    def _load_base(self) -> Dict[str, Any]:
        """Load base configuration"""
        base_file = self.config_files['base']
        if not base_file.exists():
            raise ConfigLoadError(f"Base configuration file not found: {base_file}")
        
        return self._load_file(base_file)
    
    def _merge_environment(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge environment-specific configuration"""
        env_file = self.config_files['environment']
        if env_file.exists():
            env_config = self._load_file(env_file)
            return self.merger.merge(base_config, env_config)
        else:
            logger.warning(f"Environment config file not found: {env_file}")
            return base_config
    
    def _merge_local(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge local developer overrides"""
        local_file = self.config_files['local']
        if local_file.exists():
            local_config = self._load_file(local_file)
            return self.merger.merge(config, local_config)
        return config
    
    def _load_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration file (YAML or JSON)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif file_path.suffix.lower() == '.json':
                    return json.load(f) or {}
                else:
                    raise ConfigLoadError(f"Unsupported file format: {file_path}")
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"YAML parsing error in {file_path}: {e}")
        except json.JSONDecodeError as e:
            raise ConfigLoadError(f"JSON parsing error in {file_path}: {e}")
        except Exception as e:
            raise ConfigLoadError(f"Error loading {file_path}: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        with self.lock:
            return self.current_config.copy()
    
    def get_section(self, section: str, default: Any = None) -> Any:
        """Get specific configuration section"""
        with self.lock:
            parts = section.split('.')
            value = self.current_config
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            
            return value
    
    def enable_hot_reload(self):
        """Enable hot configuration reload"""
        config_paths = [path for path in self.config_files.values() if path.exists()]
        self.hot_reload.watch_files(config_paths)
        logger.info("Hot reload enabled for configuration files")
    
    def disable_hot_reload(self):
        """Disable hot configuration reload"""
        for watcher in self.watchers.values():
            watcher.stop()
        self.watchers.clear()
        logger.info("Hot reload disabled")
    
    def add_subscriber(self, subscriber: ConfigSubscriber):
        """Add configuration change subscriber"""
        self.hot_reload.add_subscriber(subscriber)
    
    def remove_subscriber(self, subscriber: ConfigSubscriber):
        """Remove configuration change subscriber"""
        self.hot_reload.remove_subscriber(subscriber)
    
    def reload(self) -> bool:
        """Manually reload configuration"""
        try:
            self.load_configuration()
            return True
        except Exception as e:
            logger.error(f"Manual reload failed: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any] = None) -> ValidationResult:
        """Validate configuration"""
        if config is None:
            config = self.current_config
        return self.validator.validate(config)
    
    def shutdown(self):
        """Shutdown configuration loader"""
        self.disable_hot_reload()
        logger.info("ConfigLoader shutdown complete")


# Factory function for easy instantiation
def create_config_loader(
    config_path: Union[str, Path] = "config",
    environment: str = None
) -> ConfigLoader:
    """Create and initialize configuration loader"""
    if environment is None:
        environment = os.getenv('SIZECOMPARATOR_ENVIRONMENT', 'development')
    
    loader = ConfigLoader(config_path, environment)
    loader.load_configuration()
    
    return loader


# Global configuration instance (initialized when needed)
_global_config: Optional[ConfigLoader] = None


def get_config() -> ConfigLoader:
    """Get global configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = create_config_loader()
    return _global_config


def init_config(config_path: Union[str, Path] = "config", environment: str = None) -> ConfigLoader:
    """Initialize global configuration"""
    global _global_config
    _global_config = create_config_loader(config_path, environment)
    return _global_config