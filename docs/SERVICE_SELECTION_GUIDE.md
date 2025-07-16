# Service Selection Guide

**Version**: 1.0.0  
**Last Updated**: 2025-07-14

## Overview

The SizeComparator service factory provides intelligent routing to optimal comparison services based on weight characteristics, performance requirements, and system availability. This guide explains how services are selected and how to influence the selection process.

## Service Types

### Basic Service
- **Implementation**: `MVPComparisonService`
- **Response Time**: ~500ms
- **Accuracy**: 60% (static comparisons)
- **Requirements**: None (always available)
- **Use Case**: Fallback when AI providers unavailable

**Characteristics:**
- Uses static weight-to-object mapping
- No AI provider dependency
- Consistent response times
- Limited creativity and accuracy

### Fast Validation Service
- **Implementation**: `FastValidationService`
- **Response Time**: ~1800ms (target <2s)
- **Accuracy**: 80%
- **Requirements**: At least one AI provider
- **Use Case**: Speed-critical applications

**Characteristics:**
- Optimized for common weights (1-100kg)
- Parallel AI calls with rule-based validation
- Aggressive timeouts and fallback strategies
- Balance of speed and accuracy

### Full Validation Service
- **Implementation**: `AIValidationService`
- **Response Time**: ~4000ms
- **Accuracy**: 95%
- **Requirements**: AI provider with higher timeout tolerance
- **Use Case**: Accuracy-critical applications

**Characteristics:**
- Comprehensive AI validation
- Multiple validation rounds
- Higher accuracy guarantees
- Longer processing time acceptable

### Comprehensive Service
- **Implementation**: `AIValidationService` (enhanced)
- **Response Time**: ~6000ms
- **Accuracy**: 98%
- **Requirements**: Multiple AI providers preferred
- **Use Case**: Research and detailed analysis

**Characteristics:**
- Most thorough analysis available
- Multiple AI providers consulted
- Quality scoring and validation
- Highest accuracy at cost of speed

## Service Selection Logic

### Selection Priority

1. **Explicit Query Parameter**
   ```
   GET /api/compare?service_mode=fast_validation
   ```

2. **HTTP Header**
   ```
   X-Service-Mode: full_validation
   ```

3. **Intelligent Selection** (based on request characteristics)
4. **Environment Defaults**
5. **Application Default** (fast_validation)

### Intelligent Selection Algorithm

The service factory analyzes multiple factors to select the optimal service:

#### Weight-Based Selection

```python
# Weight categorization
LIGHT_WEIGHT_THRESHOLD = 0.1  # kg
HEAVY_WEIGHT_THRESHOLD = 100.0  # kg  
EXTREME_WEIGHT_THRESHOLD = 1000.0  # kg

def categorize_weight(weight_kg):
    if weight_kg < LIGHT_WEIGHT_THRESHOLD:
        return "extreme_light"
    elif weight_kg <= HEAVY_WEIGHT_THRESHOLD:
        return "common"
    elif weight_kg <= EXTREME_WEIGHT_THRESHOLD:
        return "heavy"
    else:
        return "extreme_heavy"
```

**Selection Rules:**
- **Common weights (0.1-100kg)**: Fast validation preferred
- **Extreme weights (<0.1kg or >100kg)**: Full validation required
- **Very extreme weights (>1000kg)**: Comprehensive validation recommended

#### Performance Profile-Based Selection

**Speed Optimized Profile:**
```python
if timeout_ms <= 2000:
    return select_fast_service(weight_kg)
else:
    return ServiceType.FAST_VALIDATION
```

**Accuracy Optimized Profile:**
```python
if weight_is_extreme(weight_kg):
    return ServiceType.FULL_VALIDATION
else:
    return ServiceType.COMPREHENSIVE
```

**Balanced Profile:**
```python
if weight_is_extreme(weight_kg):
    if timeout_ms <= 2000:
        return ServiceType.FAST_VALIDATION
    else:
        return ServiceType.FULL_VALIDATION
else:
    return select_balanced_service(weight_kg, timeout_ms)
```

#### Environment-Based Selection

**Development Environment:**
```python
if force_basic_in_development:
    return ServiceType.BASIC
else:
    return intelligent_selection()
```

**Production Environment:**
```python
if require_validation_in_production:
    if profile == "speed_optimized":
        return ServiceType.FAST_VALIDATION
    else:
        return ServiceType.FULL_VALIDATION
else:
    return intelligent_selection()
```

## Service Selection Examples

### Example 1: Common Weight, Speed Priority
```python
# Request: 5 kg, timeout 1500ms, speed_optimized
weight_kg = 5.0
timeout_ms = 1500
profile = "speed_optimized"

# Selection logic:
# 1. Weight is common (0.1-100kg) ✓
# 2. Timeout is aggressive (<2s) ✓
# 3. Speed optimized profile ✓
# Result: BASIC service (fastest for common weights)
```

### Example 2: Extreme Weight, Accuracy Priority
```python
# Request: 0.05 kg, timeout 8000ms, accuracy_optimized
weight_kg = 0.05
timeout_ms = 8000
profile = "accuracy_optimized"

# Selection logic:
# 1. Weight is extreme (<0.1kg) ✓
# 2. Timeout allows longer processing ✓
# 3. Accuracy optimized profile ✓
# Result: COMPREHENSIVE service (best for extreme weights)
```

### Example 3: Balanced Request
```python
# Request: 25 kg, timeout 3000ms, balanced
weight_kg = 25.0
timeout_ms = 3000
profile = "balanced"

# Selection logic:
# 1. Weight is common (0.1-100kg) ✓
# 2. Timeout is moderate (2-5s) ✓
# 3. Balanced profile ✓
# Result: FAST_VALIDATION service (optimal balance)
```

## Service Availability and Fallback

### Availability Checking

The service factory checks availability before selection:

```python
def is_service_available(service_type):
    if service_type == ServiceType.BASIC:
        return True  # Always available
    
    if requires_ai_providers(service_type):
        return ai_providers_available()
    
    return True
```

### Fallback Chain

When a service is unavailable, the factory follows this fallback chain:

```
COMPREHENSIVE → FULL_VALIDATION → FAST_VALIDATION → BASIC
```

**Example Fallback Scenario:**
1. Request asks for comprehensive service
2. No AI providers available
3. Falls back to full validation
4. Still no AI providers
5. Falls back to fast validation  
6. Still no AI providers
7. Falls back to basic service (always available)

## Performance Tuning

### Configuration Parameters

#### Weight Thresholds
```python
# Adjust these in service factory configuration
LIGHT_WEIGHT_THRESHOLD_KG = 0.1
HEAVY_WEIGHT_THRESHOLD_KG = 100.0
EXTREME_WEIGHT_THRESHOLD_KG = 1000.0
```

#### Timeout Thresholds
```python
FAST_TIMEOUT_THRESHOLD_MS = 2000
STANDARD_TIMEOUT_THRESHOLD_MS = 5000
```

#### Service Strategy
```python
# Environment variable
SIZECOMPARATOR_SERVICE_STRATEGY = "smart_routing"  # default
# Options: "smart_routing", "performance_first", "accuracy_first", "basic_only"
```

### Performance Optimization Strategies

#### Performance First Strategy
- Prioritizes response time over accuracy
- Prefers basic service for common weights
- Aggressive timeouts
- Quick fallback to simpler services

#### Accuracy First Strategy
- Prioritizes accuracy over speed
- Prefers comprehensive validation
- Longer timeouts acceptable
- Fallback only when absolutely necessary

#### Smart Routing Strategy (Default)
- Balances speed and accuracy
- Considers all factors for optimal selection
- Adaptive to request characteristics
- Provides best overall user experience

## Monitoring and Debugging

### Service Selection Logging

Enable debug logging to see selection decisions:

```python
# Environment variable
SIZECOMPARATOR_LOG_LEVEL=debug

# Log output example
logger.info(
    f"Selected {service_type.value} service for weight={weight_kg}kg, "
    f"timeout={timeout_ms}ms, profile={profile.value}"
)
```

### Service Health Monitoring

Check service availability and health:

```bash
# GET /api/status
{
  "service_factory": {
    "factory_status": "healthy",
    "services": {
      "basic": {
        "avg_response_time_ms": 500,
        "accuracy_score": 0.6,
        "resource_intensity": 1
      },
      "fast_validation": {
        "avg_response_time_ms": 1800,
        "accuracy_score": 0.8,
        "resource_intensity": 3
      }
    },
    "availability": {
      "basic": true,
      "fast_validation": true,
      "full_validation": false,  # AI provider unavailable
      "comprehensive": false
    }
  }
}
```

### Performance Metrics

Track service selection patterns:

```python
# Available in /api/status
"app_metrics": {
    "requests_by_mode": {
        "basic": 200,
        "fast_validation": 800,
        "full_validation": 200,
        "comprehensive": 50
    },
    "response_times": [1200, 1800, 2100, ...],
    "errors_total": 15
}
```

## Advanced Usage

### Custom Service Selection

Force specific service selection:

```python
# Via query parameter
POST /api/compare?service_mode=comprehensive

# Via header
POST /api/compare
X-Service-Mode: fast_validation
X-Performance-Profile: speed_optimized
```

### Performance Profile Headers

Control selection via performance profiles:

```python
# Speed optimized
X-Performance-Profile: speed_optimized

# Accuracy optimized  
X-Performance-Profile: accuracy_optimized

# Balanced (default)
X-Performance-Profile: balanced
```

### Timeout Control

Control service selection via timeout:

```python
# Short timeout favors basic/fast services
POST /api/compare?timeout_ms=1000

# Long timeout allows comprehensive services
POST /api/compare?timeout_ms=10000
```

## Best Practices

### For Speed-Critical Applications
1. Use `service_mode=fast_validation` or `service_mode=basic`
2. Set `X-Performance-Profile: speed_optimized`
3. Use shorter timeouts (`timeout_ms=1500`)
4. Configure `SIZECOMPARATOR_SERVICE_STRATEGY=performance_first`

### For Accuracy-Critical Applications
1. Use `service_mode=comprehensive` or `service_mode=full_validation`
2. Set `X-Performance-Profile: accuracy_optimized`
3. Use longer timeouts (`timeout_ms=8000`)
4. Configure `SIZECOMPARATOR_SERVICE_STRATEGY=accuracy_first`

### For Production Systems
1. Keep default `smart_routing` strategy
2. Ensure at least one AI provider is configured
3. Monitor service availability and fallback patterns
4. Use appropriate caching to reduce service load

### For Development
1. Use `SIZECOMPARATOR_FORCE_BASIC_SERVICE=true` for testing
2. Monitor service selection logs for debugging
3. Test with different weight ranges and profiles
4. Verify fallback behavior when AI providers unavailable

## Troubleshooting

### Common Issues

#### Always Getting Basic Service
**Cause**: No AI providers configured or available
**Solution**: 
- Check AI provider API keys
- Verify provider availability
- Check service factory health status

#### Poor Performance
**Cause**: Wrong service selection for use case
**Solution**:
- Use explicit service mode selection
- Adjust performance profile
- Tune timeout values
- Monitor service metrics

#### Inconsistent Results
**Cause**: Service selection varying based on availability
**Solution**:
- Use explicit service mode selection
- Ensure stable AI provider configuration
- Monitor service availability patterns

### Debugging Steps

1. **Check service status**: `GET /api/status`
2. **Enable debug logging**: `SIZECOMPARATOR_LOG_LEVEL=debug`
3. **Test explicit selection**: Use `service_mode` parameter
4. **Monitor metrics**: Track service selection patterns
5. **Verify configuration**: Check AI provider settings

## Future Enhancements

### Planned Features
1. **Machine Learning Selection**: Use ML to optimize service selection
2. **Load Balancing**: Distribute requests across multiple AI providers
3. **Adaptive Timeouts**: Dynamically adjust timeouts based on performance
4. **Custom Profiles**: User-defined performance profiles
5. **A/B Testing**: Test different selection strategies

### Configuration Extensions
1. **Weight-Based Rules**: Custom weight thresholds per use case
2. **Provider Preferences**: Prefer specific AI providers for certain weights
3. **Time-Based Selection**: Different strategies for different times of day
4. **Cost Optimization**: Consider AI provider costs in selection