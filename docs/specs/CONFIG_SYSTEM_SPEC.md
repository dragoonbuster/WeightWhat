# Configuration Management System Specification

## 1. Overview

The Configuration Management System for SizeComparator provides a robust, file-based configuration framework supporting runtime management, hot-reload capabilities, and zero-deployment updates. This specification defines the architecture, implementation details, and interfaces for managing application configuration, prompt templates, and runtime settings.

### 1.1 Goals
- Enable configuration changes without code deployment
- Support hierarchical configuration with environment-specific overrides
- Provide template-based prompt management with variable substitution
- Implement secure configuration handling with validation
- Support A/B testing through configuration variants
- Enable real-time configuration updates via hot-reload
- Prevent runtime errors through strict schema validation
- Ensure hot-reload safety with atomic updates and rollback

### 1.2 Scope
This specification covers:
- Configuration file formats (YAML/JSON) with exact schemas
- Environment variable integration with SIZECOMPARATOR_* prefix
- Prompt template management for AI_PROVIDER_SPEC
- Comprehensive validation framework
- Safe hot-reload implementation
- Security requirements
- Component interfaces with type safety

## 2. Configuration Structure

### 2.1 File Hierarchy
```
config/
├── base/
│   ├── app.yaml              # Base application config
│   ├── prompts.yaml          # Base prompt templates
│   └── features.yaml         # Feature flags
├── environments/
│   ├── development.yaml      # Dev overrides
│   ├── staging.yaml          # Staging overrides
│   └── production.yaml       # Production overrides
├── variants/                 # A/B test configurations
│   ├── experiment_a.yaml
│   └── experiment_b.yaml
└── schema/
    ├── app.schema.json       # JSON Schema for validation
    └── prompts.schema.json   # Prompt template schema
```

### 2.2 Configuration Schema
Base configuration structure with EXACT schemas:

#### 2.2.1 Application Configuration (app.yaml)
```yaml
# app.yaml - EXACT SCHEMA
application:
  name: "SizeComparator"                    # string, required
  version: "${SIZECOMPARATOR_VERSION:-1.0.0}" # string, semver format
  environment: "${SIZECOMPARATOR_ENV:-development}" # enum: development|staging|production
  
api:
  providers:
    openai:
      endpoint: "${SIZECOMPARATOR_OPENAI_ENDPOINT}" # string, required, valid URL
      api_key: "${SIZECOMPARATOR_OPENAI_API_KEY}"   # string, required, sensitive
      model: "${SIZECOMPARATOR_OPENAI_MODEL:-gpt-4}" # string, required
      timeout_seconds: 30                            # integer, range: 5-300
      max_tokens: 4096                               # integer, range: 100-128000
      temperature: 0.7                               # float, range: 0.0-2.0
      retry:
        max_attempts: 3                              # integer, range: 1-10
        initial_delay_ms: 1000                       # integer, range: 100-10000
        max_delay_ms: 30000                          # integer, range: 1000-60000
        exponential_base: 2                          # float, range: 1.1-3.0
    
    anthropic:
      endpoint: "${SIZECOMPARATOR_ANTHROPIC_ENDPOINT:-https://api.anthropic.com}" 
      api_key: "${SIZECOMPARATOR_ANTHROPIC_API_KEY}"
      model: "${SIZECOMPARATOR_ANTHROPIC_MODEL:-claude-3-opus-20240229}"
      timeout_seconds: 30
      max_tokens: 4096
      
comparison:
  max_objects: 100                          # integer, range: 2-1000
  default_unit: "meters"                    # enum: meters|feet|kilometers|miles
  precision: 2                              # integer, range: 0-6
  dimension_analysis:
    enabled: true                           # boolean
    include_volume: true                    # boolean
    include_surface_area: false             # boolean
  
cache:
  provider: "redis"                         # enum: redis|memory|dynamodb
  connection:
    host: "${SIZECOMPARATOR_REDIS_HOST:-localhost}"  # string
    port: "${SIZECOMPARATOR_REDIS_PORT:-6379}"       # integer, range: 1-65535
    password: "${SIZECOMPARATOR_REDIS_PASSWORD}"     # string, optional, sensitive
    db: 0                                             # integer, range: 0-15
    tls:
      enabled: "${SIZECOMPARATOR_REDIS_TLS:-false}"  # boolean
      ca_cert: "${SIZECOMPARATOR_REDIS_CA_CERT}"     # string, file path
  settings:
    ttl_seconds: 3600                       # integer, range: 60-86400
    max_entries: 10000                      # integer, range: 100-1000000
    eviction_policy: "lru"                  # enum: lru|lfu|ttl
    
monitoring:
  metrics:
    enabled: true                           # boolean
    provider: "prometheus"                  # enum: prometheus|cloudwatch|datadog
    port: 9090                             # integer, range: 1024-65535
    path: "/metrics"                       # string, URL path
  logging:
    level: "${SIZECOMPARATOR_LOG_LEVEL:-info}"  # enum: debug|info|warn|error
    format: "json"                              # enum: json|text
    output: "stdout"                            # enum: stdout|file|syslog
    file_path: "${SIZECOMPARATOR_LOG_FILE}"     # string, required if output=file
  tracing:
    enabled: false                              # boolean
    provider: "jaeger"                          # enum: jaeger|zipkin|otlp
    endpoint: "${SIZECOMPARATOR_TRACE_ENDPOINT}" # string, valid URL
    
features:
  enhanced_visualizations: true             # boolean
  multi_language_support: false             # boolean
  real_time_updates: true                   # boolean
  experimental:
    ai_suggestions: false                   # boolean
    3d_rendering: false                     # boolean
```

### 2.3 Environment Variable Standards
All environment variables MUST follow these naming conventions:
- Prefix: `SIZECOMPARATOR_`
- Format: `SIZECOMPARATOR_<COMPONENT>_<PROPERTY>`
- Examples:
  - `SIZECOMPARATOR_API_TIMEOUT`
  - `SIZECOMPARATOR_OPENAI_API_KEY`
  - `SIZECOMPARATOR_REDIS_HOST`
  - `SIZECOMPARATOR_LOG_LEVEL`

Reserved environment variables:
- `SIZECOMPARATOR_ENV` - Runtime environment (development|staging|production)
- `SIZECOMPARATOR_CONFIG_DIR` - Configuration directory path
- `SIZECOMPARATOR_HOT_RELOAD` - Enable/disable hot reload (true|false)
- `SIZECOMPARATOR_CONFIG_VALIDATION` - Validation mode (strict|warn|off)

## 3. Prompt Template System for AI_PROVIDER_SPEC

### 3.1 Template Structure (prompts.yaml)
EXACT schema for AI provider prompt templates:

```yaml
# prompts.yaml - EXACT SCHEMA
version: "1.0"                              # string, required, semver format
metadata:
  created_by: "system"                      # string, required
  created_at: "2024-01-15T10:00:00Z"      # string, required, ISO 8601 format
  schema_version: "1.0"                    # string, required, semver format
  
templates:
  size_comparison_basic:
    id: "size_comp_v1"                     # string, required, unique
    provider: "openai"                     # enum: openai|anthropic|custom
    model_requirements:
      min_context_length: 4096             # integer, minimum context window
      supports_function_calling: false     # boolean
      supports_vision: false               # boolean
    
    prompt:
      system: |                            # string, required, system prompt
        You are a size comparison expert. 
        Provide accurate, scientific comparisons between objects.
        Always include dimensional analysis when possible.
        
      user_template: |                     # string, required, user prompt template
        Compare the size of {{object1}} to {{object2}}.
        
        Requirements:
        - Use {{unit}} as the primary measurement unit
        - Precision: {{precision}} decimal places
        {{#if include_volume}}
        - Include volume calculations
        {{/if}}
        {{#if include_surface_area}}
        - Include surface area calculations
        {{/if}}
        
        Format your response as JSON with the following structure:
        {
          "comparison": "string",
          "ratio": number,
          "details": {
            "object1_dimensions": {},
            "object2_dimensions": {},
            "analysis": "string"
          }
        }
    
    variables:
      - name: object1                      # string, required
        type: string                       # enum: string|number|boolean|array|object
        required: true                     # boolean, required
        validation:
          min_length: 1                    # integer, for strings
          max_length: 200                  # integer, for strings
          pattern: "^[a-zA-Z0-9\\s\\-_]+$" # string, regex pattern
        description: "First object to compare"
        
      - name: object2
        type: string
        required: true
        validation:
          min_length: 1
          max_length: 200
          pattern: "^[a-zA-Z0-9\\s\\-_]+$"
        description: "Second object to compare"
        
      - name: unit
        type: string
        required: false
        default: "meters"
        validation:
          enum: ["meters", "feet", "kilometers", "miles", "centimeters", "inches"]
        description: "Measurement unit for comparison"
        
      - name: precision
        type: number
        required: false
        default: 2
        validation:
          minimum: 0
          maximum: 6
        description: "Decimal precision for measurements"
        
      - name: include_volume
        type: boolean
        required: false
        default: true
        description: "Include volume calculations in comparison"
        
      - name: include_surface_area
        type: boolean
        required: false
        default: false
        description: "Include surface area calculations"
    
    output_schema:                         # JSON Schema for response validation
      type: object
      required: ["comparison", "ratio", "details"]
      properties:
        comparison:
          type: string
          minLength: 10
          maxLength: 500
        ratio:
          type: number
          minimum: 0
        details:
          type: object
          required: ["analysis"]
          properties:
            object1_dimensions:
              type: object
            object2_dimensions:
              type: object
            analysis:
              type: string
              minLength: 50
    
    examples:                              # Array of test examples
      - input:
          object1: "basketball"
          object2: "ping pong ball"
          unit: "centimeters"
          precision: 2
        expected_output:
          comparison: "A basketball is significantly larger than a ping pong ball"
          ratio: 343.0
          details:
            analysis: "Volume comparison shows basketball is 343 times larger"
            
    metadata:
      version: "1.0"                      # string, required, template version
      author: "system"                    # string, required
      last_modified: "2024-01-15T10:00:00Z" # string, required, ISO 8601
      tags: ["size", "comparison", "basic"] # array of strings
      usage_stats:
        total_calls: 0                    # integer, usage tracking
        success_rate: 0.0                 # float, success percentage
        avg_response_time_ms: 0           # integer, performance metric
      
  size_comparison_detailed:
    # Similar structure for detailed comparisons
    id: "size_comp_detailed_v1"
    # ... full schema definition
    
  ai_suggestion_prompt:
    id: "ai_suggest_v1"
    provider: "anthropic"
    # ... template for AI suggestions feature
```

### 3.2 Template Processing Rules
- **Variable Substitution**: Handlebars-style `{{variable}}` syntax
- **Conditionals**: `{{#if condition}}...{{/if}}`
- **Loops**: `{{#each array}}...{{/each}}`
- **Helpers**: Built-in functions for formatting
  - `{{format_number value precision}}`
  - `{{uppercase text}}`
  - `{{lowercase text}}`
  - `{{trim text}}`
  - `{{default value fallback}}`
- **Escaping**: `\{{literal}}` for literal braces
- **Partials**: `{{>partial_name}}` for reusable components

### 3.3 AI Provider Integration
Templates MUST specify provider-specific configurations:

```yaml
provider_configs:
  openai:
    api_version: "2023-12-01"
    temperature_range: [0.0, 2.0]
    max_tokens_limit: 128000
    supported_models: ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]
    
  anthropic:
    api_version: "2023-06-01"
    temperature_range: [0.0, 1.0]
    max_tokens_limit: 200000
    supported_models: ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
    
  custom:
    # Configuration for custom AI providers
    endpoint_template: "{{base_url}}/v1/chat/completions"
    auth_header: "Bearer {{api_key}}"
    request_format: "openai_compatible"
```

### 3.4 Template Validation Framework
STRICT validation rules to prevent runtime errors:

1. **Syntax Validation**:
   - Valid Handlebars syntax
   - Balanced braces and conditionals
   - No undefined helpers or partials

2. **Variable Validation**:
   - All template variables defined in schema
   - Required variables marked appropriately
   - Type constraints enforced
   - Range/pattern validation applied

3. **Provider Compatibility**:
   - Model requirements satisfied
   - Token limits respected
   - API version compatibility

4. **Output Validation**:
   - Response matches output_schema
   - Required fields present
   - Data types correct

5. **Security Validation**:
   - No template injection vulnerabilities
   - Sanitized variable content
   - Safe helper functions only

## 4. Comprehensive Validation Framework

### 4.1 JSON Schema Definitions
EXACT schemas for preventing runtime errors:

#### 4.1.1 Application Configuration Schema (app.schema.json)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://sizecomparator.com/schemas/app.schema.json",
  "title": "SizeComparator Application Configuration",
  "type": "object",
  "required": ["application", "api", "comparison", "cache", "monitoring", "features"],
  "properties": {
    "application": {
      "type": "object",
      "required": ["name", "version", "environment"],
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^[A-Za-z][A-Za-z0-9]*$",
          "minLength": 1,
          "maxLength": 50
        },
        "version": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+\\.\\d+(-[a-zA-Z0-9]+)?$"
        },
        "environment": {
          "type": "string",
          "enum": ["development", "staging", "production"]
        }
      }
    },
    "api": {
      "type": "object",
      "required": ["providers"],
      "properties": {
        "providers": {
          "type": "object",
          "minProperties": 1,
          "properties": {
            "openai": {
              "type": "object",
              "required": ["endpoint", "api_key", "model"],
              "properties": {
                "endpoint": {
                  "type": "string",
                  "format": "uri",
                  "pattern": "^https://"
                },
                "api_key": {
                  "type": "string",
                  "minLength": 10,
                  "pattern": "^[A-Za-z0-9\\-_]+$"
                },
                "model": {
                  "type": "string",
                  "enum": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"]
                },
                "timeout_seconds": {
                  "type": "integer",
                  "minimum": 5,
                  "maximum": 300
                },
                "max_tokens": {
                  "type": "integer",
                  "minimum": 100,
                  "maximum": 128000
                },
                "temperature": {
                  "type": "number",
                  "minimum": 0.0,
                  "maximum": 2.0
                },
                "retry": {
                  "type": "object",
                  "required": ["max_attempts"],
                  "properties": {
                    "max_attempts": {
                      "type": "integer",
                      "minimum": 1,
                      "maximum": 10
                    },
                    "initial_delay_ms": {
                      "type": "integer",
                      "minimum": 100,
                      "maximum": 10000
                    },
                    "max_delay_ms": {
                      "type": "integer",
                      "minimum": 1000,
                      "maximum": 60000
                    },
                    "exponential_base": {
                      "type": "number",
                      "minimum": 1.1,
                      "maximum": 3.0
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "comparison": {
      "type": "object",
      "required": ["max_objects", "default_unit", "precision"],
      "properties": {
        "max_objects": {
          "type": "integer",
          "minimum": 2,
          "maximum": 1000
        },
        "default_unit": {
          "type": "string",
          "enum": ["meters", "feet", "kilometers", "miles", "centimeters", "inches"]
        },
        "precision": {
          "type": "integer",
          "minimum": 0,
          "maximum": 6
        },
        "dimension_analysis": {
          "type": "object",
          "properties": {
            "enabled": {"type": "boolean"},
            "include_volume": {"type": "boolean"},
            "include_surface_area": {"type": "boolean"}
          }
        }
      }
    },
    "cache": {
      "type": "object",
      "required": ["provider", "connection", "settings"],
      "properties": {
        "provider": {
          "type": "string",
          "enum": ["redis", "memory", "dynamodb"]
        },
        "connection": {
          "type": "object",
          "allOf": [
            {
              "if": {"properties": {"../provider": {"const": "redis"}}},
              "then": {
                "required": ["host", "port"],
                "properties": {
                  "host": {"type": "string", "minLength": 1},
                  "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                  "password": {"type": "string"},
                  "db": {"type": "integer", "minimum": 0, "maximum": 15}
                }
              }
            }
          ]
        }
      }
    }
  }
}
```

#### 4.1.2 Prompt Template Schema (prompts.schema.json)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://sizecomparator.com/schemas/prompts.schema.json",
  "title": "SizeComparator Prompt Templates",
  "type": "object",
  "required": ["version", "metadata", "templates"],
  "properties": {
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$"
    },
    "metadata": {
      "type": "object",
      "required": ["created_by", "created_at", "schema_version"],
      "properties": {
        "created_by": {"type": "string", "minLength": 1},
        "created_at": {"type": "string", "format": "date-time"},
        "schema_version": {"type": "string", "pattern": "^\\d+\\.\\d+$"}
      }
    },
    "templates": {
      "type": "object",
      "patternProperties": {
        "^[a-z][a-z0-9_]*$": {
          "type": "object",
          "required": ["id", "provider", "prompt", "variables", "output_schema", "metadata"],
          "properties": {
            "id": {
              "type": "string",
              "pattern": "^[a-z][a-z0-9_]*_v\\d+$"
            },
            "provider": {
              "type": "string",
              "enum": ["openai", "anthropic", "custom"]
            },
            "model_requirements": {
              "type": "object",
              "properties": {
                "min_context_length": {"type": "integer", "minimum": 1024},
                "supports_function_calling": {"type": "boolean"},
                "supports_vision": {"type": "boolean"}
              }
            },
            "prompt": {
              "type": "object",
              "required": ["system", "user_template"],
              "properties": {
                "system": {"type": "string", "minLength": 10},
                "user_template": {"type": "string", "minLength": 10}
              }
            },
            "variables": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["name", "type", "required"],
                "properties": {
                  "name": {
                    "type": "string",
                    "pattern": "^[a-z][a-z0-9_]*$"
                  },
                  "type": {
                    "type": "string",
                    "enum": ["string", "number", "boolean", "array", "object"]
                  },
                  "required": {"type": "boolean"},
                  "default": {},
                  "validation": {
                    "type": "object",
                    "properties": {
                      "min_length": {"type": "integer", "minimum": 0},
                      "max_length": {"type": "integer", "minimum": 1},
                      "pattern": {"type": "string"},
                      "enum": {"type": "array"},
                      "minimum": {"type": "number"},
                      "maximum": {"type": "number"}
                    }
                  }
                }
              }
            },
            "output_schema": {
              "type": "object",
              "$ref": "http://json-schema.org/draft-07/schema#"
            }
          }
        }
      }
    }
  }
}
```

### 4.2 Runtime Validation Rules
Comprehensive validation to prevent ALL runtime errors:

#### 4.2.1 Configuration Loading Validation
```typescript
interface ValidationConfig {
  mode: 'strict' | 'warn' | 'off';    // SIZECOMPARATOR_CONFIG_VALIDATION
  fail_fast: boolean;                  // Stop on first error
  require_environment_vars: boolean;   // Ensure all env vars are set
  validate_file_paths: boolean;        // Check file existence
  validate_network_endpoints: boolean; // Test API endpoints
}

// Validation stages (ALL must pass in strict mode)
enum ValidationStage {
  SYNTAX = 'syntax',                   // YAML/JSON parsing
  SCHEMA = 'schema',                   // JSON Schema validation
  ENVIRONMENT = 'environment',         // Env var resolution
  BUSINESS_LOGIC = 'business_logic',   // Custom rules
  CONNECTIVITY = 'connectivity',       // External dependencies
  SECURITY = 'security'                // Security checks
}
```

#### 4.2.2 Template Validation Rules
```typescript
interface TemplateValidationRules {
  // Syntax validation
  handlebars_syntax: boolean;          // Valid Handlebars template
  balanced_braces: boolean;            // All {{}} properly closed
  no_undefined_helpers: boolean;       // All helpers are registered
  
  // Variable validation  
  all_variables_defined: boolean;      // Template vars in schema
  required_variables_present: boolean; // Required vars provided
  type_constraints: boolean;           // Variable types match
  range_validation: boolean;           // Numeric ranges valid
  pattern_validation: boolean;         // Regex patterns match
  
  // Security validation
  no_code_injection: boolean;          // No executable code
  sanitized_variables: boolean;        // Variables are escaped
  safe_helpers_only: boolean;          // Only whitelisted helpers
  
  // Output validation
  valid_json_schema: boolean;          // Output schema is valid
  response_validation: boolean;        // Responses match schema
}
```

### 4.3 Enhanced Error Handling
Detailed error reporting for debugging:

```typescript
interface ValidationError {
  // Error identification
  id: string;                          // Unique error ID
  stage: ValidationStage;              // Which validation stage failed
  severity: 'error' | 'warning' | 'info'; // Error severity
  
  // Location information
  path: string;                        // JSONPath to error location
  file: string;                        // Configuration file name
  line?: number;                       // Line number (if applicable)
  column?: number;                     // Column number (if applicable)
  
  // Error details
  code: string;                        // Error code (e.g., "TYPE_MISMATCH")
  message: string;                     // Human-readable description
  expected: any;                       // Expected value/type
  actual: any;                         // Actual value received
  
  // Context
  context: Record<string, any>;        // Additional context
  suggestions: string[];               // Fix suggestions
  documentation_url?: string;          // Link to docs
  
  // Metadata
  timestamp: Date;                     // When error occurred
  environment: string;                 // Which environment
  validation_mode: string;             // Validation mode active
}

// Validation result summary
interface ValidationResult {
  success: boolean;                    // Overall validation success
  errors: ValidationError[];           // All errors found
  warnings: ValidationError[];         // All warnings found
  performance: {
    total_time_ms: number;             // Total validation time
    stage_times: Record<ValidationStage, number>; // Per-stage timing
  };
  metadata: {
    config_files_processed: string[]; // Files validated
    environment_variables_resolved: string[]; // Env vars used
    templates_validated: string[];     // Template IDs validated
  };
}
```

### 4.4 Pre-deployment Validation
Validation hooks to catch errors BEFORE deployment:

```typescript
// Configuration validation pipeline
class ConfigurationValidator {
  // Required validation before any config changes
  async validateBeforeApply(config: any): Promise<ValidationResult> {
    const results: ValidationError[] = [];
    
    // 1. Schema validation (MUST pass)
    results.push(...await this.validateSchema(config));
    
    // 2. Environment variable resolution (MUST pass)
    results.push(...await this.validateEnvironmentVars(config));
    
    // 3. Cross-reference validation
    results.push(...await this.validateCrossReferences(config));
    
    // 4. External dependency validation
    results.push(...await this.validateExternalDependencies(config));
    
    // 5. Security validation
    results.push(...await this.validateSecurity(config));
    
    return this.compileResults(results);
  }
  
  // Template-specific validation
  async validateTemplate(template: Template): Promise<ValidationResult> {
    // Handlebars syntax check
    // Variable definition validation
    // Provider compatibility check
    // Output schema validation
    // Security scanning
  }
}

## 5. Safe Hot-Reload Implementation

### 5.1 File Watching with Safety Guarantees
```typescript
interface FileWatcherConfig {
  // Watch configuration
  directories: string[];               // Config directories to monitor
  patterns: string[];                  // File patterns to watch (.yaml, .json)
  ignore_patterns: string[];           // Patterns to ignore (.tmp, .swp)
  
  // Debouncing (prevent rapid reload cycles)
  debounce_delay_ms: 500;             // Wait time after last change
  max_rapid_changes: 10;              // Max changes before throttling
  throttle_window_ms: 5000;           // Throttling window
  
  // Safety settings
  atomic_detection: boolean;           // Wait for atomic file operations
  checksum_validation: boolean;        // Verify file integrity
  backup_on_change: boolean;           // Create backup before reload
  
  // Rollback configuration  
  enable_rollback: boolean;            // Enable automatic rollback
  rollback_timeout_ms: 30000;         // Max time before rollback
  health_check_interval_ms: 5000;     // Service health check frequency
}

class SafeFileWatcher {
  private watchedFiles: Map<string, FileMetadata> = new Map();
  private debounceTimers: Map<string, NodeJS.Timer> = new Map();
  private rapidChangeCount: Map<string, number> = new Map();
  
  async watchFiles(config: FileWatcherConfig): Promise<void> {
    // Use platform-specific watchers (inotify, FSEvents, etc.)
    // Implement atomic operation detection
    // Set up debouncing and throttling
    // Configure backup and rollback mechanisms
  }
  
  private async handleFileChange(filepath: string, event: FileChangeEvent): Promise<void> {
    // 1. Validate file change is atomic and complete
    if (!await this.isAtomicOperationComplete(filepath)) {
      this.scheduleRetry(filepath, event);
      return;
    }
    
    // 2. Apply debouncing
    this.debounceChange(filepath, () => this.processFileChange(filepath, event));
  }
  
  private async isAtomicOperationComplete(filepath: string): Promise<boolean> {
    // Check if file size is stable
    // Verify file is not locked
    // Ensure checksum consistency
    return true;
  }
}
```

### 5.2 Safe Reload Process with Rollback
```typescript
enum ReloadPhase {
  DETECTION = 'detection',             // File change detected
  VALIDATION = 'validation',           // New config validation
  BACKUP = 'backup',                   // Current config backup
  PREPARATION = 'preparation',         // Prepare new config
  APPLICATION = 'application',         // Apply new config
  VERIFICATION = 'verification',       // Verify system health
  COMPLETION = 'completion',           // Reload complete
  ROLLBACK = 'rollback'               // Emergency rollback
}

class SafeConfigReloader {
  private currentConfig: ConfigSnapshot;
  private backupConfig: ConfigSnapshot;
  private reloadInProgress: boolean = false;
  private healthCheckers: Map<string, HealthChecker> = new Map();
  
  async reloadConfiguration(changedFiles: string[]): Promise<ReloadResult> {
    if (this.reloadInProgress) {
      throw new Error('Reload already in progress');
    }
    
    const reloadId = this.generateReloadId();
    const startTime = Date.now();
    
    try {
      this.reloadInProgress = true;
      
      // PHASE 1: Backup current configuration
      await this.createConfigBackup(reloadId);
      
      // PHASE 2: Load and validate new configuration
      const newConfig = await this.loadNewConfiguration(changedFiles);
      const validationResult = await this.validateConfiguration(newConfig);
      
      if (!validationResult.success) {
        throw new ConfigValidationError(validationResult.errors);
      }
      
      // PHASE 3: Prepare configuration changes
      const changeset = await this.calculateChangeset(this.currentConfig, newConfig);
      const affectedServices = this.identifyAffectedServices(changeset);
      
      // PHASE 4: Apply configuration with health monitoring
      await this.applyConfigurationSafely(newConfig, affectedServices, reloadId);
      
      // PHASE 5: Verify system health
      const healthResult = await this.verifySystemHealth(affectedServices);
      
      if (!healthResult.healthy) {
        throw new HealthCheckFailureError(healthResult.failures);
      }
      
      // PHASE 6: Commit changes
      this.currentConfig = newConfig;
      this.cleanupBackup(reloadId);
      
      return {
        success: true,
        reloadId,
        duration: Date.now() - startTime,
        affectedServices,
        changeset
      };
      
    } catch (error) {
      // EMERGENCY ROLLBACK
      await this.rollbackConfiguration(reloadId, error);
      throw error;
    } finally {
      this.reloadInProgress = false;
    }
  }
  
  private async applyConfigurationSafely(
    newConfig: ConfigSnapshot,
    affectedServices: string[],
    reloadId: string
  ): Promise<void> {
    // Apply changes incrementally with service health monitoring
    for (const service of affectedServices) {
      await this.updateServiceConfiguration(service, newConfig);
      
      // Immediate health check after each service update
      const healthCheck = await this.checkServiceHealth(service);
      if (!healthCheck.healthy) {
        throw new ServiceHealthError(service, healthCheck.error);
      }
      
      // Brief stabilization delay
      await this.sleep(1000);
    }
  }
  
  private async rollbackConfiguration(reloadId: string, error: Error): Promise<void> {
    try {
      // Restore from backup
      const backupConfig = await this.loadConfigBackup(reloadId);
      
      // Apply backup configuration immediately
      await this.forceApplyConfiguration(backupConfig);
      
      // Verify rollback success
      const healthResult = await this.verifySystemHealth();
      
      if (!healthResult.healthy) {
        // CRITICAL: Manual intervention required
        await this.alertOperations('CRITICAL_ROLLBACK_FAILURE', {
          reloadId,
          originalError: error,
          rollbackError: healthResult.failures
        });
      }
      
    } catch (rollbackError) {
      // CRITICAL: Both reload and rollback failed
      await this.alertOperations('CRITICAL_CONFIG_FAILURE', {
        reloadId,
        originalError: error,
        rollbackError
      });
      
      // Trigger emergency mode
      await this.activateEmergencyMode();
    }
  }
}
```

### 5.3 Service Health Monitoring
```typescript
interface HealthChecker {
  serviceName: string;
  checkInterval: number;
  timeout: number;
  retries: number;
  
  check(): Promise<HealthResult>;
}

interface HealthResult {
  healthy: boolean;
  service: string;
  timestamp: Date;
  responseTime: number;
  error?: string;
  details?: Record<string, any>;
}

class ServiceHealthMonitor {
  private healthCheckers: Map<string, HealthChecker> = new Map();
  private healthHistory: Map<string, HealthResult[]> = new Map();
  
  // Register health checkers for each service
  registerHealthChecker(service: string, checker: HealthChecker): void {
    this.healthCheckers.set(service, checker);
  }
  
  // Continuous health monitoring
  async startHealthMonitoring(): Promise<void> {
    setInterval(async () => {
      for (const [service, checker] of this.healthCheckers) {
        try {
          const result = await checker.check();
          this.recordHealthResult(service, result);
          
          if (!result.healthy) {
            await this.handleUnhealthyService(service, result);
          }
        } catch (error) {
          await this.handleHealthCheckError(service, error);
        }
      }
    }, 5000); // Check every 5 seconds
  }
  
  private async handleUnhealthyService(service: string, result: HealthResult): Promise<void> {
    const history = this.healthHistory.get(service) || [];
    const recentFailures = history.filter(h => 
      !h.healthy && 
      Date.now() - h.timestamp.getTime() < 30000 // Last 30 seconds
    );
    
    if (recentFailures.length >= 3) {
      // Service is consistently unhealthy - trigger rollback
      await this.triggerEmergencyRollback(service, 'PERSISTENT_HEALTH_FAILURE');
    }
  }
}
```

### 5.4 Change Event System
```typescript
interface ConfigChangeEvent {
  // Event identification
  eventId: string;                     // Unique event ID
  timestamp: Date;                     // When change occurred
  reloadId?: string;                   // Associated reload ID
  
  // Change details  
  changeType: 'create' | 'update' | 'delete' | 'rollback';
  scope: 'file' | 'section' | 'property'; // Change granularity
  path: string;                        // JSONPath to changed property
  file: string;                        // Source configuration file
  
  // Values
  previousValue?: any;                 // Previous value (if update/delete)
  newValue?: any;                      // New value (if create/update)
  
  // Impact analysis
  affectedServices: string[];          // Services impacted by change
  requiredRestarts: string[];          // Services requiring restart
  compatibilityBreaking: boolean;      // Breaking change indicator
  
  // Metadata
  source: 'file_change' | 'hot_reload' | 'api_update' | 'rollback';
  user?: string;                       // User who made change (if applicable)
  reason?: string;                     // Reason for change
  environment: string;                 // Environment where change occurred
}

class ConfigChangeNotifier {
  private subscribers: Map<string, ConfigChangeSubscriber[]> = new Map();
  private eventHistory: ConfigChangeEvent[] = [];
  
  // Subscribe to configuration changes
  subscribe(pattern: string, subscriber: ConfigChangeSubscriber): void {
    const subscribers = this.subscribers.get(pattern) || [];
    subscribers.push(subscriber);
    this.subscribers.set(pattern, subscribers);
  }
  
  // Emit change event to subscribers
  async emitChange(event: ConfigChangeEvent): Promise<void> {
    // Record event in history
    this.eventHistory.push(event);
    
    // Find matching subscribers
    const matchingSubscribers = this.findMatchingSubscribers(event.path);
    
    // Notify subscribers asynchronously
    const notifications = matchingSubscribers.map(async (subscriber) => {
      try {
        await subscriber.onConfigChange(event);
      } catch (error) {
        console.error(`Subscriber ${subscriber.id} failed to handle config change:`, error);
      }
    });
    
    await Promise.allSettled(notifications);
  }
  
  // Get change history for analysis
  getChangeHistory(filter?: ConfigChangeFilter): ConfigChangeEvent[] {
    return this.eventHistory.filter(event => this.matchesFilter(event, filter));
  }
}
```

### 5.5 Hot-Reload Safety Features
Key safety mechanisms to prevent service disruption:

1. **Atomic Configuration Updates**:
   - All-or-nothing configuration application
   - Transactional updates across services
   - Automatic rollback on partial failures

2. **Pre-flight Validation**:
   - Schema validation before application
   - Connectivity tests for external dependencies
   - Business logic validation
   - Security vulnerability scanning

3. **Gradual Rollout**:
   - Canary-style configuration deployment
   - Incremental service updates
   - Health monitoring between updates

4. **Emergency Procedures**:
   - Automatic rollback on health check failures
   - Manual rollback capabilities
   - Emergency mode with minimal configuration
   - Operations team alerting

5. **Configuration Drift Protection**:
   - Checksum verification of config files
   - Detection of unauthorized changes
   - Audit trail for all modifications
   - Compliance reporting

## 6. Configuration Hierarchy & Merging

### 6.1 Load Order
1. Base configuration files
2. Environment-specific overrides
3. Variant configurations (A/B testing)
4. Environment variables
5. Runtime overrides (if applicable)

### 6.2 Merge Strategy
- Deep merge for objects
- Array replacement (not concatenation)
- Explicit null to remove values
- Type consistency enforcement

### 6.3 Resolution Example
```yaml
# base/app.yaml
api:
  timeout: 30
  retry:
    attempts: 3

# environments/production.yaml
api:
  timeout: 60
  retry:
    attempts: 5

# Result after merge:
api:
  timeout: 60
  retry:
    attempts: 5
```

## 7. A/B Testing Support

### 7.1 Variant Configuration
```yaml
# variants/experiment_a.yaml
experiment:
  id: "prompt_optimization_2024Q1"
  allocation: 0.5  # 50% of traffic
  overrides:
    templates:
      size_comparison:
        content: "Alternative prompt template..."
```

### 7.2 Variant Selection
- User-based allocation (consistent experience)
- Percentage-based distribution
- Feature flag integration
- Metrics collection hooks

## 8. Security Requirements

### 8.1 Sensitive Data Handling
- No secrets in configuration files
- Use environment variables for sensitive data
- Implement secret reference syntax: `${secret:vault/path/to/secret}`
- Audit log for configuration access

### 8.2 Template Injection Prevention
- Sanitize all template variables
- Disable dangerous helpers (file access, execution)
- Whitelist allowed template functions
- Escape user-provided content

### 8.3 Access Control
- Read-only configuration files in production
- Restricted write access to configuration directory
- Configuration change audit trail
- Role-based access for configuration updates

## 9. Component Interfaces

### 9.1 Enhanced Configuration Service Interface
```typescript
interface IConfigurationService {
  // Core operations with type safety
  get<T>(path: string, defaultValue?: T): Promise<T>;
  getSync<T>(path: string, defaultValue?: T): T;
  set(path: string, value: any): Promise<ValidationResult>;
  has(path: string): boolean;
  delete(path: string): Promise<ValidationResult>;
  
  // Environment handling
  getEnvironment(): string;
  setEnvironment(env: string): Promise<void>;
  getEnvironmentVariable(name: string, defaultValue?: string): string;
  resolveEnvironmentVariables(config: any): Promise<any>;
  
  // Schema and validation
  validateConfiguration(config?: any): Promise<ValidationResult>;
  validatePartial(path: string, value: any): Promise<ValidationResult>;
  getSchema(path?: string): JSONSchema7;
  registerCustomValidator(path: string, validator: CustomValidator): void;
  
  // Hot reload with safety
  enableHotReload(options?: HotReloadOptions): Promise<void>;
  disableHotReload(): Promise<void>;
  isHotReloadEnabled(): boolean;
  getHotReloadStatus(): HotReloadStatus;
  
  // Event handling
  onConfigChange(callback: (event: ConfigChangeEvent) => void): Subscription;
  onValidationError(callback: (error: ValidationError) => void): Subscription;
  onReloadStart(callback: (reloadId: string) => void): Subscription;
  onReloadComplete(callback: (result: ReloadResult) => void): Subscription;
  
  // Configuration snapshots
  createSnapshot(id?: string): Promise<ConfigSnapshot>;
  restoreSnapshot(id: string): Promise<ReloadResult>;
  listSnapshots(): ConfigSnapshot[];
  deleteSnapshot(id: string): Promise<void>;
  
  // Debugging and introspection
  getConfigSource(path: string): ConfigSource;
  getConfigHistory(path?: string): ConfigChangeEvent[];
  getValidationErrors(): ValidationError[];
  getPerformanceMetrics(): PerformanceMetrics;
  
  // Security
  maskSensitiveValues(config: any): any;
  isPathSensitive(path: string): boolean;
  auditConfigAccess(path: string, operation: string): void;
}

interface HotReloadOptions {
  debounceMs?: number;
  maxRetries?: number;
  healthCheckTimeout?: number;
  rollbackOnFailure?: boolean;
  validateBeforeApply?: boolean;
}

interface HotReloadStatus {
  enabled: boolean;
  lastReload?: Date;
  reloadCount: number;
  failureCount: number;
  currentReloadId?: string;
  isReloading: boolean;
}
```

### 9.2 Enhanced Template Service Interface
```typescript
interface ITemplateService {
  // Template operations with AI provider integration
  getTemplate(id: string, provider?: string): Promise<Template>;
  renderTemplate(
    id: string, 
    variables: Record<string, any>,
    options?: RenderOptions
  ): Promise<RenderedTemplate>;
  
  // Template validation and testing
  validateTemplate(template: Template): Promise<ValidationResult>;
  testTemplate(
    id: string, 
    testData: Record<string, any>
  ): Promise<TemplateTestResult>;
  
  // Template management
  registerTemplate(template: Template): Promise<ValidationResult>;
  updateTemplate(id: string, template: Template): Promise<ValidationResult>;
  deleteTemplate(id: string): Promise<void>;
  listTemplates(filter?: TemplateFilter): Template[];
  
  // Helper and partial management
  registerHelper(name: string, helper: TemplateHelper): void;
  unregisterHelper(name: string): void;
  listHelpers(): TemplateHelper[];
  registerPartial(name: string, partial: string): void;
  
  // AI provider integration
  getProviderConfig(provider: string): ProviderConfig;
  validateProviderCompatibility(
    template: Template, 
    provider: string
  ): Promise<CompatibilityResult>;
  
  // A/B testing and variants
  getVariant(
    userId: string, 
    experimentId: string,
    context?: Record<string, any>
  ): Promise<string>;
  getTemplateVariant(
    templateId: string, 
    userId: string,
    context?: Record<string, any>
  ): Promise<Template>;
  
  // Template analytics
  getTemplateUsageStats(id: string): TemplateUsageStats;
  getTemplatePerformanceMetrics(id: string): TemplatePerformanceMetrics;
  
  // Template caching
  precompileTemplate(id: string): Promise<void>;
  clearTemplateCache(id?: string): void;
  getTemplateCacheStats(): TemplateCacheStats;
}

interface RenderOptions {
  provider?: string;
  validateOutput?: boolean;
  timeout?: number;
  context?: Record<string, any>;
  dryRun?: boolean;
}

interface RenderedTemplate {
  content: string;
  metadata: {
    templateId: string;
    provider: string;
    renderTime: number;
    variablesUsed: string[];
    validationResult?: ValidationResult;
  };
}

interface TemplateTestResult {
  success: boolean;
  output: RenderedTemplate;
  validationResult: ValidationResult;
  performanceMetrics: {
    renderTime: number;
    variableResolutionTime: number;
    validationTime: number;
  };
  errors: TemplateError[];
}
```

### 9.3 Component Integration Points
Precise integration specifications for each system component:

#### 9.3.1 API Handler Integration
```typescript
interface APIHandlerConfigInterface {
  // Configuration dependencies
  getProviderConfig(provider: string): Promise<ProviderConfig>;
  getRetryConfiguration(): RetryConfig;
  getTimeoutConfiguration(): TimeoutConfig;
  
  // Hot-reload support
  onProviderConfigChange(callback: (provider: string, config: ProviderConfig) => void): void;
  onRetryConfigChange(callback: (config: RetryConfig) => void): void;
  
  // Health monitoring
  reportProviderHealth(provider: string, status: HealthStatus): void;
  getProviderHealthStatus(provider: string): HealthStatus;
}
```

#### 9.3.2 Comparison Engine Integration
```typescript
interface ComparisonEngineConfigInterface {
  // Core configuration
  getComparisonConfig(): ComparisonConfig;
  getUnitConfiguration(): UnitConfig;
  getPrecisionSettings(): PrecisionConfig;
  
  // Template integration
  getComparisonTemplate(type: string): Promise<Template>;
  renderComparison(
    templateId: string,
    comparisonData: ComparisonData
  ): Promise<RenderedTemplate>;
  
  // Feature flags
  isDimensionAnalysisEnabled(): boolean;
  isVolumeCalculationEnabled(): boolean;
  isSurfaceAreaCalculationEnabled(): boolean;
  
  // Configuration change handling
  onComparisonConfigChange(callback: (config: ComparisonConfig) => void): void;
  onTemplateChange(callback: (templateId: string, template: Template) => void): void;
}
```

#### 9.3.3 Cache Service Integration
```typescript
interface CacheServiceConfigInterface {
  // Cache configuration
  getCacheProvider(): CacheProvider;
  getCacheConnectionConfig(): CacheConnectionConfig;
  getCacheSettings(): CacheSettings;
  
  // Dynamic reconfiguration
  switchCacheProvider(provider: CacheProvider): Promise<void>;
  updateCacheSettings(settings: Partial<CacheSettings>): Promise<void>;
  
  // Health and monitoring
  getCacheHealthStatus(): HealthStatus;
  getCachePerformanceMetrics(): CacheMetrics;
  
  // Configuration change handling
  onCacheConfigChange(callback: (config: CacheConfig) => void): void;
}
```

#### 9.3.4 Monitoring Service Integration
```typescript
interface MonitoringServiceConfigInterface {
  // Monitoring configuration
  getMetricsConfig(): MetricsConfig;
  getLoggingConfig(): LoggingConfig;
  getTracingConfig(): TracingConfig;
  
  // Configuration change reporting
  reportConfigurationChange(event: ConfigChangeEvent): void;
  reportValidationError(error: ValidationError): void;
  reportHotReloadEvent(event: HotReloadEvent): void;
  
  // Performance monitoring
  trackConfigurationPerformance(metrics: PerformanceMetrics): void;
  trackTemplatePerformance(templateId: string, metrics: TemplateMetrics): void;
  
  // Health monitoring integration
  registerHealthChecker(service: string, checker: HealthChecker): void;
  reportHealthStatus(service: string, status: HealthStatus): void;
}
```

#### 9.3.5 Feature Toggle Service Integration
```typescript
interface FeatureToggleConfigInterface {
  // Feature flag access
  isFeatureEnabled(featureName: string, context?: FeatureContext): boolean;
  getFeatureValue<T>(featureName: string, defaultValue: T, context?: FeatureContext): T;
  getAllFeatures(context?: FeatureContext): Record<string, any>;
  
  // Dynamic feature updates
  updateFeatureFlag(featureName: string, value: any): Promise<ValidationResult>;
  enableFeature(featureName: string): Promise<void>;
  disableFeature(featureName: string): Promise<void>;
  
  // A/B testing integration
  getExperimentVariant(
    experimentId: string,
    userId: string,
    context?: FeatureContext
  ): string;
  
  // Feature change notifications
  onFeatureChange(
    featureName: string,
    callback: (newValue: any, oldValue: any) => void
  ): void;
  
  // Feature analytics
  trackFeatureUsage(featureName: string, context?: FeatureContext): void;
  getFeatureUsageStats(featureName: string): FeatureUsageStats;
}
```

## 10. Error Handling & Recovery

### 10.1 Common Error Scenarios
1. **Missing Required Fields**
   - Detection: Schema validation
   - Recovery: Use defaults or fail fast
   - Logging: Error with field path

2. **Invalid YAML/JSON Syntax**
   - Detection: Parser exceptions
   - Recovery: Fall back to last valid config
   - Logging: Syntax error details

3. **Environment Variable Not Set**
   - Detection: Template resolution
   - Recovery: Use default or fail if required
   - Logging: Missing variable name

4. **Template Syntax Errors**
   - Detection: Template compilation
   - Recovery: Use fallback template
   - Logging: Template error location

5. **Type Mismatches**
   - Detection: Runtime validation
   - Recovery: Type coercion or rejection
   - Logging: Expected vs actual type

### 10.2 Rollback Strategy
- Maintain last known good configuration
- Automatic rollback on validation failure
- Manual rollback capability
- Configuration version history

## 11. Performance Considerations

### 11.1 Caching Strategy
- In-memory configuration cache
- Lazy loading for large configurations
- Partial cache invalidation on changes
- Pre-compiled template cache

### 11.2 Optimization Techniques
- Configuration preprocessing at startup
- Minimal file I/O during runtime
- Efficient deep merge algorithms
- Template compilation caching

## 12. Monitoring & Observability

### 12.1 Metrics
- Configuration load time
- Hot reload frequency
- Validation failure rate
- Template rendering performance
- A/B test distribution

### 12.2 Logging
- Configuration changes (audit trail)
- Validation errors
- Environment variable resolution
- Template rendering failures
- Hot reload events

## 13. Testing Strategy

### 13.1 Unit Tests
- Schema validation tests
- Template rendering tests
- Environment variable substitution
- Merge logic verification

### 13.2 Integration Tests
- Hot reload functionality
- Multi-environment loading
- A/B testing distribution
- Component integration

### 13.3 Load Tests
- High-frequency configuration changes
- Large configuration files
- Concurrent access patterns
- Template rendering performance

## 14. Migration & Compatibility

### 14.1 Configuration Version Management
```typescript
interface ConfigurationVersion {
  major: number;                       // Breaking changes
  minor: number;                       // New features, backward compatible
  patch: number;                       // Bug fixes, backward compatible
  prerelease?: string;                 // Pre-release identifier
  build?: string;                      // Build metadata
}

interface MigrationScript {
  fromVersion: string;                 // Source version pattern
  toVersion: string;                   // Target version
  description: string;                 // Migration description
  reversible: boolean;                 // Can be rolled back
  
  // Migration execution
  migrate(config: any): Promise<MigrationResult>;
  rollback?(config: any): Promise<MigrationResult>;
  
  // Validation
  validate(config: any): Promise<ValidationResult>;
  getDryRunChanges(config: any): Promise<ConfigChangeset>;
}

class ConfigurationMigrationManager {
  private migrationRegistry: Map<string, MigrationScript[]> = new Map();
  
  // Register migration scripts
  registerMigration(script: MigrationScript): void {
    const key = `${script.fromVersion}->${script.toVersion}`;
    const scripts = this.migrationRegistry.get(key) || [];
    scripts.push(script);
    this.migrationRegistry.set(key, scripts);
  }
  
  // Execute migration with safety checks
  async migrate(
    config: any,
    targetVersion: string,
    options?: MigrationOptions
  ): Promise<MigrationResult> {
    const currentVersion = this.extractVersion(config);
    const migrationPath = this.calculateMigrationPath(currentVersion, targetVersion);
    
    // Validate migration path
    const pathValidation = await this.validateMigrationPath(migrationPath);
    if (!pathValidation.valid) {
      throw new MigrationPathError(pathValidation.errors);
    }
    
    // Create backup before migration
    const backupId = await this.createMigrationBackup(config);
    
    try {
      // Execute migration steps
      let migratedConfig = config;
      for (const step of migrationPath) {
        migratedConfig = await this.executeMigrationStep(migratedConfig, step);
      }
      
      // Validate final configuration
      const finalValidation = await this.validateConfiguration(migratedConfig);
      if (!finalValidation.success) {
        throw new MigrationValidationError(finalValidation.errors);
      }
      
      return {
        success: true,
        fromVersion: currentVersion,
        toVersion: targetVersion,
        migratedConfig,
        backupId,
        migrationPath
      };
      
    } catch (error) {
      // Automatic rollback on failure
      if (options?.rollbackOnFailure !== false) {
        await this.rollbackMigration(backupId);
      }
      throw error;
    }
  }
}
```

### 14.2 Zero-Downtime Configuration Updates
```typescript
interface DeploymentStrategy {
  type: 'blue_green' | 'canary' | 'rolling' | 'immediate';
  settings: DeploymentSettings;
}

interface CanaryDeploymentSettings {
  canaryPercentage: number;            // Percentage of traffic to new config
  canaryDuration: number;              // Duration in seconds
  canaryHealthThreshold: number;       // Required health percentage
  rollbackOnFailure: boolean;          // Auto-rollback on health failure
  
  // Traffic routing
  userSegmentation?: UserSegment[];    // Specific user segments for canary
  featureFlags?: string[];             // Feature flags to enable for canary
  
  // Monitoring
  metricsToTrack: string[];           // Key metrics to monitor
  alertThresholds: AlertThreshold[];   // When to trigger alerts
}

class ZeroDowntimeDeploymentManager {
  async deployConfiguration(
    newConfig: any,
    strategy: DeploymentStrategy
  ): Promise<DeploymentResult> {
    switch (strategy.type) {
      case 'canary':
        return this.deployCanary(newConfig, strategy.settings as CanaryDeploymentSettings);
      case 'blue_green':
        return this.deployBlueGreen(newConfig, strategy.settings);
      case 'rolling':
        return this.deployRolling(newConfig, strategy.settings);
      default:
        return this.deployImmediate(newConfig);
    }
  }
  
  private async deployCanary(
    newConfig: any,
    settings: CanaryDeploymentSettings
  ): Promise<DeploymentResult> {
    // Phase 1: Deploy to canary infrastructure
    const canaryEnvironment = await this.createCanaryEnvironment(newConfig);
    
    // Phase 2: Route canary traffic
    await this.routeCanaryTraffic(settings.canaryPercentage, canaryEnvironment);
    
    // Phase 3: Monitor canary health
    const healthResult = await this.monitorCanaryHealth(
      settings.canaryDuration,
      settings.canaryHealthThreshold
    );
    
    if (!healthResult.healthy) {
      // Rollback canary deployment
      await this.rollbackCanary();
      throw new CanaryDeploymentFailureError(healthResult.issues);
    }
    
    // Phase 4: Promote canary to production
    await this.promoteCanaryToProduction(canaryEnvironment);
    
    return {
      success: true,
      strategy: 'canary',
      deploymentTime: Date.now(),
      healthMetrics: healthResult.metrics
    };
  }
}
```

## 15. SIZECOMPARATOR Environment Variable Reference

### 15.1 Complete Environment Variable Catalog
All environment variables with exact specifications:

```bash
# Core Application Configuration
SIZECOMPARATOR_ENV=development                    # Required: development|staging|production
SIZECOMPARATOR_VERSION=1.0.0                     # Optional: Semver format
SIZECOMPARATOR_CONFIG_DIR=/app/config             # Optional: Config directory path
SIZECOMPARATOR_LOG_LEVEL=info                    # Optional: debug|info|warn|error

# Configuration System Control
SIZECOMPARATOR_CONFIG_VALIDATION=strict          # Optional: strict|warn|off
SIZECOMPARATOR_HOT_RELOAD=true                   # Optional: Enable hot reload
SIZECOMPARATOR_CONFIG_BACKUP=true               # Optional: Enable config backups
SIZECOMPARATOR_CONFIG_AUDIT=true                # Optional: Enable audit logging

# AI Provider - OpenAI
SIZECOMPARATOR_OPENAI_API_KEY=sk-1234567890     # Required: OpenAI API key
SIZECOMPARATOR_OPENAI_ENDPOINT=https://api.openai.com/v1  # Optional: Custom endpoint
SIZECOMPARATOR_OPENAI_MODEL=gpt-4               # Optional: Model name
SIZECOMPARATOR_OPENAI_TIMEOUT=30                # Optional: Timeout in seconds
SIZECOMPARATOR_OPENAI_MAX_TOKENS=4096           # Optional: Max tokens per request

# AI Provider - Anthropic
SIZECOMPARATOR_ANTHROPIC_API_KEY=sk-ant-1234567 # Required: Anthropic API key
SIZECOMPARATOR_ANTHROPIC_ENDPOINT=https://api.anthropic.com  # Optional: Custom endpoint
SIZECOMPARATOR_ANTHROPIC_MODEL=claude-3-opus-20240229       # Optional: Model name
SIZECOMPARATOR_ANTHROPIC_TIMEOUT=30             # Optional: Timeout in seconds

# Cache Configuration - Redis
SIZECOMPARATOR_REDIS_HOST=localhost              # Optional: Redis host
SIZECOMPARATOR_REDIS_PORT=6379                  # Optional: Redis port
SIZECOMPARATOR_REDIS_PASSWORD=secret123         # Optional: Redis password
SIZECOMPARATOR_REDIS_DB=0                       # Optional: Redis database number
SIZECOMPARATOR_REDIS_TLS=false                  # Optional: Enable TLS
SIZECOMPARATOR_REDIS_CA_CERT=/path/to/ca.pem    # Optional: TLS CA certificate

# Cache Configuration - DynamoDB
SIZECOMPARATOR_DYNAMODB_REGION=us-east-1        # Optional: AWS region
SIZECOMPARATOR_DYNAMODB_TABLE=sizecomparator-cache  # Optional: Table name
SIZECOMPARATOR_DYNAMODB_ACCESS_KEY_ID=AKIA123   # Optional: AWS access key
SIZECOMPARATOR_DYNAMODB_SECRET_ACCESS_KEY=secret # Optional: AWS secret key

# Monitoring and Observability
SIZECOMPARATOR_METRICS_ENABLED=true             # Optional: Enable metrics
SIZECOMPARATOR_METRICS_PORT=9090                # Optional: Metrics port
SIZECOMPARATOR_METRICS_PATH=/metrics            # Optional: Metrics endpoint

# Logging Configuration
SIZECOMPARATOR_LOG_FORMAT=json                  # Optional: json|text
SIZECOMPARATOR_LOG_OUTPUT=stdout                # Optional: stdout|file|syslog
SIZECOMPARATOR_LOG_FILE=/var/log/sizecomparator.log  # Required if LOG_OUTPUT=file

# Tracing Configuration
SIZECOMPARATOR_TRACE_ENABLED=false              # Optional: Enable tracing
SIZECOMPARATOR_TRACE_PROVIDER=jaeger            # Optional: jaeger|zipkin|otlp
SIZECOMPARATOR_TRACE_ENDPOINT=http://jaeger:14268/api/traces  # Required if tracing enabled

# Security Configuration
SIZECOMPARATOR_SECRET_KEY=super-secret-key-32-chars    # Required: Encryption key
SIZECOMPARATOR_CORS_ORIGINS=http://localhost:3000      # Optional: CORS origins
SIZECOMPARATOR_RATE_LIMIT_ENABLED=true         # Optional: Enable rate limiting
SIZECOMPARATOR_RATE_LIMIT_REQUESTS=100         # Optional: Requests per minute

# Feature Flags
SIZECOMPARATOR_FEATURE_ENHANCED_VIZ=true       # Optional: Enhanced visualizations
SIZECOMPARATOR_FEATURE_MULTI_LANG=false       # Optional: Multi-language support
SIZECOMPARATOR_FEATURE_REAL_TIME=true         # Optional: Real-time updates
SIZECOMPARATOR_FEATURE_AI_SUGGESTIONS=false   # Optional: AI suggestions
SIZECOMPARATOR_FEATURE_3D_RENDERING=false     # Optional: 3D rendering

# Development and Testing
SIZECOMPARATOR_DEBUG=false                     # Optional: Debug mode
SIZECOMPARATOR_TEST_MODE=false                 # Optional: Test mode
SIZECOMPARATOR_MOCK_AI_RESPONSES=false         # Optional: Mock AI responses
SIZECOMPARATOR_PERFORMANCE_PROFILING=false    # Optional: Enable profiling
```

### 15.2 Environment Variable Validation Rules
```typescript
interface EnvironmentVariableSpec {
  name: string;
  required: boolean;
  type: 'string' | 'number' | 'boolean' | 'enum' | 'url' | 'file_path';
  default?: any;
  validation?: {
    pattern?: string;              // Regex pattern
    enum?: string[];              // Allowed values
    min?: number;                 // Minimum value (numbers)
    max?: number;                 // Maximum value (numbers)
    minLength?: number;           // Minimum length (strings)
    maxLength?: number;           // Maximum length (strings)
  };
  sensitive?: boolean;            // Mask in logs
  description: string;
}

const ENVIRONMENT_VARIABLES: EnvironmentVariableSpec[] = [
  {
    name: 'SIZECOMPARATOR_ENV',
    required: true,
    type: 'enum',
    validation: { enum: ['development', 'staging', 'production'] },
    description: 'Runtime environment'
  },
  {
    name: 'SIZECOMPARATOR_OPENAI_API_KEY',
    required: false,  // Required only if OpenAI provider is used
    type: 'string',
    validation: { pattern: '^sk-[A-Za-z0-9]+$', minLength: 20 },
    sensitive: true,
    description: 'OpenAI API key for AI provider'
  },
  {
    name: 'SIZECOMPARATOR_REDIS_PORT',
    required: false,
    type: 'number',
    default: 6379,
    validation: { min: 1, max: 65535 },
    description: 'Redis server port'
  }
  // ... Complete specification for all variables
];
```

## 16. Production Deployment Checklist

### 16.1 Pre-Deployment Configuration Validation
```bash
#!/bin/bash
# Production readiness check script

echo "🔍 SizeComparator Configuration Validation"

# 1. Environment variable validation
echo "Validating environment variables..."
required_vars=(
  "SIZECOMPARATOR_ENV"
  "SIZECOMPARATOR_OPENAI_API_KEY"
  "SIZECOMPARATOR_SECRET_KEY"
)

for var in "${required_vars[@]}"; do
  if [[ -z "${!var}" ]]; then
    echo "❌ Missing required environment variable: $var"
    exit 1
  fi
done

# 2. Configuration file validation
echo "Validating configuration files..."
if ! npx ajv validate -s config/schema/app.schema.json -d config/base/app.yaml; then
  echo "❌ Configuration validation failed"
  exit 1
fi

# 3. Template validation
echo "Validating prompt templates..."
if ! npx ajv validate -s config/schema/prompts.schema.json -d config/base/prompts.yaml; then
  echo "❌ Prompt template validation failed"
  exit 1
fi

# 4. External dependency checks
echo "Testing external dependencies..."
if ! curl -f "${SIZECOMPARATOR_OPENAI_ENDPOINT}/models" -H "Authorization: Bearer ${SIZECOMPARATOR_OPENAI_API_KEY}"; then
  echo "❌ OpenAI API connection failed"
  exit 1
fi

if ! redis-cli -h "${SIZECOMPARATOR_REDIS_HOST}" -p "${SIZECOMPARATOR_REDIS_PORT}" ping; then
  echo "❌ Redis connection failed"
  exit 1
fi

echo "✅ All validation checks passed"
echo "🚀 Configuration ready for production deployment"
```

This comprehensive update to the CONFIG_SYSTEM_SPEC.md provides:

1. **Exact schemas** for all configuration components with precise type definitions and validation rules
2. **Standardized environment variable naming** using the SIZECOMPARATOR_* prefix with complete specifications
3. **Detailed prompt template format** specifically designed for AI_PROVIDER_SPEC integration
4. **Comprehensive validation framework** that prevents runtime errors through multi-stage validation
5. **Safe hot-reload implementation** with atomic updates, health monitoring, and automatic rollback
6. **Enhanced component interfaces** with type safety and error handling
7. **Production-ready deployment procedures** with validation checklists and migration support

The specification now serves as the "central nervous system" with extreme precision about schemas, validation rules, and safety mechanisms to ensure the configuration system is robust and error-free.