# Configuration Loader Specification

## Overview

The Configuration Loader system provides a robust, hot-reloadable configuration management framework for SizeComparator. It supports YAML and JSON formats, environment variable templating, hierarchical configuration merging, and atomic updates with rollback capabilities.

## 1. File Loading Architecture

### Configuration Discovery

The loader automatically discovers and loads configuration files in a specific order:

```yaml
# Loading precedence (highest to lowest)
1. config/local.yaml      # Developer overrides (gitignored)
2. config/{env}.yaml      # Environment-specific (dev, staging, prod)
3. config/base.yaml       # Base configuration defaults
```

### File Loading Implementation

```python
class ConfigLoader:
    def __init__(self, base_path: Path, environment: str):
        self.base_path = base_path
        self.environment = environment
        self.watchers: Dict[Path, FileWatcher] = {}
        self.current_config: Dict[str, Any] = {}
        self.lock = threading.RLock()
        
    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration with atomic updates"""
        with self.lock:
            try:
                # Load in precedence order
                config = self._load_base()
                config = self._merge_environment(config)
                config = self._merge_local(config)
                
                # Validate before applying
                self._validate_config(config)
                
                # Atomic update
                old_config = self.current_config
                self.current_config = config
                
                return config
            except Exception as e:
                # Rollback on failure
                self.current_config = old_config
                raise ConfigLoadError(f"Configuration load failed: {e}")
```

### File Watching System

```python
class FileWatcher:
    def __init__(self, path: Path, callback: Callable):
        self.path = path
        self.callback = callback
        self.observer = Observer()
        self.debouncer = Debouncer(delay=500)  # 500ms debounce
        
    def start(self):
        handler = FileSystemEventHandler()
        handler.on_modified = self._on_change
        self.observer.schedule(handler, str(self.path.parent))
        self.observer.start()
        
    def _on_change(self, event):
        if event.src_path == str(self.path):
            self.debouncer.call(self.callback)
```

### Atomic Update Mechanism

Configuration updates are performed atomically using a copy-on-write strategy:

1. Load new configuration into temporary structure
2. Validate entire configuration
3. If valid, swap references atomically
4. If invalid, maintain current configuration
5. Notify listeners of successful updates

## 2. Environment Variable Resolution

### Template Syntax

Environment variables use the format `${VAR_NAME:-default_value}`:

```yaml
# config/base.yaml
database:
  host: ${DB_HOST:-localhost}
  port: ${DB_PORT:-5432}
  name: ${DB_NAME}  # Required, no default
  
api:
  url: ${API_BASE_URL:-https://api.example.com}
  key: ${SIZECOMPARATOR_API_KEY}  # Enforced prefix
```

### Resolution Engine

```python
class EnvResolver:
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
        def replacer(match):
            var_spec = match.group(1)
            var_name, default = self._parse_var_spec(var_spec)
            
            # Enforce prefix for custom variables
            if not var_name.startswith(('PATH', 'HOME', 'USER')):
                if not var_name.startswith(self.PREFIX):
                    raise ValidationError(f"Variable {var_name} must start with {self.PREFIX}")
            
            env_value = os.environ.get(var_name, default)
            if env_value is None:
                raise MissingVariableError(f"Required variable {var_name} not found")
                
            # Recursive resolution
            return self.resolve(env_value, depth + 1)
            
        return self.TEMPLATE_PATTERN.sub(replacer, value)
```

### Type Conversion

Environment variables are automatically converted to appropriate types:

```python
def convert_type(value: str, schema_type: str) -> Any:
    """Convert string values to schema-defined types"""
    converters = {
        'integer': int,
        'number': float,
        'boolean': lambda v: v.lower() in ('true', '1', 'yes'),
        'array': lambda v: [i.strip() for i in v.split(',')],
        'object': json.loads
    }
    
    if schema_type in converters:
        try:
            return converters[schema_type](value)
        except ValueError as e:
            raise TypeConversionError(f"Cannot convert '{value}' to {schema_type}: {e}")
    
    return value  # Default to string
```

## 3. Configuration Hierarchy Management

### Merge Strategy

Configuration files are merged using a deep merge strategy with explicit rules:

```python
class ConfigMerger:
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
```

### Configuration Structure

```yaml
# config/base.yaml - Base defaults
app:
  name: SizeComparator
  version: 1.0.0
  log_level: INFO
  
database:
  pool_size: 10
  timeout: 30
  
services:
  - name: api
    enabled: true
  - name: worker
    enabled: true

# config/dev.yaml - Development overrides
app:
  log_level: DEBUG
  
database:
  host: localhost
  pool_size: 5
  
services:
  $append:
    - name: debugger
      enabled: true

# config/local.yaml - Developer overrides (gitignored)
app:
  custom_feature: true
  
database:
  host: docker.local
```

## 4. JSON Schema Validation Framework

### Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["app", "database"],
  "properties": {
    "app": {
      "type": "object",
      "required": ["name", "version"],
      "properties": {
        "name": {"type": "string"},
        "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
        "log_level": {
          "type": "string",
          "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]
        }
      }
    },
    "database": {
      "type": "object",
      "required": ["host", "port"],
      "properties": {
        "host": {"type": "string", "format": "hostname"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "pool_size": {"type": "integer", "minimum": 1, "maximum": 100}
      }
    }
  }
}
```

### Validation Implementation

```python
class SchemaValidator:
    def __init__(self, schema_path: Path):
        self.schema = self._load_schema(schema_path)
        self.validator = Draft7Validator(self.schema)
        self.custom_validators = {}
        
    def validate(self, config: Dict) -> ValidationResult:
        """Validate configuration against schema"""
        errors = []
        
        # JSON Schema validation
        for error in self.validator.iter_errors(config):
            errors.append(ValidationError(
                path='.'.join(str(p) for p in error.path),
                message=error.message,
                value=error.instance
            ))
        
        # Custom validators
        if not errors:
            errors.extend(self._run_custom_validators(config))
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=self._check_deprecations(config)
        )
```

### Custom Validators

```python
class CustomValidators:
    @validator('database.host')
    def validate_database_reachability(self, value: str, config: Dict) -> Optional[str]:
        """Check if database host is reachable"""
        try:
            socket.gethostbyname(value)
            return None
        except socket.gaierror:
            return f"Database host '{value}' is not reachable"
    
    @validator('api.key')
    def validate_api_key_format(self, value: str, config: Dict) -> Optional[str]:
        """Validate API key format"""
        if not re.match(r'^sk-[a-zA-Z0-9]{48}$', value):
            return "API key must match format: sk-{48 alphanumeric characters}"
        return None
    
    @validator('services')
    def validate_service_dependencies(self, services: List[Dict], config: Dict) -> Optional[str]:
        """Ensure service dependencies are satisfied"""
        enabled_services = {s['name'] for s in services if s.get('enabled', True)}
        
        for service in services:
            deps = service.get('depends_on', [])
            missing = set(deps) - enabled_services
            if missing:
                return f"Service '{service['name']}' depends on disabled services: {missing}"
        
        return None
```

## 5. Hot-Reload and Error Handling

### File System Monitoring

```python
class HotReloadManager:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.subscribers: List[ConfigSubscriber] = []
        self.reload_lock = threading.Lock()
        self.last_reload = time.time()
        self.min_reload_interval = 1.0  # Prevent reload storms
        
    def watch_files(self, paths: List[Path]):
        """Monitor configuration files for changes"""
        for path in paths:
            if path.exists():
                watcher = FileWatcher(path, lambda: self._on_file_change(path))
                watcher.start()
                self.config_loader.watchers[path] = watcher
    
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
```

### Safe Update Protocol

```python
class SafeConfigUpdater:
    def update_config(self, new_config: Dict) -> bool:
        """Safely update configuration with validation and rollback"""
        # Phase 1: Pre-validation
        validation_result = self.validator.validate(new_config)
        if not validation_result.valid:
            raise ValidationError(validation_result.errors)
        
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
            old_config = self.current_config
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
```

### Change Notification System

```python
class ConfigSubscriber(ABC):
    @abstractmethod
    def on_config_change(self, event: ConfigChangeEvent):
        """Handle configuration changes"""
        pass
    
    @abstractmethod
    def on_config_error(self, event: ConfigErrorEvent):
        """Handle configuration errors"""
        pass

class ComponentConfigAdapter(ConfigSubscriber):
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
```

### Error Recovery

```python
class ConfigErrorHandler:
    def __init__(self):
        self.error_threshold = 5
        self.error_window = 300  # 5 minutes
        self.recent_errors: Deque[datetime] = deque()
        
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
            
    def _enter_safe_mode(self):
        """Fall back to last known good configuration"""
        logger.warning("Entering configuration safe mode")
        # Disable hot reload
        # Use cached valid configuration
        # Alert administrators
```

## Integration Points

- **CONFIG_SYSTEM_SPEC**: Implements the configuration loading layer of the overall system
- **ENV_MANAGER_SPEC**: Leverages environment variable processing capabilities
- **ERROR_MONITORING_SPEC**: Reports configuration errors and validation failures
- **Component Integration**: All components receive configuration through the subscriber pattern

## Performance Considerations

- Configuration validation results are cached for repeated checks
- File watching uses efficient OS-level notifications (inotify/FSEvents)
- Debouncing prevents reload storms during rapid file changes
- Atomic updates minimize lock contention
- Lazy loading for optional configuration sections