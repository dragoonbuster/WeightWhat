# Metrics Collection and Monitoring Specification for SizeComparator

## Overview

This specification defines a comprehensive metrics collection and monitoring strategy for the SizeComparator system that aligns with ERROR_MONITORING_SPEC requirements and integrates with DEPLOYMENT_OPS_SPEC health monitoring. The metrics framework emphasizes Prometheus-based collection, RED (Rate, Errors, Duration) methodology, custom AI provider monitoring, performance tracking for 99% uptime SLA compliance, and operational excellence through intelligent alerting and cardinality optimization.

## 1. Prometheus Metrics Collection Architecture (1 page)

### 1.1 RED Metrics Implementation

**Core RED Metrics Framework**:
```python
# Rate - Requests per second
sizecomparator_requests_total{method="POST", endpoint="/api/v1/compare", status="200"} 1250
sizecomparator_requests_total{method="GET", endpoint="/api/v1/health", status="200"} 4800

# Errors - Error rate by category (aligned with ERROR_MONITORING_SPEC)
sizecomparator_errors_total{category="CLIENT_ERROR", endpoint="/api/v1/compare", error_code="INVALID_WEIGHT_FORMAT"} 45
sizecomparator_errors_total{category="INTEGRATION_ERROR", provider="openai", error_code="TIMEOUT"} 12
sizecomparator_errors_total{category="SERVER_ERROR", component="weight_processor", error_code="MEMORY_LIMIT"} 3

# Duration - Response time percentiles
sizecomparator_request_duration_seconds{endpoint="/api/v1/compare", quantile="0.50"} 0.45
sizecomparator_request_duration_seconds{endpoint="/api/v1/compare", quantile="0.95"} 1.2
sizecomparator_request_duration_seconds{endpoint="/api/v1/compare", quantile="0.99"} 2.1
```

**Business Metrics Collection**:
```python
# Weight comparison processing
sizecomparator_comparisons_processed_total{template_type="relative", ai_provider="openai"} 890
sizecomparator_comparisons_processed_total{template_type="absolute", ai_provider="anthropic"} 234

# AI provider utilization and success rates
sizecomparator_ai_provider_requests_total{provider="openai", status="success"} 800
sizecomparator_ai_provider_requests_total{provider="anthropic", status="circuit_open"} 50
sizecomparator_ai_provider_requests_total{provider="xai", status="rate_limited"} 25

# Template rendering performance
sizecomparator_template_renders_total{template_id="weight_comparison", provider="openai", status="success"} 750
sizecomparator_template_cache_hits_total{template_type="relative"} 1200
sizecomparator_template_cache_misses_total{template_type="absolute"} 150
```

### 1.2 Metrics Exposition Integration

**Prometheus Endpoint Configuration** (aligned with DEPLOYMENT_OPS_SPEC /metrics):
```python
from prometheus_client import CollectorRegistry, generate_latest, Counter, Histogram, Gauge
from fastapi import FastAPI
from fastapi.responses import Response

# Initialize metrics registry
metrics_registry = CollectorRegistry()

# Core application metrics
request_counter = Counter(
    'sizecomparator_requests_total',
    'Total requests processed',
    ['method', 'endpoint', 'status'],
    registry=metrics_registry
)

request_duration = Histogram(
    'sizecomparator_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
    registry=metrics_registry
)

# AI provider specific metrics
ai_provider_requests = Counter(
    'sizecomparator_ai_provider_requests_total',
    'AI provider requests',
    ['provider', 'status'],
    registry=metrics_registry
)

circuit_breaker_state = Gauge(
    'sizecomparator_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half_open, 2=open)',
    ['provider'],
    registry=metrics_registry
)

@app.get("/api/v1/metrics")
async def metrics_endpoint():
    """Expose Prometheus metrics for DEPLOYMENT_OPS_SPEC monitoring"""
    return Response(
        generate_latest(metrics_registry),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )
```

**Metrics Collection Middleware**:
```python
import time
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        
        # Track request
        request_counter.labels(
            method=request.method,
            endpoint=request.url.path,
            status="processing"
        ).inc()
        
        try:
            response = await call_next(request)
            
            # Record successful request
            duration = time.time() - start_time
            request_duration.labels(endpoint=request.url.path).observe(duration)
            request_counter.labels(
                method=request.method,
                endpoint=request.url.path,
                status=str(response.status_code)
            ).inc()
            
            return response
            
        except Exception as e:
            # Record error (integrated with ERROR_MONITORING_SPEC)
            duration = time.time() - start_time
            request_duration.labels(endpoint=request.url.path).observe(duration)
            
            error_category = determine_error_category(e)
            request_counter.labels(
                method=request.method,
                endpoint=request.url.path,
                status="error"
            ).inc()
            
            raise
```

## 2. Custom AI Provider Monitoring Metrics (1.5 pages)

### 2.1 Provider-Specific Metric Definitions

**Circuit Breaker State Monitoring** (aligned with AI_PROVIDER_SPEC):
```python
# Circuit breaker state tracking
sizecomparator_circuit_breaker_state{provider="openai"} 0  # CLOSED
sizecomparator_circuit_breaker_state{provider="anthropic"} 2  # OPEN
sizecomparator_circuit_breaker_state{provider="xai"} 1  # HALF_OPEN

# Circuit breaker transitions
sizecomparator_circuit_breaker_transitions_total{provider="openai", from_state="closed", to_state="open"} 3
sizecomparator_circuit_breaker_transitions_total{provider="anthropic", from_state="open", to_state="half_open"} 8

# Provider health status
sizecomparator_provider_health_status{provider="openai", status="healthy"} 1
sizecomparator_provider_health_status{provider="anthropic", status="unhealthy"} 1
sizecomparator_provider_health_status{provider="xai", status="degraded"} 1
```

**AI Provider Performance Metrics**:
```python
# Response time tracking per provider
sizecomparator_ai_response_duration_seconds{provider="openai", operation="weight_comparison", quantile="0.95"} 1.8
sizecomparator_ai_response_duration_seconds{provider="anthropic", operation="weight_comparison", quantile="0.95"} 2.3
sizecomparator_ai_response_duration_seconds{provider="xai", operation="weight_comparison", quantile="0.95"} 1.5

# Token usage and cost tracking
sizecomparator_ai_tokens_used_total{provider="openai", token_type="input"} 125000
sizecomparator_ai_tokens_used_total{provider="openai", token_type="output"} 45000
sizecomparator_ai_cost_usd_total{provider="openai"} 12.50
sizecomparator_ai_cost_usd_total{provider="anthropic"} 8.75

# Rate limit monitoring
sizecomparator_ai_rate_limit_remaining{provider="openai", limit_type="requests_per_minute"} 2850
sizecomparator_ai_rate_limit_remaining{provider="anthropic", limit_type="tokens_per_minute"} 95000
sizecomparator_ai_rate_limit_violations_total{provider="xai", limit_type="requests_per_minute"} 12

# Provider failover tracking
sizecomparator_ai_failover_events_total{from_provider="openai", to_provider="anthropic", reason="circuit_open"} 5
sizecomparator_ai_failover_events_total{from_provider="anthropic", to_provider="xai", reason="timeout"} 3
```

### 2.2 Custom Metrics Implementation

**AI Provider Metrics Collector**:
```python
from dataclasses import dataclass
from typing import Dict, Optional
import asyncio

@dataclass
class ProviderMetrics:
    requests_total: int
    errors_total: int
    response_time_p95: float
    circuit_breaker_state: str
    rate_limit_remaining: int
    tokens_used: int
    cost_usd: float

class AIProviderMetricsCollector:
    def __init__(self):
        self.provider_metrics = Gauge(
            'sizecomparator_provider_response_time_p95',
            'Provider response time 95th percentile',
            ['provider'],
            registry=metrics_registry
        )
        
        self.token_usage = Counter(
            'sizecomparator_ai_tokens_used_total',
            'Total tokens used by provider',
            ['provider', 'token_type'],
            registry=metrics_registry
        )
        
        self.cost_tracking = Counter(
            'sizecomparator_ai_cost_usd_total',
            'Total cost in USD by provider',
            ['provider'],
            registry=metrics_registry
        )
    
    async def collect_provider_metrics(self, provider_name: str, response_data: dict):
        """Collect metrics from AI provider response"""
        # Response time tracking
        if 'response_time' in response_data:
            self.provider_metrics.labels(provider=provider_name).set(
                response_data['response_time']
            )
        
        # Token usage tracking
        if 'usage' in response_data:
            usage = response_data['usage']
            self.token_usage.labels(
                provider=provider_name, 
                token_type='input'
            ).inc(usage.get('prompt_tokens', 0))
            
            self.token_usage.labels(
                provider=provider_name, 
                token_type='output'
            ).inc(usage.get('completion_tokens', 0))
        
        # Cost calculation and tracking
        cost = self.calculate_cost(provider_name, response_data)
        if cost > 0:
            self.cost_tracking.labels(provider=provider_name).inc(cost)
    
    def calculate_cost(self, provider_name: str, response_data: dict) -> float:
        """Calculate cost based on provider pricing"""
        pricing_map = {
            'openai': {'input': 0.0001, 'output': 0.0002},  # per token
            'anthropic': {'input': 0.00008, 'output': 0.00024},
            'xai': {'input': 0.00005, 'output': 0.00015}
        }
        
        if provider_name not in pricing_map or 'usage' not in response_data:
            return 0.0
        
        usage = response_data['usage']
        rates = pricing_map[provider_name]
        
        input_cost = usage.get('prompt_tokens', 0) * rates['input']
        output_cost = usage.get('completion_tokens', 0) * rates['output']
        
        return input_cost + output_cost
```

**Circuit Breaker Metrics Integration**:
```python
class CircuitBreakerMetrics:
    def __init__(self):
        self.state_gauge = Gauge(
            'sizecomparator_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=half_open, 2=open)',
            ['provider'],
            registry=metrics_registry
        )
        
        self.transitions_counter = Counter(
            'sizecomparator_circuit_breaker_transitions_total',
            'Circuit breaker state transitions',
            ['provider', 'from_state', 'to_state'],
            registry=metrics_registry
        )
    
    def record_state_change(self, provider: str, from_state: str, to_state: str):
        """Record circuit breaker state transitions"""
        state_values = {'closed': 0, 'half_open': 1, 'open': 2}
        
        self.state_gauge.labels(provider=provider).set(state_values[to_state])
        self.transitions_counter.labels(
            provider=provider,
            from_state=from_state,
            to_state=to_state
        ).inc()
        
        # Log state change for ERROR_MONITORING_SPEC integration
        logger.warning(
            f"Circuit breaker state change",
            extra={
                'provider': provider,
                'from_state': from_state,
                'to_state': to_state,
                'component': 'circuit_breaker',
                'category': 'INTEGRATION_ERROR' if to_state == 'open' else 'INFO'
            }
        )
```

## 3. Performance Monitoring and SLA Tracking (1 page)

### 3.1 SLA Compliance Metrics

**99% Uptime SLA Tracking** (aligned with DEPLOYMENT_OPS_SPEC requirements):
```python
# Uptime tracking
sizecomparator_uptime_percentage{period="1h"} 99.95
sizecomparator_uptime_percentage{period="24h"} 99.8
sizecomparator_uptime_percentage{period="30d"} 99.2

# SLA breach tracking
sizecomparator_sla_breaches_total{sla_type="uptime", threshold="99%"} 2
sizecomparator_sla_breaches_total{sla_type="response_time", threshold="2s"} 8

# Response time SLA compliance
sizecomparator_response_time_sla_compliance{endpoint="/api/v1/compare", threshold="2s"} 0.98
sizecomparator_response_time_sla_compliance{endpoint="/api/v1/health", threshold="500ms"} 0.999

# Service availability by component
sizecomparator_component_availability{component="ai_provider_service"} 0.992
sizecomparator_component_availability{component="weight_processor"} 0.998
sizecomparator_component_availability{component="cache_service"} 0.995
```

**Performance Baseline Metrics**:
```python
class SLAMetricsCollector:
    def __init__(self):
        self.uptime_gauge = Gauge(
            'sizecomparator_uptime_percentage',
            'Service uptime percentage',
            ['period'],
            registry=metrics_registry
        )
        
        self.sla_compliance = Gauge(
            'sizecomparator_response_time_sla_compliance',
            'Response time SLA compliance rate',
            ['endpoint', 'threshold'],
            registry=metrics_registry
        )
        
        self.sla_breaches = Counter(
            'sizecomparator_sla_breaches_total',
            'Total SLA breaches',
            ['sla_type', 'threshold'],
            registry=metrics_registry
        )
    
    async def calculate_sla_metrics(self):
        """Calculate SLA compliance metrics"""
        # Calculate uptime for different periods
        for period in ['1h', '24h', '30d']:
            uptime_pct = await self.calculate_uptime_percentage(period)
            self.uptime_gauge.labels(period=period).set(uptime_pct)
            
            # Track SLA breaches
            if uptime_pct < 99.0:
                self.sla_breaches.labels(
                    sla_type='uptime',
                    threshold='99%'
                ).inc()
        
        # Calculate response time compliance
        for endpoint in ['/api/v1/compare', '/api/v1/health']:
            compliance_rate = await self.calculate_response_time_compliance(
                endpoint, threshold_ms=2000
            )
            self.sla_compliance.labels(
                endpoint=endpoint,
                threshold='2s'
            ).set(compliance_rate)
    
    async def calculate_uptime_percentage(self, period: str) -> float:
        """Calculate uptime percentage for given period"""
        # Implementation would query health check history
        # and calculate percentage of successful checks
        pass
    
    async def calculate_response_time_compliance(self, endpoint: str, threshold_ms: int) -> float:
        """Calculate percentage of requests meeting response time SLA"""
        # Implementation would analyze request duration metrics
        # and calculate compliance rate
        pass
```

### 3.2 Resource Utilization Monitoring

**System Resource Metrics**:
```python
# CPU and memory utilization
sizecomparator_cpu_usage_percent{instance="pod-1"} 45.2
sizecomparator_memory_usage_bytes{instance="pod-1", type="heap"} 1073741824
sizecomparator_memory_usage_percent{instance="pod-1"} 68.5

# AI provider connection pool metrics
sizecomparator_connection_pool_active{provider="openai"} 8
sizecomparator_connection_pool_idle{provider="anthropic"} 12
sizecomparator_connection_pool_max{provider="xai"} 20

# Cache performance metrics
sizecomparator_cache_hit_ratio{cache_type="template"} 0.85
sizecomparator_cache_evictions_total{cache_type="response", reason="ttl_expired"} 450
sizecomparator_cache_size_bytes{cache_type="template"} 52428800
```

## 4. Metric Cardinality Management and Optimization (1 page)

### 4.1 Cardinality Control Strategy

**Label Limitation Framework**:
```python
# Maximum labels per metric: 10 (Prometheus best practice)
# High cardinality labels to avoid:
# - request_id (use for logging, not metrics)
# - user_id (aggregate to user_type)
# - timestamp (use implicit timestamp)
# - detailed error messages (use error_code)

# Good: Limited cardinality
sizecomparator_requests_total{method="POST", endpoint="/api/v1/compare", status="200"}

# Bad: High cardinality (avoid)
# sizecomparator_requests_total{method="POST", endpoint="/api/v1/compare", status="200", request_id="uuid-123", user_id="user-456"}
```

**Metric Aggregation Rules**:
```python
class MetricCardinalityController:
    def __init__(self):
        self.max_labels_per_metric = 10
        self.label_whitelist = {
            'method': ['GET', 'POST', 'PUT', 'DELETE'],
            'status': ['200', '400', '401', '403', '404', '429', '500', '502', '503'],
            'provider': ['openai', 'anthropic', 'xai'],
            'error_category': ['CLIENT_ERROR', 'SERVER_ERROR', 'INTEGRATION_ERROR', 'BUSINESS_LOGIC_ERROR'],
            'endpoint': ['/api/v1/compare', '/api/v1/health', '/api/v1/ready', '/api/v1/metrics']
        }
    
    def sanitize_labels(self, labels: Dict[str, str]) -> Dict[str, str]:
        """Sanitize labels to prevent cardinality explosion"""
        sanitized = {}
        
        for key, value in labels.items():
            if key in self.label_whitelist:
                # Use only whitelisted values
                if value in self.label_whitelist[key]:
                    sanitized[key] = value
                else:
                    sanitized[key] = 'other'
            else:
                # Skip non-whitelisted labels
                continue
        
        return sanitized
    
    def aggregate_error_metrics(self, error_type: str) -> str:
        """Aggregate detailed errors into categories"""
        error_mappings = {
            'timeout': 'INTEGRATION_ERROR',
            'rate_limited': 'INTEGRATION_ERROR',
            'invalid_api_key': 'INTEGRATION_ERROR',
            'validation_failed': 'CLIENT_ERROR',
            'invalid_weight': 'CLIENT_ERROR',
            'memory_error': 'SERVER_ERROR',
            'config_error': 'SERVER_ERROR'
        }
        
        return error_mappings.get(error_type, 'SERVER_ERROR')
```

### 4.2 Metric Retention and Storage Optimization

**Retention Policy Configuration**:
```yaml
# Prometheus retention configuration
retention_policies:
  high_frequency_metrics:  # Every 15s
    patterns:
      - sizecomparator_requests_total
      - sizecomparator_request_duration_seconds
      - sizecomparator_circuit_breaker_state
    retention: 7d
    
  medium_frequency_metrics:  # Every 60s
    patterns:
      - sizecomparator_ai_provider_*
      - sizecomparator_cache_*
      - sizecomparator_uptime_*
    retention: 30d
    
  low_frequency_metrics:  # Every 300s
    patterns:
      - sizecomparator_cost_*
      - sizecomparator_sla_*
    retention: 90d
```

**Storage Optimization Strategy**:
```python
# Metric sampling for high-volume endpoints
class MetricSampler:
    def __init__(self):
        self.sample_rates = {
            '/api/v1/health': 0.1,  # Sample 10% of health checks
            '/api/v1/ready': 0.1,   # Sample 10% of readiness checks
            '/api/v1/compare': 1.0, # Sample 100% of business operations
            '/api/v1/metrics': 0.05 # Sample 5% of metrics requests
        }
    
    def should_record_metric(self, endpoint: str) -> bool:
        """Determine if metric should be recorded based on sampling rate"""
        import random
        sample_rate = self.sample_rates.get(endpoint, 1.0)
        return random.random() < sample_rate
```

## 5. Alert Threshold Configuration and Notification (1.5 pages)

### 5.1 Intelligent Alert Thresholds

**Dynamic Threshold Configuration** (aligned with ERROR_MONITORING_SPEC alert levels):
```yaml
# alert_thresholds.yml
critical_alerts:
  service_down:
    metric: sizecomparator_uptime_percentage{period="5m"}
    condition: "< 95"
    duration: 1m
    severity: critical
    notification: ["pagerduty", "slack-critical"]
    
  circuit_breaker_open:
    metric: sizecomparator_circuit_breaker_state
    condition: "== 2"  # OPEN state
    duration: 30s
    severity: critical
    notification: ["pagerduty", "slack-critical"]
    context:
      runbook: "https://wiki.company.com/runbooks/circuit-breaker-recovery"
      
  high_error_rate:
    metric: rate(sizecomparator_errors_total[5m])
    condition: "> 0.1"  # >10% error rate
    duration: 2m
    severity: critical
    notification: ["pagerduty", "slack-critical"]

warning_alerts:
  degraded_performance:
    metric: sizecomparator_request_duration_seconds{quantile="0.95"}
    condition: "> 2.0"  # >2s response time
    duration: 5m
    severity: warning
    notification: ["slack-alerts"]
    
  ai_provider_degraded:
    metric: sizecomparator_provider_health_status{status="degraded"}
    condition: "== 1"
    duration: 2m
    severity: warning
    notification: ["slack-alerts"]
    
  cache_miss_rate_high:
    metric: sizecomparator_cache_hit_ratio
    condition: "< 0.7"  # <70% hit rate
    duration: 10m
    severity: warning
    notification: ["slack-alerts"]

info_alerts:
  circuit_breaker_recovery:
    metric: sizecomparator_circuit_breaker_transitions_total{to_state="closed"}
    condition: "increase(1m) > 0"
    duration: 0s
    severity: info
    notification: ["slack-info"]
    
  cost_threshold_reached:
    metric: increase(sizecomparator_ai_cost_usd_total[1h])
    condition: "> 50"  # >$50/hour
    duration: 0s
    severity: info
    notification: ["slack-finance"]
```

### 5.2 Alert Fatigue Prevention

**Intelligent Alert Grouping**:
```python
class AlertManager:
    def __init__(self):
        self.alert_groups = {}
        self.silence_periods = {
            'circuit_breaker_flapping': 300,  # 5 minutes
            'rate_limit_burst': 600,          # 10 minutes
            'config_reload': 120              # 2 minutes
        }
    
    def should_send_alert(self, alert_type: str, labels: Dict[str, str]) -> bool:
        """Determine if alert should be sent based on grouping and silence rules"""
        # Group similar alerts
        group_key = self.create_group_key(alert_type, labels)
        
        if group_key in self.alert_groups:
            last_sent = self.alert_groups[group_key]['last_sent']
            silence_period = self.silence_periods.get(alert_type, 60)
            
            if time.time() - last_sent < silence_period:
                return False
        
        # Update group tracking
        self.alert_groups[group_key] = {
            'last_sent': time.time(),
            'count': self.alert_groups.get(group_key, {}).get('count', 0) + 1
        }
        
        return True
    
    def create_group_key(self, alert_type: str, labels: Dict[str, str]) -> str:
        """Create grouping key for similar alerts"""
        # Group by alert type and key labels
        key_labels = ['provider', 'endpoint', 'component']
        group_parts = [alert_type]
        
        for label in key_labels:
            if label in labels:
                group_parts.append(f"{label}:{labels[label]}")
        
        return "_".join(group_parts)
```

**Contextual Alert Enhancement**:
```python
class ContextualAlerting:
    def __init__(self):
        self.context_providers = {
            'circuit_breaker': self.get_circuit_breaker_context,
            'high_latency': self.get_performance_context,
            'error_spike': self.get_error_context
        }
    
    async def enhance_alert(self, alert_type: str, labels: Dict[str, str]) -> Dict[str, Any]:
        """Add contextual information to alerts"""
        base_alert = {
            'alert_type': alert_type,
            'labels': labels,
            'timestamp': time.time(),
            'severity': self.determine_severity(alert_type, labels)
        }
        
        # Add context if provider exists
        if alert_type in self.context_providers:
            context = await self.context_providers[alert_type](labels)
            base_alert['context'] = context
        
        return base_alert
    
    async def get_circuit_breaker_context(self, labels: Dict[str, str]) -> Dict[str, Any]:
        """Get circuit breaker specific context"""
        provider = labels.get('provider')
        if not provider:
            return {}
        
        return {
            'recent_errors': await self.get_recent_error_count(provider),
            'success_rate_24h': await self.get_success_rate(provider, '24h'),
            'last_successful_request': await self.get_last_success_time(provider),
            'suggested_actions': [
                f"Check {provider} API status",
                "Verify API credentials",
                "Review rate limiting"
            ]
        }
    
    async def get_performance_context(self, labels: Dict[str, str]) -> Dict[str, Any]:
        """Get performance degradation context"""
        endpoint = labels.get('endpoint')
        return {
            'p95_trend_1h': await self.get_latency_trend(endpoint, '1h'),
            'concurrent_requests': await self.get_concurrent_requests(endpoint),
            'resource_utilization': await self.get_resource_usage(),
            'suggested_actions': [
                "Check AI provider response times",
                "Review system resource usage",
                "Consider scaling up"
            ]
        }
```

### 5.3 Notification Channel Integration

**Multi-Channel Notification Strategy**:
```python
class NotificationManager:
    def __init__(self):
        self.channels = {
            'pagerduty': PagerDutyNotifier(),
            'slack-critical': SlackNotifier(channel='#alerts-critical'),
            'slack-alerts': SlackNotifier(channel='#alerts'),
            'slack-info': SlackNotifier(channel='#monitoring'),
            'slack-finance': SlackNotifier(channel='#finance-alerts'),
            'email': EmailNotifier(),
            'webhook': WebhookNotifier()
        }
    
    async def send_alert(self, alert: Dict[str, Any], channels: List[str]):
        """Send alert to specified notification channels"""
        tasks = []
        
        for channel_name in channels:
            if channel_name in self.channels:
                notifier = self.channels[channel_name]
                tasks.append(notifier.send(alert))
        
        # Send to all channels concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def format_alert_for_slack(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Format alert for Slack notification"""
        severity_colors = {
            'critical': '#FF0000',
            'warning': '#FFA500', 
            'info': '#00FF00'
        }
        
        return {
            'attachments': [{
                'color': severity_colors.get(alert['severity'], '#808080'),
                'title': f"SizeComparator Alert: {alert['alert_type']}",
                'fields': [
                    {
                        'title': 'Severity',
                        'value': alert['severity'].upper(),
                        'short': True
                    },
                    {
                        'title': 'Component',
                        'value': alert['labels'].get('component', 'Unknown'),
                        'short': True
                    },
                    {
                        'title': 'Details',
                        'value': self.format_alert_details(alert),
                        'short': False
                    }
                ],
                'footer': 'SizeComparator Monitoring',
                'ts': int(alert['timestamp'])
            }]
        }
    
    def format_alert_details(self, alert: Dict[str, Any]) -> str:
        """Format alert details for human consumption"""
        details = []
        
        # Add basic information
        for key, value in alert['labels'].items():
            details.append(f"*{key.title()}*: {value}")
        
        # Add context if available
        if 'context' in alert:
            context = alert['context']
            if 'suggested_actions' in context:
                details.append("\n*Suggested Actions*:")
                for action in context['suggested_actions']:
                    details.append(f"• {action}")
        
        return "\n".join(details)
```

## Integration Matrix and Success Metrics

### Cross-Component Integration Points
| Component | Metric Integration | Alert Integration | Health Check Integration |
|-----------|-------------------|-------------------|-------------------------|
| ERROR_MONITORING_SPEC | Structured error metrics with request IDs | Error category-based alerting | Circuit breaker state monitoring |
| DEPLOYMENT_OPS_SPEC | SLA compliance metrics via /metrics endpoint | Health check failures trigger alerts | Uptime percentage calculation |
| AI_PROVIDER_SPEC | Provider health and circuit breaker metrics | Provider failover alerts | Provider connectivity checks |
| CONFIG_SYSTEM_SPEC | Configuration reload metrics | Config validation failure alerts | Hot-reload status monitoring |
| BACKEND_CORE_SPEC | Request/response metrics with error categories | Endpoint-specific performance alerts | FastAPI health endpoint integration |

### Success Criteria
- **Metric Collection**: 99.9% successful metric collection with <1% data loss
- **Alert Accuracy**: <5% false positive rate, <2% false negative rate for critical alerts
- **Performance Impact**: <2% overhead from metrics collection on application performance
- **Cardinality Control**: <10,000 active time series per service instance
- **Alert Response**: Mean Time to Alert (MTTA) <2 minutes for critical issues
- **Integration**: 100% compatibility with DEPLOYMENT_OPS_SPEC health monitoring and ERROR_MONITORING_SPEC error tracking

This comprehensive metrics collection specification ensures robust monitoring and observability for the SizeComparator system while maintaining optimal performance and operational excellence through intelligent alerting and efficient resource utilization.