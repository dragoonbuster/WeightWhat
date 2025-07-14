"""
Prometheus Metrics API Endpoint

This module implements the metrics endpoint for DEPLOYMENT_OPS_SPEC compliance:
- GET /metrics - Prometheus-formatted metrics for monitoring systems
- Exposes application, system, and business metrics
- Supports both text and JSON formats
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Response, Query
from fastapi.responses import PlainTextResponse
import psutil

from ...models.responses import MetricsResponse
from ..main import get_metrics_service, get_config_service, app_state

logger = logging.getLogger(__name__)

metrics_router = APIRouter()


@metrics_router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Metrics endpoint in Prometheus format for monitoring and alerting systems",
    responses={
        200: {
            "description": "Metrics in Prometheus text format",
            "content": {
                "text/plain": {
                    "example": """# HELP sizecomparator_requests_total Total requests processed
# TYPE sizecomparator_requests_total counter
sizecomparator_requests_total{method="POST",endpoint="/api/v1/compare",status="200"} 125
sizecomparator_requests_total{method="GET",endpoint="/health",status="200"} 2486

# HELP sizecomparator_request_duration_seconds Request processing duration
# TYPE sizecomparator_request_duration_seconds histogram
sizecomparator_request_duration_seconds_bucket{endpoint="/api/v1/compare",le="0.1"} 23
sizecomparator_request_duration_seconds_bucket{endpoint="/api/v1/compare",le="0.5"} 87
sizecomparator_request_duration_seconds_bucket{endpoint="/api/v1/compare",le="1.0"} 118
sizecomparator_request_duration_seconds_bucket{endpoint="/api/v1/compare",le="+Inf"} 125
sizecomparator_request_duration_seconds_sum{endpoint="/api/v1/compare"} 45.3
sizecomparator_request_duration_seconds_count{endpoint="/api/v1/compare"} 125"""
                }
            }
        }
    }
)
async def prometheus_metrics(
    format: Optional[str] = Query(default="text", description="Output format: 'text' or 'json'"),
    metrics_service = Depends(get_metrics_service),
    config_service = Depends(get_config_service)
):
    """
    Prometheus metrics endpoint for monitoring integration.
    
    Exposes application metrics in Prometheus format for monitoring
    and alerting systems like Prometheus, Grafana, and others.
    
    Metrics include:
    - Request counters and durations (RED pattern)
    - AI provider performance metrics
    - System resource usage
    - Business metrics (weight comparisons)
    - Cache operation metrics
    """
    
    try:
        # Collect current metrics
        current_metrics = await _collect_current_metrics(metrics_service, config_service)
        
        if format.lower() == "json":
            # Return JSON format for API consumption
            return MetricsResponse(
                metrics=current_metrics,
                timestamp=datetime.utcnow()
            )
        else:
            # Return Prometheus text format (default)
            prometheus_text = _format_prometheus_metrics(current_metrics)
            return PlainTextResponse(
                content=prometheus_text,
                media_type="text/plain; version=0.0.4; charset=utf-8"
            )
            
    except Exception as e:
        logger.error(f"Failed to collect metrics: {e}")
        # Return minimal error metrics
        error_metrics = [
            {
                "name": "sizecomparator_metrics_collection_errors_total",
                "help": "Total metrics collection errors",
                "type": "counter",
                "samples": [{"value": 1, "labels": {"error": str(e)[:100]}}]
            }
        ]
        
        if format.lower() == "json":
            return MetricsResponse(metrics=error_metrics)
        else:
            return PlainTextResponse(
                content=_format_prometheus_metrics(error_metrics),
                media_type="text/plain; version=0.0.4; charset=utf-8"
            )


async def _collect_current_metrics(metrics_service, config_service) -> list[Dict[str, Any]]:
    """Collect current application metrics"""
    
    metrics = []
    
    # Get stored metrics from metrics service
    if metrics_service:
        stored_metrics = metrics_service.get_metrics()
        
        # Convert counters to Prometheus format
        for counter_key, value in stored_metrics.get("counters", {}).items():
            metric_name, labels_str = _parse_metric_key(counter_key)
            labels = _parse_labels(labels_str)
            
            # Find or create metric
            metric = _find_or_create_metric(metrics, metric_name, "counter")
            metric["samples"].append({"value": value, "labels": labels})
        
        # Convert histograms to Prometheus format
        for hist_key, values in stored_metrics.get("histograms", {}).items():
            metric_name, labels_str = _parse_metric_key(hist_key)
            labels = _parse_labels(labels_str)
            
            if values:
                # Create histogram buckets
                metric = _find_or_create_metric(metrics, metric_name, "histogram")
                
                # Calculate histogram statistics
                sorted_values = sorted(values)
                total_count = len(values)
                total_sum = sum(values)
                
                # Add buckets (0.1, 0.5, 1.0, 2.0, 5.0, +Inf)
                buckets = [0.1, 0.5, 1.0, 2.0, 5.0, float("inf")]
                for le in buckets:
                    count = sum(1 for v in sorted_values if v <= le)
                    bucket_labels = {**labels, "le": str(le) if le != float("inf") else "+Inf"}
                    metric["samples"].append({
                        "metric_name": f"{metric_name}_bucket",
                        "value": count,
                        "labels": bucket_labels
                    })
                
                # Add sum and count
                metric["samples"].append({
                    "metric_name": f"{metric_name}_sum",
                    "value": total_sum,
                    "labels": labels
                })
                metric["samples"].append({
                    "metric_name": f"{metric_name}_count", 
                    "value": total_count,
                    "labels": labels
                })
        
        # Convert gauges to Prometheus format
        for gauge_key, value in stored_metrics.get("gauges", {}).items():
            metric_name, labels_str = _parse_metric_key(gauge_key)
            labels = _parse_labels(labels_str)
            
            metric = _find_or_create_metric(metrics, metric_name, "gauge")
            metric["samples"].append({"value": value, "labels": labels})
    
    # Add system metrics
    _add_system_metrics(metrics)
    
    # Add application metrics
    _add_application_metrics(metrics, config_service)
    
    return metrics


def _parse_metric_key(key: str) -> tuple[str, str]:
    """Parse metric key into name and labels"""
    if ":" in key:
        parts = key.split(":", 1)
        return parts[0], parts[1] if len(parts) > 1 else ""
    return key, ""


def _parse_labels(labels_str: str) -> Dict[str, str]:
    """Parse labels string into dictionary"""
    if not labels_str:
        return {}
    
    labels = {}
    for label_pair in labels_str.split(":"):
        if "=" in label_pair:
            key, value = label_pair.split("=", 1)
            labels[key] = value
    
    return labels


def _find_or_create_metric(metrics: list, name: str, metric_type: str) -> Dict[str, Any]:
    """Find existing metric or create new one"""
    for metric in metrics:
        if metric["name"] == name:
            return metric
    
    # Create new metric
    new_metric = {
        "name": name,
        "type": metric_type,
        "samples": []
    }
    
    # Add help text based on metric name
    help_text = _get_help_text(name)
    if help_text:
        new_metric["help"] = help_text
    
    metrics.append(new_metric)
    return new_metric


def _get_help_text(metric_name: str) -> Optional[str]:
    """Get help text for metric"""
    help_texts = {
        "sizecomparator_requests_total": "Total requests processed",
        "sizecomparator_request_duration_seconds": "Request processing duration",
        "sizecomparator_ai_provider_requests_total": "AI provider requests",
        "sizecomparator_ai_provider_duration_seconds": "AI provider response time",
        "sizecomparator_cache_operations_total": "Cache operations",
        "sizecomparator_weight_comparisons_total": "Total weight comparisons processed",
        "sizecomparator_memory_usage_bytes": "Current memory usage",
        "sizecomparator_cpu_usage_percent": "Current CPU usage percentage",
        "sizecomparator_uptime_seconds": "Application uptime",
        "sizecomparator_active_connections": "Current active connections"
    }
    return help_texts.get(metric_name)


def _add_system_metrics(metrics: list):
    """Add system resource metrics"""
    try:
        process = psutil.Process()
        
        # Memory usage
        memory_metric = _find_or_create_metric(metrics, "sizecomparator_memory_usage_bytes", "gauge")
        memory_metric["samples"].append({
            "value": process.memory_info().rss,
            "labels": {"type": "rss"}
        })
        memory_metric["samples"].append({
            "value": process.memory_info().vms,
            "labels": {"type": "vms"}
        })
        
        # CPU usage
        cpu_metric = _find_or_create_metric(metrics, "sizecomparator_cpu_usage_percent", "gauge")
        cpu_metric["samples"].append({
            "value": process.cpu_percent(),
            "labels": {}
        })
        
        # Thread count
        threads_metric = _find_or_create_metric(metrics, "sizecomparator_threads_total", "gauge")
        threads_metric["samples"].append({
            "value": process.num_threads(),
            "labels": {}
        })
        
    except Exception as e:
        logger.warning(f"Failed to collect system metrics: {e}")


def _add_application_metrics(metrics: list, config_service):
    """Add application-specific metrics"""
    try:
        # Uptime
        startup_time = app_state.get("startup_time")
        if startup_time:
            uptime_seconds = (datetime.utcnow() - startup_time).total_seconds()
            uptime_metric = _find_or_create_metric(metrics, "sizecomparator_uptime_seconds", "gauge")
            uptime_metric["samples"].append({
                "value": int(uptime_seconds),
                "labels": {}
            })
        
        # Service status
        services = [
            ("config_service", app_state.get("config_service") is not None),
            ("comparison_service", app_state.get("comparison_service") is not None),
            ("weight_processor", app_state.get("weight_processor") is not None),
            ("cache_service", app_state.get("cache_service") is not None),
            ("ai_provider_factory", app_state.get("ai_provider_factory") is not None)
        ]
        
        service_metric = _find_or_create_metric(metrics, "sizecomparator_service_status", "gauge")
        for service_name, is_healthy in services:
            service_metric["samples"].append({
                "value": 1 if is_healthy else 0,
                "labels": {"service": service_name}
            })
        
        # Application info
        if config_service:
            version = config_service.get_section("application.version", "unknown")
            environment = config_service.get_section("application.environment", "unknown")
            
            info_metric = _find_or_create_metric(metrics, "sizecomparator_info", "gauge")
            info_metric["samples"].append({
                "value": 1,
                "labels": {
                    "version": version,
                    "environment": environment
                }
            })
        
    except Exception as e:
        logger.warning(f"Failed to collect application metrics: {e}")


def _format_prometheus_metrics(metrics: list[Dict[str, Any]]) -> str:
    """Format metrics in Prometheus text format"""
    lines = []
    
    for metric in metrics:
        # Add HELP line
        if "help" in metric:
            lines.append(f"# HELP {metric['name']} {metric['help']}")
        
        # Add TYPE line
        lines.append(f"# TYPE {metric['name']} {metric['type']}")
        
        # Add metric samples
        for sample in metric.get("samples", []):
            # Determine metric name (could be modified for histograms)
            sample_name = sample.get("metric_name", metric["name"])
            
            # Format labels
            labels = sample.get("labels", {})
            if labels:
                label_pairs = [f'{k}="{v}"' for k, v in labels.items()]
                label_str = "{" + ",".join(label_pairs) + "}"
            else:
                label_str = ""
            
            # Format value
            value = sample["value"]
            if isinstance(value, float):
                value_str = f"{value:.6f}".rstrip("0").rstrip(".")
            else:
                value_str = str(value)
            
            lines.append(f"{sample_name}{label_str} {value_str}")
        
        # Add blank line between metrics
        lines.append("")
    
    return "\n".join(lines)