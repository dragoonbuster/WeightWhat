# Cache Service Specification Prompt for SizeComparator

## Context
You are a senior software architect and DevOps engineer designing the caching layer for SizeComparator, a web application that converts weight inputs into AI-generated object comparisons. The cache service must integrate seamlessly with the existing Phase 1 foundation components and align with the AI_PROVIDER_SPEC caching requirements.

## Objective
Create a comprehensive specification (8-10 pages) for the cache service that provides high-performance caching for AI provider responses, configuration data, and processed weights while maintaining cache coherency and supporting horizontal scaling.

## System Context
- **Foundation Components**: DATA_MODELS (Pydantic models), CONFIG_LOADER (hot-reload config), ENV_MANAGER (secure env vars), WEIGHT_PROCESSOR (Decimal precision), ERROR_MONITORING (metrics/logging)
- **AI Providers**: OpenAI, Anthropic, X.ai with response caching requirements
- **Performance Goals**: <100ms cache operations, 90%+ cache hit rate for repeated queries
- **Scale Requirements**: Support for distributed caching across multiple instances

## Specification Requirements

### 1. Cache Architecture (1.5 pages)
Design the caching layer architecture:
- **Technology Selection**: Redis as primary cache with justification (performance, persistence, clustering)
- **Cache Topology**: Single instance for dev, Redis Sentinel for staging, Redis Cluster for production
- **Connection Management**: Connection pooling, health checks, automatic reconnection
- **Data Serialization**: JSON serialization with Pydantic model support, compression for large responses
- **Key Design**: Hierarchical key structure supporting invalidation patterns
- **Memory Management**: LRU eviction, memory limits, key expiration strategies

### 2. Cache Service Implementation (2 pages)
Define the core cache service:
- **CacheService Interface**: Abstract base class with get/set/delete/exists/flush operations
- **RedisCache Implementation**: Concrete implementation with connection management
- **Batch Operations**: Multi-get/set for performance, pipeline support
- **Atomic Operations**: Increment/decrement, set-if-not-exists, compare-and-swap
- **TTL Management**: Default TTLs by data type, sliding expiration support
- **Error Handling**: Graceful degradation on cache failures, circuit breaker integration

### 3. AI Response Caching (1.5 pages)
Implement AI provider response caching aligned with AI_PROVIDER_SPEC:
- **Cache Key Generation**: Deterministic keys from weight input + provider + model + prompt template
- **Response Storage**: Store AIProviderResponse models with metadata
- **Invalidation Strategy**: TTL-based (24 hours default), manual invalidation, version-based invalidation
- **Cache Warming**: Pre-populate common weight comparisons
- **Hit Rate Optimization**: Normalize inputs for better cache efficiency
- **Cost Savings Tracking**: Monitor cache hits to calculate API cost savings

### 4. Configuration Caching (1 page)
Cache configuration data from CONFIG_LOADER:
- **Config Version Tracking**: Version keys to handle hot-reload updates
- **Distributed Config Sync**: Pub/sub for configuration change notifications
- **Template Caching**: Cache compiled prompt templates with variables
- **Feature Flag Caching**: Fast feature flag lookups with instant propagation

### 5. Weight Processing Cache (1 page)
Cache processed weight calculations:
- **Calculation Results**: Cache WeightProcessor outputs by input string
- **Unit Conversions**: Cache common unit conversion results
- **Category Mappings**: Cache weight category determinations
- **Validation Results**: Cache expensive validation operations

### 6. Cache Monitoring and Metrics (1 page)
Integrate with ERROR_MONITORING for observability:
- **Performance Metrics**: Operation latency, throughput, queue depth
- **Hit Rate Metrics**: By cache type (AI, config, weight), by key pattern
- **Memory Metrics**: Usage, eviction rate, key count by type
- **Error Metrics**: Connection failures, timeout rate, serialization errors
- **Business Metrics**: API cost savings, response time improvement

### 7. Security and Compliance (0.5 pages)
Implement security measures:
- **Encryption**: TLS for Redis connections, encryption at rest in production
- **Access Control**: Redis ACL for least privilege, separate users per environment
- **Key Sanitization**: Prevent injection attacks in cache keys
- **PII Protection**: No personal data in cache, anonymized keys

### 8. Testing Strategy (0.5 pages)
Define comprehensive testing approach:
- **Unit Tests**: Mock Redis client, test serialization/deserialization
- **Integration Tests**: Real Redis instance, connection failure scenarios
- **Performance Tests**: Benchmark operations, load testing
- **Chaos Tests**: Network partitions, Redis failures

## Implementation Guidelines

### Code Organization
```
src/services/cache/
├── __init__.py
├── base.py          # Abstract cache interface
├── redis_cache.py   # Redis implementation
├── serializers.py   # Pydantic serialization
├── key_builder.py   # Cache key generation
└── decorators.py    # @cache_result decorator
```

### Configuration Integration
- Use ENV_MANAGER for Redis connection settings (SIZECOMPARATOR_REDIS_HOST, etc.)
- Support CONFIG_LOADER hot-reload for cache TTL changes
- Integrate with ERROR_MONITORING for metrics and logging

### Error Handling Patterns
- Never let cache failures break core functionality
- Log all cache misses at DEBUG level
- Alert on cache hit rate below 80%
- Use circuit breakers for Redis operations

### Performance Requirements
- Connection pool size: min 10, max 50
- Operation timeout: 100ms
- Batch size limit: 100 keys
- Pipeline size limit: 1000 operations

## Example Usage

```python
from src.services.cache import CacheService, cache_result

cache = CacheService.from_env()

# AI response caching
@cache_result(ttl=86400, prefix="ai_response")
async def get_ai_comparison(weight: ProcessedWeight, provider: AIProvider):
    return await provider.generate_comparison(weight)

# Manual cache operations
await cache.set("config:version", "1.2.3", ttl=300)
version = await cache.get("config:version")

# Batch operations
keys = ["weight:5kg", "weight:10lbs", "weight:100g"]
values = await cache.multi_get(keys)
```

## Quality Metrics
- Test coverage: 95%+ for cache service
- Cache hit rate: 90%+ in production
- Operation latency: p99 < 10ms
- Zero data loss on Redis restart

Generate a comprehensive specification that provides clear implementation guidance while maintaining flexibility for future enhancements like multi-region caching or alternative cache backends.