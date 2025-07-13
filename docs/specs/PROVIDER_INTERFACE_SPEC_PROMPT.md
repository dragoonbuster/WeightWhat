# Provider Interface Specification Prompt

Create a focused PROVIDER_INTERFACE_SPEC.md specification for SizeComparator's abstract AI provider interface. Target 5-6 pages maximum.

## Context
This specification defines the abstract base class and contracts that all AI providers (OpenAI, Anthropic, X.ai) must implement, ensuring consistent behavior and seamless integration across the system.

## Document Requirements

### 1. Abstract Base Class Definition (1.5 pages)
- Complete `AIProvider` abstract base class with all required methods
- `generate_comparisons(weight: Weight) -> List[Comparison]` - Core comparison generation
- `validate_response(response: Any) -> bool` - Response validation interface
- `get_health_status() -> ProviderHealth` - Health monitoring interface
- `parse_response(raw_response: str) -> ComparisonResponse` - Response parsing

### 2. Provider Lifecycle Management (1 page)
- Initialization patterns with configuration injection
- Graceful shutdown procedures with resource cleanup
- Configuration hot-reload support
- Error recovery and restart procedures

### 3. Circuit Breaker Integration (1 page) 
- Circuit breaker state management (CLOSED, OPEN, HALF_OPEN)
- Health check integration with DEPLOYMENT_OPS_SPEC endpoints
- Failure threshold configuration and monitoring
- Automatic recovery testing procedures

### 4. Response Validation Framework (1 page)
- Quality scoring interface (0.0-1.0 confidence)
- Content validation (exactly 2 comparisons, appropriate objects)
- Mathematical accuracy validation (weight relationships)
- Safety filtering interface for inappropriate content

### 5. Error Handling and Retry Logic (1 page)
- Provider-specific error categorization
- Retry strategy interface with exponential backoff
- Timeout handling and request cancellation
- Integration with ERROR_MONITORING_SPEC logging

### 6. Configuration and Testing Integration (0.5 pages)
- CONFIG_SYSTEM_SPEC integration for provider settings
- Mock provider interface for TESTING_SPEC
- Performance monitoring and metrics collection
- Extensibility patterns for new providers

## Integration Requirements
- Reference AI_PROVIDER_SPEC for overall architecture
- Define exact contracts for OPENAI_PROVIDER_SPEC, ANTHROPIC_PROVIDER_SPEC, XAI_PROVIDER_SPEC
- Integrate with CONFIG_SYSTEM_SPEC for configuration management
- Align with ERROR_MONITORING_SPEC for structured logging
- Support DEPLOYMENT_OPS_SPEC health monitoring

## Focus Areas
- Extensibility for adding new AI providers
- Testability with comprehensive mock interfaces  
- Reliability through circuit breakers and retries
- Performance monitoring and optimization hooks
- Type safety with full Pydantic integration