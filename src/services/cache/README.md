# SizeComparator Cache Service

A comprehensive caching layer built on Redis that dramatically improves application performance and reduces AI provider costs. The cache service achieves response times under 100ms for cached requests while reducing API costs by over 80% for repeated queries.

## Features

### 🚀 Performance
- **Sub-100ms operations** with 90%+ cache hit rates
- **Pipeline operations** for efficient batch processing
- **Connection pooling** with health checks and automatic reconnection
- **Circuit breaker protection** for fault tolerance

### 🎯 AI Integration
- **AI response caching** with intelligent key generation
- **Cost tracking** and savings metrics
- **Provider fallback** support with cache consistency
- **Template-based** caching with variable normalization

### 🏗️ Architecture
- **Multiple deployment modes**: Standalone, Sentinel, Cluster
- **Type-safe serialization** with Pydantic model support
- **Hierarchical key structure** for efficient invalidation
- **Comprehensive monitoring** and metrics collection

### 🔧 Developer Experience
- **Decorators** for automatic caching
- **Environment-based configuration** with secure defaults
- **Graceful degradation** when cache is unavailable
- **Memory fallback** for development environments

## Quick Start

### Basic Usage

```python
from src.services.cache import CacheService

# Create cache service from environment
cache = CacheService.from_env()

# Basic operations
await cache.set("key", "value", ttl=3600)
result = await cache.get("key")

# Pydantic model caching
from src.models.weight import ProcessedWeight
weight = ProcessedWeight(...)
await cache.set("weight:elephant", weight, ttl=3600)
cached_weight = await cache.get("weight:elephant", ProcessedWeight)
```

### Using Decorators

```python
from src.services.cache import cache_result, cache_ai_response

@cache_result(ttl=3600, key_prefix="expensive_calc")
async def expensive_calculation(data):
    # Expensive operation
    return result

@cache_ai_response(ttl=86400)
async def generate_comparison(weight1, weight2, provider="openai"):
    # AI provider call
    return ai_response
```

## Configuration

### Environment Variables

The cache service is configured through environment variables:

```bash
# Redis Connection
SIZECOMPARATOR_REDIS_HOST=localhost
SIZECOMPARATOR_REDIS_PORT=6379
SIZECOMPARATOR_REDIS_PASSWORD=secret
SIZECOMPARATOR_REDIS_DB=0
SIZECOMPARATOR_REDIS_TLS=false

# Connection Pool
SIZECOMPARATOR_REDIS_MAX_CONNECTIONS=50
SIZECOMPARATOR_REDIS_SOCKET_TIMEOUT=5.0
```

### Deployment Modes

#### Standalone (Development)
```python
from src.services.cache import RedisCache, RedisConfig

config = RedisConfig(
    mode="standalone",
    host="localhost",
    port=6379
)
cache = RedisCache(config)
```

#### Sentinel (Staging)
```python
config = RedisConfig(
    mode="sentinel",
    sentinels=[
        ("sentinel-1", 26379),
        ("sentinel-2", 26379),
        ("sentinel-3", 26379)
    ],
    master_name="mymaster"
)
```

#### Cluster (Production)
```python
config = RedisConfig(
    mode="cluster",
    nodes=[
        ("redis-1", 7000),
        ("redis-2", 7000),
        ("redis-3", 7000)
    ]
)
```

## Cache Key Patterns

The cache service uses hierarchical key structures for efficient invalidation:

### AI Responses
```
ai:v1:openai:gpt_4:abc123def:10.5kg
```
- `ai`: Prefix for AI responses
- `v1`: Version
- `openai`: Provider name
- `gpt_4`: Model name
- `abc123def`: Prompt hash (first 12 chars)
- `10.5kg`: Normalized weight

### Weight Processing
```
wgt:parsed:10_5_kg
```
- `wgt`: Prefix for weight operations
- `parsed`: Operation type
- `10_5_kg`: Normalized weight string

### Configuration
```
cfg:app:1.0.0:production
```
- `cfg`: Configuration prefix
- `app`: Config type
- `1.0.0`: Version
- `production`: Environment (optional)

## Serialization

### Pydantic Models

The cache service automatically handles Pydantic model serialization:

```python
from src.models.weight import ProcessedWeight

# Automatic serialization
weight = ProcessedWeight(...)
await cache.set("weight:key", weight)

# Automatic deserialization
cached = await cache.get("weight:key", ProcessedWeight)
```

### Compression

Large values are automatically compressed:

```python
# Values >1KB are automatically compressed
large_data = {"content": "x" * 2000}
await cache.set("large:key", large_data)  # Automatically compressed
```

### Custom Serialization

```python
from src.services.cache.serializers import CacheSerializer, TypeSafeSerializer

# Type-safe serializer for specific models
weight_serializer = TypeSafeSerializer(ProcessedWeight)
serialized = await weight_serializer.serialize(weight)
deserialized = await weight_serializer.deserialize(data)
```

## Monitoring and Metrics

### Health Checks

```python
# Basic health check
is_healthy = await cache.health_check()

# Detailed statistics
stats = await cache.get_stats()
print(f"Hit rate: {stats['hit_rates']['default']['hit_rate']:.2%}")
```

### Performance Metrics

The cache service automatically tracks:

- **Operation latency** (p50, p95, p99)
- **Hit/miss rates** by key prefix
- **Error rates** and circuit breaker state
- **Memory usage** and key distribution
- **Cost savings** from AI response caching

### Example Metrics Output

```json
{
  "uptime_seconds": 3600,
  "total_operations": 1000,
  "error_rate": 0.01,
  "operations": {
    "get": {
      "count": 800,
      "avg_time_ms": 2.5,
      "error_rate": 0.0
    },
    "set": {
      "count": 200,
      "avg_time_ms": 3.1,
      "error_rate": 0.02
    }
  },
  "hit_rates": {
    "ai": {
      "hit_rate": 0.85,
      "total_requests": 500,
      "hits": 425,
      "misses": 75
    }
  }
}
```

## Error Handling

### Circuit Breaker Protection

The cache service includes built-in circuit breaker protection:

```python
# Circuit breaker automatically handles failures
try:
    result = await cache.get("key")
except CacheConnectionError:
    # Circuit breaker is open
    result = fallback_value
```

### Graceful Degradation

Cache failures never break core functionality:

```python
@cache_result(ttl=3600)
async def important_function(data):
    # Function executes normally even if cache fails
    return process_data(data)
```

## Advanced Features

### Batch Operations

```python
# Efficient multi-get
keys = ["key1", "key2", "key3"]
results = await cache.multi_get(keys, ProcessedWeight)

# Efficient multi-set
items = {
    "key1": value1,
    "key2": value2,
    "key3": value3
}
await cache.multi_set(items, ttl=3600)
```

### Atomic Operations

```python
# Atomic increment
new_count = await cache.increment("counter", 5)

# Conditional set
was_set = await cache.set_if_not_exists("lock:resource", "owner", ttl=60)
```

### Pattern-Based Invalidation

```python
# Invalidate all AI responses from OpenAI
await cache.flush("ai:*:openai:*")

# Invalidate all user data
await cache.flush("user:123:*")

# Get invalidation patterns for AI responses
from src.services.cache import CacheKeyBuilder
patterns = CacheKeyBuilder.get_invalidation_patterns(
    "ai_response", 
    provider="openai"
)
```

## Best Practices

### Key Design

1. **Use hierarchical keys** for efficient invalidation
2. **Normalize inputs** for better cache hits
3. **Include version** in keys when schemas change
4. **Keep keys under 250 characters** for Redis compatibility

### TTL Management

1. **Use appropriate TTLs** by data type:
   - AI responses: 24 hours
   - Configuration: 5 minutes
   - Weight processing: 1 hour
   - Temporary data: 1 minute

2. **Consider data freshness** requirements
3. **Use longer TTLs** for expensive operations
4. **Implement cache warming** for critical data

### Performance Optimization

1. **Use batch operations** when possible
2. **Monitor hit rates** and adjust caching strategies
3. **Implement cache warming** for predictable loads
4. **Use compression** for large payloads
5. **Monitor memory usage** and eviction patterns

### Error Handling

1. **Never fail** core functionality due to cache errors
2. **Use circuit breakers** for external dependencies
3. **Implement fallbacks** for critical operations
4. **Monitor error rates** and set up alerting

## Testing

### Unit Testing

```python
import pytest
from src.services.cache import MemoryCache

@pytest.fixture
async def cache():
    """Create memory cache for testing."""
    return MemoryCache()

async def test_basic_operations(cache):
    await cache.set("test", "value")
    result = await cache.get("test")
    assert result == "value"
```

### Integration Testing

```python
async def test_redis_integration():
    """Test with actual Redis instance."""
    from src.services.cache import RedisCache, RedisConfig
    
    config = RedisConfig(host="localhost", port=6379)
    cache = RedisCache(config)
    await cache.initialize()
    
    # Test operations
    await cache.set("test", "value")
    result = await cache.get("test")
    assert result == "value"
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check Redis server is running
   - Verify host/port configuration
   - Check firewall settings

2. **High Error Rates**
   - Monitor Redis memory usage
   - Check network connectivity
   - Review circuit breaker state

3. **Low Hit Rates**
   - Review key normalization
   - Check TTL configuration
   - Monitor eviction patterns

4. **Performance Issues**
   - Enable connection pooling
   - Use batch operations
   - Monitor Redis slow queries

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger("src.services.cache").setLevel(logging.DEBUG)

# Check cache health
stats = await cache.get_stats()
print(f"Cache type: {stats['type']}")
print(f"Error rate: {stats.get('error_rate', 0):.2%}")

# Monitor circuit breaker
if hasattr(cache, '_circuit_breaker'):
    print(f"Circuit breaker state: {cache._circuit_breaker.state}")
```

## Contributing

### Adding New Cache Types

1. **Extend key builder** with new patterns
2. **Add serialization** support for new models
3. **Update TTL defaults** in configuration
4. **Add invalidation patterns** for new data types

### Performance Improvements

1. **Profile operations** with timing decorators
2. **Optimize serialization** for common types
3. **Implement smarter eviction** policies
4. **Add connection optimization**

### Monitoring Enhancements

1. **Add new metrics** to CacheMetrics class
2. **Implement alerting** for error conditions
3. **Add performance dashboards**
4. **Include business metrics** (cost savings, etc.)

For more examples, see the `examples/cache_usage.py` file.