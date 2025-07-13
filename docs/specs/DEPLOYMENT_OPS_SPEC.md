# SizeComparator Deployment & Operations Specification

Last Updated: 2025-07-13

## 1. Executive Summary & SLA Requirements

### Project Deployment Overview

SizeComparator deployment emphasizes simplicity, reliability, and operational excellence through containerization and automated CI/CD pipelines. The system must maintain 99% uptime while supporting AI provider integration and graceful degradation.

### Service Level Agreements (SLA)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Uptime | 99% | Monthly availability |
| Response Time | < 2 seconds (95th percentile) | API endpoint monitoring |
| Recovery Time | < 5 minutes | From failure detection |
| Deployment Success | 99% | CI/CD pipeline success rate |

### Component Integration Architecture

```
Load Balancer
     ↓
SizeComparator Container (FastAPI + Static Frontend)
     ↓
Health Check Endpoints (/health, /ready, /metrics)
     ↓
AI Provider Health Monitoring (OpenAI, Anthropic, X.ai)
     ↓
Error Monitoring & Alerting (Prometheus + Grafana)
```

## 2. Health Check System Integration

### Health Endpoints (BACKEND_CORE_SPEC Integration)

**Primary Health Endpoint**: `GET /api/v1/health`
```json
{
    "status": "healthy|degraded|unhealthy",
    "timestamp": "2025-07-13T10:30:00Z",
    "version": "1.0.0",
    "components": {
        "database": "healthy",
        "ai_providers": "degraded",
        "configuration": "healthy"
    }
}
```

**Readiness Endpoint**: `GET /api/v1/ready`
```json
{
    "ready": true,
    "checks": {
        "ai_provider_connectivity": "pass",
        "configuration_loaded": "pass",
        "memory_usage": "pass",
        "disk_space": "pass"
    },
    "timestamp": "2025-07-13T10:30:00Z",
    "details": {
        "ai_providers": {
            "openai": "healthy",
            "anthropic": "circuit_open",
            "xai": "healthy"
        }
    }
}
```

**Metrics Endpoint**: `GET /api/v1/metrics`
```
# HELP sizecomparator_requests_total Total requests processed
# TYPE sizecomparator_requests_total counter
sizecomparator_requests_total{method="POST",endpoint="/api/compare",status="200"} 1250

# HELP sizecomparator_ai_provider_requests AI provider request metrics
# TYPE sizecomparator_ai_provider_requests counter
sizecomparator_ai_provider_requests{provider="openai",status="success"} 800
sizecomparator_ai_provider_requests{provider="anthropic",status="circuit_open"} 50
```

### AI Provider Health Integration (AI_PROVIDER_SPEC)

```python
# Health check implementation
async def check_ai_provider_health():
    health_status = {
        "openai": await openai_provider.get_health_status(),
        "anthropic": await anthropic_provider.get_health_status(), 
        "xai": await xai_provider.get_health_status()
    }
    
    # Circuit breaker state integration
    overall_status = determine_overall_health(health_status)
    return overall_status
```

## 3. Environment Management (CONFIG_SYSTEM_SPEC Integration)

### Required Environment Variables

**Core Application Variables**:
```bash
SIZECOMPARATOR_ENVIRONMENT=production
SIZECOMPARATOR_LOG_LEVEL=info
SIZECOMPARATOR_LOG_FORMAT=json
SIZECOMPARATOR_API_HOST=0.0.0.0
SIZECOMPARATOR_API_PORT=8000
SIZECOMPARATOR_WORKERS=4
```

**AI Provider Configuration**:
```bash
SIZECOMPARATOR_OPENAI_API_KEY=sk-...
SIZECOMPARATOR_ANTHROPIC_API_KEY=sk-ant-...
SIZECOMPARATOR_XAI_API_KEY=xai-...
SIZECOMPARATOR_AI_TIMEOUT_SECONDS=30
SIZECOMPARATOR_AI_MAX_RETRIES=3
SIZECOMPARATOR_AI_CIRCUIT_BREAKER_THRESHOLD=5
```

**Monitoring Integration**:
```bash
SIZECOMPARATOR_METRICS_ENABLED=true
SIZECOMPARATOR_METRICS_PORT=9090
SIZECOMPARATOR_HEALTH_CHECK_INTERVAL=30
SIZECOMPARATOR_ALERT_WEBHOOK_URL=https://hooks.slack.com/...
```

### Environment Variable Validation Script

```bash
#!/bin/bash
# validate_environment.sh
set -e

# Required variables
required_vars=(
    "SIZECOMPARATOR_OPENAI_API_KEY"
    "SIZECOMPARATOR_ANTHROPIC_API_KEY" 
    "SIZECOMPARATOR_XAI_API_KEY"
    "SIZECOMPARATOR_ENVIRONMENT"
)

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

echo "✅ Environment validation passed"
```

## 4. Container Architecture & Build Process

### Multi-Stage Dockerfile

```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim
RUN groupadd -g 999 sizecomparator && \
    useradd -r -u 999 -g sizecomparator sizecomparator

COPY --from=builder /root/.local /home/sizecomparator/.local
COPY --chown=sizecomparator:sizecomparator . /app

USER sizecomparator
WORKDIR /app
ENV PATH=/home/sizecomparator/.local/bin:$PATH

EXPOSE 8000 9090
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Security Hardening

- Non-root user execution
- Minimal base image (python:3.11-slim)
- No package managers in final image
- Regular vulnerability scanning in CI/CD

## 5. CI/CD Pipeline (TESTING_SPEC Integration)

### GitHub Actions Workflow

```yaml
name: Deploy SizeComparator
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      
      - name: Run tests with coverage (TESTING_SPEC)
        run: |
          pytest tests/ --cov=src --cov-report=xml --cov-fail-under=80
          mypy src/
          ruff check src/
      
      - name: Test AI provider mocks
        run: pytest tests/integration/test_ai_providers.py -v

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Vulnerability scan
        run: |
          pip install safety bandit
          safety check -r requirements.txt
          bandit -r src/

  deploy:
    needs: [test, security]
    runs-on: ubuntu-latest
    steps:
      - name: Build and push Docker image
        run: |
          docker build -t sizecomparator:${{ github.sha }} .
          docker tag sizecomparator:${{ github.sha }} sizecomparator:latest
      
      - name: Deploy with zero downtime
        run: |
          # Blue-green deployment strategy
          ./scripts/deploy.sh ${{ github.sha }}
```

## 6. Monitoring & Alerting (ERROR_MONITORING_SPEC Integration)

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'sizecomparator'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/api/v1/metrics'
    scrape_interval: 30s
```

### Alert Rules

```yaml
# alerts.yml
groups:
  - name: sizecomparator_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(sizecomparator_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: AIProviderDown
        expr: sizecomparator_ai_provider_health{status="unhealthy"} == 1
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "AI provider {{ $labels.provider }} is unhealthy"
          
      - alert: CircuitBreakerOpen
        expr: sizecomparator_circuit_breaker_state{state="open"} == 1
        for: 30s
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker open for {{ $labels.provider }}"
```

### Grafana Dashboard Configuration

Key metrics to monitor:
- Request rate and response times (RED metrics)
- AI provider health and response times
- Circuit breaker state transitions
- Error rate by category (ERROR_MONITORING_SPEC)
- System resource utilization

## 7. Scaling & Performance Strategy

### Horizontal Pod Autoscaling (AI-Aware)

```yaml
# hpa.yml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sizecomparator-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sizecomparator
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: ai_provider_queue_length
        target:
          type: AverageValue
          averageValue: "5"
```

### AI Provider Rate Limit Management

```python
# Rate limit aware scaling
class AIProviderLoadBalancer:
    def __init__(self):
        self.provider_limits = {
            "openai": 3500,    # RPM
            "anthropic": 1000, # RPM  
            "xai": 500         # RPM
        }
    
    def should_scale_up(self) -> bool:
        current_load = self.calculate_current_load()
        total_capacity = sum(self.provider_limits.values())
        return current_load > (total_capacity * 0.8)
```

## 8. Incident Response & Recovery

### Incident Response Runbook

**Critical Incident (Service Down)**:
1. Check health endpoints: `/api/v1/health` and `/api/v1/ready`
2. Verify AI provider connectivity
3. Check error logs for patterns (ERROR_MONITORING_SPEC categories)
4. Initiate rollback if deployment-related
5. Scale up if capacity issue

**AI Provider Degradation**:
1. Monitor circuit breaker states via `/api/v1/metrics`
2. Verify provider failover working correctly
3. Check rate limiting and quota usage
4. Update provider priority if needed

### Automated Recovery

```python
# Automated recovery procedures
class RecoveryManager:
    async def handle_ai_provider_failure(self, provider: str):
        # Circuit breaker will handle immediate failover
        # This handles longer-term recovery
        
        if await self.is_provider_recovered(provider):
            await self.reset_circuit_breaker(provider)
            await self.gradually_restore_traffic(provider)
        
    async def handle_high_error_rate(self):
        # Scale up immediately if resource constrained
        if await self.is_resource_constrained():
            await self.trigger_scale_up()
        
        # Otherwise investigate and alert
        await self.trigger_investigation_alert()
```

### Zero-Downtime Deployment Process

```bash
#!/bin/bash
# deploy.sh - Zero downtime deployment script

VERSION=$1
CURRENT_SERVICE="sizecomparator-blue"
NEW_SERVICE="sizecomparator-green"

# Deploy new version
echo "Deploying version $VERSION to $NEW_SERVICE"
kubectl set image deployment/$NEW_SERVICE app=sizecomparator:$VERSION

# Wait for rollout
kubectl rollout status deployment/$NEW_SERVICE --timeout=300s

# Health check new deployment
for i in {1..30}; do
    if curl -f http://$NEW_SERVICE/api/v1/ready; then
        echo "Health check passed"
        break
    fi
    sleep 10
done

# Switch traffic
kubectl patch service sizecomparator -p '{"spec":{"selector":{"version":"'$VERSION'"}}}'

# Verify traffic switch
sleep 30
if curl -f http://sizecomparator/api/v1/health; then
    echo "Traffic switch successful"
    # Scale down old version
    kubectl scale deployment $CURRENT_SERVICE --replicas=0
else
    echo "Traffic switch failed, rolling back"
    kubectl patch service sizecomparator -p '{"spec":{"selector":{"version":"previous"}}}'
    exit 1
fi
```

## Integration Validation Checklist

### Component Integration Requirements

- [x] **BACKEND_CORE_SPEC**: Health endpoints implemented with exact `HealthResponse` models
- [x] **CONFIG_SYSTEM_SPEC**: All `SIZECOMPARATOR_*` environment variables properly configured
- [x] **ERROR_MONITORING_SPEC**: Structured logging with request ID propagation
- [x] **TESTING_SPEC**: Complete test pipeline with 80%+ coverage requirements
- [x] **AI_PROVIDER_SPEC**: Circuit breaker states and provider health monitoring
- [x] **FRONTEND_SPEC**: Static file serving and theme system deployment

### Operational Excellence Verification

- [x] 99% uptime SLA monitoring in place
- [x] Cross-component incident response procedures defined
- [x] Integrated capacity planning considering all AI provider rate limits
- [x] SLA definitions encompassing all component requirements
- [x] Zero-downtime deployment with automated rollback capability

This deployment specification ensures reliable operation of the SizeComparator system while maintaining the required 99% uptime SLA through proper monitoring, scaling, and incident response procedures.