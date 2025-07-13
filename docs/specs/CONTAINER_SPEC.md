# Container Specification Prompt for SizeComparator

Create a comprehensive 5-page specification document (CONTAINER_SPEC.md) for Docker containerization of the SizeComparator application. This specification must provide production-ready containerization guidelines with advanced security hardening, optimization techniques, and operational excellence practices.

## Required Sections and Content:

### 1. Multi-Stage Docker Build Architecture (1 page)

**Build Stage Requirements:**
- **Stage 1 - Dependencies**: Python 3.11-slim base, pip wheel compilation, dependency caching
- **Stage 2 - Security Scanning**: Integration with Trivy/Snyk for vulnerability scanning
- **Stage 3 - Application Build**: Code compilation, static analysis, type checking
- **Stage 4 - Production Runtime**: Minimal attack surface, distroless considerations

**Security Hardening in Build Process:**
```dockerfile
# Example structure to detail:
FROM python:3.11-slim AS dependencies
# - Use specific image digests for reproducibility
# - Install only build essentials
# - Create wheel files for all dependencies
# - Implement pip hash checking

FROM dependencies AS security-scan
# - Run Trivy/Snyk vulnerability scanning
# - SAST tools integration (bandit, safety)
# - License compliance checking
# - Generate SBOM (Software Bill of Materials)

FROM python:3.11-slim AS runtime
# - Non-root user creation (UID/GID 1001)
# - Remove package managers and shells
# - Set read-only root filesystem
# - Configure AppArmor/SELinux profiles
```

**Build Arguments and Secrets Management:**
- ARG usage for build-time configuration
- BuildKit secrets mounting for sensitive data
- Multi-platform build support (linux/amd64, linux/arm64)
- Layer caching optimization strategies

### 2. Container Size and Performance Optimization (1 page)

**Size Reduction Techniques:**
- Alpine vs slim base image analysis with benchmarks
- Dependency optimization (pip --no-cache-dir, --no-compile)
- Multi-stage artifact copying strategies
- Static binary compilation where applicable
- Image layer deduplication techniques

**Performance Optimization:**
- Python optimization flags (PYTHONOPTIMIZE=2)
- Precompiled .pyc file generation
- Memory allocation tuning (PYTHONMALLOC)
- FastAPI/Uvicorn worker configuration
- Connection pooling for Redis/Database
- Startup time optimization techniques

**Benchmark Requirements:**
- Final image size < 150MB
- Container startup time < 5 seconds
- Memory footprint < 256MB idle
- CPU efficiency metrics

### 3. Security Best Practices Implementation (1 page)

**Non-Root User Configuration:**
```dockerfile
# Detailed implementation:
RUN groupadd -g 1001 sizecomparator && \
    useradd -r -u 1001 -g sizecomparator \
    -d /home/sizecomparator -s /sbin/nologin \
    -c "SizeComparator service account" sizecomparator
```

**Security Hardening Checklist:**
- Capability dropping (CAP_DROP: ALL)
- Read-only root filesystem configuration
- tmpfs mounts for writable directories
- Network policy specifications
- Secrets mounting best practices
- Signal handling for security events

**Vulnerability Management:**
- CVE scanning integration in CI/CD
- Automated base image updates
- Security patch automation
- Runtime security monitoring
- Container escape prevention

### 4. Health Checks and Graceful Shutdown (1 page)

**Multi-Level Health Check Implementation:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import requests; \
    r = requests.get('http://localhost:8000/api/v1/health'); \
    assert r.status_code == 200; \
    assert r.json()['status'] in ['healthy', 'degraded']"
```

**Health Check Endpoints (from DEPLOYMENT_OPS_SPEC):**
- /api/v1/health - Overall system health
- /api/v1/ready - Readiness for traffic
- /api/v1/metrics - Prometheus metrics

**Graceful Shutdown Handling:**
- SIGTERM signal handling implementation
- Connection draining (30s timeout)
- In-flight request completion
- Cache persistence
- State cleanup procedures
- Kubernetes preStop hook integration

**Startup Probes:**
- Initial delay configuration
- Dependency health verification
- AI provider connectivity checks
- Configuration validation on startup

### 5. Environment Variable Management and Secret Injection (1 page)

**Environment Variable Standards (from CONFIG_SYSTEM_SPEC):**
```yaml
# Required variables with validation:
SIZECOMPARATOR_ENV: production|staging|development
SIZECOMPARATOR_OPENAI_API_KEY: ^sk-[A-Za-z0-9]+$
SIZECOMPARATOR_ANTHROPIC_API_KEY: ^sk-ant-[A-Za-z0-9]+$
SIZECOMPARATOR_XAI_API_KEY: ^xai-[A-Za-z0-9]+$
SIZECOMPARATOR_SECRET_KEY: [32-char minimum]
```

**Secret Injection Methods:**
1. **Docker Secrets** (Swarm mode)
2. **Kubernetes Secrets** with volume mounts
3. **HashiCorp Vault** integration
4. **AWS Secrets Manager/Parameter Store**
5. **Environment file encryption**

**Runtime Configuration:**
- Environment variable validation on startup
- Default value management
- Secret rotation support
- Configuration hot-reload triggers
- Audit logging for configuration access

## Additional Requirements:

### Container Registry Best Practices:
- Image signing with Docker Content Trust
- Vulnerability scanning before push
- Automated tagging strategy (semver, git SHA)
- Multi-registry replication
- Image retention policies

### Monitoring and Observability:
- Structured logging to stdout/stderr
- Prometheus metrics exposure (port 9090)
- OpenTelemetry trace integration
- Container resource metrics
- Custom application metrics

### Docker Compose Integration:
```yaml
version: '3.8'
services:
  sizecomparator:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - BUILD_VERSION=${VERSION}
      secrets:
        - api_keys
    security_opt:
      - no-new-privileges:true
      - apparmor:docker-default
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

### Kubernetes Deployment Considerations:
- SecurityContext configuration
- Resource limits and requests
- PodSecurityPolicy compliance
- NetworkPolicy definitions
- Service mesh integration readiness

### CI/CD Pipeline Integration:
```yaml
# GitHub Actions example:
- name: Build and scan container
  run: |
    docker build --secret id=api_keys,src=.secrets \
      --build-arg VERSION=${{ github.sha }} \
      -t sizecomparator:${{ github.sha }} .
    
    trivy image --severity HIGH,CRITICAL \
      sizecomparator:${{ github.sha }}
    
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
      aquasec/trivy image sizecomparator:${{ github.sha }}
```

### Performance Testing Requirements:
- Container startup benchmarks
- Memory usage profiling
- CPU utilization under load
- Network latency measurements
- Storage I/O optimization

### Security Scanning Integration:
- Trivy for vulnerability scanning
- Hadolint for Dockerfile linting
- Dockle for best practices checking
- Falco for runtime security
- OWASP dependency checking

## Specification Deliverables:

1. **Complete Dockerfile** with all stages, security hardening, and optimizations
2. **docker-compose.yml** for local development with security constraints
3. **Security scanning configuration** files (trivy.yaml, .hadolint.yaml)
4. **Build scripts** with multi-platform support
5. **Deployment manifests** for Kubernetes with security policies
6. **Benchmarking scripts** for size and performance validation
7. **Documentation** for building, running, and deploying containers

## Integration Points:

- **DEPLOYMENT_OPS_SPEC**: Container must implement all health check endpoints and monitoring integration
- **CONFIG_SYSTEM_SPEC**: Support all SIZECOMPARATOR_* environment variables with validation
- **AI_PROVIDER_SPEC**: Ensure proper timeout and connection handling for AI providers
- **ERROR_MONITORING_SPEC**: Structured logging and error reporting from containers

## Success Criteria:

1. Final container image < 150MB
2. Zero HIGH/CRITICAL vulnerabilities
3. 99.9% container startup success rate
4. < 5 second cold start time
5. Graceful shutdown within 30 seconds
6. All security best practices implemented
7. Full observability integration
8. Automated security scanning in CI/CD

This specification should result in a production-ready, secure, and optimized container implementation that seamlessly integrates with the existing SizeComparator architecture while maintaining operational excellence standards.