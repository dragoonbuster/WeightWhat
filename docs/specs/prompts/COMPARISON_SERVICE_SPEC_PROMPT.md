# Weight Comparison Service Specification Prompt for SizeComparator

## Context
You are a senior software architect designing the core comparison service for SizeComparator, which orchestrates the entire weight comparison flow from user input to AI-generated responses. This service is the central orchestrator that ties together all Phase 1 foundation components and Phase 2 provider implementations.

## Objective
Create a comprehensive specification (10-12 pages) for the weight comparison service that processes user requests, selects appropriate AI providers, manages fallbacks, and returns engaging weight comparisons while ensuring high availability and performance.

## System Context
- **Foundation**: Weight processing with Decimal precision, configuration hot-reload, environment management, comprehensive monitoring
- **AI Providers**: OpenAI, Anthropic, X.ai with different capabilities and costs
- **Caching**: Redis-based caching for responses and calculations
- **Requirements**: 99% uptime SLA, <2 second response time, graceful degradation

## Specification Requirements

### 1. Service Architecture (2 pages)
Design the comparison service architecture:
- **Service Pattern**: Orchestrator pattern with dependency injection
- **Component Design**: ComparisonService, ProviderSelector, ResponseBuilder, ComparisonCache
- **Request Flow**: Input validation → Weight processing → Provider selection → AI generation → Response building → Caching
- **Concurrency Model**: Async/await with proper timeout handling
- **Dependency Management**: Constructor injection for all dependencies
- **State Management**: Stateless service design for horizontal scaling

### 2. Core Comparison Logic (2 pages)
Implement the main comparison workflow:
- **Request Processing Pipeline**:
  - Parse and validate weight input using WeightProcessor
  - Determine weight category and context
  - Select appropriate comparison objects
  - Build provider-specific prompts
- **Context Enhancement**: Add relevant context based on weight category (microscopic, light, heavy, etc.)
- **Comparison Strategies**: Single object, multiple objects, creative combinations
- **Localization Support**: Format weights based on user locale
- **Response Enrichment**: Add metadata, confidence scores, visualization prompts

### 3. AI Provider Selection (2 pages)
Implement intelligent provider selection aligned with AI_PROVIDER_SPEC:
- **Selection Criteria**:
  - Provider availability (circuit breaker state)
  - Cost optimization (prefer cheaper providers for simple requests)
  - Capability matching (complex requests to advanced models)
  - User preferences (explicit provider selection)
- **Fallback Chain**: Primary → Secondary → Tertiary with configuration
- **Load Balancing**: Round-robin or weighted selection for available providers
- **A/B Testing Support**: Route percentage of traffic to test new providers
- **Provider Specialization**: Route specific weight categories to best providers

### 4. Prompt Engineering (1.5 pages)
Design the prompt generation system:
- **Template Management**: Load templates from configuration
- **Variable Injection**: Safe template variable substitution
- **Context Building**:
  ```
  weight_value, weight_unit, category, comparable_objects, user_context
  ```
- **Provider Adaptation**: Adjust prompts for provider-specific requirements
- **Prompt Optimization**: Track successful prompts, iterate on templates
- **Safety Filters**: Ensure appropriate content generation

### 5. Response Processing (1.5 pages)
Process and enhance AI responses:
- **Response Parsing**: Extract comparison text and metadata from AI responses
- **Validation**: Ensure response contains actual comparisons
- **Enhancement**:
  - Add visualization suggestions
  - Include confidence scores
  - Format numbers consistently
  - Add source attribution
- **Fallback Responses**: Pre-generated comparisons for common weights
- **Response Caching**: Store successful responses with appropriate TTL

### 6. Error Handling and Resilience (1.5 pages)
Implement comprehensive error handling:
- **Error Scenarios**:
  - Invalid weight input → Return specific validation errors
  - All providers unavailable → Return cached or fallback response
  - Timeout → Try faster provider or return partial response
  - Invalid AI response → Retry with adjusted prompt
- **Graceful Degradation**:
  - Serve cached responses when possible
  - Use pre-computed comparisons for common weights
  - Provide basic mathematical comparisons as last resort
- **Circuit Breaker Integration**: Per-provider circuit breakers with monitoring
- **Retry Logic**: Exponential backoff with jitter, max 3 retries

### 7. Performance Optimization (1 page)
Optimize for <2 second response time:
- **Caching Strategy**:
  - Cache hit path: <100ms response time
  - Normalize inputs for better cache efficiency
  - Pre-warm cache with common comparisons
- **Parallel Processing**: When using fallbacks, query multiple providers concurrently
- **Timeout Management**: 1.5s provider timeout to meet 2s SLA
- **Resource Pooling**: Connection pools for Redis and HTTP clients
- **Request Deduplication**: Combine identical concurrent requests

### 8. Monitoring and Analytics (1 page)
Comprehensive monitoring integration:
- **Service Metrics**:
  - Request rate, response time, error rate (RED metrics)
  - Provider selection distribution
  - Cache hit rate by weight category
  - Fallback usage rate
- **Business Metrics**:
  - Popular weight comparisons
  - User satisfaction (based on response quality)
  - Cost per comparison by provider
  - API credit usage tracking
- **Quality Metrics**:
  - Response relevance scores
  - Comparison accuracy tracking
  - User feedback integration

### 9. Testing Strategy (0.5 pages)
Comprehensive testing approach:
- **Unit Tests**: Mock all dependencies, test error paths
- **Integration Tests**: Test with real providers using test API keys
- **Load Tests**: Verify 2-second SLA under load
- **Chaos Tests**: Provider failures, network issues
- **Contract Tests**: Verify provider API compatibility

## Implementation Guidelines

### Code Organization
```
src/services/comparison/
├── __init__.py
├── comparison_service.py    # Main orchestrator
├── provider_selector.py     # Provider selection logic
├── prompt_builder.py        # Prompt generation
├── response_processor.py    # Response enhancement
├── fallback_handler.py      # Fallback logic
└── comparison_cache.py      # Caching integration
```

### Configuration Schema
```yaml
comparison_service:
  provider_selection:
    strategy: "cost_optimized"  # or "round_robin", "capability_based"
    fallback_chain: ["openai", "anthropic", "xai"]
    cost_threshold: 0.01  # Switch to cheaper provider below this
  
  prompt_templates:
    default: "templates/comparison_default.json"
    creative: "templates/comparison_creative.json"
    technical: "templates/comparison_technical.json"
  
  response_processing:
    min_comparison_length: 50
    max_comparison_length: 500
    require_objects: true
    confidence_threshold: 0.7
  
  performance:
    provider_timeout_ms: 1500
    max_retries: 3
    cache_ttl_seconds: 86400
```

### API Interface
```python
class ComparisonService:
    async def create_comparison(
        self,
        weight_input: str,
        preferred_provider: Optional[AIProvider] = None,
        comparison_style: str = "default",
        include_visualization: bool = True,
        user_context: Optional[Dict[str, Any]] = None
    ) -> WeightComparisonResponse:
        """
        Create a weight comparison using AI providers.
        
        Returns a complete response with comparison text,
        metadata, and visualization suggestions.
        """
```

## Example Usage

```python
# Initialize service
comparison_service = ComparisonService(
    weight_processor=weight_processor,
    provider_factory=provider_factory,
    cache_service=cache_service,
    config=config,
    metrics=metrics_collector
)

# Create comparison
response = await comparison_service.create_comparison(
    weight_input="5.5 kilograms",
    comparison_style="creative",
    include_visualization=True
)

# Response includes:
# - comparison_text: "5.5 kilograms is about the weight of a bowling ball..."
# - comparison_objects: ["bowling ball", "house cat"]
# - visualization_prompt: "Draw a balanced scale with..."
# - metadata: provider used, response time, cache hit, confidence
```

## Success Criteria
- 99% uptime with graceful degradation
- <2 second response time (p95)
- 90%+ cache hit rate for common weights
- Zero data loss during provider failures
- Seamless provider fallback without user impact

Generate a comprehensive specification that makes the comparison service the reliable, performant heart of the SizeComparator application while maintaining flexibility for future enhancements.