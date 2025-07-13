# SizeComparator Unit Testing Framework Specification

## Document Overview

This comprehensive specification defines the unit testing framework for SizeComparator, focusing on isolated component testing with 80%+ coverage requirements. The framework emphasizes deterministic test execution through sophisticated mocking, comprehensive validation scenarios, and robust test organization strategies that integrate seamlessly with all system components.

**Document Length**: 5 pages  
**Coverage Target**: 80%+ line and branch coverage  
**Integration Reference**: TESTING_SPEC.md  
**Dependencies**: BACKEND_CORE_SPEC.md, AI_PROVIDER_SPEC.md, CONFIG_SYSTEM_SPEC.md, ERROR_MONITORING_SPEC.md

## 1. Unit Testing Architecture & Patterns (1 page)

### 1.1 Testing Philosophy

The SizeComparator unit testing framework follows a test-first approach with clear boundaries between unit, integration, and end-to-end tests. Unit tests focus exclusively on isolated component behavior without external dependencies.

```python
# Core testing principles
from typing import Dict, Any, Optional, List
from decimal import Decimal, ROUND_HALF_UP
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pydantic import ValidationError

class UnitTestBase:
    """Base class for all unit tests with common setup patterns"""
    
    def setup_method(self):
        """Setup clean test environment for each test"""
        self.mock_config = Mock()
        self.mock_logger = Mock()
        self.test_data = TestDataFactory()
        
    def teardown_method(self):
        """Cleanup after each test"""
        self.mock_config.reset_mock()
        self.mock_logger.reset_mock()

# Pattern 1: Weight Processing Unit Tests
class TestWeightProcessor(UnitTestBase):
    """Unit tests for weight processing logic with pure function testing"""
    
    def test_parse_weight_input_valid_formats(self):
        """Test weight parsing with deterministic inputs"""
        processor = WeightProcessor(self.mock_config)
        
        test_cases = [
            ("100 kg", Decimal("100.000000"), WeightUnit.KILOGRAM),
            ("5.5 pounds", Decimal("2.494758"), WeightUnit.POUND),
            ("2.3 stone", Decimal("14.515177"), WeightUnit.STONE),
            ("1000g", Decimal("1.000000"), WeightUnit.GRAM),
            ("50 oz", Decimal("1.417476"), WeightUnit.OUNCE)
        ]
        
        for input_str, expected_kg, expected_unit in test_cases:
            result = processor.parse_weight_input(input_str)
            assert result.weight_kg == expected_kg
            assert result.unit_used == expected_unit
            assert result.original_input == input_str

    def test_weight_conversion_precision(self):
        """Test high-precision weight conversions"""
        converter = WeightConverter()
        
        # Test kg to pound conversion with 6 decimal precision
        kg_value = Decimal("1.000000")
        pound_result = converter.convert(kg_value, WeightUnit.KILOGRAM, WeightUnit.POUND)
        expected = Decimal("2.204623")  # Exact conversion factor
        assert pound_result == expected
        
        # Test round-trip conversion maintains precision
        back_to_kg = converter.convert(pound_result, WeightUnit.POUND, WeightUnit.KILOGRAM)
        assert back_to_kg == kg_value

    def test_weight_validation_edge_cases(self):
        """Test weight validation boundary conditions"""
        validator = WeightValidator(self.mock_config)
        
        # Configure mock for validation limits
        self.mock_config.get.side_effect = lambda key, default=None: {
            "comparison.min_weight_kg": Decimal("0.001"),
            "comparison.max_weight_kg": Decimal("1000000"),
            "comparison.precision": 6
        }.get(key, default)
        
        # Test boundary values
        assert validator.validate_weight(Decimal("0.001")) is True  # Minimum valid
        assert validator.validate_weight(Decimal("1000000")) is True  # Maximum valid
        
        with pytest.raises(ValidationError):
            validator.validate_weight(Decimal("0.0001"))  # Below minimum
        
        with pytest.raises(ValidationError):
            validator.validate_weight(Decimal("1000001"))  # Above maximum

# Pattern 2: Parameterized Testing for Multiple Scenarios
@pytest.mark.parametrize("input_text,expected_weight,expected_unit,should_succeed", [
    ("100 kilograms", Decimal("100.000000"), WeightUnit.KILOGRAM, True),
    ("fifty pounds", None, None, False),  # Natural language - requires AI
    ("5.5 lbs", Decimal("2.494758"), WeightUnit.POUND, True),
    ("invalid weight", None, None, False),
    ("0 kg", None, None, False),  # Zero weight invalid
    ("-5 kg", None, None, False),  # Negative weight invalid
])
def test_weight_parsing_scenarios(input_text, expected_weight, expected_unit, should_succeed):
    """Parameterized testing for weight parsing scenarios"""
    processor = WeightProcessor(Mock())
    
    if should_succeed:
        result = processor.parse_weight_input(input_text)
        assert result.weight_kg == expected_weight
        assert result.unit_used == expected_unit
    else:
        with pytest.raises((ValidationError, ValueError)):
            processor.parse_weight_input(input_text)

# Pattern 3: Error Condition Testing
class TestWeightProcessorErrorHandling(UnitTestBase):
    """Test error handling in weight processing"""
    
    def test_invalid_unit_handling(self):
        """Test handling of invalid weight units"""
        processor = WeightProcessor(self.mock_config)
        
        invalid_inputs = [
            "100 invalid_unit",
            "50 xyz",
            "weight without unit",
            "just text"
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises(ValidationError) as exc_info:
                processor.parse_weight_input(invalid_input)
            
            # Verify error structure follows ERROR_MONITORING_SPEC
            assert "INVALID_WEIGHT_FORMAT" in str(exc_info.value)

    def test_numerical_overflow_protection(self):
        """Test protection against numerical overflow"""
        converter = WeightConverter()
        
        with pytest.raises(ValidationError) as exc_info:
            # Test extremely large number
            converter.convert(Decimal("1e50"), WeightUnit.KILOGRAM, WeightUnit.GRAM)
        
        assert "NUMERICAL_OVERFLOW" in str(exc_info.value)
```

### 1.2 Test Organization Strategy

```python
# Directory structure for unit tests
"""
tests/
├── unit/
│   ├── core/
│   │   ├── test_weight_processor.py      # Weight processing logic
│   │   ├── test_weight_validator.py      # Input validation
│   │   ├── test_weight_converter.py      # Unit conversions
│   │   └── test_weight_formatter.py      # Display formatting
│   ├── models/
│   │   ├── test_request_models.py        # Pydantic request validation
│   │   ├── test_response_models.py       # Response model testing
│   │   ├── test_error_models.py          # Error response models
│   │   └── test_ai_models.py             # AI provider models
│   ├── api/
│   │   ├── test_dependencies.py          # FastAPI dependencies
│   │   ├── test_route_handlers.py        # Route logic (without HTTP)
│   │   └── test_middleware.py            # Custom middleware
│   ├── config/
│   │   ├── test_configuration_service.py # CONFIG_SYSTEM_SPEC compliance
│   │   ├── test_settings_validation.py   # Settings validation
│   │   └── test_environment_loading.py   # Environment variable handling
│   └── utils/
│       ├── test_exceptions.py            # Custom exception classes
│       ├── test_decorators.py            # Utility decorators
│       └── test_helpers.py               # Helper functions
├── fixtures/
│   ├── weight_data.py                    # Weight test data
│   ├── config_data.py                    # Configuration fixtures
│   └── response_data.py                  # Response fixtures
└── conftest.py                           # Pytest configuration
"""
```

## 2. Mock Implementations for AI Providers & Dependencies (1.5 pages)

### 2.1 AI Provider Mock Interface

```python
from typing import Dict, Any, Optional, Callable, List
import asyncio
from unittest.mock import AsyncMock
from backend.ai_providers.interface import AIProvider, ProviderHealth, ProviderStatus
from backend.models.responses import WeightComparisonResponse

class MockAIProviderFactory:
    """Factory for creating AI provider mocks with configurable behaviors"""
    
    @staticmethod
    def create_basic_mock() -> Mock:
        """Create basic AI provider mock for simple test scenarios"""
        mock_provider = AsyncMock(spec=AIProvider)
        mock_provider.name = "mock_provider"
        mock_provider.provider_type = "test"
        
        # Default successful response
        default_response = TestDataFactory.create_weight_comparison_response()
        mock_provider.generate_comparison.return_value = default_response
        mock_provider.get_health_status.return_value = ProviderHealth(
            status=ProviderStatus.HEALTHY,
            success_rate=1.0,
            avg_response_time_ms=150,
            error_count=0,
            last_error=None,
            circuit_state="CLOSED",
            provider_name="mock_provider"
        )
        
        return mock_provider
    
    @staticmethod
    def create_failing_mock(error_type: Exception = Exception("Mock error")) -> Mock:
        """Create AI provider mock that simulates failures"""
        mock_provider = AsyncMock(spec=AIProvider)
        mock_provider.name = "failing_mock_provider"
        mock_provider.generate_comparison.side_effect = error_type
        mock_provider.get_health_status.return_value = ProviderHealth(
            status=ProviderStatus.UNHEALTHY,
            success_rate=0.0,
            avg_response_time_ms=0,
            error_count=1,
            last_error=str(error_type),
            circuit_state="OPEN",
            provider_name="failing_mock_provider"
        )
        
        return mock_provider
    
    @staticmethod
    def create_configurable_mock(response_config: Dict[str, Any]) -> Mock:
        """Create AI provider mock with configurable responses"""
        mock_provider = AsyncMock(spec=AIProvider)
        mock_provider.name = "configurable_mock_provider"
        
        # Configure responses based on input patterns
        async def mock_generate_comparison(request):
            request_key = f"{request.item1_name}_{request.item2_name}"
            if request_key in response_config.get("responses", {}):
                return response_config["responses"][request_key]
            elif response_config.get("default_error"):
                raise response_config["default_error"]
            else:
                return TestDataFactory.create_weight_comparison_response()
        
        mock_provider.generate_comparison.side_effect = mock_generate_comparison
        
        # Configure health status
        health_config = response_config.get("health", {})
        mock_provider.get_health_status.return_value = ProviderHealth(
            status=health_config.get("status", ProviderStatus.HEALTHY),
            success_rate=health_config.get("success_rate", 1.0),
            avg_response_time_ms=health_config.get("avg_response_time_ms", 150),
            error_count=health_config.get("error_count", 0),
            last_error=health_config.get("last_error"),
            circuit_state=health_config.get("circuit_state", "CLOSED"),
            provider_name="configurable_mock_provider"
        )
        
        return mock_provider

class TestAIProviderIntegration(UnitTestBase):
    """Unit tests for AI provider integration without actual API calls"""
    
    def test_ai_provider_response_validation(self):
        """Test AI provider response validation logic"""
        from backend.core.ai_interface import AIProviderInterface
        
        # Setup mock provider
        mock_provider = MockAIProviderFactory.create_basic_mock()
        ai_interface = AIProviderInterface(mock_provider, self.mock_config)
        
        # Test successful validation
        valid_response = TestDataFactory.create_weight_comparison_response()
        assert ai_interface.validate_response(valid_response) is True
        
        # Test invalid response validation
        invalid_response = {"invalid": "response"}
        assert ai_interface.validate_response(invalid_response) is False
    
    def test_ai_provider_fallback_logic(self):
        """Test AI provider fallback without external dependencies"""
        from backend.core.ai_interface import AIProviderManager
        
        # Setup primary failing provider and backup working provider
        primary_provider = MockAIProviderFactory.create_failing_mock()
        backup_provider = MockAIProviderFactory.create_basic_mock()
        
        manager = AIProviderManager([primary_provider, backup_provider], self.mock_config)
        
        # Test fallback occurs when primary fails
        result = asyncio.run(manager.generate_comparison_with_fallback({
            "item1_name": "elephant",
            "item2_name": "car"
        }))
        
        # Verify backup provider was called
        backup_provider.generate_comparison.assert_called_once()
        assert isinstance(result, WeightComparisonResponse)
    
    def test_ai_provider_circuit_breaker_simulation(self):
        """Test circuit breaker behavior without real AI calls"""
        from backend.core.circuit_breaker import CircuitBreaker
        
        mock_provider = MockAIProviderFactory.create_failing_mock()
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout_seconds=60,
            expected_exception=Exception
        )
        
        # Simulate multiple failures to trigger circuit breaker
        for _ in range(4):  # One more than threshold
            with pytest.raises(Exception):
                circuit_breaker.call(mock_provider.generate_comparison, {})
        
        # Verify circuit breaker is now OPEN
        assert circuit_breaker.state == "OPEN"
```

### 2.2 External Dependencies Mock Patterns

```python
class MockConfigurationService:
    """Mock configuration service for unit testing"""
    
    def __init__(self, config_data: Dict[str, Any] = None):
        self.config_data = config_data or self._default_test_config()
        self.hot_reload_enabled = False
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value for testing"""
        keys = key.split('.')
        config = self.config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def _default_test_config(self) -> Dict[str, Any]:
        """Default test configuration"""
        return {
            "application": {
                "name": "SizeComparator",
                "version": "1.0.0-test",
                "environment": "test"
            },
            "comparison": {
                "min_weight_kg": Decimal("0.001"),
                "max_weight_kg": Decimal("1000000"),
                "precision": 6,
                "default_unit": "kg"
            },
            "api": {
                "timeout_seconds": 30,
                "rate_limit": {
                    "requests_per_minute": 100,
                    "burst_limit": 25
                }
            },
            "ai_providers": {
                "retry": {
                    "max_attempts": 3,
                    "initial_delay_ms": 1000,
                    "backoff_multiplier": 2.0
                },
                "circuit_breaker": {
                    "failure_threshold": 5,
                    "timeout_seconds": 60
                }
            }
        }

class MockDatabaseService:
    """Mock database service for unit testing"""
    
    def __init__(self):
        self.data_store = {}
        self.call_log = []
    
    async def save_comparison_result(self, result: WeightComparisonResponse) -> str:
        """Mock save operation"""
        result_id = f"test_result_{len(self.data_store)}"
        self.data_store[result_id] = result.model_dump()
        self.call_log.append(("save", result_id))
        return result_id
    
    async def get_comparison_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Mock retrieve operation"""
        self.call_log.append(("get", result_id))
        return self.data_store.get(result_id)
    
    def reset_mock(self):
        """Reset mock state"""
        self.data_store.clear()
        self.call_log.clear()

# Usage in unit tests
class TestServiceIntegration(UnitTestBase):
    """Test service integration with mocked dependencies"""
    
    def setup_method(self):
        super().setup_method()
        self.mock_config = MockConfigurationService()
        self.mock_db = MockDatabaseService()
    
    def test_service_with_mocked_dependencies(self):
        """Test service behavior with all dependencies mocked"""
        from backend.services.comparison_service import ComparisonService
        
        service = ComparisonService(
            config_service=self.mock_config,
            db_service=self.mock_db,
            logger=self.mock_logger
        )
        
        # Test successful operation
        result = asyncio.run(service.process_comparison({
            "item1_name": "elephant",
            "item1_weight": "5000 kg",
            "item2_name": "car", 
            "item2_weight": "1500 kg"
        }))
        
        # Verify mocked dependencies were called correctly
        assert len(self.mock_db.call_log) == 1
        assert self.mock_db.call_log[0][0] == "save"
        assert isinstance(result, WeightComparisonResponse)
```

## 3. Pydantic Model Testing with Comprehensive Validation (1 page)

### 3.1 Model Validation Testing Patterns

```python
class TestPydanticModelValidation:
    """Comprehensive Pydantic model validation testing"""
    
    def test_weight_comparison_request_validation(self):
        """Test WeightComparisonRequest validation scenarios"""
        from backend.models.requests import WeightComparisonRequest
        
        # Valid request
        valid_data = {
            "item1_name": "Elephant",
            "item1_weight": "5000 kg",
            "item2_name": "Car",
            "item2_weight": "1500 kg",
            "output_unit": "kg"
        }
        
        request = WeightComparisonRequest(**valid_data)
        assert request.item1_name == "Elephant"
        assert request.output_unit == WeightUnit.KILOGRAM
    
    @pytest.mark.parametrize("invalid_data,expected_error", [
        ({"item1_name": "", "item1_weight": "100 kg", "item2_name": "Car", "item2_weight": "1000 kg"}, "item1_name"),
        ({"item1_name": "A" * 101, "item1_weight": "100 kg", "item2_name": "Car", "item2_weight": "1000 kg"}, "item1_name"),
        ({"item1_name": "Elephant", "item1_weight": "", "item2_name": "Car", "item2_weight": "1000 kg"}, "item1_weight"),
        ({"item1_name": "Elephant", "item1_weight": "100 kg", "item2_name": "Car"}, "item2_weight"),
        ({"item1_name": "Elephant", "item1_weight": "100 kg", "item2_name": "Car", "item2_weight": "1000 kg", "output_unit": "invalid"}, "output_unit"),
    ])
    def test_weight_comparison_request_validation_errors(self, invalid_data, expected_error):
        """Test validation errors for invalid request data"""
        from backend.models.requests import WeightComparisonRequest
        
        with pytest.raises(ValidationError) as exc_info:
            WeightComparisonRequest(**invalid_data)
        
        # Verify specific field validation failed
        assert expected_error in str(exc_info.value)
    
    def test_weight_item_decimal_precision(self):
        """Test WeightItem Decimal precision handling"""
        from backend.models.responses import WeightItem
        
        # Test precise decimal handling
        weight_data = {
            "name": "Test Item",
            "original_input": "100.123456 kg",
            "weight_kg": Decimal("100.123456"),
            "weight_display": "100.12 kg",
            "unit_used": WeightUnit.KILOGRAM,
            "confidence": 0.95
        }
        
        item = WeightItem(**weight_data)
        assert item.weight_kg == Decimal("100.123456")
        assert item.confidence == 0.95
        
        # Test precision limits
        with pytest.raises(ValidationError):
            WeightItem(
                **{**weight_data, "weight_kg": Decimal("0.0001")}  # Below minimum
            )
    
    def test_error_response_model_validation(self):
        """Test ErrorResponse model validation following ERROR_MONITORING_SPEC"""
        from backend.models.errors import ErrorResponse, ErrorCategory, ErrorSeverity
        
        error_data = {
            "error_code": "VALIDATION_ERROR",
            "error_category": ErrorCategory.CLIENT_ERROR,
            "message": "Invalid input provided",
            "request_id": "test-req-123",
            "severity": ErrorSeverity.WARNING,
            "remediation_hint": "Check input format"
        }
        
        error_response = ErrorResponse(**error_data)
        assert error_response.error_category == ErrorCategory.CLIENT_ERROR
        assert error_response.severity == ErrorSeverity.WARNING
        assert error_response.timestamp is not None  # Auto-generated
    
    def test_response_metadata_validation(self):
        """Test ResponseMetadata model validation"""
        from backend.models.responses import ResponseMetadata
        
        metadata_data = {
            "request_id": "test-request-456",
            "processing_time_ms": 250,
            "ai_provider_used": "openai",
            "ai_response_time_ms": 200,
            "cache_hit": False,
            "version": "1.0.0"
        }
        
        metadata = ResponseMetadata(**metadata_data)
        assert metadata.processing_time_ms == 250
        assert metadata.cache_hit is False
        assert metadata.timestamp is not None
        
        # Test auto-generated UUID for request_id
        metadata_no_id = ResponseMetadata(
            processing_time_ms=100,
            ai_provider_used="anthropic",
            ai_response_time_ms=90,
            version="1.0.0"
        )
        assert metadata_no_id.request_id is not None
        assert len(metadata_no_id.request_id) == 36  # UUID format

### 3.2 Model Serialization Testing

class TestModelSerialization:
    """Test Pydantic model serialization and deserialization"""
    
    def test_weight_comparison_response_serialization(self):
        """Test complete WeightComparisonResponse serialization"""
        response = TestDataFactory.create_weight_comparison_response()
        
        # Test JSON serialization
        json_data = response.model_dump()
        assert "item1" in json_data
        assert "item2" in json_data
        assert "comparison" in json_data
        assert "visualization" in json_data
        assert "metadata" in json_data
        
        # Test deserialization
        restored_response = WeightComparisonResponse(**json_data)
        assert restored_response.item1.name == response.item1.name
        assert restored_response.comparison.ratio == response.comparison.ratio
    
    def test_decimal_serialization(self):
        """Test Decimal field serialization maintains precision"""
        from backend.models.responses import WeightItem
        
        item = WeightItem(
            name="Test Item",
            original_input="123.456789 kg",
            weight_kg=Decimal("123.456789"),
            weight_display="123.46 kg",
            unit_used=WeightUnit.KILOGRAM
        )
        
        # Serialize and deserialize
        json_data = item.model_dump()
        restored_item = WeightItem(**json_data)
        
        # Verify precision maintained
        assert str(restored_item.weight_kg) == "123.456789"
    
    def test_enum_serialization(self):
        """Test enum field serialization"""
        from backend.models.errors import ErrorResponse, ErrorCategory, ErrorSeverity
        
        error = ErrorResponse(
            error_code="TEST_ERROR",
            error_category=ErrorCategory.BUSINESS_LOGIC_ERROR,
            message="Test error",
            request_id="test-123",
            severity=ErrorSeverity.WARNING
        )
        
        json_data = error.model_dump()
        assert json_data["error_category"] == "BUSINESS_LOGIC_ERROR"
        assert json_data["severity"] == "WARNING"
        
        # Test deserialization
        restored_error = ErrorResponse(**json_data)
        assert restored_error.error_category == ErrorCategory.BUSINESS_LOGIC_ERROR
        assert restored_error.severity == ErrorSeverity.WARNING
```

## 4. Pytest Configuration & Test Organization (1 page)

### 4.1 Pytest Configuration

```python
# conftest.py - Global pytest configuration
import pytest
import asyncio
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

# Pytest configuration
pytest_plugins = ["pytest_asyncio"]

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_config_service():
    """Provide mock configuration service for tests"""
    return MockConfigurationService()

@pytest.fixture
def mock_ai_provider():
    """Provide mock AI provider for tests"""
    return MockAIProviderFactory.create_basic_mock()

@pytest.fixture
def test_data_factory():
    """Provide test data factory for consistent test data"""
    return TestDataFactory()

@pytest.fixture(autouse=True)
def reset_mocks():
    """Auto-reset mocks between tests"""
    yield
    # Cleanup happens after test runs

class TestDataFactory:
    """Factory for creating consistent test data"""
    
    @staticmethod
    def create_weight_comparison_response() -> WeightComparisonResponse:
        """Create standardized WeightComparisonResponse for testing"""
        return WeightComparisonResponse(
            item1=WeightItem(
                name="Elephant",
                original_input="5000 kg",
                weight_kg=Decimal("5000.000000"),
                weight_display="5000.00 kg",
                unit_used=WeightUnit.KILOGRAM,
                confidence=0.95
            ),
            item2=WeightItem(
                name="Car", 
                original_input="1500 kg",
                weight_kg=Decimal("1500.000000"),
                weight_display="1500.00 kg",
                unit_used=WeightUnit.KILOGRAM,
                confidence=0.98
            ),
            comparison=ComparisonResult(
                ratio=Decimal("3.333333"),
                percentage_difference=Decimal("233.33"),
                heavier_item="Elephant",
                weight_difference_kg=Decimal("3500.000000"),
                calculation_method="direct_conversion"
            ),
            visualization=VisualizationPrompt(
                prompt="The elephant weighs 3.33 times more than the car",
                confidence_score=0.92,
                generation_time_ms=180,
                provider_used="test_provider"
            ),
            metadata=ResponseMetadata(
                request_id="test-request-123",
                processing_time_ms=250,
                ai_provider_used="test_provider",
                ai_response_time_ms=180,
                cache_hit=False,
                version="1.0.0"
            )
        )
    
    @staticmethod
    def create_validation_error_scenarios() -> List[Dict[str, Any]]:
        """Create scenarios for validation error testing"""
        return [
            {
                "name": "empty_item_name",
                "data": {"item1_name": "", "item1_weight": "100 kg"},
                "expected_error": "item1_name"
            },
            {
                "name": "invalid_weight_format",
                "data": {"item1_name": "Test", "item1_weight": "invalid"},
                "expected_error": "item1_weight"
            },
            {
                "name": "negative_weight",
                "data": {"item1_name": "Test", "item1_weight": "-100 kg"},
                "expected_error": "weight_kg"
            }
        ]

# pytest.ini configuration
"""
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --disable-warnings
    --cov=backend
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    -ra
markers =
    unit: Unit tests (isolated components)
    integration: Integration tests (component interactions)
    slow: Slow running tests
    asyncio: Async function tests
    parametrize: Parameterized tests
    mock: Tests using mocks
"""
```

### 4.2 Test Organization Strategies

```python
# Test category markers for organization
import pytest

class TestOrganizationPatterns:
    """Demonstrate test organization strategies"""
    
    @pytest.mark.unit
    @pytest.mark.weight_processing
    def test_weight_parsing_unit(self):
        """Unit test for weight parsing - fast, isolated"""
        pass
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_ai_provider_integration(self):
        """Integration test - slower, multiple components"""
        pass
    
    @pytest.mark.parametrize
    @pytest.mark.validation
    def test_input_validation_scenarios(self):
        """Parameterized validation test"""
        pass

# Custom test selection patterns
"""
# Run only unit tests
pytest -m unit

# Run only weight processing tests
pytest -m weight_processing

# Run everything except slow tests
pytest -m "not slow"

# Run unit tests with coverage
pytest -m unit --cov=backend.core

# Run specific test file
pytest tests/unit/core/test_weight_processor.py

# Run with verbose output
pytest -v -m unit
"""

# Test discovery patterns
class TestDiscoveryConfiguration:
    """Configuration for test discovery and execution"""
    
    @staticmethod
    def configure_test_collection():
        """Configure how pytest discovers tests"""
        # Tests must start with 'test_'
        # Test classes must start with 'Test'
        # Test files must start with 'test_'
        # All in 'tests/' directory
        pass
    
    @staticmethod
    def configure_test_execution_order():
        """Configure test execution order for consistency"""
        # Unit tests run first (fastest)
        # Integration tests run second
        # E2E tests run last (slowest)
        pass
```

## 5. Coverage Requirements & Quality Gates (0.5 pages)

### 5.1 Coverage Requirements

```python
# Coverage configuration for quality gates
class CoverageRequirements:
    """Define coverage requirements and quality gates"""
    
    COVERAGE_THRESHOLDS = {
        "line_coverage": 80,      # Minimum 80% line coverage
        "branch_coverage": 75,    # Minimum 75% branch coverage  
        "function_coverage": 90,  # Minimum 90% function coverage
    }
    
    CRITICAL_COMPONENTS = {
        "backend.core.weight_processor": 95,    # Critical weight logic
        "backend.models": 85,                   # Pydantic models
        "backend.core.validators": 90,          # Validation logic
        "backend.api.routes": 80,               # API endpoints
    }
    
    EXCLUDED_FROM_COVERAGE = [
        "*/tests/*",                # Test files themselves
        "*/migrations/*",           # Database migrations
        "*/venv/*",                 # Virtual environment
        "*/conftest.py",           # Test configuration
        "*/setup.py",              # Setup scripts
    ]

# Quality gate enforcement
def check_coverage_requirements():
    """Enforce coverage requirements in CI/CD pipeline"""
    
    coverage_command = [
        "pytest", 
        "--cov=backend",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        f"--cov-fail-under={CoverageRequirements.COVERAGE_THRESHOLDS['line_coverage']}",
        "tests/unit/"
    ]
    
    # Additional quality checks
    quality_checks = [
        "flake8 backend/",          # Code style
        "mypy backend/",            # Type checking  
        "bandit -r backend/",       # Security scanning
        "safety check",             # Dependency vulnerability scanning
    ]
    
    return coverage_command, quality_checks

# CI/CD Integration (GitHub Actions example)
"""
name: Unit Tests & Coverage
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements-test.txt
    
    - name: Run unit tests with coverage
      run: |
        pytest tests/unit/ --cov=backend --cov-fail-under=80 --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v1
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: true
"""

### 5.2 Efficient Coverage Achievement Strategies

```python
class EfficientCoveragePatterns:
    """Patterns for achieving high coverage efficiently"""
    
    @staticmethod
    def test_with_fixtures():
        """Use fixtures to reduce test code duplication"""
        @pytest.fixture
        def weight_processor():
            config = MockConfigurationService()
            return WeightProcessor(config)
        
        def test_multiple_scenarios(weight_processor):
            # Reuse fixture across multiple assertions
            result1 = weight_processor.parse_weight_input("100 kg")
            result2 = weight_processor.parse_weight_input("50 lbs")
            # Multiple assertions increase coverage efficiently
    
    @staticmethod
    def use_parametrized_tests():
        """Parametrized tests for comprehensive coverage"""
        @pytest.mark.parametrize("input,expected", [
            # Cover multiple branches with single test definition
            ("100 kg", Decimal("100")),
            ("50 lbs", Decimal("22.68")),
            ("10 oz", Decimal("0.283")),
        ])
        def test_conversions(input, expected):
            assert convert_weight(input) == expected
    
    @staticmethod
    def test_error_paths():
        """Ensure error paths are covered"""
        def test_comprehensive_error_handling():
            # Test each error condition
            with pytest.raises(ValidationError):
                process_weight("")  # Empty input
            
            with pytest.raises(ValidationError):
                process_weight("-10 kg")  # Negative weight
            
            with pytest.raises(ValidationError):
                process_weight("1e100 kg")  # Overflow

# Summary: 80%+ Coverage Achievement Strategy
"""
1. **Comprehensive Unit Coverage**
   - Weight processing: 95%+ (critical business logic)
   - Pydantic models: 85%+ (validation scenarios)
   - API routes: 80%+ (endpoint logic)
   - Configuration: 85%+ (settings validation)

2. **Quality Gates Enforcement**
   - Automated coverage checking in CI/CD
   - Branch protection requiring 80%+ coverage
   - Failed tests block deployment
   - Coverage reports in pull requests

3. **Testing Strategy**
   - Fast unit tests for core logic
   - Comprehensive mock implementations
   - Parameterized testing for scenarios
   - Async testing patterns
   - Error condition coverage

4. **Continuous Monitoring**
   - Coverage trending over time
   - Critical component coverage alerts
   - Quality metrics dashboard
   - Regular coverage review in code reviews
"""
```

This comprehensive unit testing specification provides a robust framework for achieving 80%+ coverage while ensuring isolated, deterministic testing of all SizeComparator components through sophisticated mocking, comprehensive validation scenarios, and well-organized test strategies.