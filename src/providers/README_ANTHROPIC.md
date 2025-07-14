# Anthropic Provider for SizeComparator

This document describes the Anthropic Claude provider implementation for SizeComparator, providing comprehensive AI-powered weight comparisons using Claude 3 models.

## Overview

The Anthropic provider implements the SizeComparator AI provider interface with specialized optimizations for Claude 3 models (Opus, Sonnet, Haiku). It includes intelligent model selection, XML-based prompt optimization, robust error handling, and comprehensive monitoring.

## Features

### Core Capabilities
- **Claude 3 Model Support**: Opus, Sonnet, and Haiku models
- **Intelligent Model Selection**: Automatically selects optimal model based on request complexity
- **XML Tag Optimization**: Uses XML tags for improved Claude performance
- **System Prompt Engineering**: Constitutional AI-optimized prompts
- **Vision Support**: Ready for future Claude vision capabilities
- **Rate Limiting**: 1000 RPM Anthropic-compliant rate limiting
- **Circuit Breaker**: Automatic failure detection and recovery
- **Token Counting**: Accurate cost estimation and usage tracking

### Anthropic-Specific Features
- **Beta Features Support**: Flag for accessing Anthropic beta features
- **Safety Filtering**: Anthropic's built-in safety mechanisms
- **Multi-turn Conversations**: Context management for complex comparisons
- **Structured Output**: JSON response parsing with fallback handling
- **Cost Optimization**: Intelligent model selection to minimize costs

## Quick Start

### Basic Usage

```python
from src.providers import AnthropicProvider, get_default_config
from src.models.requests import WeightComparisonRequest
from src.models.weight import WeightInput

# Initialize provider
config = get_default_config()
provider = AnthropicProvider(config)

# Create comparison request
request = WeightComparisonRequest(
    item1="African Elephant",
    item1_weight=WeightInput(value="5000 kg", confidence=0.95),
    item2="Tesla Model 3", 
    item2_weight=WeightInput(value=1611.0, unit="kg", confidence=1.0),
    comparison_type="detailed",
    include_visualization=True
)

# Generate comparison
response = await provider.generate_comparison(request)
print(f"Ratio: {response.analysis.weight_ratio}")
print(f"Explanation: {response.analysis.explanation}")
```

### Configuration

#### Environment Variables
Set these environment variables for configuration:

```bash
# Required
export SIZECOMPARATOR_ANTHROPIC_API_KEY="your-api-key"

# Optional
export SIZECOMPARATOR_ANTHROPIC_MODEL="claude-3-sonnet-20240229"
export SIZECOMPARATOR_ANTHROPIC_ENDPOINT="https://api.anthropic.com"
export SIZECOMPARATOR_ANTHROPIC_TIMEOUT="60"
export SIZECOMPARATOR_ANTHROPIC_MAX_TOKENS="1024"
export SIZECOMPARATOR_ANTHROPIC_TEMPERATURE="0.7"
export SIZECOMPARATOR_ANTHROPIC_BETA_FEATURES="false"
export SIZECOMPARATOR_DEBUG="false"
```

#### Programmatic Configuration

```python
from src.providers import AnthropicConfigBuilder, AnthropicModel

# Production configuration
config = (AnthropicConfigBuilder()
          .with_api_key("your-api-key")
          .with_model(AnthropicModel.SONNET)
          .with_intelligent_selection(True)
          .with_xml_tags(True)
          .with_safety(True)
          .with_temperature(0.7)
          .with_timeout(30.0)
          .build())

# Development configuration
config = get_development_config()

# Cost-optimized configuration
config = get_cost_optimized_config()

# Performance-optimized configuration
config = get_performance_optimized_config()
```

## Model Selection

### Intelligent Model Selection

When enabled, the provider automatically selects the optimal Claude model based on request complexity:

```python
# Complexity factors:
# - Length of item names (>50 chars = +2 points)
# - Complex weight parsing needed (+2 points)  
# - Detailed comparison requested (+3 points)
# - Visualization requested (+2 points)

# Model selection:
# - Complexity >= 7: Claude Opus (most capable)
# - Complexity >= 4: Claude Sonnet (balanced)
# - Complexity < 4: Claude Haiku (fastest/cheapest)
```

### Manual Model Selection

```python
from src.providers import AnthropicConfigBuilder, AnthropicModel

# Force specific model
config = (AnthropicConfigBuilder()
          .with_model(AnthropicModel.OPUS)  # Always use Opus
          .with_intelligent_selection(False)  # Disable auto-selection
          .build())
```

## Advanced Features

### XML Tag Optimization

Claude performs better with XML-structured prompts:

```python
config = AnthropicConfigBuilder().with_xml_tags(True).build()

# Generates prompts like:
# <task>Compare weights of these items</task>
# <items>
#   <item1>Name: Elephant, Weight: 5000 kg</item1>
#   <item2>Name: Car, Weight: 1611 kg</item2>
# </items>
# <requirements>1. Parse weights 2. Calculate ratio...</requirements>
```

### Safety Controls

```python
# Enable Anthropic's safety filtering
config = AnthropicConfigBuilder().with_safety(True).build()

# The provider automatically:
# - Validates input for inappropriate content
# - Uses Constitutional AI principles
# - Applies safety guidelines to responses
# - Blocks harmful comparisons
```

### Beta Features

```python
# Access Anthropic beta features
config = AnthropicConfigBuilder().with_beta_features(True).build()

# Note: Beta features may have different rate limits or capabilities
```

## Error Handling

The provider includes comprehensive error handling:

```python
from src.core.exceptions import (
    AIProviderException,
    AIProviderRateLimitException, 
    AIProviderTimeoutException
)

try:
    response = await provider.generate_comparison(request)
except AIProviderRateLimitException as e:
    # Handle rate limiting
    print(f"Rate limited: {e}")
    # Implement exponential backoff
    
except AIProviderTimeoutException as e:
    # Handle timeouts
    print(f"Request timed out: {e}")
    # Retry or use fallback
    
except AIProviderException as e:
    # Handle general provider errors
    print(f"Provider error: {e}")
    # Log error and use fallback provider
```

## Monitoring and Health

### Health Monitoring

```python
# Check provider health
health = provider.get_health()
print(f"Status: {health.status}")
print(f"Success Rate: {health.success_rate:.2%}")
print(f"Circuit Breaker: {health.circuit_breaker_state}")
print(f"Avg Response Time: {health.avg_response_time_ms}ms")
```

### Circuit Breaker

The provider includes automatic circuit breaker protection:

```python
# Configure circuit breaker
config = (AnthropicConfigBuilder()
          .with_circuit_breaker(
              failure_threshold=5,    # Open after 5 failures
              recovery_timeout=60     # Try recovery after 60 seconds
          )
          .build())

# Circuit breaker states:
# - CLOSED: Normal operation
# - OPEN: Failing fast, blocking requests
# - HALF_OPEN: Testing recovery
```

### Metrics Collection

```python
# The provider automatically tracks:
# - Request count and success rate
# - Token usage and costs
# - Response times and latency
# - Error rates by category
# - Circuit breaker events
```

## Cost Optimization

### Model Selection for Cost

```python
# Cost per 1K tokens (as of 2024):
# - Haiku: $0.00025 input, $0.00125 output (cheapest)
# - Sonnet: $0.003 input, $0.015 output (balanced)
# - Opus: $0.015 input, $0.075 output (most expensive)

# Use cost-optimized configuration
config = get_cost_optimized_config()  # Always uses Haiku

# Or balance cost vs quality
config = (AnthropicConfigBuilder()
          .with_intelligent_selection(True)  # Auto-select based on complexity
          .with_max_tokens(512)              # Limit output tokens
          .build())
```

### Token Management

```python
# Monitor token usage
response = await provider.generate_comparison(request)
metadata = response.metadata

print(f"Input tokens: {metadata.component_timings.get('input_tokens', 0)}")
print(f"Output tokens: {metadata.component_timings.get('output_tokens', 0)}")
print(f"Total cost: ${metadata.component_timings.get('cost_estimate', 0):.4f}")
```

## Integration Examples

### With SizeComparator API

```python
from fastapi import FastAPI, HTTPException
from src.providers import AnthropicProvider, get_production_config

app = FastAPI()
provider = AnthropicProvider(get_production_config())

@app.post("/compare")
async def compare_weights(request: WeightComparisonRequest):
    try:
        response = await provider.generate_comparison(request)
        return response
    except AIProviderException as e:
        raise HTTPException(status_code=503, detail=str(e))
```

### With Fallback Providers

```python
async def generate_with_fallback(request):
    providers = [
        AnthropicProvider(get_production_config()),
        # OpenAIProvider(openai_config),  # Fallback
    ]
    
    for provider in providers:
        try:
            if provider.get_health().status in ["healthy", "degraded"]:
                return await provider.generate_comparison(request)
        except Exception as e:
            print(f"Provider {provider.provider_name} failed: {e}")
            continue
    
    raise Exception("All providers failed")
```

## Testing

### Unit Tests

```bash
# Run unit tests
pytest src/providers/test_anthropic_provider.py -v

# Run with coverage
pytest src/providers/test_anthropic_provider.py --cov=src.providers.anthropic_provider
```

### Integration Tests

```bash
# Set API key for integration tests
export SIZECOMPARATOR_ANTHROPIC_API_KEY="your-api-key"

# Run integration tests
pytest src/providers/test_anthropic_provider.py::test_real_anthropic_integration -v
```

### Manual Testing

```python
# Use the example script
python src/providers/example_usage.py
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```
   Error: Anthropic API key not found
   Solution: Set SIZECOMPARATOR_ANTHROPIC_API_KEY environment variable
   ```

2. **Rate Limit Exceeded**
   ```
   Error: Anthropic rate limit exceeded
   Solution: Implement exponential backoff or reduce request rate
   ```

3. **Invalid JSON Response**
   ```
   Error: Failed to extract valid JSON from Anthropic response
   Solution: Check prompt formatting or try a different model
   ```

4. **Circuit Breaker Open**
   ```
   Error: Circuit breaker open for anthropic
   Solution: Wait for recovery or check provider health
   ```

### Debug Mode

```python
# Enable debug logging
config = AnthropicConfigBuilder().with_debug_logging(True).build()

# Or set environment variable
export SIZECOMPARATOR_DEBUG=true
```

### Health Checks

```python
# Check overall health
health = provider.get_health()
if health.status == "unhealthy":
    print(f"Last error: {health.last_error}")
    print(f"Error count: {health.error_count}")
    
    # Reset circuit breaker if needed
    await provider.circuit_breaker.reset()
```

## Performance Optimization

### Response Time Optimization

```python
# Use faster model for simple requests
config = (AnthropicConfigBuilder()
          .with_model(AnthropicModel.HAIKU)  # Fastest model
          .with_max_tokens(256)              # Shorter responses
          .with_timeout(15.0)                # Shorter timeout
          .build())
```

### Throughput Optimization

```python
# Optimize for high throughput
config = (AnthropicConfigBuilder()
          .with_rate_limit(1000)             # Max rate limit
          .with_circuit_breaker(
              failure_threshold=3,           # Fail fast
              recovery_timeout=30            # Quick recovery
          )
          .build())
```

## Security Considerations

1. **API Key Management**: Store API keys securely, never in code
2. **Input Validation**: Provider validates inputs for safety
3. **Output Sanitization**: Responses are validated and sanitized
4. **Rate Limiting**: Prevents abuse and quota exhaustion
5. **Circuit Breaking**: Protects against cascade failures

## Support

- **Documentation**: See ANTHROPIC_PROVIDER_SPEC.md for detailed specifications
- **Issues**: Report issues through the SizeComparator issue tracker
- **Examples**: Check `example_usage.py` for working examples
- **Tests**: Review `test_anthropic_provider.py` for usage patterns

## License

This implementation is part of the SizeComparator project and follows the same license terms.