# Logging Framework Specification for SizeComparator

## 1. Overview

The Logging Framework provides a comprehensive structured logging system for SizeComparator, serving as the foundation for observability, debugging, and operational excellence. This specification defines the implementation of JSON-structured logging with request ID propagation, log level management, PII protection, performance monitoring, and log aggregation strategies that integrate seamlessly with all system components.

### 1.1 Goals
- Implement structured JSON logging with consistent format across all services
- Enable end-to-end request tracing through request ID propagation
- Provide comprehensive log level management and filtering capabilities
- Ensure PII protection and sensitive data masking in all log outputs
- Support performance logging and detailed request tracing
- Define scalable log aggregation and rotation strategies
- Integrate with ERROR_MONITORING_SPEC requirements for unified observability

### 1.2 Integration Requirements
This logging framework integrates with:
- **BACKEND_CORE_SPEC**: Request ID context propagation and error categorization
- **ERROR_MONITORING_SPEC**: Unified error handling and alert correlation
- **AI_PROVIDER_SPEC**: Provider-specific logging and circuit breaker state tracking
- **CONFIG_SYSTEM_SPEC**: Environment-driven configuration and hot-reload support
- **DEPLOYMENT_OPS_SPEC**: Health endpoint integration and SLA monitoring

---

## 2. Structured JSON Logging Architecture

### 2.1 Core Log Format Specification

All log entries across the SizeComparator system MUST conform to the following JSON structure:

```json
{
  "timestamp": "2024-07-13T14:30:45.123Z",
  "request_id": "req_abc123def456",
  "service_name": "backend-core|ai-provider|cache-service|weight-processor",
  "environment": "development|staging|production",
  "log_level": "DEBUG|INFO|WARN|ERROR|FATAL",
  "message": "Human-readable log message",
  "context": {
    "operation_type": "weight_comparison|ai_request|cache_operation",
    "provider_name": "openai|anthropic|xai",
    "circuit_breaker_state": "CLOSED|OPEN|HALF_OPEN",
    "template_id": "comparison_template_v1",
    "user_agent": "SizeComparator/1.0",
    "endpoint": "/api/v1/weight/compare",
    "method": "POST|GET|PUT|DELETE",
    "status_code": 200,
    "duration_ms": 1250,
    "error_category": "CLIENT_ERROR|SERVER_ERROR|INTEGRATION_ERROR|BUSINESS_LOGIC_ERROR"
  },
  "metadata": {
    "version": "1.2.3",
    "instance_id": "backend-core-pod-abc123",
    "correlation_id": "corr_xyz789abc",
    "trace_id": "trace_123456789",
    "span_id": "span_987654321"
  }
}
```

### 2.2 Field Specifications

#### Mandatory Fields (Present in ALL logs)
- **timestamp**: ISO 8601 UTC timestamp with millisecond precision
- **request_id**: Unique identifier from BACKEND_CORE_SPEC request_id_context
- **service_name**: Standardized service identifier
- **environment**: Runtime environment from SIZECOMPARATOR_ENVIRONMENT
- **log_level**: Severity level following standard conventions
- **message**: Clear, actionable log message

#### Contextual Fields (Service-specific)
- **operation_type**: High-level operation classification
- **provider_name**: AI provider identifier (when applicable)
- **circuit_breaker_state**: Current state from AI_PROVIDER_SPEC
- **template_id**: Prompt template identifier from CONFIG_SYSTEM_SPEC
- **endpoint**: API endpoint being accessed
- **duration_ms**: Operation duration for performance tracking
- **error_category**: Aligned with ERROR_MONITORING_SPEC taxonomy

#### Metadata Fields (Optional but recommended)
- **version**: Application version for deployment correlation
- **instance_id**: Container/pod identifier for distributed debugging
- **correlation_id**: Cross-service operation tracking
- **trace_id**: Distributed tracing identifier
- **span_id**: Individual operation span identifier

### 2.3 Request ID Propagation Strategy

Request IDs MUST be propagated through the entire request lifecycle:

1. **Generation**: Created at API gateway using format `req_{8_char_alphanumeric}`
2. **Header Propagation**: Passed via `X-Request-ID` header between services
3. **Context Storage**: Stored in thread-local storage for automatic inclusion
4. **Database Correlation**: Included in all database operation logs
5. **External Service Calls**: Forwarded to AI providers and external APIs

**Implementation Pattern**:
```python
import contextvars
from typing import Optional

request_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('request_id', default=None)

def set_request_id(request_id: str) -> None:
    request_id_context.set(request_id)

def get_request_id() -> Optional[str]:
    return request_id_context.get()
```

---

## 3. Log Level Management and Filtering

### 3.1 Log Level Hierarchy

The system implements five log levels with specific usage guidelines:

#### DEBUG (Level 10)
- **Purpose**: Detailed diagnostic information for development and troubleshooting
- **When to Use**: Variable values, function entry/exit, detailed state information
- **Examples**:
  - Weight parsing intermediate steps
  - AI provider request/response payloads (sanitized)
  - Cache hit/miss details
  - Configuration reload steps

```json
{
  "log_level": "DEBUG",
  "message": "Weight parsing intermediate result",
  "context": {
    "operation_type": "weight_parsing",
    "raw_input": "5.2 lbs",
    "parsed_value": 5.2,
    "parsed_unit": "pounds",
    "conversion_factor": 0.453592
  }
}
```

#### INFO (Level 20)
- **Purpose**: General operational information confirming normal system behavior
- **When to Use**: Request start/completion, successful operations, system state changes
- **Examples**:
  - Successful weight comparisons
  - AI provider selection and response
  - Cache operations
  - Configuration updates

```json
{
  "log_level": "INFO",
  "message": "Weight comparison completed successfully",
  "context": {
    "operation_type": "weight_comparison",
    "provider_name": "openai",
    "template_id": "comparison_template_v1",
    "duration_ms": 1250,
    "status_code": 200
  }
}
```

#### WARN (Level 30)
- **Purpose**: Potentially harmful situations or recoverable errors
- **When to Use**: Circuit breaker state changes, retry attempts, degraded performance
- **Examples**:
  - AI provider timeouts with successful fallback
  - Cache connection issues with fallback to direct processing
  - Rate limiting approaching thresholds

```json
{
  "log_level": "WARN",
  "message": "AI provider circuit breaker opened, failing over to secondary provider",
  "context": {
    "operation_type": "ai_request",
    "provider_name": "openai",
    "circuit_breaker_state": "OPEN",
    "fallback_provider": "anthropic",
    "error_category": "INTEGRATION_ERROR"
  }
}
```

#### ERROR (Level 40)
- **Purpose**: Error events that allow the application to continue running
- **When to Use**: Handled exceptions, validation failures, external service failures
- **Examples**:
  - Invalid weight format submissions
  - AI provider authentication failures
  - Malformed configuration files

```json
{
  "log_level": "ERROR",
  "message": "Invalid weight format provided",
  "context": {
    "operation_type": "weight_validation",
    "error_category": "CLIENT_ERROR",
    "validation_error": "Unable to parse weight value: 'five pounds'",
    "expected_format": "numeric value with optional unit (e.g., '5.2 lbs')"
  }
}
```

#### FATAL (Level 50)
- **Purpose**: Critical errors that may cause application termination
- **When to Use**: Database connection failures, critical configuration errors, OOM conditions
- **Examples**:
  - Database unavailability
  - Critical configuration missing
  - Unrecoverable system errors

### 3.2 Dynamic Log Level Configuration

Log levels are configured via environment variables with hot-reload support:

```yaml
# config/base/app.yaml
logging:
  level: "${SIZECOMPARATOR_LOG_LEVEL:INFO}"
  format: "${SIZECOMPARATOR_LOG_FORMAT:json}"
  output: "${SIZECOMPARATOR_LOG_OUTPUT:stdout}"
  file_path: "${SIZECOMPARATOR_LOG_FILE:/var/log/sizecomparator/app.log}"
  
  # Service-specific log levels
  service_levels:
    backend_core: "${SIZECOMPARATOR_BACKEND_LOG_LEVEL:INFO}"
    ai_provider: "${SIZECOMPARATOR_AI_LOG_LEVEL:INFO}"
    weight_processor: "${SIZECOMPARATOR_WEIGHT_LOG_LEVEL:INFO}"
    cache_service: "${SIZECOMPARATOR_CACHE_LOG_LEVEL:INFO}"

  # Feature-specific log levels
  feature_levels:
    request_tracing: "${SIZECOMPARATOR_TRACE_LOG_LEVEL:DEBUG}"
    performance_monitoring: "${SIZECOMPARATOR_PERF_LOG_LEVEL:INFO}"
    circuit_breaker: "${SIZECOMPARATOR_CB_LOG_LEVEL:WARN}"
```

### 3.3 Filtering and Sampling

To manage log volume in high-traffic scenarios:

```yaml
logging:
  sampling:
    enabled: true
    rate: 0.1  # Sample 10% of DEBUG logs
    levels:
      DEBUG: 0.1    # 10% sampling
      INFO: 1.0     # No sampling
      WARN: 1.0     # No sampling
      ERROR: 1.0    # No sampling
      FATAL: 1.0    # No sampling
  
  filtering:
    # Exclude noisy endpoints from DEBUG logging
    exclude_paths:
      - "/health"
      - "/ready"
      - "/metrics"
    
    # Rate limiting for repetitive errors
    rate_limiting:
      enabled: true
      window_seconds: 60
      max_identical_logs: 10
```

---

## 4. PII Protection and Sensitive Data Masking

### 4.1 PII Protection Strategy

The logging framework implements comprehensive PII protection through multiple layers:

#### Data Classification
- **Public**: Non-sensitive operational data (timestamps, service names, status codes)
- **Internal**: Business data requiring protection (user IDs, request details)
- **Confidential**: Authentication data, API keys, personal information
- **Restricted**: Highly sensitive data that must never be logged

#### Sanitization Rules
All log entries MUST be processed through sanitization filters before output:

```python
import re
from typing import Dict, Any

class LogSanitizer:
    """Sanitizes log data to prevent PII leakage"""
    
    # Patterns for sensitive data detection
    SENSITIVE_PATTERNS = {
        'api_key': re.compile(r'(api[_-]?key|token|secret)["\s]*[:=]["\s]*([a-zA-Z0-9-_]{20,})', re.IGNORECASE),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'phone': re.compile(r'\b\d{3}-\d{3}-\d{4}\b'),
        'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    }
    
    # Fields that should never be logged
    BLOCKED_FIELDS = {
        'password', 'passwd', 'pwd', 'secret', 'private_key',
        'access_token', 'refresh_token', 'session_id', 'csrf_token'
    }
    
    # Environment variables to mask
    ENV_MASK_PATTERNS = [
        'SIZECOMPARATOR_OPENAI_API_KEY',
        'SIZECOMPARATOR_ANTHROPIC_API_KEY',
        'SIZECOMPARATOR_XAI_API_KEY',
        'SIZECOMPARATOR_DATABASE_URL',
        'SIZECOMPARATOR_REDIS_URL'
    ]
    
    @classmethod
    def sanitize_log_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize log data"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if key.lower() in cls.BLOCKED_FIELDS:
                    sanitized[key] = "[REDACTED]"
                elif isinstance(value, str):
                    sanitized[key] = cls._mask_sensitive_strings(value)
                elif isinstance(value, (dict, list)):
                    sanitized[key] = cls.sanitize_log_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [cls.sanitize_log_data(item) for item in data]
        elif isinstance(data, str):
            return cls._mask_sensitive_strings(data)
        return data
    
    @classmethod
    def _mask_sensitive_strings(cls, text: str) -> str:
        """Mask sensitive patterns in strings"""
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            text = pattern.sub(f'[{pattern_name.upper()}_MASKED]', text)
        return text
```

### 4.2 Environment Variable Protection

API keys and sensitive configuration MUST be masked in logs:

```python
def mask_environment_variables(log_data: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive environment variables in log context"""
    env_patterns = [
        r'SIZECOMPARATOR_.*_API_KEY',
        r'SIZECOMPARATOR_.*_SECRET',
        r'SIZECOMPARATOR_.*_PASSWORD',
        r'DATABASE_URL',
        r'REDIS_URL'
    ]
    
    for key, value in log_data.items():
        if isinstance(value, str):
            for pattern in env_patterns:
                if re.match(pattern, key, re.IGNORECASE):
                    # Mask all but first 4 and last 4 characters
                    if len(value) > 8:
                        masked = value[:4] + '*' * (len(value) - 8) + value[-4:]
                        log_data[key] = masked
                    else:
                        log_data[key] = '[MASKED]'
    
    return log_data
```

### 4.3 AI Provider Content Sanitization

Special handling for AI provider request/response logging:

```python
def sanitize_ai_content(content: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize AI provider request/response content"""
    sanitized = {}
    
    # Allow logging of system prompts and templates
    if 'system_prompt' in content:
        sanitized['system_prompt'] = content['system_prompt'][:200] + "..." if len(content['system_prompt']) > 200 else content['system_prompt']
    
    # Mask user input but preserve structure for debugging
    if 'user_input' in content:
        user_input = content['user_input']
        sanitized['user_input'] = {
            'length': len(user_input),
            'type': type(user_input).__name__,
            'contains_numbers': bool(re.search(r'\d', str(user_input))),
            'word_count': len(str(user_input).split())
        }
    
    # Log AI response metadata without content
    if 'ai_response' in content:
        response = content['ai_response']
        sanitized['ai_response'] = {
            'length': len(str(response)),
            'tokens_used': content.get('tokens_used', 0),
            'model': content.get('model', 'unknown'),
            'finish_reason': content.get('finish_reason', 'unknown')
        }
    
    return sanitized
```

---

## 5. Performance Logging and Request Tracing

### 5.1 Request Lifecycle Tracing

Every request generates a complete trace through the system with performance metrics:

#### Request Start Logging
```json
{
  "timestamp": "2024-07-13T14:30:45.123Z",
  "request_id": "req_abc123def456",
  "service_name": "backend-core",
  "log_level": "INFO",
  "message": "Request started",
  "context": {
    "operation_type": "weight_comparison",
    "endpoint": "/api/v1/weight/compare",
    "method": "POST",
    "user_agent": "SizeComparator-Client/1.0",
    "content_length": 1024,
    "request_start_time": "2024-07-13T14:30:45.123Z"
  },
  "metadata": {
    "trace_id": "trace_123456789",
    "span_id": "span_root"
  }
}
```

#### Service Call Tracing
```json
{
  "timestamp": "2024-07-13T14:30:45.456Z",
  "request_id": "req_abc123def456",
  "service_name": "ai-provider",
  "log_level": "INFO",
  "message": "AI provider request initiated",
  "context": {
    "operation_type": "ai_request",
    "provider_name": "openai",
    "model": "gpt-4",
    "template_id": "comparison_template_v1",
    "circuit_breaker_state": "CLOSED",
    "request_tokens": 150,
    "timeout_ms": 30000
  },
  "metadata": {
    "trace_id": "trace_123456789",
    "span_id": "span_ai_request",
    "parent_span_id": "span_root"
  }
}
```

#### Request Completion Logging
```json
{
  "timestamp": "2024-07-13T14:30:46.789Z",
  "request_id": "req_abc123def456",
  "service_name": "backend-core",
  "log_level": "INFO",
  "message": "Request completed",
  "context": {
    "operation_type": "weight_comparison",
    "endpoint": "/api/v1/weight/compare",
    "method": "POST",
    "status_code": 200,
    "duration_ms": 1666,
    "response_size_bytes": 512,
    "ai_provider_calls": 1,
    "cache_hits": 0,
    "cache_misses": 1
  },
  "performance": {
    "breakdown": {
      "validation_ms": 15,
      "weight_parsing_ms": 25,
      "ai_request_ms": 1200,
      "response_formatting_ms": 50,
      "total_ms": 1666
    },
    "resources": {
      "memory_used_mb": 45.2,
      "cpu_time_ms": 234
    }
  }
}
```

### 5.2 Performance Metrics Collection

The logging framework captures detailed performance metrics:

#### Database Operation Metrics
```python
class DatabaseLogger:
    """Logs database operations with performance metrics"""
    
    @staticmethod
    def log_query_performance(query_type: str, table: str, duration_ms: float, 
                            rows_affected: int, request_id: str):
        log_data = {
            "message": f"Database {query_type} completed",
            "context": {
                "operation_type": "database_operation",
                "query_type": query_type,
                "table": table,
                "duration_ms": duration_ms,
                "rows_affected": rows_affected,
                "slow_query": duration_ms > 1000
            }
        }
        
        if duration_ms > 1000:
            log_data["log_level"] = "WARN"
            log_data["context"]["performance_warning"] = "Slow query detected"
        else:
            log_data["log_level"] = "INFO"
            
        logger.log(log_data)
```

#### AI Provider Performance Tracking
```python
class AIProviderLogger:
    """Logs AI provider interactions with detailed metrics"""
    
    @staticmethod
    def log_provider_request(provider: str, model: str, tokens: int, 
                           duration_ms: float, success: bool, request_id: str):
        log_data = {
            "message": f"AI provider request {'completed' if success else 'failed'}",
            "log_level": "INFO" if success else "ERROR",
            "context": {
                "operation_type": "ai_request",
                "provider_name": provider,
                "model": model,
                "request_tokens": tokens,
                "duration_ms": duration_ms,
                "success": success,
                "tokens_per_second": tokens / (duration_ms / 1000) if duration_ms > 0 else 0
            }
        }
        
        if duration_ms > 30000:  # 30 second timeout
            log_data["log_level"] = "WARN"
            log_data["context"]["timeout_warning"] = True
            
        logger.log(log_data)
```

### 5.3 Circuit Breaker State Logging

Integration with AI_PROVIDER_SPEC circuit breaker monitoring:

```python
class CircuitBreakerLogger:
    """Logs circuit breaker state changes and health metrics"""
    
    @staticmethod
    def log_state_transition(provider: str, from_state: str, to_state: str, 
                           failure_count: int, request_id: str):
        log_data = {
            "message": f"Circuit breaker state transition: {from_state} -> {to_state}",
            "log_level": "WARN" if to_state == "OPEN" else "INFO",
            "context": {
                "operation_type": "circuit_breaker",
                "provider_name": provider,
                "circuit_breaker_state": to_state,
                "previous_state": from_state,
                "failure_count": failure_count,
                "state_change_reason": "failure_threshold_exceeded" if to_state == "OPEN" else "health_restored"
            }
        }
        
        if to_state == "OPEN":
            log_data["context"]["error_category"] = "INTEGRATION_ERROR"
            log_data["context"]["alert_required"] = True
            
        logger.log(log_data)
```

---

## 6. Log Aggregation and Rotation Strategies

### 6.1 Log Collection Architecture

The SizeComparator logging system implements a multi-tier collection strategy:

#### Local Collection
- **Structured Logging**: All services emit JSON logs to stdout/stderr
- **Log Rotation**: Local file rotation with size and time-based triggers
- **Buffer Management**: In-memory buffering with flush controls

#### Centralized Aggregation
```yaml
# Fluentd/Fluent Bit configuration for log shipping
<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

<filter sizecomparator.**>
  @type parser
  key_name message
  reserve_data true
  <parse>
    @type json
    time_key timestamp
    time_format %Y-%m-%dT%H:%M:%S.%LZ
  </parse>
</filter>

<filter sizecomparator.**>
  @type record_transformer
  enable_ruby true
  <record>
    cluster_name "#{ENV['CLUSTER_NAME']}"
    namespace "#{ENV['NAMESPACE']}"
    pod_name "#{ENV['POD_NAME']}"
  </record>
</filter>

<match sizecomparator.**>
  @type elasticsearch
  host elasticsearch.logging.svc.cluster.local
  port 9200
  index_name sizecomparator-logs
  type_name _doc
  logstash_format true
  logstash_prefix sizecomparator
  logstash_dateformat %Y%m%d
  include_timestamp true
  reload_connections false
  reconnect_on_error true
  reload_on_failure true
  <buffer>
    @type file
    path /var/log/fluentd-buffers/sizecomparator
    flush_mode interval
    flush_interval 10s
    chunk_limit_size 10m
    queue_limit_length 32
    retry_forever true
    retry_wait 1s
  </buffer>
</match>
```

### 6.2 Storage Strategy

#### Hot Storage (0-7 days)
- **Technology**: Elasticsearch cluster with SSD storage
- **Purpose**: Real-time search, alerting, and dashboard queries
- **Retention**: 7 days of full-text searchable logs
- **Indexing**: All fields indexed for fast query performance
- **Replicas**: 2 replicas for high availability

```json
{
  "index_patterns": ["sizecomparator-logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 2,
      "index.refresh_interval": "10s",
      "index.translog.flush_threshold_size": "1gb"
    },
    "mappings": {
      "properties": {
        "timestamp": {"type": "date"},
        "request_id": {"type": "keyword"},
        "service_name": {"type": "keyword"},
        "log_level": {"type": "keyword"},
        "message": {"type": "text", "analyzer": "standard"},
        "context": {
          "properties": {
            "operation_type": {"type": "keyword"},
            "provider_name": {"type": "keyword"},
            "circuit_breaker_state": {"type": "keyword"},
            "duration_ms": {"type": "long"},
            "status_code": {"type": "short"}
          }
        }
      }
    }
  }
}
```

#### Warm Storage (8-30 days)
- **Technology**: Elasticsearch with slower storage tier
- **Purpose**: Historical analysis and compliance requirements
- **Compression**: LZ4 compression to reduce storage costs
- **Reduced Indexing**: Limited field indexing for cost optimization

#### Cold Storage (31-365 days)
- **Technology**: S3/Object storage with high compression
- **Purpose**: Long-term retention for compliance and auditing
- **Format**: Compressed JSON lines with daily partitioning
- **Access**: Archived logs accessible via data lake queries

### 6.3 Log Rotation Configuration

#### File-based Rotation
```yaml
logging:
  rotation:
    enabled: true
    max_file_size: "100MB"
    max_files: 10
    rotation_time: "24h"
    compression: true
    
  # Service-specific rotation policies
  services:
    backend_core:
      max_file_size: "200MB"  # Higher volume service
      max_files: 15
    ai_provider:
      max_file_size: "50MB"   # Lower volume service
      max_files: 5
    
  # Log level specific retention
  level_retention:
    DEBUG: "24h"     # Debug logs rotated daily
    INFO: "7d"       # Info logs kept for a week
    WARN: "30d"      # Warnings kept for a month
    ERROR: "90d"     # Errors kept for 90 days
    FATAL: "1y"      # Fatal errors kept for a year
```

#### Kubernetes Log Rotation
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sizecomparator-log-config
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Path              /var/log/containers/sizecomparator-*.log
        Parser            cri
        Tag               sizecomparator.*
        Refresh_Interval  5
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On

    [FILTER]
        Name                kubernetes
        Match               sizecomparator.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Merge_Log           On
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off

    [OUTPUT]
        Name            es
        Match           sizecomparator.*
        Host            elasticsearch.logging.svc.cluster.local
        Port            9200
        Index           sizecomparator-logs
        Type            _doc
        Logstash_Format On
        Logstash_Prefix sizecomparator
        Retry_Limit     5
        Buffer_Size     5MB
        Workers         2
```

### 6.4 Performance Optimization

#### Indexing Strategy
```python
class LogIndexManager:
    """Manages Elasticsearch index optimization for log data"""
    
    @staticmethod
    def create_index_template():
        """Create optimized index template for log data"""
        return {
            "index_patterns": ["sizecomparator-logs-*"],
            "template": {
                "settings": {
                    "number_of_shards": 3,
                    "number_of_replicas": 1,
                    "index.refresh_interval": "30s",
                    "index.translog.flush_threshold_size": "512mb",
                    "index.merge.policy.max_merged_segment": "2gb",
                    "index.mapping.total_fields.limit": 2000
                },
                "mappings": {
                    "dynamic_templates": [
                        {
                            "strings_as_keywords": {
                                "match_mapping_type": "string",
                                "match": "*_id",
                                "mapping": {"type": "keyword"}
                            }
                        },
                        {
                            "numbers_as_long": {
                                "match_mapping_type": "long",
                                "match": "*_ms",
                                "mapping": {"type": "long"}
                            }
                        }
                    ]
                }
            }
        }
    
    @staticmethod
    def setup_lifecycle_policy():
        """Configure index lifecycle management"""
        return {
            "policy": {
                "phases": {
                    "hot": {
                        "actions": {
                            "rollover": {
                                "max_size": "5gb",
                                "max_age": "1d"
                            }
                        }
                    },
                    "warm": {
                        "min_age": "7d",
                        "actions": {
                            "allocate": {
                                "number_of_replicas": 0
                            },
                            "forcemerge": {
                                "max_num_segments": 1
                            }
                        }
                    },
                    "cold": {
                        "min_age": "30d",
                        "actions": {
                            "allocate": {
                                "number_of_replicas": 0
                            }
                        }
                    },
                    "delete": {
                        "min_age": "365d"
                    }
                }
            }
        }
```

---

## 7. Integration with System Components

### 7.1 FastAPI Backend Integration

The backend core integrates logging through middleware and dependency injection:

```python
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import time
import uuid
from typing import Callable

class LoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for request/response logging"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID and set context
        request_id = f"req_{uuid.uuid4().hex[:16]}"
        set_request_id(request_id)
        
        # Log request start
        start_time = time.time()
        logger.info("Request started", extra={
            "context": {
                "operation_type": "http_request",
                "endpoint": str(request.url.path),
                "method": request.method,
                "user_agent": request.headers.get("user-agent"),
                "content_length": request.headers.get("content-length", 0)
            }
        })
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful response
            logger.info("Request completed", extra={
                "context": {
                    "operation_type": "http_request",
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2)
                }
            })
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error response
            logger.error("Request failed", extra={
                "context": {
                    "operation_type": "http_request",
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "error_category": "SERVER_ERROR",
                    "duration_ms": round(duration_ms, 2),
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                }
            })
            raise

app = FastAPI()
app.add_middleware(LoggingMiddleware)
```

### 7.2 AI Provider Service Integration

AI provider calls include detailed logging with circuit breaker state tracking:

```python
from ai_provider_spec import AIProvider, CircuitBreakerState
import asyncio

class LoggingAIProvider(AIProvider):
    """AI Provider wrapper with comprehensive logging"""
    
    async def process_request(self, prompt: str, model: str) -> str:
        request_start = time.time()
        
        logger.info("AI provider request initiated", extra={
            "context": {
                "operation_type": "ai_request",
                "provider_name": self.provider_name,
                "model": model,
                "circuit_breaker_state": self.circuit_breaker.state.value,
                "prompt_length": len(prompt),
                "timeout_ms": self.timeout_ms
            }
        })
        
        try:
            if self.circuit_breaker.state == CircuitBreakerState.OPEN:
                logger.warn("Circuit breaker is OPEN, rejecting request", extra={
                    "context": {
                        "operation_type": "circuit_breaker",
                        "provider_name": self.provider_name,
                        "circuit_breaker_state": "OPEN",
                        "error_category": "INTEGRATION_ERROR"
                    }
                })
                raise CircuitBreakerOpenException()
            
            response = await self._make_api_call(prompt, model)
            duration_ms = (time.time() - request_start) * 1000
            
            # Log successful response
            logger.info("AI provider request completed", extra={
                "context": {
                    "operation_type": "ai_request",
                    "provider_name": self.provider_name,
                    "model": model,
                    "duration_ms": round(duration_ms, 2),
                    "response_length": len(response),
                    "circuit_breaker_state": self.circuit_breaker.state.value
                }
            })
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - request_start) * 1000
            
            logger.error("AI provider request failed", extra={
                "context": {
                    "operation_type": "ai_request",
                    "provider_name": self.provider_name,
                    "model": model,
                    "duration_ms": round(duration_ms, 2),
                    "error_category": "INTEGRATION_ERROR",
                    "exception_type": type(e).__name__,
                    "circuit_breaker_state": self.circuit_breaker.state.value
                }
            })
            
            # Update circuit breaker state
            self.circuit_breaker.record_failure()
            raise
```

### 7.3 Configuration System Integration

Hot-reload configuration changes with comprehensive logging:

```python
from config_system_spec import ConfigurationManager
import yaml

class LoggingConfigManager(ConfigurationManager):
    """Configuration manager with logging integration"""
    
    def reload_configuration(self, config_path: str) -> bool:
        """Reload configuration with detailed logging"""
        logger.info("Configuration reload initiated", extra={
            "context": {
                "operation_type": "config_reload",
                "config_path": config_path,
                "previous_version": self.current_version
            }
        })
        
        try:
            # Validate new configuration
            new_config = self._load_and_validate_config(config_path)
            
            # Apply configuration changes
            changes = self._calculate_config_diff(self.current_config, new_config)
            
            logger.info("Configuration changes detected", extra={
                "context": {
                    "operation_type": "config_reload",
                    "changes_count": len(changes),
                    "changed_sections": list(changes.keys())
                }
            })
            
            # Update logging configuration if changed
            if 'logging' in changes:
                self._update_logging_config(new_config['logging'])
                logger.info("Logging configuration updated", extra={
                    "context": {
                        "operation_type": "config_reload",
                        "new_log_level": new_config['logging']['level'],
                        "new_log_format": new_config['logging']['format']
                    }
                })
            
            self.current_config = new_config
            self.current_version = new_config['version']
            
            logger.info("Configuration reload completed successfully", extra={
                "context": {
                    "operation_type": "config_reload",
                    "new_version": self.current_version,
                    "reload_duration_ms": round((time.time() - start_time) * 1000, 2)
                }
            })
            
            return True
            
        except Exception as e:
            logger.error("Configuration reload failed", extra={
                "context": {
                    "operation_type": "config_reload",
                    "config_path": config_path,
                    "error_category": "SERVER_ERROR",
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                }
            })
            return False
```

---

## 8. Implementation Guidelines and Best Practices

### 8.1 Logger Configuration

```python
import structlog
import logging
import json
from pythonjsonlogger import jsonlogger

def configure_structured_logging():
    """Configure structured logging for the application"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, os.getenv('SIZECOMPARATOR_LOG_LEVEL', 'INFO'))
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_request_id_processor,
            sanitize_log_processor,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def add_request_id_processor(logger, method_name, event_dict):
    """Add request ID to all log entries"""
    request_id = get_request_id()
    if request_id:
        event_dict['request_id'] = request_id
    return event_dict

def sanitize_log_processor(logger, method_name, event_dict):
    """Sanitize sensitive data from log entries"""
    return LogSanitizer.sanitize_log_data(event_dict)
```

### 8.2 Testing and Validation

The logging framework includes comprehensive testing utilities:

```python
import pytest
from unittest.mock import patch, MagicMock
import json

class LoggingTestCase:
    """Base test case for logging functionality"""
    
    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing"""
        with patch('structlog.get_logger') as mock:
            yield mock.return_value
    
    def assert_log_structure(self, log_call, expected_level: str, expected_fields: list):
        """Assert log entry has correct structure"""
        args, kwargs = log_call
        log_data = kwargs.get('extra', {})
        
        # Check mandatory fields
        mandatory_fields = ['timestamp', 'request_id', 'service_name', 'log_level', 'message']
        for field in mandatory_fields:
            assert field in log_data, f"Missing mandatory field: {field}"
        
        # Check expected fields
        for field in expected_fields:
            assert field in log_data.get('context', {}), f"Missing expected field: {field}"
        
        # Validate log level
        assert log_data['log_level'] == expected_level
    
    def assert_no_pii_leakage(self, log_call):
        """Assert no PII data in log entry"""
        args, kwargs = log_call
        log_json = json.dumps(kwargs)
        
        # Check for common PII patterns
        pii_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b',  # Credit card
            r'sk-[a-zA-Z0-9]{48}',  # OpenAI API key pattern
        ]
        
        for pattern in pii_patterns:
            assert not re.search(pattern, log_json), f"PII pattern found: {pattern}"

# Example test cases
class TestRequestLogging(LoggingTestCase):
    
    def test_request_start_logging(self, mock_logger):
        """Test request start logging structure"""
        # Simulate request start
        log_request_start("/api/v1/weight/compare", "POST", "req_123")
        
        # Assert logging was called correctly
        mock_logger.info.assert_called_once()
        self.assert_log_structure(
            mock_logger.info.call_args,
            "INFO",
            ["operation_type", "endpoint", "method"]
        )
    
    def test_ai_provider_logging_no_pii(self, mock_logger):
        """Test AI provider logging doesn't leak PII"""
        # Simulate AI provider request with sensitive data
        log_ai_request("openai", "user@example.com asks about weight", "req_123")
        
        # Assert no PII leakage
        self.assert_no_pii_leakage(mock_logger.info.call_args)
```

### 8.3 Deployment Configuration

Production deployment configuration for the logging framework:

```yaml
# config/production/logging.yaml
logging:
  level: "INFO"
  format: "json"
  output: "stdout"
  
  # Production-specific settings
  sampling:
    enabled: true
    debug_rate: 0.01  # Sample 1% of debug logs in production
    
  # Enhanced PII protection for production
  pii_protection:
    strict_mode: true
    mask_user_data: true
    log_sanitization: true
    
  # Performance optimization
  async_logging: true
  buffer_size: 10000
  flush_interval: 5
  
  # Compliance settings
  retention:
    audit_logs: "7y"    # Compliance requirement
    error_logs: "2y"
    info_logs: "90d"
    debug_logs: "7d"

# Kubernetes deployment with logging
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sizecomparator-backend
spec:
  template:
    spec:
      containers:
      - name: backend
        image: sizecomparator/backend:latest
        env:
        - name: SIZECOMPARATOR_LOG_LEVEL
          value: "INFO"
        - name: SIZECOMPARATOR_LOG_FORMAT
          value: "json"
        - name: SIZECOMPARATOR_ENVIRONMENT
          value: "production"
        volumeMounts:
        - name: log-config
          mountPath: /app/config/logging.yaml
          subPath: logging.yaml
      volumes:
      - name: log-config
        configMap:
          name: sizecomparator-log-config
```

This comprehensive logging framework specification provides the foundation for observability, debugging, and operational excellence across the SizeComparator system, ensuring seamless integration with all components while maintaining security, performance, and compliance requirements.

---

## Success Criteria

The logging framework implementation is considered successful when:

1. **Structured Logging**: 100% of log entries conform to JSON structure specification
2. **Request Tracing**: All requests have complete trace through system with request ID propagation
3. **PII Protection**: Zero PII leakage incidents in production logs
4. **Performance**: Log processing adds <10ms latency to request handling
5. **Integration**: All system components (Backend Core, AI Providers, Config System) emit consistent logs
6. **Operational Excellence**: Mean Time To Detect (MTTD) <5 minutes for critical issues through log-based alerting
7. **Compliance**: Log retention and sanitization meets security and regulatory requirements