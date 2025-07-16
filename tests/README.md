# SizeComparator Test Suite

This directory contains the consolidated test suite for the SizeComparator project, organized around the unified architecture.

## Test Structure

```
tests/
├── conftest.py                           # Shared fixtures and configuration
├── pytest.ini                           # Pytest configuration
├── README.md                            # This file
├── test_unified_application.py          # Unified app and service factory tests
├── test_comparison_services.py          # All comparison service tests
├── unit/
│   ├── test_weight_processor_consolidated.py  # Weight processing unit tests
│   ├── test_ai_providers_consolidated.py      # AI provider unit tests
│   └── test_openai_provider.py               # Original OpenAI tests (kept for reference)
└── integration/
    └── test_complete_system.py          # End-to-end integration tests
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Weight Processor**: Comprehensive tests for weight validation, conversion, and processing
- **AI Providers**: Tests for OpenAI, Anthropic, and XAI providers including configuration and responses
- **Core Components**: Tests for individual components and utilities

### Integration Tests (`tests/integration/`)
- **Complete System**: End-to-end tests covering the full request-response cycle
- **Service Integration**: Tests for service factory, provider selection, and fallback behavior
- **Performance**: Tests for response times, throughput, and resource usage

### Unified Application Tests (`tests/`)
- **Unified Application**: Tests for the unified FastAPI application
- **Service Factory**: Tests for intelligent service selection and routing
- **Comparison Services**: Tests for all comparison service implementations

## Test Markers

The test suite uses pytest markers to organize and control test execution:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (require full system)
- `@pytest.mark.ai_required` - Tests requiring AI provider API keys
- `@pytest.mark.performance` - Performance and load tests
- `@pytest.mark.slow` - Tests that take more than a few seconds

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only
```bash
pytest -m unit
```

### Integration Tests Only
```bash
pytest -m integration
```

### Skip AI Tests (when no API keys available)
```bash
pytest -m "not ai_required"
```

### Performance Tests
```bash
pytest -m performance
```

### Specific Test File
```bash
pytest tests/test_unified_application.py
pytest tests/unit/test_weight_processor_consolidated.py
pytest tests/integration/test_complete_system.py
```

### With Coverage
```bash
pytest --cov=src --cov-report=html
```

## Test Configuration

### Environment Variables
- `RUN_INTEGRATION_TESTS=true` - Enable integration tests
- `SIZECOMPARATOR_OPENAI_API_KEY` - OpenAI API key for AI tests
- `SIZECOMPARATOR_ANTHROPIC_API_KEY` - Anthropic API key for AI tests
- `SIZECOMPARATOR_XAI_API_KEY` - XAI API key for AI tests

### Test Environment
Tests run in a controlled environment with:
- Mock dependencies by default
- Isolated test database/cache
- Disabled external API calls (unless marked `ai_required`)
- Predictable test data

## Test Data and Fixtures

### Common Fixtures (conftest.py)
- `sample_mvp_request` - Standard MVP request for testing
- `sample_mvp_requests` - Multiple requests for batch testing
- `test_env_manager` - Environment manager configured for testing
- `mock_service_factory` - Mock service factory for unit tests
- `enable_ai_providers` - Enable AI providers for testing
- `disable_ai_providers` - Disable AI providers for fallback testing

### Weight Test Data
- Light weights: 0.1 kg, 100 g, 1 oz
- Medium weights: 5 kg, 10 lbs, 2.5 kg
- Heavy weights: 100 kg, 1000 lbs, 1 ton
- Extreme weights: 10 tons, 0.001 g

### Service Test Scenarios
- Basic service (fallback only)
- Fast validation (AI with <2s target)
- Full validation (comprehensive AI analysis)
- Comprehensive service (full feature set)

## Test Quality Standards

### Coverage Requirements
- Unit tests: 95% coverage minimum
- Integration tests: Cover all major user flows
- Overall: 80% coverage minimum (enforced by pytest)

### Test Principles
1. **Fast by default**: Unit tests should run in milliseconds
2. **Isolated**: Tests should not depend on external services
3. **Deterministic**: Tests should produce consistent results
4. **Comprehensive**: Cover both happy paths and error cases
5. **Maintainable**: Clear test names and structure

### Error Testing
All tests include error scenarios:
- Invalid input handling
- Network failures
- Service unavailability
- Timeout conditions
- Rate limiting
- Malformed responses

## Continuous Integration

The test suite is designed for CI/CD pipelines:

```yaml
# Example CI configuration
test:
  script:
    - pytest -m "not ai_required" --cov=src --cov-report=xml
    - pytest -m "unit" --junitxml=junit.xml
```

### Test Stages
1. **Unit Tests**: Fast, isolated tests
2. **Integration Tests**: Full system tests (may skip AI)
3. **Performance Tests**: Load and performance validation
4. **AI Tests**: Optional tests with real API keys

## Maintenance

### Adding New Tests
1. Choose appropriate test category (unit/integration)
2. Use existing fixtures when possible
3. Follow naming conventions: `test_<functionality>_<scenario>`
4. Add appropriate markers
5. Include both success and failure cases

### Updating Tests
When adding new features:
1. Update relevant test files
2. Add new fixtures if needed
3. Update test data for new scenarios
4. Ensure backward compatibility

### Test Data Management
- Use factories for complex test objects
- Keep test data minimal and focused
- Use parameterized tests for multiple scenarios
- Mock external dependencies

## Debugging Tests

### Common Issues
- **Import errors**: Check PYTHONPATH and src directory structure
- **Fixture not found**: Ensure conftest.py is in the right location
- **AI tests failing**: Check API key configuration
- **Slow tests**: Use appropriate markers and consider mocking

### Debug Commands
```bash
# Run with verbose output
pytest -v

# Run with debugging
pytest --pdb

# Run specific test with output
pytest -s tests/test_unified_application.py::TestUnifiedApplication::test_app_initialization

# Show test coverage
pytest --cov=src --cov-report=term-missing
```

## Future Enhancements

Planned improvements:
1. **Property-based testing** for weight processing
2. **Contract testing** for API endpoints
3. **Mutation testing** for test quality validation
4. **Performance regression detection**
5. **Automated test data generation**