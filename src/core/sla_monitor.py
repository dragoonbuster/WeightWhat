"""
SLA monitoring and performance tracking system.

Implements 99% uptime and <2s response time SLA requirements from 
DEPLOYMENT_OPS_SPEC with comprehensive performance metrics and alerting.
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from .monitoring import get_logger, get_metrics, ErrorSeverity
from .exceptions import ErrorCategory


class SLAMetricType(Enum):
    """Types of SLA metrics tracked."""
    UPTIME = "uptime"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"
    THROUGHPUT = "throughput"


@dataclass
class SLATarget:
    """SLA target definition."""
    name: str
    metric_type: SLAMetricType
    target_value: float
    threshold_warning: float
    threshold_critical: float
    measurement_window_seconds: int = 300  # 5 minutes
    evaluation_period_seconds: int = 3600  # 1 hour


@dataclass
class SLAMeasurement:
    """Individual SLA measurement."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SLAViolation:
    """SLA violation record."""
    sla_name: str
    metric_type: SLAMetricType
    timestamp: datetime
    actual_value: float
    target_value: float
    severity: ErrorSeverity
    duration_seconds: float
    context: Dict[str, Any] = field(default_factory=dict)


class SLACalculator:
    """Calculator for various SLA metrics."""
    
    @staticmethod
    def calculate_uptime_percentage(
        measurements: List[SLAMeasurement],
        window_seconds: int
    ) -> float:
        """Calculate uptime percentage over time window."""
        if not measurements:
            return 100.0
        
        now = time.time()
        cutoff_time = now - window_seconds
        
        # Filter measurements to window
        recent_measurements = [
            m for m in measurements 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_measurements:
            return 100.0
        
        # Count successful vs failed measurements
        total_measurements = len(recent_measurements)
        successful_measurements = sum(
            1 for m in recent_measurements if m.value == 1.0
        )
        
        return (successful_measurements / total_measurements) * 100.0
    
    @staticmethod
    def calculate_response_time_percentile(
        measurements: List[SLAMeasurement],
        percentile: float,
        window_seconds: int
    ) -> float:
        """Calculate response time percentile over time window."""
        if not measurements:
            return 0.0
        
        now = time.time()
        cutoff_time = now - window_seconds
        
        # Filter measurements to window
        recent_measurements = [
            m for m in measurements 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_measurements:
            return 0.0
        
        # Extract response times and sort
        response_times = sorted([m.value for m in recent_measurements])
        
        if len(response_times) == 1:
            return response_times[0]
        
        # Calculate percentile
        index = int((percentile / 100.0) * (len(response_times) - 1))
        return response_times[index]
    
    @staticmethod
    def calculate_error_rate(
        error_measurements: List[SLAMeasurement],
        total_measurements: List[SLAMeasurement],
        window_seconds: int
    ) -> float:
        """Calculate error rate percentage over time window."""
        now = time.time()
        cutoff_time = now - window_seconds
        
        # Filter measurements to window
        recent_errors = [
            m for m in error_measurements 
            if m.timestamp >= cutoff_time
        ]
        recent_total = [
            m for m in total_measurements 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_total:
            return 0.0
        
        error_count = sum(m.value for m in recent_errors)
        total_count = sum(m.value for m in recent_total)
        
        if total_count == 0:
            return 0.0
        
        return (error_count / total_count) * 100.0
    
    @staticmethod
    def calculate_availability(
        health_measurements: List[SLAMeasurement],
        window_seconds: int
    ) -> float:
        """Calculate service availability over time window."""
        if not health_measurements:
            return 100.0
        
        now = time.time()
        cutoff_time = now - window_seconds
        
        # Filter measurements to window
        recent_measurements = [
            m for m in health_measurements 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_measurements:
            return 100.0
        
        # Calculate time-weighted availability
        total_time = 0
        available_time = 0
        
        for i, measurement in enumerate(recent_measurements):
            if i == 0:
                continue
            
            prev_measurement = recent_measurements[i - 1]
            duration = measurement.timestamp - prev_measurement.timestamp
            
            total_time += duration
            if prev_measurement.value == 1.0:  # Service was available
                available_time += duration
        
        if total_time == 0:
            return 100.0
        
        return (available_time / total_time) * 100.0
    
    @staticmethod
    def calculate_throughput(
        request_measurements: List[SLAMeasurement],
        window_seconds: int
    ) -> float:
        """Calculate requests per second over time window."""
        if not request_measurements:
            return 0.0
        
        now = time.time()
        cutoff_time = now - window_seconds
        
        # Filter measurements to window
        recent_measurements = [
            m for m in request_measurements 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_measurements:
            return 0.0
        
        total_requests = sum(m.value for m in recent_measurements)
        actual_window = min(window_seconds, now - recent_measurements[0].timestamp)
        
        if actual_window <= 0:
            return 0.0
        
        return total_requests / actual_window


class SLAMonitor:
    """
    SLA monitoring system for comprehensive performance tracking.
    
    Tracks multiple SLA targets and generates alerts when violations occur.
    Implements DEPLOYMENT_OPS_SPEC 99% uptime and <2s response time requirements.
    """
    
    def __init__(
        self,
        service_name: str = "sizecomparator",
        logger=None,
        metrics=None
    ):
        self.service_name = service_name
        self.logger = logger or get_logger()
        self.metrics = metrics or get_metrics()
        
        # SLA targets and measurements
        self.sla_targets: Dict[str, SLATarget] = {}
        self.measurements: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.violations: List[SLAViolation] = []
        
        # State tracking
        self.current_violations: Dict[str, SLAViolation] = {}
        self.last_evaluation: Dict[str, float] = {}
        
        # Performance counters
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.service_start_time = time.time()
        
        # Setup default SLA targets
        self._setup_default_sla_targets()
    
    def _setup_default_sla_targets(self):
        """Setup default SLA targets per DEPLOYMENT_OPS_SPEC."""
        
        # 99% uptime SLA
        self.register_sla_target(SLATarget(
            name="uptime_sla",
            metric_type=SLAMetricType.UPTIME,
            target_value=99.0,
            threshold_warning=98.5,
            threshold_critical=98.0,
            measurement_window_seconds=300,
            evaluation_period_seconds=3600
        ))
        
        # <2s response time SLA (P99)
        self.register_sla_target(SLATarget(
            name="response_time_p99_sla",
            metric_type=SLAMetricType.RESPONSE_TIME,
            target_value=2.0,
            threshold_warning=1.8,
            threshold_critical=2.2,
            measurement_window_seconds=300,
            evaluation_period_seconds=900
        ))
        
        # Error rate SLA
        self.register_sla_target(SLATarget(
            name="error_rate_sla",
            metric_type=SLAMetricType.ERROR_RATE,
            target_value=5.0,  # Max 5% error rate
            threshold_warning=3.0,
            threshold_critical=7.0,
            measurement_window_seconds=300,
            evaluation_period_seconds=600
        ))
        
        # Service availability SLA
        self.register_sla_target(SLATarget(
            name="availability_sla",
            metric_type=SLAMetricType.AVAILABILITY,
            target_value=99.0,
            threshold_warning=98.0,
            threshold_critical=97.0,
            measurement_window_seconds=3600,
            evaluation_period_seconds=3600
        ))
    
    def register_sla_target(self, target: SLATarget):
        """Register a new SLA target for monitoring."""
        self.sla_targets[target.name] = target
        
        self.logger.info(
            f"Registered SLA target: {target.name}",
            sla_name=target.name,
            metric_type=target.metric_type.value,
            target_value=target.target_value,
            warning_threshold=target.threshold_warning,
            critical_threshold=target.threshold_critical
        )
    
    def record_measurement(
        self,
        sla_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a measurement for SLA tracking."""
        measurement = SLAMeasurement(
            timestamp=time.time(),
            value=value,
            labels=labels or {},
            metadata=metadata or {}
        )
        
        self.measurements[sla_name].append(measurement)
        
        self.logger.debug(
            f"Recorded SLA measurement: {sla_name}",
            sla_name=sla_name,
            value=value,
            labels=labels,
            metadata=metadata
        )
    
    def record_request_performance(
        self,
        duration: float,
        status_code: int,
        endpoint: str,
        method: str
    ):
        """Record request performance for SLA calculations."""
        self.request_count += 1
        self.total_response_time += duration
        
        # Record uptime measurement (successful if not 5xx)
        uptime_value = 1.0 if status_code < 500 else 0.0
        self.record_measurement(
            "uptime_sla",
            uptime_value,
            labels={"endpoint": endpoint, "method": method},
            metadata={"status_code": status_code}
        )
        
        # Record response time measurement
        self.record_measurement(
            "response_time_p99_sla",
            duration,
            labels={"endpoint": endpoint, "method": method},
            metadata={"status_code": status_code}
        )
        
        # Record error measurement
        if status_code >= 400:
            self.error_count += 1
            self.record_measurement(
                "error_rate_sla",
                1.0,
                labels={"endpoint": endpoint, "method": method, "error_category": self._get_error_category(status_code)},
                metadata={"status_code": status_code}
            )
        
        # Record total request measurement for error rate calculation
        self.record_measurement(
            "error_rate_sla_total",
            1.0,
            labels={"endpoint": endpoint, "method": method},
            metadata={"status_code": status_code}
        )
    
    def record_service_health(self, is_healthy: bool):
        """Record service health for availability SLA."""
        self.record_measurement(
            "availability_sla",
            1.0 if is_healthy else 0.0,
            metadata={"health_check": True}
        )
    
    def evaluate_sla_compliance(self) -> Dict[str, Any]:
        """Evaluate all SLA targets and check for violations."""
        now = time.time()
        results = {}
        new_violations = []
        
        for sla_name, target in self.sla_targets.items():
            # Check if it's time to evaluate this SLA
            last_eval = self.last_evaluation.get(sla_name, 0)
            if now - last_eval < target.evaluation_period_seconds:
                continue
            
            self.last_evaluation[sla_name] = now
            
            # Calculate current metric value
            current_value = self._calculate_sla_metric(target)
            
            # Check for violations
            violation = self._check_sla_violation(target, current_value)
            
            if violation:
                new_violations.append(violation)
                
                # Check if this is a new violation
                if sla_name not in self.current_violations:
                    self.current_violations[sla_name] = violation
                    self._handle_sla_violation(violation)
                else:
                    # Update existing violation
                    existing = self.current_violations[sla_name]
                    existing.duration_seconds = now - existing.timestamp.timestamp()
            else:
                # Check if we recovered from a violation
                if sla_name in self.current_violations:
                    recovered_violation = self.current_violations.pop(sla_name)
                    self._handle_sla_recovery(recovered_violation, target, current_value)
            
            # Update Prometheus metrics
            self._update_sla_metrics(target, current_value)
            
            results[sla_name] = {
                'target_value': target.target_value,
                'current_value': current_value,
                'compliant': violation is None,
                'violation_severity': violation.severity.value if violation else None,
                'last_evaluation': now
            }
        
        # Store new violations
        self.violations.extend(new_violations)
        
        # Keep only recent violations (last 24 hours)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        self.violations = [
            v for v in self.violations 
            if v.timestamp > cutoff_time
        ]
        
        return results
    
    def _calculate_sla_metric(self, target: SLATarget) -> float:
        """Calculate current value for an SLA metric."""
        measurements = list(self.measurements.get(target.name, []))
        
        if target.metric_type == SLAMetricType.UPTIME:
            return SLACalculator.calculate_uptime_percentage(
                measurements, target.measurement_window_seconds
            )
        
        elif target.metric_type == SLAMetricType.RESPONSE_TIME:
            return SLACalculator.calculate_response_time_percentile(
                measurements, 99.0, target.measurement_window_seconds
            )
        
        elif target.metric_type == SLAMetricType.ERROR_RATE:
            error_measurements = measurements
            total_measurements = list(self.measurements.get(f"{target.name}_total", []))
            return SLACalculator.calculate_error_rate(
                error_measurements, total_measurements, target.measurement_window_seconds
            )
        
        elif target.metric_type == SLAMetricType.AVAILABILITY:
            return SLACalculator.calculate_availability(
                measurements, target.measurement_window_seconds
            )
        
        elif target.metric_type == SLAMetricType.THROUGHPUT:
            return SLACalculator.calculate_throughput(
                measurements, target.measurement_window_seconds
            )
        
        return 0.0
    
    def _check_sla_violation(self, target: SLATarget, current_value: float) -> Optional[SLAViolation]:
        """Check if current value violates SLA target."""
        violation_threshold = None
        severity = None
        
        # Determine violation type based on metric
        if target.metric_type in [SLAMetricType.UPTIME, SLAMetricType.AVAILABILITY]:
            # For uptime/availability, lower values are worse
            if current_value <= target.threshold_critical:
                violation_threshold = target.threshold_critical
                severity = ErrorSeverity.CRITICAL
            elif current_value <= target.threshold_warning:
                violation_threshold = target.threshold_warning
                severity = ErrorSeverity.WARNING
        
        elif target.metric_type in [SLAMetricType.RESPONSE_TIME, SLAMetricType.ERROR_RATE]:
            # For response time/error rate, higher values are worse
            if current_value >= target.threshold_critical:
                violation_threshold = target.threshold_critical
                severity = ErrorSeverity.CRITICAL
            elif current_value >= target.threshold_warning:
                violation_threshold = target.threshold_warning
                severity = ErrorSeverity.WARNING
        
        if violation_threshold is not None:
            return SLAViolation(
                sla_name=target.name,
                metric_type=target.metric_type,
                timestamp=datetime.now(timezone.utc),
                actual_value=current_value,
                target_value=target.target_value,
                severity=severity,
                duration_seconds=0.0,
                context={
                    'measurement_window_seconds': target.measurement_window_seconds,
                    'violation_threshold': violation_threshold
                }
            )
        
        return None
    
    def _handle_sla_violation(self, violation: SLAViolation):
        """Handle a new SLA violation."""
        
        # Log violation
        if violation.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(
                f"SLA violation - {violation.sla_name}",
                sla_name=violation.sla_name,
                metric_type=violation.metric_type.value,
                actual_value=violation.actual_value,
                target_value=violation.target_value,
                severity=violation.severity.value
            )
        else:
            self.logger.warning(
                f"SLA violation - {violation.sla_name}",
                sla_name=violation.sla_name,
                metric_type=violation.metric_type.value,
                actual_value=violation.actual_value,
                target_value=violation.target_value,
                severity=violation.severity.value
            )
    
    def _handle_sla_recovery(
        self, 
        violation: SLAViolation, 
        target: SLATarget, 
        current_value: float
    ):
        """Handle recovery from SLA violation."""
        
        self.logger.info(
            f"SLA recovery - {violation.sla_name}",
            sla_name=violation.sla_name,
            metric_type=violation.metric_type.value,
            current_value=current_value,
            target_value=target.target_value,
            violation_duration_seconds=violation.duration_seconds
        )
    
    def _update_sla_metrics(self, target: SLATarget, current_value: float):
        """Update Prometheus metrics for SLA monitoring."""
        # Update SLA compliance metric
        metric_name = f"sla_{target.metric_type.value}_current"
        
        if hasattr(self.metrics, 'sla_uptime') and target.metric_type == SLAMetricType.UPTIME:
            self.metrics.sla_uptime.set(current_value)
        
        if hasattr(self.metrics, 'sla_response_time_p99') and target.metric_type == SLAMetricType.RESPONSE_TIME:
            self.metrics.sla_response_time_p99.set(current_value)
    
    def _get_error_category(self, status_code: int) -> str:
        """Get error category from status code."""
        if 400 <= status_code < 500:
            return ErrorCategory.CLIENT_ERROR.value
        elif 500 <= status_code < 600:
            return ErrorCategory.SERVER_ERROR.value
        else:
            return "unknown"
    
    def get_sla_summary(self) -> Dict[str, Any]:
        """Get comprehensive SLA summary."""
        now = time.time()
        service_uptime = now - self.service_start_time
        
        summary = {
            'service_name': self.service_name,
            'service_uptime_seconds': service_uptime,
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'overall_error_rate': (self.error_count / self.request_count * 100) if self.request_count > 0 else 0,
            'average_response_time': (self.total_response_time / self.request_count) if self.request_count > 0 else 0,
            'current_violations': len(self.current_violations),
            'total_violations_24h': len(self.violations),
            'sla_targets': {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Add individual SLA target status
        for sla_name, target in self.sla_targets.items():
            current_value = self._calculate_sla_metric(target)
            violation = self._check_sla_violation(target, current_value)
            
            summary['sla_targets'][sla_name] = {
                'metric_type': target.metric_type.value,
                'target_value': target.target_value,
                'current_value': current_value,
                'compliant': violation is None,
                'violation_severity': violation.severity.value if violation else None,
                'measurement_window_seconds': target.measurement_window_seconds
            }
        
        return summary
    
    def get_violation_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get violation history for specified hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_violations = [
            v for v in self.violations 
            if v.timestamp > cutoff_time
        ]
        
        return [
            {
                'sla_name': v.sla_name,
                'metric_type': v.metric_type.value,
                'timestamp': v.timestamp.isoformat(),
                'actual_value': v.actual_value,
                'target_value': v.target_value,
                'severity': v.severity.value,
                'duration_seconds': v.duration_seconds,
                'context': v.context
            }
            for v in recent_violations
        ]
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous SLA monitoring."""
        self.logger.info(
            "Starting SLA monitoring",
            interval_seconds=interval_seconds,
            sla_targets=list(self.sla_targets.keys())
        )
        
        while True:
            try:
                results = self.evaluate_sla_compliance()
                
                self.logger.debug(
                    "SLA evaluation completed",
                    results=results,
                    current_violations=len(self.current_violations)
                )
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(
                    "Error during SLA monitoring",
                    error=str(e)
                )
                await asyncio.sleep(interval_seconds)