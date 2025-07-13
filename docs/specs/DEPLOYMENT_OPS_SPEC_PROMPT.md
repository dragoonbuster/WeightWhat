# Deployment and Operations Specification Prompt for SizeComparator

## Context
You are tasked with creating a comprehensive Deployment and Operations Specification document (DEPLOYMENT_OPS_SPEC.md) for the SizeComparator application. The specification must integrate seamlessly with all other system components and their specific requirements. Your specification should focus exclusively on production deployment, operational excellence, and maintaining the 99% uptime SLA requirement while orchestrating all components correctly.

## Critical Integration Requirements

### 1. BACKEND_CORE_SPEC Health Endpoints Integration
Health endpoints must implement the exact interfaces defined in BACKEND_CORE_SPEC:
- **GET /api/v1/health**: Must return `HealthResponse` Pydantic model with status="healthy|unhealthy"
- **GET /api/v1/ready**: Must return `ReadinessResponse` with AI provider connectivity checks
- **GET /api/v1/metrics**: Must expose Prometheus metrics for monitoring
- Health checks must include request ID correlation as specified in BACKEND_CORE_SPEC
- All health responses must follow FastAPI async patterns and error handling

### 2. CONFIG_SYSTEM_SPEC Environment Variables
Configuration management must use the standardized SIZECOMPARATOR_* environment variables:
- **SIZECOMPARATOR_ENV**: Environment selection (development|staging|production)
- **SIZECOMPARATOR_CONFIG_VALIDATION**: Validation mode (strict|warn|off)
- **SIZECOMPARATOR_HOT_RELOAD**: Enable configuration hot-reload
- **AI Provider Variables**: SIZECOMPARATOR_OPENAI_API_KEY, SIZECOMPARATOR_ANTHROPIC_API_KEY
- **Cache Configuration**: SIZECOMPARATOR_REDIS_HOST, SIZECOMPARATOR_REDIS_PORT
- **Monitoring**: SIZECOMPARATOR_METRICS_ENABLED, SIZECOMPARATOR_LOG_LEVEL
- Must validate all environment variables against CONFIG_SYSTEM_SPEC JSON schema
- Support hot-reload configuration changes without restart

### 3. ERROR_MONITORING_SPEC Metrics and Alerts
Monitoring must align with the structured logging and metrics framework:
- **Error Categories**: Monitor CLIENT_ERROR, SERVER_ERROR, INTEGRATION_ERROR, BUSINESS_LOGIC_ERROR
- **Circuit Breaker States**: Track CLOSED, OPEN, HALF_OPEN states from AI_PROVIDER_SPEC
- **Request ID Propagation**: All monitoring must include request correlation IDs
- **Alert Severity Levels**: CRITICAL, WARNING, INFO aligned with ERROR_MONITORING_SPEC
- **Log Aggregation**: Follow structured JSON logging format with mandatory fields
- **Provider Health Metrics**: Monitor ProviderHealth status from AI_PROVIDER_SPEC

### 4. TESTING_SPEC Test Pipeline Integration
CI/CD pipeline must include comprehensive testing as defined in TESTING_SPEC:
- **Unit Tests**: 80% coverage minimum, 95% for critical paths
- **Integration Tests**: MockAIProvider testing with circuit breaker scenarios
- **E2E Tests**: Full request/response cycles with real provider integration
- **Performance Tests**: Response time SLA validation (<2s for 95th percentile)
- **Load Testing**: 50 RPS sustained load with <5% error rate
- **Fixture Data**: Use standardized test fixtures from TESTING_SPEC

### 5. AI_PROVIDER_SPEC Configuration Deployment
AI provider configurations must be deployed consistently:
- **Provider Priority**: Deploy OpenAI (priority 1), Anthropic (priority 2), X.ai (priority 3)
- **Circuit Breaker Settings**: Deploy failure_threshold=5, recovery_timeout=60s
- **Rate Limiting**: Deploy provider-specific rate limits from AI_PROVIDER_SPEC
- **Timeout Configuration**: Deploy 30s default with provider-specific overrides
- **Health Check Integration**: Deploy ProviderHealth monitoring to /ready endpoint
- **Failover Logic**: Deploy automatic failover with logging to ERROR_MONITORING_SPEC

## Document Requirements

### Length and Structure
- **Maximum Length**: 9 pages (expanded to accommodate integration requirements)
- **Focus**: Production deployment orchestrating ALL components correctly
- **Writing Style**: Clear, actionable, implementation-focused with cross-references
- **Structure**: Use numbered sections with clear hierarchies and integration points

### Core Topics to Cover

1. **Component Integration Architecture** (1 page)
   - System component diagram showing all spec relationships
   - Integration validation checklist
   - Cross-component dependency management
   - Configuration consistency enforcement
   - Health check aggregation from all components

2. **Docker Containerization Strategy** (1 page)
   - Multi-stage Dockerfile implementing BACKEND_CORE_SPEC structure
   - Environment variable injection for CONFIG_SYSTEM_SPEC compliance
   - Health check commands calling BACKEND_CORE_SPEC endpoints
   - Security hardening with non-root user
   - Resource limits aligned with AI_PROVIDER_SPEC timeout requirements

3. **Enhanced Health Check System** (1 page)
   - BACKEND_CORE_SPEC health endpoint implementation details
   - AI_PROVIDER_SPEC circuit breaker state monitoring
   - CONFIG_SYSTEM_SPEC configuration validation checks
   - ERROR_MONITORING_SPEC structured health logging
   - Dependency health aggregation with request ID correlation
   - Kubernetes probe configurations using exact endpoint schemas

4. **Comprehensive CI/CD Pipeline** (1.5 pages)
   - TESTING_SPEC test execution: unit → integration → e2e
   - CONFIG_SYSTEM_SPEC validation in pipeline
   - AI_PROVIDER_SPEC mock testing integration
   - ERROR_MONITORING_SPEC log validation
   - Container vulnerability scanning
   - Configuration schema validation
   - Cross-component integration testing

5. **Environment Management with Full Integration** (1 page)
   - CONFIG_SYSTEM_SPEC environment variable management
   - SIZECOMPARATOR_* variable validation and injection
   - AI_PROVIDER_SPEC provider configuration per environment
   - ERROR_MONITORING_SPEC monitoring configuration
   - Secret management for API keys
   - Hot-reload configuration deployment

6. **Intelligent Scaling Strategy** (1 page)
   - AI_PROVIDER_SPEC rate limit aware autoscaling
   - ERROR_MONITORING_SPEC metric-based scaling triggers
   - BACKEND_CORE_SPEC performance target maintenance
   - Circuit breaker state influenced scaling decisions
   - Cache layer scaling with CONFIG_SYSTEM_SPEC
   - Load balancer configuration for health checks

7. **Zero-Downtime Deployment Process** (1 page)
   - Pre-deployment validation of all component configurations
   - Rolling update with BACKEND_CORE_SPEC health validation
   - AI_PROVIDER_SPEC circuit breaker state preservation
   - CONFIG_SYSTEM_SPEC hot-reload during deployment
   - ERROR_MONITORING_SPEC deployment event logging
   - Automated rollback on any component failure

8. **Integrated Secret Management** (0.5 pages)
   - AI_PROVIDER_SPEC API key management
   - CONFIG_SYSTEM_SPEC environment variable security
   - ERROR_MONITORING_SPEC secret access auditing
   - Emergency key rotation procedures
   - Compliance with security standards

9. **Unified Monitoring and Alerting** (1 page)
   - ERROR_MONITORING_SPEC metrics collection implementation
   - AI_PROVIDER_SPEC circuit breaker state alerts
   - BACKEND_CORE_SPEC performance monitoring
   - CONFIG_SYSTEM_SPEC configuration change alerts
   - TESTING_SPEC synthetic monitoring
   - Cross-component correlation dashboards

10. **Operational Risk Mitigation** (1 page)
    - Component failure cascade prevention
    - AI_PROVIDER_SPEC timeout and retry configurations
    - ERROR_MONITORING_SPEC incident response procedures
    - CONFIG_SYSTEM_SPEC configuration drift detection
    - TESTING_SPEC chaos engineering practices
    - Cross-component disaster recovery plans

### Specific Implementation Details Required

1. **Component-Integrated Docker Implementation**:
   ```dockerfile
   # Multi-stage Dockerfile with BACKEND_CORE_SPEC structure
   # CONFIG_SYSTEM_SPEC environment variable validation
   # BACKEND_CORE_SPEC health check endpoint integration
   # AI_PROVIDER_SPEC timeout-aligned resource limits
   # ERROR_MONITORING_SPEC structured logging setup
   ```

2. **Integrated Health Check Endpoints**:
   ```python
   # BACKEND_CORE_SPEC HealthResponse and ReadinessResponse models
   # AI_PROVIDER_SPEC circuit breaker state monitoring
   # CONFIG_SYSTEM_SPEC configuration validation in health checks
   # ERROR_MONITORING_SPEC request ID correlation
   # Provider-specific connectivity verification
   ```

3. **Full Integration CI/CD Pipeline**:
   ```yaml
   # TESTING_SPEC test execution pipeline (unit → integration → e2e)
   # CONFIG_SYSTEM_SPEC validation and schema checking
   # AI_PROVIDER_SPEC mock provider testing
   # ERROR_MONITORING_SPEC log format validation
   # Cross-component integration testing
   # Performance testing against BACKEND_CORE_SPEC targets
   ```

4. **Cross-Component Monitoring Dashboard**:
   - BACKEND_CORE_SPEC API endpoint performance metrics
   - AI_PROVIDER_SPEC circuit breaker state visualization
   - CONFIG_SYSTEM_SPEC configuration change tracking
   - ERROR_MONITORING_SPEC error categorization charts
   - TESTING_SPEC synthetic test results
   - Cross-component correlation views
   - SLA compliance against all spec requirements

5. **Integrated Secret Management**:
   ```yaml
   # AI_PROVIDER_SPEC API key management (OPENAI, ANTHROPIC, XAI)
   # CONFIG_SYSTEM_SPEC SIZECOMPARATOR_* environment variables
   # ERROR_MONITORING_SPEC secret access audit logging
   # Kubernetes secret injection with validation
   # Hot-reload secret rotation without restart
   ```

6. **Component Integration Examples**:
   ```python
   # BACKEND_CORE_SPEC FastAPI dependency injection
   # CONFIG_SYSTEM_SPEC hot-reload configuration loading
   # AI_PROVIDER_SPEC provider manager initialization
   # ERROR_MONITORING_SPEC structured logging setup
   # TESTING_SPEC mock provider integration
   ```

7. **Environment Variable Validation**:
   ```bash
   # Complete SIZECOMPARATOR_* variable validation script
   # CONFIG_SYSTEM_SPEC schema validation
   # AI_PROVIDER_SPEC provider configuration validation
   # ERROR_MONITORING_SPEC logging configuration validation
   # Pre-deployment integration verification
   ```

### Operational Excellence Requirements

1. **Integrated SLA Definition**:
   - 99% uptime across ALL components (allows 7.2 hours downtime/month)
   - BACKEND_CORE_SPEC response time < 2s for 95th percentile
   - AI_PROVIDER_SPEC circuit breaker success rate > 99%
   - ERROR_MONITORING_SPEC error rate < 1% for valid requests
   - CONFIG_SYSTEM_SPEC hot-reload success rate > 99.5%
   - Cross-component SLA measurement and reporting procedures

2. **Cross-Component Incident Response**:
   - ERROR_MONITORING_SPEC severity levels (CRITICAL, WARNING, INFO)
   - AI_PROVIDER_SPEC circuit breaker state escalation procedures
   - CONFIG_SYSTEM_SPEC configuration drift response protocols
   - BACKEND_CORE_SPEC performance degradation procedures
   - TESTING_SPEC synthetic monitoring failure response
   - Post-mortem template covering all component interactions

3. **Integrated Capacity Planning**:
   - TESTING_SPEC load testing procedures (50 RPS sustained)
   - AI_PROVIDER_SPEC rate limit capacity planning
   - CONFIG_SYSTEM_SPEC configuration scaling triggers
   - ERROR_MONITORING_SPEC monitoring overhead planning
   - Cross-component resource scaling triggers
   - Cost optimization across all specifications

### Key Principles to Emphasize

1. **Component Integration First**: All deployment decisions must consider cross-component impacts
2. **Reliability Through Integration**: 99% uptime requires ALL components working together seamlessly
3. **Security by Design**: Implement defense in depth across BACKEND_CORE_SPEC, CONFIG_SYSTEM_SPEC, and AI_PROVIDER_SPEC
4. **Automation with Validation**: Manual processes are failure points - automate with CONFIG_SYSTEM_SPEC validation
5. **Comprehensive Observability**: ERROR_MONITORING_SPEC provides visibility across all components
6. **Testing-Driven Deployment**: TESTING_SPEC ensures deployment reliability at every stage

### Critical Integration References

All deployment specifications must reference and align with:

#### BACKEND_CORE_SPEC Integration Points
- Section 2.1: FastAPI application structure for health endpoints
- Section 4.1: Pydantic response models for health check schemas
- Section 5.1: API endpoint specifications (/health, /ready, /metrics)
- Section 8.1: Error response format for deployment failures

#### CONFIG_SYSTEM_SPEC Integration Points  
- Section 2.2: Environment variable standards (SIZECOMPARATOR_*)
- Section 4.1: JSON schema validation for deployment configuration
- Section 5: Hot-reload implementation for zero-downtime updates
- Section 15.1: Complete environment variable catalog

#### AI_PROVIDER_SPEC Integration Points
- Section 2.1: Provider health status monitoring
- Section 5.1: Circuit breaker state tracking for deployment decisions
- Section 7: Rate limiting considerations for scaling
- Section 10.1: Provider configuration deployment

#### ERROR_MONITORING_SPEC Integration Points
- Section 1: Structured logging framework for deployment events
- Section 2: Error categorization for deployment failures
- Section 4: Metrics collection for deployment monitoring
- Section 5: Alert configuration for deployment issues

#### TESTING_SPEC Integration Points
- Section 4: Integration test setup for deployment validation
- Section 5: E2E test scenarios for deployment verification
- Section 6: Performance testing for deployment SLA validation
- Section 9.1: Mock provider integration for deployment testing

### Deliverable Format

The specification should be structured as:

```markdown
# SizeComparator Deployment and Operations Specification

## Executive Summary
[Cross-component deployment architecture overview]

## 1. Component Integration Architecture  
[System integration diagram and dependency management]

## 2. Docker Containerization Strategy
[Multi-stage build with all spec integrations]

## 3. Enhanced Health Check System
[BACKEND_CORE_SPEC endpoints with cross-component monitoring]

## 4. Comprehensive CI/CD Pipeline
[TESTING_SPEC integration with full component validation]

## 5. Environment Management with Full Integration
[CONFIG_SYSTEM_SPEC variable management and validation]

## 6. Intelligent Scaling Strategy
[AI_PROVIDER_SPEC aware scaling with monitoring integration]

## 7. Zero-Downtime Deployment Process
[Cross-component deployment with rollback procedures]

## 8. Integrated Secret Management
[Multi-component secret handling with audit logging]

## 9. Unified Monitoring and Alerting
[ERROR_MONITORING_SPEC implementation across all components]

## 10. Operational Risk Mitigation
[Cross-component failure prevention and recovery]
```

### Success Criteria

Your specification will be considered complete when it:

#### Component Integration Requirements
1. **BACKEND_CORE_SPEC Compliance**: All health endpoints implement exact Pydantic schemas
2. **CONFIG_SYSTEM_SPEC Integration**: All SIZECOMPARATOR_* variables validated and documented
3. **AI_PROVIDER_SPEC Alignment**: Circuit breaker states monitored in deployment health
4. **ERROR_MONITORING_SPEC Implementation**: Structured logging with request ID propagation
5. **TESTING_SPEC Coverage**: Full test pipeline integration with 80%+ coverage validation

#### Operational Excellence Requirements
6. **Cross-Component SLA Support**: 99% uptime across ALL integrated components
7. **Integration Validation**: Pre-deployment validation of all component configurations
8. **Hot-Reload Capability**: Zero-downtime configuration updates via CONFIG_SYSTEM_SPEC
9. **Circuit Breaker Integration**: AI provider health influencing deployment decisions
10. **Comprehensive Monitoring**: ERROR_MONITORING_SPEC metrics across all components

#### Implementation Quality Standards
11. **Working Integration Examples**: Complete deployment configurations with cross-references
12. **Validation Scripts**: Environment variable and configuration validation automation
13. **Risk Mitigation**: Component failure cascade prevention strategies
14. **Rollback Procedures**: Automated rollback on any component failure detection
15. **Documentation**: Clear integration points with specific section references

### Critical Integration Validation

The deployment specification must demonstrate:
- **Health endpoint schemas** match BACKEND_CORE_SPEC exactly
- **Environment variables** follow CONFIG_SYSTEM_SPEC naming and validation
- **Circuit breaker monitoring** aligns with AI_PROVIDER_SPEC states
- **Error logging** implements ERROR_MONITORING_SPEC structured format
- **Test integration** covers TESTING_SPEC scenarios in CI/CD pipeline
- **Cross-component dependency** management and failure isolation
- **Configuration consistency** across all specification requirements

Remember: This deployment specification is the orchestration layer that must ensure ALL components work together seamlessly. Focus on integration points, validation procedures, and cross-component health monitoring to achieve true system reliability.