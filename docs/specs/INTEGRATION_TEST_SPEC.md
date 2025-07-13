# Integration Testing Specification for SizeComparator

## Document Overview

This specification defines comprehensive integration testing patterns for SizeComparator's component interactions, API endpoints, external service integrations, and system-wide contract validation. Building upon TESTING_SPEC.md foundations, this document provides detailed implementation guidance for validating all component interfaces work together correctly, including AI provider failover scenarios and configuration hot-reload mechanisms.

## 1. Executive Summary

### 1.1 Integration Testing Scope

SizeComparator's integration testing validates the orchestration between backend services, AI providers, configuration management, and external dependencies through realistic scenarios that mirror production behavior. The framework ensures reliable component contracts while providing deterministic test execution through controlled environments.

**Primary Integration Boundaries:**
- FastAPI backend ↔ AI provider services (AI_PROVIDER_SPEC)
- Configuration service ↔ Application components (CONFIG_SYSTEM_SPEC)
- Error monitoring ↔ All system components (ERROR_MONITORING_SPEC)
- Health endpoints ↔ Deployment infrastructure (DEPLOYMENT_OPS_SPEC)
- API endpoints ↔ Frontend clients (API_ENDPOINTS_SPEC)

**Testing Methodology:**
- Contract-based testing using BACKEND_CORE_SPEC Pydantic models
- Real FastAPI test client with dependency injection
- Controlled external service mocking with realistic failure patterns
- Environment isolation with automatic setup/teardown
- Performance validation under concurrent load scenarios

**Quality Gates:**
- 95% integration test coverage across all component boundaries
- All critical user flows validated end-to-end
- AI provider failover scenarios tested automatically
- Configuration hot-reload safety verified
- Health endpoint compliance with load balancer requirements

### 1.2 Integration with System Architecture

| Component Spec | Integration Focus | Test Validation |
|----------------|-------------------|-----------------|
| BACKEND_CORE_SPEC | Pydantic model contracts, FastAPI routing | Request/response validation, async handling |
| AI_PROVIDER_SPEC | Provider interface, circuit breaker states | Failover scenarios, error propagation |
| CONFIG_SYSTEM_SPEC | Hot-reload safety, validation chains | Configuration change impacts, rollback testing |
| ERROR_MONITORING_SPEC | Structured logging, error categorization | Log format compliance, error context enrichment |
| DEPLOYMENT_OPS_SPEC | Health endpoints, metrics collection | Load balancer compatibility, monitoring integration |

## 2. Component Integration Testing Framework

### 2.1 FastAPI Test Client Integration Architecture

The integration testing framework leverages FastAPI's TestClient with sophisticated dependency injection to create realistic testing environments while maintaining complete control over external dependencies.

```python
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.config.service import ConfigurationService
from backend.ai_providers.manager import AIProviderManager
from backend.monitoring.logger import StructuredLogger
import pytest
import asyncio
from typing import Dict, Any, Optional
import uuid

class IntegrationTestFramework:
    """Comprehensive integration testing framework for SizeComparator components."""
    
    def __init__(self):
        self.app = None
        self.test_client = None
        self.mock_config_service = None
        self.mock_ai_provider = None
        self.mock_logger = None
        self.test_request_id = None
        self.dependency_overrides = {}
    
    async def setup_integration_environment(
        self, 
        config_overrides: Dict[str, Any] = None,
        ai_provider_config: Dict[str, Any] = None,
        enable_real_providers: bool = False
    ) -> TestClient:
        """
        Setup complete integration testing environment with controlled dependencies.
        
        Args:
            config_overrides: Configuration values to override for testing
            ai_provider_config: AI provider mock configuration
            enable_real_providers: Whether to use real AI providers (for staging tests)
        
        Returns:
            Configured TestClient with dependency injection
        """
        self.test_request_id = str(uuid.uuid4())
        
        # 1. Setup test configuration service
        self.mock_config_service = await self._setup_test_configuration(config_overrides)
        
        # 2. Setup AI provider service (mock or real)
        if enable_real_providers:
            self.mock_ai_provider = await self._setup_real_ai_providers(ai_provider_config)
        else:
            self.mock_ai_provider = await self._setup_mock_ai_providers(ai_provider_config)
        
        # 3. Setup structured logging
        self.mock_logger = await self._setup_test_logging()
        
        # 4. Create FastAPI application
        self.app = create_app()
        
        # 5. Configure dependency overrides for controlled testing
        self.dependency_overrides = {
            ConfigurationService: lambda: self.mock_config_service,
            AIProviderManager: lambda: self.mock_ai_provider,
            StructuredLogger: lambda: self.mock_logger,
        }
        
        # Apply dependency overrides
        for dependency, override in self.dependency_overrides.items():
            self.app.dependency_overrides[dependency] = override
        
        # 6. Create test client
        self.test_client = TestClient(self.app)
        
        return self.test_client
    
    async def _setup_test_configuration(self, overrides: Dict[str, Any] = None) -> ConfigurationService:
        """Setup test configuration service with CONFIG_SYSTEM_SPEC compliance."""
        from backend.testing.mocks.config import TestConfigurationService
        
        # Default test configuration
        base_config = {
            "application": {
                "name": "SizeComparator",
                "version": "1.0.0-test",
                "environment": "integration_test"
            },
            "api": {
                "cors": {
                    "allow_origins": ["*"],
                    "allow_methods": ["*"],
                    "allow_headers": ["*"]
                },
                "request_timeout_seconds": 30,
                "providers": {
                    "openai": {
                        "endpoint": "https://api.openai.com/v1",
                        "api_key": "test-key-openai",
                        "model": "gpt-4",
                        "timeout_seconds": 10,
                        "retry": {
                            "max_attempts": 3,
                            "initial_delay_ms": 1000,
                            "exponential_base": 2.0,
                            "max_delay_ms": 8000
                        }
                    },
                    "anthropic": {
                        "endpoint": "https://api.anthropic.com",
                        "api_key": "test-key-anthropic",
                        "model": "claude-3-sonnet-20240229",
                        "timeout_seconds": 10,
                        "retry": {
                            "max_attempts": 3,
                            "initial_delay_ms": 1000
                        }
                    }
                }
            },
            "comparison": {
                "max_weight_difference_ratio": 1000000,
                "supported_units": ["kg", "lbs", "g", "oz", "tons"],
                "default_output_unit": "kg",
                "precision_decimal_places": 6
            },
            "circuit_breaker": {
                "failure_threshold": 5,
                "success_threshold": 2,
                "timeout_seconds": 60,
                "half_open_max_calls": 3
            },
            "monitoring": {
                "logging": {
                    "level": "DEBUG",
                    "format": "json",
                    "include_request_id": True,
                    "sanitize_sensitive_data": True
                },
                "metrics": {
                    "enabled": True,
                    "prometheus_endpoint": "/api/v1/metrics"
                }
            },
            "features": {
                "enhanced_visualizations": True,
                "real_time_updates": True,
                "a_b_testing": False
            }
        }
        
        # Apply test-specific overrides
        if overrides:
            base_config = self._deep_merge_config(base_config, overrides)
        
        # Create test configuration service
        test_config_service = TestConfigurationService()
        await test_config_service.load_test_config(base_config)
        
        return test_config_service
    
    async def _setup_mock_ai_providers(self, provider_config: Dict[str, Any] = None) -> AIProviderManager:
        """Setup mock AI provider manager with configurable behaviors."""
        from backend.testing.mocks.ai_providers import MockAIProviderManager
        
        mock_manager = MockAIProviderManager()
        
        # Configure default mock behaviors
        default_config = {
            "response_latency": {"min_ms": 100, "max_ms": 500},
            "success_rate": 0.95,
            "circuit_breaker": {"enabled": True, "failure_threshold": 5},
            "rate_limiting": {"requests_per_minute": 100}
        }
        
        if provider_config:
            default_config.update(provider_config)
        
        await mock_manager.configure_test_behavior(default_config)
        
        return mock_manager
    
    async def _setup_real_ai_providers(self, provider_config: Dict[str, Any] = None) -> AIProviderManager:
        """Setup real AI provider manager for staging integration tests."""
        from backend.ai_providers.manager import AIProviderManager
        
        # Use real providers but with test-specific configuration
        provider_manager = AIProviderManager()
        
        # Configure for test environment (shorter timeouts, different endpoints if needed)
        test_provider_config = {
            "use_test_endpoints": True,
            "timeout_seconds": 5,  # Shorter timeouts for faster test execution
            "retry_max_attempts": 2
        }
        
        if provider_config:
            test_provider_config.update(provider_config)
        
        await provider_manager.configure_for_testing(test_provider_config)
        
        return provider_manager
    
    async def _setup_test_logging(self) -> StructuredLogger:
        """Setup test-specific structured logging."""
        from backend.testing.mocks.logging import MockStructuredLogger
        
        mock_logger = MockStructuredLogger()
        mock_logger.configure_for_testing({
            "capture_logs": True,
            "validate_structure": True,
            "request_id": self.test_request_id
        })
        
        return mock_logger
    
    def _deep_merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge configuration dictionaries."""
        import copy
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    async def teardown_integration_environment(self):
        """Cleanup integration testing environment."""
        if self.test_client:
            self.test_client.close()
        
        if self.mock_ai_provider:
            await self.mock_ai_provider.cleanup_test_state()
        
        if self.mock_config_service:
            await self.mock_config_service.cleanup_test_config()
        
        if self.mock_logger:
            await self.mock_logger.reset_captured_logs()
        
        # Clear dependency overrides
        if self.app:
            self.app.dependency_overrides.clear()
```

### 2.2 Contract Testing with Pydantic Models

Integration tests validate all API contracts using exact BACKEND_CORE_SPEC Pydantic models to ensure request/response compatibility across the entire system.

```python
from backend.models.requests import WeightComparisonRequest
from backend.models.responses import WeightComparisonResponse, HealthResponse, ReadinessResponse
from backend.models.errors import ErrorResponse
from pydantic import ValidationError
import pytest
from typing import Dict, Any, List

class ContractTestValidator:
    """Validates API contracts using BACKEND_CORE_SPEC Pydantic models."""
    
    def __init__(self, test_client: TestClient):
        self.test_client = test_client
    
    def validate_weight_comparison_contract(
        self, 
        request_data: Dict[str, Any],
        expected_status: int = 200
    ) -> WeightComparisonResponse:
        """
        Validate weight comparison API contract with exact Pydantic model validation.
        
        Args:
            request_data: Request payload to test
            expected_status: Expected HTTP status code
            
        Returns:
            Validated WeightComparisonResponse object
            
        Raises:
            AssertionError: If contract validation fails
        """
        # Make API request
        response = self.test_client.post("/api/v1/compare", json=request_data)
        
        # Validate HTTP status
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.text}"
        )
        
        if expected_status == 200:
            # Validate successful response contract
            response_data = response.json()
            
            try:
                # This will raise ValidationError if contract is violated
                weight_response = WeightComparisonResponse(**response_data)
            except ValidationError as e:
                pytest.fail(f"WeightComparisonResponse contract violation: {e}")
            
            # Validate specific contract requirements
            self._validate_weight_response_contract(weight_response, request_data)
            
            return weight_response
        
        else:
            # Validate error response contract
            error_data = response.json()
            
            try:
                error_response = ErrorResponse(**error_data)
            except ValidationError as e:
                pytest.fail(f"ErrorResponse contract violation: {e}")
            
            # Validate error response requirements
            self._validate_error_response_contract(error_response, expected_status)
            
            return error_response
    
    def _validate_weight_response_contract(
        self, 
        response: WeightComparisonResponse, 
        original_request: Dict[str, Any]
    ):
        """Validate weight comparison response meets contract requirements."""
        # Validate item1 contract
        assert response.item1.name == original_request["item1_name"]
        assert response.item1.original_input == original_request["item1_weight"]
        assert response.item1.weight_kg > 0
        assert 0.0 <= response.item1.confidence <= 1.0
        
        # Validate item2 contract
        assert response.item2.name == original_request["item2_name"] 
        assert response.item2.original_input == original_request["item2_weight"]
        assert response.item2.weight_kg > 0
        assert 0.0 <= response.item2.confidence <= 1.0
        
        # Validate comparison contract
        assert response.comparison.ratio > 0
        assert response.comparison.percentage_difference >= 0
        assert response.comparison.heavier_item in [response.item1.name, response.item2.name]
        assert response.comparison.weight_difference_kg >= 0
        
        # Validate visualization contract
        assert len(response.visualization.prompt) > 0
        assert 0.0 <= response.visualization.confidence_score <= 1.0
        assert response.visualization.generation_time_ms > 0
        assert response.visualization.provider_used is not None
        
        # Validate metadata contract
        assert response.metadata.request_id is not None
        assert response.metadata.processing_time_ms > 0
        assert response.metadata.ai_provider_used is not None
        assert response.metadata.ai_response_time_ms > 0
        assert response.metadata.timestamp is not None
        assert response.metadata.version is not None
    
    def _validate_error_response_contract(self, error_response: ErrorResponse, status_code: int):
        """Validate error response meets ERROR_MONITORING_SPEC contract."""
        # Validate required fields
        assert error_response.error_code is not None
        assert error_response.error_category is not None
        assert error_response.message is not None
        assert error_response.request_id is not None
        assert error_response.timestamp is not None
        assert error_response.severity is not None
        
        # Validate error category matches status code
        status_to_category = {
            400: "CLIENT_ERROR",
            401: "CLIENT_ERROR", 
            403: "CLIENT_ERROR",
            422: "CLIENT_ERROR",
            429: "CLIENT_ERROR",
            500: "SERVER_ERROR",
            502: "INTEGRATION_ERROR", 
            503: "INTEGRATION_ERROR",
            504: "INTEGRATION_ERROR"
        }
        
        expected_category = status_to_category.get(status_code)
        if expected_category:
            assert error_response.error_category.value == expected_category
    
    def validate_health_endpoint_contract(self) -> HealthResponse:
        """Validate health endpoint contract compliance."""
        response = self.test_client.get("/api/v1/health")
        
        assert response.status_code == 200
        health_data = response.json()
        
        try:
            health_response = HealthResponse(**health_data)
        except ValidationError as e:
            pytest.fail(f"HealthResponse contract violation: {e}")
        
        # Validate health response requirements per DEPLOYMENT_OPS_SPEC
        assert health_response.status in ["healthy", "degraded", "unhealthy"]
        assert health_response.timestamp is not None
        assert health_response.version is not None
        
        return health_response
    
    def validate_readiness_endpoint_contract(self) -> ReadinessResponse:
        """Validate readiness endpoint contract compliance."""
        response = self.test_client.get("/api/v1/ready")
        
        assert response.status_code == 200
        readiness_data = response.json()
        
        try:
            readiness_response = ReadinessResponse(**readiness_data)
        except ValidationError as e:
            pytest.fail(f"ReadinessResponse contract violation: {e}")
        
        # Validate readiness response requirements
        assert isinstance(readiness_response.ready, bool)
        assert isinstance(readiness_response.checks, dict)
        assert "ai_providers" in readiness_response.checks
        assert "configuration" in readiness_response.checks
        
        return readiness_response
```

## 3. API Endpoint Integration Testing

### 3.1 Weight Comparison Endpoint Test Suite

Comprehensive integration testing for the primary weight comparison endpoint covering all success and failure scenarios with real FastAPI request/response cycles.

```python
class TestWeightComparisonEndpointIntegration:
    """Integration tests for weight comparison API endpoint."""
    
    @pytest.fixture
    async def integration_env(self):
        """Setup integration testing environment."""
        framework = IntegrationTestFramework()
        test_client = await framework.setup_integration_environment()
        yield framework, test_client
        await framework.teardown_integration_environment()
    
    @pytest.mark.integration
    async def test_successful_weight_comparison_flow(self, integration_env):
        """Test complete successful weight comparison through all components."""
        framework, test_client = integration_env
        
        # Setup AI provider to return successful response
        expected_ai_response = self._create_test_ai_response()
        framework.mock_ai_provider.configure_response("test_pattern", expected_ai_response)
        
        # Prepare test request
        request_data = {
            "item1_name": "African Elephant",
            "item1_weight": "6000 kg",
            "item2_name": "Honda Civic",
            "item2_weight": "2800 pounds",
            "output_unit": "kg",
            "include_visualization": True
        }
        
        # Validate contract and response
        contract_validator = ContractTestValidator(test_client)
        response = contract_validator.validate_weight_comparison_contract(request_data)
        
        # Verify business logic integration
        assert abs(float(response.item1.weight_kg) - 6000.0) < 0.001
        assert abs(float(response.item2.weight_kg) - 1270.058) < 0.1  # ~2800 lbs in kg
        
        # Verify AI provider integration
        assert response.visualization.provider_used == "mock"
        assert response.metadata.ai_provider_used == "mock"
        
        # Verify logging integration
        logs = framework.mock_logger.get_captured_logs()
        assert any("weight_comparison_requested" in log.get("message", "") for log in logs)
        assert any("ai_provider_called" in log.get("message", "") for log in logs)
        assert any("weight_comparison_completed" in log.get("message", "") for log in logs)
    
    @pytest.mark.integration
    async def test_weight_comparison_with_ai_provider_failure(self, integration_env):
        """Test weight comparison handling AI provider failures."""
        framework, test_client = integration_env
        
        # Configure AI provider to fail
        framework.mock_ai_provider.configure_failure_scenario({
            "failure_type": "timeout",
            "failure_rate": 1.0,
            "error_message": "AI provider timeout"
        })
        
        request_data = {
            "item1_name": "Test Item 1", 
            "item1_weight": "100 kg",
            "item2_name": "Test Item 2",
            "item2_weight": "50 kg"
        }
        
        # Should get error response due to AI provider failure
        contract_validator = ContractTestValidator(test_client)
        error_response = contract_validator.validate_weight_comparison_contract(
            request_data, 
            expected_status=503
        )
        
        # Verify error categorization
        assert error_response.error_category.value == "INTEGRATION_ERROR"
        assert "AI provider" in error_response.message
        
        # Verify circuit breaker integration
        assert framework.mock_ai_provider.get_circuit_breaker_state() == "OPEN"
        
        # Verify error logging
        logs = framework.mock_logger.get_captured_logs()
        error_logs = [log for log in logs if log.get("level") == "ERROR"]
        assert len(error_logs) > 0
        assert any("ai_provider_failure" in log.get("message", "") for log in error_logs)
    
    @pytest.mark.integration
    async def test_weight_comparison_with_invalid_input(self, integration_env):
        """Test weight comparison input validation integration."""
        framework, test_client = integration_env
        
        invalid_requests = [
            # Missing required fields
            {
                "item1_name": "Test Item",
                "item1_weight": "100 kg"
                # Missing item2
            },
            # Invalid weight format
            {
                "item1_name": "Test Item 1",
                "item1_weight": "invalid weight",
                "item2_name": "Test Item 2", 
                "item2_weight": "100 kg"
            },
            # Empty item names
            {
                "item1_name": "",
                "item1_weight": "100 kg",
                "item2_name": "Test Item 2",
                "item2_weight": "50 kg"
            },
            # Unsupported unit
            {
                "item1_name": "Test Item 1",
                "item1_weight": "100 xyz",
                "item2_name": "Test Item 2",
                "item2_weight": "50 kg"
            }
        ]
        
        contract_validator = ContractTestValidator(test_client)
        
        for i, invalid_request in enumerate(invalid_requests):
            with pytest.raises(AssertionError) if i == 0 else None:
                error_response = contract_validator.validate_weight_comparison_contract(
                    invalid_request,
                    expected_status=422
                )
                
                # Verify client error categorization
                assert error_response.error_category.value == "CLIENT_ERROR"
                assert "validation" in error_response.message.lower()
    
    @pytest.mark.integration
    async def test_weight_comparison_with_concurrent_requests(self, integration_env):
        """Test weight comparison under concurrent load."""
        framework, test_client = integration_env
        
        # Configure AI provider for consistent responses
        framework.mock_ai_provider.configure_latency(min_ms=50, max_ms=150)
        
        import concurrent.futures
        import time
        
        def make_weight_comparison_request(request_id: int):
            """Make a single weight comparison request."""
            request_data = {
                "item1_name": f"Test Item 1-{request_id}",
                "item1_weight": f"{100 + request_id} kg",
                "item2_name": f"Test Item 2-{request_id}",
                "item2_weight": f"{50 + request_id} kg"
            }
            
            start_time = time.time()
            response = test_client.post("/api/v1/compare", json=request_data)
            duration = time.time() - start_time
            
            return {
                "request_id": request_id,
                "status_code": response.status_code,
                "duration": duration,
                "response_data": response.json() if response.status_code == 200 else None
            }
        
        # Execute concurrent requests
        num_concurrent_requests = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_weight_comparison_request, i) 
                for i in range(num_concurrent_requests)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Verify all requests succeeded
        success_count = sum(1 for r in results if r["status_code"] == 200)
        success_rate = success_count / len(results)
        
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95% threshold"
        
        # Verify response times are reasonable
        durations = [r["duration"] for r in results if r["status_code"] == 200]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        
        assert avg_duration < 2.0, f"Average response time {avg_duration:.2f}s exceeds 2s limit"
        assert max_duration < 5.0, f"Max response time {max_duration:.2f}s exceeds 5s limit"
        
        # Verify each response has valid contract
        contract_validator = ContractTestValidator(test_client)
        for result in results:
            if result["status_code"] == 200:
                try:
                    WeightComparisonResponse(**result["response_data"])
                except ValidationError as e:
                    pytest.fail(f"Contract violation in concurrent request {result['request_id']}: {e}")
    
    def _create_test_ai_response(self):
        """Create a test AI response for mocking."""
        from backend.models.responses import WeightItem, ComparisonResult, VisualizationPrompt, ResponseMetadata
        from decimal import Decimal
        import uuid
        from datetime import datetime
        
        return {
            "item1": WeightItem(
                name="African Elephant",
                original_input="6000 kg",
                weight_kg=Decimal("6000.000000"),
                weight_display="6000 kg",
                unit_used="kg",
                confidence=0.95
            ),
            "item2": WeightItem(
                name="Honda Civic", 
                original_input="2800 pounds",
                weight_kg=Decimal("1270.058"),
                weight_display="2800 lbs",
                unit_used="lbs",
                confidence=0.90
            ),
            "comparison": ComparisonResult(
                ratio=Decimal("4.724"),
                percentage_difference=Decimal("372.4"),
                heavier_item="African Elephant",
                weight_difference_kg=Decimal("4729.942"),
                calculation_method="direct_conversion"
            ),
            "visualization": VisualizationPrompt(
                prompt="An African elephant stands majestically next to a Honda Civic...",
                comparisons=["The elephant weighs about 4.7 times more than the car"],
                confidence_score=0.92,
                generation_time_ms=180,
                provider_used="mock"
            ),
            "metadata": ResponseMetadata(
                request_id=str(uuid.uuid4()),
                processing_time_ms=250,
                ai_provider_used="mock",
                ai_response_time_ms=180,
                cache_hit=False,
                timestamp=datetime.utcnow(),
                version="1.0.0-test"
            )
        }
```

### 3.2 Health and Monitoring Endpoint Integration

Integration testing for DEPLOYMENT_OPS_SPEC health endpoints with realistic dependency checking and load balancer compatibility validation.

```python
class TestHealthEndpointIntegration:
    """Integration tests for health and monitoring endpoints."""
    
    @pytest.fixture
    async def health_integration_env(self):
        """Setup health-focused integration environment."""
        framework = IntegrationTestFramework()
        
        # Configure for health testing scenarios
        config_overrides = {
            "monitoring": {
                "health_check": {
                    "timeout_seconds": 1,
                    "dependency_timeout_seconds": 0.5
                }
            }
        }
        
        test_client = await framework.setup_integration_environment(
            config_overrides=config_overrides
        )
        yield framework, test_client
        await framework.teardown_integration_environment()
    
    @pytest.mark.integration
    async def test_health_endpoint_with_healthy_dependencies(self, health_integration_env):
        """Test health endpoint when all dependencies are healthy."""
        framework, test_client = health_integration_env
        
        # Configure all dependencies as healthy
        framework.mock_ai_provider.configure_health_status("healthy")
        framework.mock_config_service.set_health_status("healthy")
        
        # Test health endpoint
        contract_validator = ContractTestValidator(test_client)
        health_response = contract_validator.validate_health_endpoint_contract()
        
        # Verify healthy status
        assert health_response.status == "healthy"
        assert health_response.components["ai_providers"] == "healthy"
        assert health_response.components["configuration"] == "healthy"
        
        # Verify response time for load balancer compatibility
        import time
        start_time = time.time()
        test_client.get("/api/v1/health")
        response_time = time.time() - start_time
        
        assert response_time < 0.1, f"Health check took {response_time:.3f}s, should be < 0.1s"
    
    @pytest.mark.integration
    async def test_health_endpoint_with_degraded_dependencies(self, health_integration_env):
        """Test health endpoint when some dependencies are degraded."""
        framework, test_client = health_integration_env
        
        # Configure AI provider as degraded (some providers down)
        framework.mock_ai_provider.configure_health_status("degraded")
        framework.mock_config_service.set_health_status("healthy")
        
        health_response = test_client.get("/api/v1/health").json()
        
        # System should report degraded but still operational
        assert health_response["status"] == "degraded"
        assert health_response["components"]["ai_providers"] == "degraded"
        assert health_response["components"]["configuration"] == "healthy"
    
    @pytest.mark.integration 
    async def test_readiness_endpoint_integration(self, health_integration_env):
        """Test readiness endpoint integration with dependencies."""
        framework, test_client = health_integration_env
        
        # Test ready state
        framework.mock_ai_provider.configure_readiness(True)
        framework.mock_config_service.set_readiness(True)
        
        contract_validator = ContractTestValidator(test_client)
        readiness_response = contract_validator.validate_readiness_endpoint_contract()
        
        assert readiness_response.ready is True
        assert readiness_response.checks["ai_providers"] is True
        assert readiness_response.checks["configuration"] is True
        
        # Test not ready state (AI providers circuit breaker open)
        framework.mock_ai_provider.configure_readiness(False)
        
        readiness_response = contract_validator.validate_readiness_endpoint_contract()
        
        assert readiness_response.ready is False
        assert readiness_response.checks["ai_providers"] is False
        assert readiness_response.checks["configuration"] is True
    
    @pytest.mark.integration
    async def test_metrics_endpoint_integration(self, health_integration_env):
        """Test metrics endpoint integration with Prometheus format."""
        framework, test_client = health_integration_env
        
        # Generate some activity for metrics
        test_client.post("/api/v1/compare", json={
            "item1_name": "Test", "item1_weight": "100 kg",
            "item2_name": "Test", "item2_weight": "50 kg"
        })
        
        # Test metrics endpoint
        response = test_client.get("/api/v1/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        
        metrics_content = response.text
        
        # Verify Prometheus format compliance
        assert "# HELP" in metrics_content
        assert "# TYPE" in metrics_content
        
        # Verify required metrics are present
        required_metrics = [
            "http_requests_total",
            "http_request_duration_seconds", 
            "ai_provider_requests_total",
            "circuit_breaker_state"
        ]
        
        for metric in required_metrics:
            assert metric in metrics_content, f"Missing required metric: {metric}"
    
    @pytest.mark.integration
    async def test_health_endpoints_under_load(self, health_integration_env):
        """Test health endpoints can handle load balancer frequency."""
        framework, test_client = health_integration_env
        
        import concurrent.futures
        import time
        
        def health_check():
            start = time.time()
            response = test_client.get("/api/v1/health")
            duration = time.time() - start
            return response.status_code, duration
        
        # Simulate load balancer health checking every second for 30 seconds
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(health_check) for _ in range(30)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All health checks should succeed
        status_codes, durations = zip(*results)
        success_rate = sum(1 for code in status_codes if code == 200) / len(status_codes)
        
        assert success_rate >= 0.99, f"Health check success rate {success_rate:.2%} below 99%"
        
        # Response times should be consistent and fast
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        
        assert avg_duration < 0.05, f"Average health check time {avg_duration:.3f}s too slow"
        assert max_duration < 0.1, f"Max health check time {max_duration:.3f}s too slow"
```

## 4. AI Provider Integration and Failover Testing

### 4.1 AI Provider Failover Scenarios

Comprehensive testing of AI provider failover mechanisms with realistic failure patterns and circuit breaker behavior validation.

```python
class TestAIProviderFailoverIntegration:
    """Integration tests for AI provider failover and circuit breaker behavior."""
    
    @pytest.fixture
    async def ai_failover_env(self):
        """Setup AI provider failover testing environment."""
        framework = IntegrationTestFramework()
        
        # Configure multiple AI providers for failover testing
        config_overrides = {
            "api": {
                "providers": {
                    "openai": {
                        "priority": 1,
                        "circuit_breaker": {"failure_threshold": 3, "timeout_seconds": 30}
                    },
                    "anthropic": { 
                        "priority": 2,
                        "circuit_breaker": {"failure_threshold": 3, "timeout_seconds": 30}
                    },
                    "xai": {
                        "priority": 3,
                        "circuit_breaker": {"failure_threshold": 3, "timeout_seconds": 30}
                    }
                }
            }
        }
        
        test_client = await framework.setup_integration_environment(
            config_overrides=config_overrides
        )
        yield framework, test_client
        await framework.teardown_integration_environment()
    
    @pytest.mark.integration
    async def test_primary_provider_failure_triggers_failover(self, ai_failover_env):
        """Test failover when primary AI provider fails."""
        framework, test_client = ai_failover_env
        
        # Configure primary provider (OpenAI) to fail
        framework.mock_ai_provider.configure_provider_failure("openai", {
            "failure_type": "timeout",
            "failure_rate": 1.0,
            "consecutive_failures": 5
        })
        
        # Configure secondary provider (Anthropic) to succeed
        framework.mock_ai_provider.configure_provider_success("anthropic")
        
        # Make request that should trigger failover
        request_data = {
            "item1_name": "Test Item 1",
            "item1_weight": "100 kg", 
            "item2_name": "Test Item 2",
            "item2_weight": "50 kg"
        }
        
        contract_validator = ContractTestValidator(test_client)
        response = contract_validator.validate_weight_comparison_contract(request_data)
        
        # Verify successful response despite primary provider failure
        assert response.metadata.ai_provider_used == "anthropic"
        
        # Verify circuit breaker state
        provider_states = framework.mock_ai_provider.get_all_circuit_breaker_states()
        assert provider_states["openai"] == "OPEN"
        assert provider_states["anthropic"] == "CLOSED"
        
        # Verify failover logging
        logs = framework.mock_logger.get_captured_logs()
        failover_logs = [log for log in logs if "provider_failover" in log.get("message", "")]
        assert len(failover_logs) > 0
        
        failover_log = failover_logs[0]
        assert failover_log["context"]["failed_provider"] == "openai"
        assert failover_log["context"]["backup_provider"] == "anthropic"
    
    @pytest.mark.integration
    async def test_all_providers_fail_returns_error(self, ai_failover_env):
        """Test system behavior when all AI providers fail."""
        framework, test_client = ai_failover_env
        
        # Configure all providers to fail
        for provider in ["openai", "anthropic", "xai"]:
            framework.mock_ai_provider.configure_provider_failure(provider, {
                "failure_type": "service_unavailable",
                "failure_rate": 1.0
            })
        
        request_data = {
            "item1_name": "Test Item 1",
            "item1_weight": "100 kg",
            "item2_name": "Test Item 2", 
            "item2_weight": "50 kg"
        }
        
        contract_validator = ContractTestValidator(test_client)
        error_response = contract_validator.validate_weight_comparison_contract(
            request_data,
            expected_status=503
        )
        
        # Verify service unavailable error
        assert error_response.error_category.value == "INTEGRATION_ERROR"
        assert "all providers unavailable" in error_response.message.lower()
        
        # Verify all circuit breakers are open
        provider_states = framework.mock_ai_provider.get_all_circuit_breaker_states()
        for provider in ["openai", "anthropic", "xai"]:
            assert provider_states[provider] == "OPEN"
    
    @pytest.mark.integration
    async def test_circuit_breaker_recovery_scenario(self, ai_failover_env):
        """Test circuit breaker recovery when provider becomes healthy again."""
        framework, test_client = ai_failover_env
        
        # Step 1: Cause primary provider to fail and open circuit breaker
        framework.mock_ai_provider.configure_provider_failure("openai", {
            "failure_type": "timeout",
            "consecutive_failures": 5
        })
        
        # Make requests to trigger circuit breaker
        for _ in range(5):
            test_client.post("/api/v1/compare", json={
                "item1_name": "Test", "item1_weight": "100 kg",
                "item2_name": "Test", "item2_weight": "50 kg"
            })
        
        # Verify circuit breaker is open
        assert framework.mock_ai_provider.get_circuit_breaker_state("openai") == "OPEN"
        
        # Step 2: Wait for circuit breaker timeout and fix provider
        import asyncio
        await asyncio.sleep(2)  # Simulate timeout passage
        
        framework.mock_ai_provider.configure_provider_recovery("openai")
        framework.mock_ai_provider.force_circuit_breaker_state("openai", "HALF_OPEN")
        
        # Step 3: Make successful requests to close circuit breaker
        for _ in range(3):
            contract_validator = ContractTestValidator(test_client)
            response = contract_validator.validate_weight_comparison_contract({
                "item1_name": "Test", "item1_weight": "100 kg",
                "item2_name": "Test", "item2_weight": "50 kg"
            })
            assert response.metadata.ai_provider_used == "openai"
        
        # Verify circuit breaker is closed
        assert framework.mock_ai_provider.get_circuit_breaker_state("openai") == "CLOSED"
        
        # Verify recovery logging
        logs = framework.mock_logger.get_captured_logs()
        recovery_logs = [log for log in logs if "circuit_breaker_closed" in log.get("message", "")]
        assert len(recovery_logs) > 0
    
    @pytest.mark.integration
    async def test_provider_performance_degradation_failover(self, ai_failover_env):
        """Test failover triggered by performance degradation."""
        framework, test_client = ai_failover_env
        
        # Configure primary provider with high latency (performance degradation)
        framework.mock_ai_provider.configure_provider_latency("openai", {
            "min_ms": 8000,  # Exceeds timeout threshold
            "max_ms": 10000,
            "failure_rate": 0.0  # Not failing, just slow
        })
        
        # Configure secondary provider with normal latency
        framework.mock_ai_provider.configure_provider_latency("anthropic", {
            "min_ms": 100,
            "max_ms": 300
        })
        
        request_data = {
            "item1_name": "Test Item 1",
            "item1_weight": "100 kg",
            "item2_name": "Test Item 2",
            "item2_weight": "50 kg"
        }
        
        contract_validator = ContractTestValidator(test_client)
        response = contract_validator.validate_weight_comparison_contract(request_data)
        
        # Should failover to faster provider due to timeout
        assert response.metadata.ai_provider_used == "anthropic"
        
        # Verify timeout-based failover was logged
        logs = framework.mock_logger.get_captured_logs()
        timeout_logs = [log for log in logs if "provider_timeout" in log.get("message", "")]
        assert len(timeout_logs) > 0
    
    @pytest.mark.integration
    async def test_partial_provider_failure_load_distribution(self, ai_failover_env):
        """Test load distribution when one provider has partial failures."""
        framework, test_client = ai_failover_env
        
        # Configure primary provider with 50% failure rate
        framework.mock_ai_provider.configure_provider_failure("openai", {
            "failure_type": "intermittent",
            "failure_rate": 0.5
        })
        
        # Configure secondary provider as fully healthy
        framework.mock_ai_provider.configure_provider_success("anthropic")
        
        # Make multiple requests and track which provider handles them
        num_requests = 20
        provider_usage = {"openai": 0, "anthropic": 0}
        
        for i in range(num_requests):
            try:
                contract_validator = ContractTestValidator(test_client)
                response = contract_validator.validate_weight_comparison_contract({
                    "item1_name": f"Test Item 1-{i}",
                    "item1_weight": "100 kg",
                    "item2_name": f"Test Item 2-{i}",
                    "item2_weight": "50 kg"
                })
                provider_usage[response.metadata.ai_provider_used] += 1
            except AssertionError:
                # Some requests may fail due to 50% failure rate
                pass
        
        # Verify load shifted towards healthy provider
        total_successful = sum(provider_usage.values())
        anthropic_percentage = provider_usage["anthropic"] / total_successful if total_successful > 0 else 0
        
        # With 50% failure rate on primary, should see significant shift to secondary
        assert anthropic_percentage > 0.3, f"Expected more load on healthy provider, got {anthropic_percentage:.2%}"
```

### 4.2 Circuit Breaker State Management Testing

```python
class TestCircuitBreakerStateManagement:
    """Integration tests for circuit breaker state management and transitions."""
    
    @pytest.fixture
    async def circuit_breaker_env(self):
        """Setup circuit breaker testing environment."""
        framework = IntegrationTestFramework()
        
        config_overrides = {
            "circuit_breaker": {
                "failure_threshold": 3,
                "success_threshold": 2, 
                "timeout_seconds": 5,
                "half_open_max_calls": 2
            }
        }
        
        test_client = await framework.setup_integration_environment(
            config_overrides=config_overrides
        )
        yield framework, test_client
        await framework.teardown_integration_environment()
    
    @pytest.mark.integration
    async def test_circuit_breaker_state_transitions(self, circuit_breaker_env):
        """Test complete circuit breaker state transition cycle."""
        framework, test_client = circuit_breaker_env
        
        provider_name = "openai"
        
        # Initial state should be CLOSED
        assert framework.mock_ai_provider.get_circuit_breaker_state(provider_name) == "CLOSED"
        
        # Step 1: Trigger failures to open circuit breaker
        framework.mock_ai_provider.configure_provider_failure(provider_name, {
            "failure_type": "service_error",
            "failure_rate": 1.0
        })
        
        # Make requests to trigger failures (should need 3 failures based on config)
        for i in range(3):
            response = test_client.post("/api/v1/compare", json={
                "item1_name": f"Test {i}", "item1_weight": "100 kg",
                "item2_name": f"Test {i}", "item2_weight": "50 kg"
            })
            # Requests should fail or use fallback provider
        
        # Circuit breaker should now be OPEN
        assert framework.mock_ai_provider.get_circuit_breaker_state(provider_name) == "OPEN"
        
        # Step 2: Wait for timeout and transition to HALF_OPEN
        import asyncio
        await asyncio.sleep(6)  # Wait longer than timeout_seconds (5)
        
        # Fix the provider
        framework.mock_ai_provider.configure_provider_recovery(provider_name)
        
        # Next request should transition to HALF_OPEN
        framework.mock_ai_provider.force_circuit_breaker_state(provider_name, "HALF_OPEN")
        assert framework.mock_ai_provider.get_circuit_breaker_state(provider_name) == "HALF_OPEN"
        
        # Step 3: Make successful requests to close circuit breaker
        for i in range(2):  # success_threshold = 2
            contract_validator = ContractTestValidator(test_client)
            response = contract_validator.validate_weight_comparison_contract({
                "item1_name": f"Recovery Test {i}",
                "item1_weight": "100 kg",
                "item2_name": f"Recovery Test {i}",
                "item2_weight": "50 kg"
            })
            assert response.metadata.ai_provider_used == provider_name
        
        # Circuit breaker should now be CLOSED
        assert framework.mock_ai_provider.get_circuit_breaker_state(provider_name) == "CLOSED"
        
        # Verify all state transitions were logged
        logs = framework.mock_logger.get_captured_logs()
        state_change_logs = [log for log in logs if "circuit_breaker_state_change" in log.get("message", "")]
        
        # Should have logs for CLOSED->OPEN, OPEN->HALF_OPEN, HALF_OPEN->CLOSED
        states_logged = [log["context"]["new_state"] for log in state_change_logs]
        assert "OPEN" in states_logged
        assert "HALF_OPEN" in states_logged  
        assert "CLOSED" in states_logged
    
    @pytest.mark.integration
    async def test_circuit_breaker_metrics_integration(self, circuit_breaker_env):
        """Test circuit breaker state is properly exposed in metrics."""
        framework, test_client = circuit_breaker_env
        
        provider_name = "openai"
        
        # Test each circuit breaker state is reflected in metrics
        states_to_test = ["CLOSED", "OPEN", "HALF_OPEN"]
        
        for state in states_to_test:
            # Force circuit breaker to specific state
            framework.mock_ai_provider.force_circuit_breaker_state(provider_name, state)
            
            # Check metrics endpoint
            response = test_client.get("/api/v1/metrics")
            assert response.status_code == 200
            
            metrics_content = response.text
            
            # Verify circuit breaker state is reported in metrics
            expected_metric = f'circuit_breaker_state{{provider="{provider_name}",state="{state}"}}'
            assert expected_metric in metrics_content
    
    @pytest.mark.integration
    async def test_multiple_provider_circuit_breaker_independence(self, circuit_breaker_env):
        """Test circuit breakers for different providers operate independently."""
        framework, test_client = circuit_breaker_env
        
        # Configure different failure scenarios for different providers
        framework.mock_ai_provider.configure_provider_failure("openai", {
            "failure_type": "timeout",
            "failure_rate": 1.0
        })
        
        framework.mock_ai_provider.configure_provider_success("anthropic")
        
        # Trigger failures for OpenAI
        for _ in range(3):
            test_client.post("/api/v1/compare", json={
                "item1_name": "Test", "item1_weight": "100 kg",
                "item2_name": "Test", "item2_weight": "50 kg"
            })
        
        # Verify only OpenAI circuit breaker is affected
        assert framework.mock_ai_provider.get_circuit_breaker_state("openai") == "OPEN"
        assert framework.mock_ai_provider.get_circuit_breaker_state("anthropic") == "CLOSED"
        
        # Verify Anthropic can still handle requests successfully
        contract_validator = ContractTestValidator(test_client)
        response = contract_validator.validate_weight_comparison_contract({
            "item1_name": "Test", "item1_weight": "100 kg",
            "item2_name": "Test", "item2_weight": "50 kg"
        })
        assert response.metadata.ai_provider_used == "anthropic"
```

## 5. Configuration Hot-Reload Integration Testing

### 5.1 Configuration Change Impact Testing

Integration testing for CONFIG_SYSTEM_SPEC hot-reload capabilities with validation of system stability and configuration rollback scenarios.

```python
class TestConfigurationHotReloadIntegration:
    """Integration tests for configuration hot-reload capabilities."""
    
    @pytest.fixture
    async def config_hotreload_env(self):
        """Setup configuration hot-reload testing environment."""
        framework = IntegrationTestFramework()
        
        # Enable hot-reload for testing
        config_overrides = {
            "configuration": {
                "hot_reload": {
                    "enabled": True,
                    "watch_interval_seconds": 1,
                    "validation_timeout_seconds": 5,
                    "rollback_on_failure": True
                }
            }
        }
        
        test_client = await framework.setup_integration_environment(
            config_overrides=config_overrides
        )
        yield framework, test_client
        await framework.teardown_integration_environment()
    
    @pytest.mark.integration
    async def test_ai_provider_configuration_hot_reload(self, config_hotreload_env):
        """Test hot-reload of AI provider configuration without restart."""
        framework, test_client = config_hotreload_env
        
        # Initial state - verify current configuration
        initial_config = framework.mock_config_service.get_current_config()
        assert initial_config["api"]["providers"]["openai"]["timeout_seconds"] == 10
        
        # Make initial request to verify current behavior
        contract_validator = ContractTestValidator(test_client)
        initial_response = contract_validator.validate_weight_comparison_contract({
            "item1_name": "Test", "item1_weight": "100 kg",
            "item2_name": "Test", "item2_weight": "50 kg"
        })
        
        initial_processing_time = initial_response.metadata.processing_time_ms
        
        # Simulate configuration file change (increase timeout)
        new_config_changes = {
            "api": {
                "providers": {
                    "openai": {
                        "timeout_seconds": 20,  # Increased from 10
                        "retry": {
                            "max_attempts": 5  # Increased from 3
                        }
                    }
                }
            }
        }
        
        # Apply configuration change via hot-reload
        await framework.mock_config_service.apply_hot_reload_changes(new_config_changes)
        
        # Wait for hot-reload to take effect
        import asyncio
        await asyncio.sleep(2)
        
        # Verify configuration was updated
        updated_config = framework.mock_config_service.get_current_config()
        assert updated_config["api"]["providers"]["openai"]["timeout_seconds"] == 20
        assert updated_config["api"]["providers"]["openai"]["retry"]["max_attempts"] == 5
        
        # Verify hot-reload did not affect ongoing operations
        post_reload_response = contract_validator.validate_weight_comparison_contract({
            "item1_name": "Test", "item1_weight": "100 kg",
            "item2_name": "Test", "item2_weight": "50 kg"
        })
        
        # Application should still be working
        assert post_reload_response.metadata.ai_provider_used is not None
        
        # Verify configuration change was logged
        logs = framework.mock_logger.get_captured_logs()
        config_logs = [log for log in logs if "configuration_hot_reload" in log.get("message", "")]
        assert len(config_logs) > 0
        
        hot_reload_log = config_logs[0]
        assert hot_reload_log["context"]["changed_keys"] == ["api.providers.openai.timeout_seconds", "api.providers.openai.retry.max_attempts"]
        assert hot_reload_log["context"]["reload_success"] is True
    
    @pytest.mark.integration
    async def test_invalid_configuration_hot_reload_rollback(self, config_hotreload_env):
        """Test hot-reload rollback when invalid configuration is provided."""
        framework, test_client = config_hotreload_env
        
        # Capture initial working configuration
        initial_config = framework.mock_config_service.get_current_config()
        
        # Verify system is working initially
        contract_validator = ContractTestValidator(test_client)
        initial_response = contract_validator.validate_weight_comparison_contract({
            "item1_name": "Test", "item1_weight": "100 kg",
            "item2_name": "Test", "item2_weight": "50 kg"
        })
        assert initial_response.metadata.ai_provider_used is not None
        
        # Attempt to apply invalid configuration
        invalid_config_changes = {
            "api": {
                "providers": {
                    "openai": {
                        "timeout_seconds": "invalid_value",  # Should be integer
                        "api_key": None  # Invalid null value
                    }
                }
            }
        }
        
        # Apply invalid configuration (should trigger rollback)
        rollback_triggered = False
        try:
            await framework.mock_config_service.apply_hot_reload_changes(invalid_config_changes)
        except Exception as e:
            rollback_triggered = True
            assert "validation" in str(e).lower()
        
        assert rollback_triggered, "Invalid configuration should have triggered rollback"
        
        # Wait for rollback to complete
        import asyncio
        await asyncio.sleep(2)
        
        # Verify configuration was rolled back to initial state
        current_config = framework.mock_config_service.get_current_config()
        assert current_config["api"]["providers"]["openai"]["timeout_seconds"] == initial_config["api"]["providers"]["openai"]["timeout_seconds"]
        
        # Verify system is still functioning after rollback
        post_rollback_response = contract_validator.validate_weight_comparison_contract({
            "item1_name": "Test", "item1_weight": "100 kg", 
            "item2_name": "Test", "item2_weight": "50 kg"
        })
        assert post_rollback_response.metadata.ai_provider_used is not None
        
        # Verify rollback was logged
        logs = framework.mock_logger.get_captured_logs()
        rollback_logs = [log for log in logs if "configuration_rollback" in log.get("message", "")]
        assert len(rollback_logs) > 0
        
        rollback_log = rollback_logs[0]
        assert rollback_log["context"]["rollback_reason"] == "validation_failure"
        assert rollback_log["context"]["invalid_keys"] == ["api.providers.openai.timeout_seconds", "api.providers.openai.api_key"]
    
    @pytest.mark.integration
    async def test_feature_flag_hot_reload_impact(self, config_hotreload_env):
        """Test hot-reload of feature flags and their immediate impact."""
        framework, test_client = config_hotreload_env
        
        # Initial state - enhanced visualizations enabled
        initial_config = framework.mock_config_service.get_current_config()
        assert initial_config["features"]["enhanced_visualizations"] is True
        
        # Make request with enhanced visualizations
        contract_validator = ContractTestValidator(test_client)
        initial_response = contract_validator.validate_weight_comparison_contract({
            "item1_name": "Test", "item1_weight": "100 kg",
            "item2_name": "Test", "item2_weight": "50 kg",
            "include_visualization": True
        })
        
        # Should have detailed visualization
        assert len(initial_response.visualization.prompt) > 100  # Enhanced visualization is longer
        
        # Change feature flag via hot-reload
        feature_flag_changes = {
            "features": {
                "enhanced_visualizations": False,
                "real_time_updates": False
            }
        }
        
        await framework.mock_config_service.apply_hot_reload_changes(feature_flag_changes)
        
        import asyncio
        await asyncio.sleep(1)
        
        # Make request after feature flag change
        post_change_response = contract_validator.validate_weight_comparison_contract({
            "item1_name": "Test", "item1_weight": "100 kg",
            "item2_name": "Test", "item2_weight": "50 kg", 
            "include_visualization": True
        })
        
        # Should have basic visualization (shorter)
        assert len(post_change_response.visualization.prompt) < 100
        
        # Verify feature flag change was applied and logged
        logs = framework.mock_logger.get_captured_logs()
        feature_logs = [log for log in logs if "feature_flag_changed" in log.get("message", "")]
        assert len(feature_logs) > 0
    
    @pytest.mark.integration
    async def test_concurrent_requests_during_hot_reload(self, config_hotreload_env):
        """Test system stability during configuration hot-reload with concurrent requests."""
        framework, test_client = config_hotreload_env
        
        import concurrent.futures
        import asyncio
        
        def make_request(request_id: int):
            """Make a weight comparison request."""
            try:
                contract_validator = ContractTestValidator(test_client)
                response = contract_validator.validate_weight_comparison_contract({
                    "item1_name": f"Test {request_id}",
                    "item1_weight": "100 kg",
                    "item2_name": f"Test {request_id}",
                    "item2_weight": "50 kg"
                })
                return {"success": True, "request_id": request_id, "provider": response.metadata.ai_provider_used}
            except Exception as e:
                return {"success": False, "request_id": request_id, "error": str(e)}
        
        async def trigger_hot_reload():
            """Trigger configuration hot-reload during concurrent requests."""
            await asyncio.sleep(1)  # Let some requests start
            
            config_changes = {
                "api": {
                    "providers": {
                        "openai": {"timeout_seconds": 15},
                        "anthropic": {"timeout_seconds": 12}
                    }
                }
            }
            
            await framework.mock_config_service.apply_hot_reload_changes(config_changes)
        
        # Start concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Submit concurrent requests
            request_futures = [executor.submit(make_request, i) for i in range(20)]
            
            # Trigger hot-reload concurrently
            asyncio.create_task(trigger_hot_reload())
            
            # Wait for all requests to complete
            results = [f.result() for f in concurrent.futures.as_completed(request_futures)]
        
        # Analyze results
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        success_rate = len(successful_requests) / len(results)
        
        # Should maintain high success rate even during hot-reload
        assert success_rate >= 0.90, f"Success rate {success_rate:.2%} too low during hot-reload"
        
        # Verify no requests failed due to configuration issues
        config_related_failures = [r for r in failed_requests if "config" in r.get("error", "").lower()]
        assert len(config_related_failures) == 0, f"Configuration-related failures during hot-reload: {config_related_failures}"
        
        # Verify hot-reload completed successfully
        logs = framework.mock_logger.get_captured_logs()
        hot_reload_logs = [log for log in logs if "configuration_hot_reload" in log.get("message", "")]
        assert any(log["context"]["reload_success"] for log in hot_reload_logs)
```

## 6. Database and External Service Integration Patterns

### 6.1 External Service Integration Testing

Testing patterns for external service dependencies including cache services, monitoring systems, and third-party APIs with realistic failure scenarios.

```python
class TestExternalServiceIntegration:
    """Integration tests for external service dependencies."""
    
    @pytest.fixture
    async def external_service_env(self):
        """Setup external service integration testing environment."""
        framework = IntegrationTestFramework()
        
        # Configure external service mocks
        config_overrides = {
            "external_services": {
                "cache": {
                    "provider": "redis",
                    "connection": {
                        "host": "localhost",
                        "port": 6379,
                        "timeout_seconds": 2
                    }
                },
                "monitoring": {
                    "prometheus": {
                        "enabled": True,
                        "pushgateway_url": "http://localhost:9091"
                    }
                }
            }
        }
        
        test_client = await framework.setup_integration_environment(
            config_overrides=config_overrides
        )
        yield framework, test_client
        await framework.teardown_integration_environment()
    
    @pytest.mark.integration
    async def test_cache_service_integration(self, external_service_env):
        """Test cache service integration with graceful degradation."""
        framework, test_client = external_service_env
        
        # Configure cache to be available initially
        framework.mock_cache_service = await self._setup_mock_cache_service()
        framework.mock_cache_service.configure_availability(True)
        
        # First request should populate cache
        request_data = {
            "item1_name": "Elephant",
            "item1_weight": "5000 kg",
            "item2_name": "Car", 
            "item2_weight": "1500 kg"
        }
        
        contract_validator = ContractTestValidator(test_client)
        first_response = contract_validator.validate_weight_comparison_contract(request_data)
        
        # Verify cache miss on first request
        assert first_response.metadata.cache_hit is False
        
        # Second identical request should hit cache
        second_response = contract_validator.validate_weight_comparison_contract(request_data)
        
        # Verify cache hit
        assert second_response.metadata.cache_hit is True
        assert second_response.metadata.processing_time_ms < first_response.metadata.processing_time_ms
        
        # Simulate cache service failure
        framework.mock_cache_service.configure_availability(False)
        
        # Request should still work without cache (graceful degradation)
        third_response = contract_validator.validate_weight_comparison_contract(request_data)
        
        assert third_response.metadata.cache_hit is False
        # Processing time should be similar to first request (no cache)
        
        # Verify cache failure was logged but didn't break the request
        logs = framework.mock_logger.get_captured_logs()
        cache_failure_logs = [log for log in logs if "cache_unavailable" in log.get("message", "")]
        assert len(cache_failure_logs) > 0
    
    @pytest.mark.integration
    async def test_monitoring_service_integration(self, external_service_env):
        """Test monitoring service integration without blocking requests."""
        framework, test_client = external_service_env
        
        # Configure monitoring service to be slow/failing
        framework.mock_monitoring_service = await self._setup_mock_monitoring_service()
        framework.mock_monitoring_service.configure_latency(5000)  # 5 second delay
        
        import time
        
        # Make request and measure total time
        start_time = time.time()
        
        contract_validator = ContractTestValidator(test_client)
        response = contract_validator.validate_weight_comparison_contract({
            "item1_name": "Test", "item1_weight": "100 kg",
            "item2_name": "Test", "item2_weight": "50 kg"
        })
        
        total_time = time.time() - start_time
        
        # Request should complete quickly despite slow monitoring
        assert total_time < 3.0, f"Request took {total_time:.2f}s, should not be blocked by monitoring"
        
        # Response should be valid
        assert response.metadata.ai_provider_used is not None
        
        # Verify monitoring was attempted but didn't block
        logs = framework.mock_logger.get_captured_logs()
        monitoring_logs = [log for log in logs if "metrics_push" in log.get("message", "")]
        assert len(monitoring_logs) > 0
    
    @pytest.mark.integration
    async def test_multiple_external_service_failures(self, external_service_env):
        """Test system resilience when multiple external services fail."""
        framework, test_client = external_service_env
        
        # Setup and fail multiple external services
        framework.mock_cache_service = await self._setup_mock_cache_service()
        framework.mock_monitoring_service = await self._setup_mock_monitoring_service()
        
        framework.mock_cache_service.configure_availability(False)
        framework.mock_monitoring_service.configure_availability(False)
        
        # Core functionality should still work
        contract_validator = ContractTestValidator(test_client)
        response = contract_validator.validate_weight_comparison_contract({
            "item1_name": "Test", "item1_weight": "100 kg",
            "item2_name": "Test", "item2_weight": "50 kg"
        })
        
        # Core response should be valid
        assert response.item1.weight_kg > 0
        assert response.item2.weight_kg > 0
        assert response.comparison.ratio > 0
        
        # Cache should be marked as miss due to unavailability
        assert response.metadata.cache_hit is False
        
        # Health endpoint should reflect degraded state
        health_response = test_client.get("/api/v1/health")
        health_data = health_response.json()
        
        # System should be degraded but not unhealthy
        assert health_data["status"] in ["degraded", "healthy"]  # Core functionality still works
        
        # Verify failures were logged appropriately
        logs = framework.mock_logger.get_captured_logs()
        
        cache_failure_logs = [log for log in logs if "cache_unavailable" in log.get("message", "")]
        monitoring_failure_logs = [log for log in logs if "monitoring_unavailable" in log.get("message", "")]
        
        assert len(cache_failure_logs) > 0
        assert len(monitoring_failure_logs) > 0
    
    async def _setup_mock_cache_service(self):
        """Setup mock cache service for testing."""
        from backend.testing.mocks.cache import MockCacheService
        
        mock_cache = MockCacheService()
        await mock_cache.initialize_for_testing()
        return mock_cache
    
    async def _setup_mock_monitoring_service(self):
        """Setup mock monitoring service for testing."""
        from backend.testing.mocks.monitoring import MockMonitoringService
        
        mock_monitoring = MockMonitoringService()
        await mock_monitoring.initialize_for_testing()
        return mock_monitoring
```

### 6.2 Database Integration Patterns

Testing patterns for database operations including connection pooling, transaction management, and data consistency validation.

```python
class TestDatabaseIntegration:
    """Integration tests for database operations and data persistence."""
    
    @pytest.fixture
    async def database_env(self):
        """Setup database integration testing environment.""" 
        framework = IntegrationTestFramework()
        
        # Configure test database
        config_overrides = {
            "database": {
                "provider": "sqlite",
                "connection": {
                    "url": "sqlite:///test_sizecomparator.db",
                    "pool_size": 5,
                    "max_overflow": 10,
                    "pool_timeout": 30
                },
                "migration": {
                    "auto_migrate": True,
                    "backup_before_migration": True
                }
            }
        }
        
        test_client = await framework.setup_integration_environment(
            config_overrides=config_overrides
        )
        
        # Setup test database
        await framework.setup_test_database()
        
        yield framework, test_client
        
        await framework.cleanup_test_database()
        await framework.teardown_integration_environment()
    
    @pytest.mark.integration
    async def test_weight_comparison_persistence(self, database_env):
        """Test weight comparison data persistence and retrieval."""
        framework, test_client = database_env
        
        # Make weight comparison request
        request_data = {
            "item1_name": "Blue Whale",
            "item1_weight": "150000 kg", 
            "item2_name": "Boeing 747",
            "item2_weight": "412000 lbs"
        }
        
        contract_validator = ContractTestValidator(test_client)
        response = contract_validator.validate_weight_comparison_contract(request_data)
        
        comparison_id = response.metadata.request_id
        
        # Verify data was persisted to database
        db_record = await framework.database_service.get_comparison_by_id(comparison_id)
        
        assert db_record is not None
        assert db_record["item1_name"] == request_data["item1_name"]
        assert db_record["item2_name"] == request_data["item2_name"] 
        assert db_record["comparison_ratio"] == float(response.comparison.ratio)
        assert db_record["ai_provider_used"] == response.metadata.ai_provider_used
        
        # Verify audit trail was created
        audit_records = await framework.database_service.get_audit_trail(comparison_id)
        assert len(audit_records) > 0
        
        creation_audit = audit_records[0]
        assert creation_audit["action"] == "comparison_created"
        assert creation_audit["request_id"] == comparison_id
    
    @pytest.mark.integration
    async def test_database_transaction_rollback(self, database_env):
        """Test database transaction rollback on errors."""
        framework, test_client = database_env
        
        # Configure scenario where AI provider succeeds but database fails
        framework.mock_ai_provider.configure_provider_success("openai")
        framework.database_service.configure_failure_scenario({
            "operation": "save_comparison",
            "failure_type": "transaction_error",
            "failure_rate": 1.0
        })
        
        request_data = {
            "item1_name": "Test Item 1",
            "item1_weight": "100 kg",
            "item2_name": "Test Item 2",
            "item2_weight": "50 kg"
        }
        
        # Request should fail due to database error
        response = test_client.post("/api/v1/compare", json=request_data)
        assert response.status_code == 500
        
        error_data = response.json()
        error_response = ErrorResponse(**error_data)
        assert error_response.error_category.value == "SERVER_ERROR"
        
        # Verify no partial data was saved (transaction rolled back)
        all_comparisons = await framework.database_service.get_all_comparisons()
        assert len(all_comparisons) == 0
        
        # Verify rollback was logged
        logs = framework.mock_logger.get_captured_logs()
        rollback_logs = [log for log in logs if "transaction_rollback" in log.get("message", "")]
        assert len(rollback_logs) > 0
    
    @pytest.mark.integration
    async def test_database_connection_pool_management(self, database_env):
        """Test database connection pool under concurrent load."""
        framework, test_client = database_env
        
        import concurrent.futures
        import asyncio
        
        async def make_concurrent_request(request_id: int):
            """Make database-intensive request."""
            request_data = {
                "item1_name": f"Item 1-{request_id}",
                "item1_weight": f"{100 + request_id} kg",
                "item2_name": f"Item 2-{request_id}",
                "item2_weight": f"{50 + request_id} kg"
            }
            
            try:
                contract_validator = ContractTestValidator(test_client)
                response = contract_validator.validate_weight_comparison_contract(request_data)
                
                # Verify data was persisted
                db_record = await framework.database_service.get_comparison_by_id(
                    response.metadata.request_id
                )
                
                return {
                    "success": True,
                    "request_id": request_id,
                    "persisted": db_record is not None
                }
            except Exception as e:
                return {
                    "success": False,
                    "request_id": request_id,
                    "error": str(e)
                }
        
        # Execute many concurrent database operations
        num_concurrent = 15  # More than pool_size (5) to test pooling
        
        tasks = [make_concurrent_request(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        success_rate = len(successful_results) / len(results)
        
        # Should handle concurrent requests without connection pool exhaustion
        assert success_rate >= 0.90, f"Success rate {success_rate:.2%} too low with connection pooling"
        
        # Verify all successful requests were properly persisted
        persisted_count = sum(1 for r in successful_results if r.get("persisted"))
        assert persisted_count == len(successful_results), "Some successful requests were not persisted"
        
        # Verify no connection pool exhaustion errors
        pool_errors = [r for r in failed_results if "pool" in r.get("error", "").lower()]
        assert len(pool_errors) == 0, f"Connection pool exhaustion detected: {pool_errors}"
```

## 7. Test Environment Management

### 7.1 Test Setup and Teardown Procedures

Comprehensive test environment management ensuring complete isolation and deterministic test execution across all integration scenarios.

```python
class IntegrationTestEnvironmentManager:
    """Manages complete integration test environment lifecycle."""
    
    def __init__(self):
        self.environments = {}
        self.cleanup_tasks = []
        self.environment_isolation = True
        
    async def create_isolated_environment(
        self, 
        test_name: str,
        config_overrides: Dict[str, Any] = None,
        enable_real_services: bool = False
    ) -> Dict[str, Any]:
        """
        Create completely isolated test environment for integration tests.
        
        Args:
            test_name: Unique identifier for this test environment
            config_overrides: Configuration overrides for this environment
            enable_real_services: Whether to use real external services (for staging)
            
        Returns:
            Environment context with all initialized services
        """
        environment_id = f"{test_name}_{uuid.uuid4().hex[:8]}"
        
        try:
            # 1. Setup isolated configuration
            config_service = await self._setup_isolated_configuration(
                environment_id, 
                config_overrides
            )
            
            # 2. Setup database isolation
            database_service = await self._setup_isolated_database(environment_id)
            
            # 3. Setup AI provider services
            if enable_real_services:
                ai_provider_service = await self._setup_real_ai_providers(environment_id)
            else:
                ai_provider_service = await self._setup_mock_ai_providers(environment_id)
            
            # 4. Setup external service mocks
            external_services = await self._setup_external_services(
                environment_id, 
                enable_real_services
            )
            
            # 5. Setup monitoring and logging
            monitoring_service = await self._setup_test_monitoring(environment_id)
            
            # 6. Create FastAPI application with isolated dependencies
            app = await self._create_isolated_app(
                config_service,
                database_service,
                ai_provider_service,
                external_services,
                monitoring_service
            )
            
            # 7. Create test client
            test_client = TestClient(app)
            
            # 8. Store environment for cleanup
            environment_context = {
                "environment_id": environment_id,
                "config_service": config_service,
                "database_service": database_service,
                "ai_provider_service": ai_provider_service,
                "external_services": external_services,
                "monitoring_service": monitoring_service,
                "app": app,
                "test_client": test_client
            }
            
            self.environments[environment_id] = environment_context
            
            # 9. Register cleanup tasks
            await self._register_cleanup_tasks(environment_id, environment_context)
            
            return environment_context
            
        except Exception as e:
            # Cleanup on failure
            await self._cleanup_failed_environment(environment_id)
            raise Exception(f"Failed to create isolated environment: {e}")
    
    async def _setup_isolated_configuration(
        self, 
        environment_id: str, 
        overrides: Dict[str, Any] = None
    ) -> ConfigurationService:
        """Setup isolated configuration for test environment."""
        from backend.testing.isolation.config import IsolatedConfigurationService
        
        # Create temporary config directory
        temp_config_dir = tempfile.mkdtemp(prefix=f"config_{environment_id}_")
        
        # Base test configuration
        base_config = {
            "application": {
                "name": "SizeComparator",
                "version": "1.0.0-test",
                "environment": f"integration_test_{environment_id}"
            },
            "api": {
                "cors": {"allow_origins": ["*"]},
                "request_timeout_seconds": 30,
                "providers": {
                    "openai": {
                        "api_key": f"test-key-{environment_id}",
                        "timeout_seconds": 10,
                        "retry": {"max_attempts": 3}
                    }
                }
            },
            "database": {
                "url": f"sqlite:///test_{environment_id}.db",
                "pool_size": 5
            },
            "monitoring": {
                "logging": {"level": "DEBUG", "format": "json"},
                "metrics": {"enabled": True}
            }
        }
        
        if overrides:
            base_config = self._deep_merge_config(base_config, overrides)
        
        # Create isolated config service
        config_service = IsolatedConfigurationService(temp_config_dir)
        await config_service.load_config(base_config)
        
        # Register for cleanup
        self.cleanup_tasks.append(
            lambda: self._cleanup_config_directory(temp_config_dir)
        )
        
        return config_service
    
    async def _setup_isolated_database(self, environment_id: str):
        """Setup isolated database for test environment."""
        from backend.testing.isolation.database import IsolatedDatabaseService
        
        database_file = f"test_{environment_id}.db"
        database_service = IsolatedDatabaseService(database_file)
        
        # Initialize test database schema
        await database_service.initialize_schema()
        
        # Register for cleanup
        self.cleanup_tasks.append(
            lambda: database_service.cleanup_database()
        )
        
        return database_service
    
    async def _setup_mock_ai_providers(self, environment_id: str):
        """Setup mock AI providers with isolation."""
        from backend.testing.mocks.ai_providers import IsolatedMockAIProviderManager
        
        mock_manager = IsolatedMockAIProviderManager(environment_id)
        
        # Configure default behaviors
        await mock_manager.configure_default_behaviors({
            "response_latency": {"min_ms": 100, "max_ms": 300},
            "success_rate": 0.95,
            "circuit_breaker": {"enabled": True}
        })
        
        return mock_manager
    
    async def _setup_real_ai_providers(self, environment_id: str):
        """Setup real AI providers for staging tests."""
        from backend.ai_providers.manager import AIProviderManager
        
        provider_manager = AIProviderManager()
        
        # Configure for test environment
        await provider_manager.configure_for_integration_testing({
            "environment_id": environment_id,
            "use_test_endpoints": True,
            "shorter_timeouts": True
        })
        
        return provider_manager
    
    async def _setup_external_services(
        self, 
        environment_id: str, 
        enable_real_services: bool
    ):
        """Setup external service mocks or real services."""
        if enable_real_services:
            return await self._setup_real_external_services(environment_id)
        else:
            return await self._setup_mock_external_services(environment_id)
    
    async def _setup_mock_external_services(self, environment_id: str):
        """Setup mock external services."""
        from backend.testing.mocks.external import MockExternalServiceManager
        
        external_manager = MockExternalServiceManager(environment_id)
        
        # Setup mock cache, monitoring, etc.
        await external_manager.setup_all_mocks({
            "cache": {"provider": "memory", "size_limit": 1000},
            "monitoring": {"provider": "mock", "capture_metrics": True}
        })
        
        return external_manager
    
    async def _setup_real_external_services(self, environment_id: str):
        """Setup real external services for staging tests."""
        from backend.external.manager import ExternalServiceManager
        
        external_manager = ExternalServiceManager()
        
        # Configure for test environment
        await external_manager.configure_for_testing({
            "environment_id": environment_id,
            "use_test_instances": True
        })
        
        return external_manager
    
    async def _setup_test_monitoring(self, environment_id: str):
        """Setup test monitoring and logging."""
        from backend.testing.mocks.monitoring import IsolatedMonitoringService
        
        monitoring = IsolatedMonitoringService(environment_id)
        
        await monitoring.initialize_test_monitoring({
            "capture_all_logs": True,
            "capture_metrics": True,
            "validate_log_structure": True
        })
        
        return monitoring
    
    async def _create_isolated_app(
        self,
        config_service,
        database_service, 
        ai_provider_service,
        external_services,
        monitoring_service
    ) -> FastAPI:
        """Create FastAPI app with isolated dependencies."""
        from backend.main import create_app
        
        app = create_app()
        
        # Override dependencies with isolated services
        app.dependency_overrides = {
            ConfigurationService: lambda: config_service,
            DatabaseService: lambda: database_service,
            AIProviderManager: lambda: ai_provider_service,
            ExternalServiceManager: lambda: external_services,
            MonitoringService: lambda: monitoring_service
        }
        
        return app
    
    async def _register_cleanup_tasks(self, environment_id: str, context: Dict[str, Any]):
        """Register cleanup tasks for environment."""
        async def cleanup_environment():
            try:
                # Cleanup services
                if "test_client" in context:
                    context["test_client"].close()
                
                if "database_service" in context:
                    await context["database_service"].cleanup()
                
                if "ai_provider_service" in context:
                    await context["ai_provider_service"].cleanup()
                
                if "external_services" in context:
                    await context["external_services"].cleanup()
                
                if "monitoring_service" in context:
                    await context["monitoring_service"].cleanup()
                
                # Clear app overrides
                if "app" in context:
                    context["app"].dependency_overrides.clear()
                
            except Exception as e:
                print(f"Error during environment cleanup {environment_id}: {e}")
        
        self.cleanup_tasks.append(cleanup_environment)
    
    async def cleanup_environment(self, environment_id: str):
        """Cleanup specific test environment."""
        if environment_id in self.environments:
            context = self.environments[environment_id]
            
            # Run cleanup tasks
            for task in self.cleanup_tasks:
                try:
                    if asyncio.iscoroutinefunction(task):
                        await task()
                    else:
                        task()
                except Exception as e:
                    print(f"Cleanup task failed: {e}")
            
            # Remove from tracking
            del self.environments[environment_id]
    
    async def cleanup_all_environments(self):
        """Cleanup all test environments."""
        environment_ids = list(self.environments.keys())
        
        for env_id in environment_ids:
            await self.cleanup_environment(env_id)
        
        self.cleanup_tasks.clear()
    
    def _deep_merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge configuration dictionaries."""
        import copy
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
```

## 8. Contract Testing and API Boundary Validation

### 8.1 Cross-Component Contract Testing

Comprehensive contract testing to ensure all component interfaces maintain compatibility and follow specification requirements.

```python
class ComponentContractTester:
    """Tests contracts between system components to ensure interface compatibility."""
    
    def __init__(self, environment_manager: IntegrationTestEnvironmentManager):
        self.environment_manager = environment_manager
        self.contract_violations = []
    
    async def test_all_component_contracts(self) -> Dict[str, Any]:
        """Test all component contracts and return comprehensive results."""
        
        # Create isolated environment for contract testing
        env = await self.environment_manager.create_isolated_environment(
            "contract_testing",
            config_overrides={"contract_testing": {"strict_validation": True}}
        )
        
        try:
            contract_results = {
                "backend_ai_provider_contract": await self._test_backend_ai_provider_contract(env),
                "backend_config_contract": await self._test_backend_config_contract(env),
                "api_frontend_contract": await self._test_api_frontend_contract(env),
                "error_monitoring_contract": await self._test_error_monitoring_contract(env),
                "health_deployment_contract": await self._test_health_deployment_contract(env)
            }
            
            # Analyze overall contract compliance
            total_violations = sum(len(result.get("violations", [])) for result in contract_results.values())
            overall_compliance = all(result.get("compliant", False) for result in contract_results.values())
            
            return {
                "overall_compliant": overall_compliance,
                "total_violations": total_violations,
                "component_results": contract_results,
                "recommendations": self._generate_contract_recommendations(contract_results)
            }
            
        finally:
            await self.environment_manager.cleanup_environment(env["environment_id"])
    
    async def _test_backend_ai_provider_contract(self, env: Dict[str, Any]) -> Dict[str, Any]:
        """Test contract between backend core and AI provider services."""
        violations = []
        
        ai_provider = env["ai_provider_service"]
        test_client = env["test_client"]
        
        # Test 1: Provider interface compliance
        try:
            # Verify all required AI_PROVIDER_SPEC methods exist
            required_methods = [
                "generate_comparison",
                "validate_response", 
                "parse_response",
                "get_health_status"
            ]
            
            for method in required_methods:
                if not hasattr(ai_provider, method):
                    violations.append(f"AI provider missing required method: {method}")
                elif not callable(getattr(ai_provider, method)):
                    violations.append(f"AI provider method not callable: {method}")
        
        except Exception as e:
            violations.append(f"AI provider interface validation failed: {e}")
        
        # Test 2: Request/response contract compliance
        try:
            from backend.models.ai_models import ComparisonRequest
            from backend.models.responses import WeightComparisonResponse
            
            # Create valid request following BACKEND_CORE_SPEC
            test_request = ComparisonRequest(
                weight=100.0,
                unit="kg",
                prompt_template="test_template",
                max_tokens=100,
                temperature=0.7,
                timeout_seconds=10.0
            )
            
            # Call AI provider
            response = await ai_provider.generate_comparison(test_request)
            
            # Verify response is valid WeightComparisonResponse
            if not isinstance(response, WeightComparisonResponse):
                violations.append(f"AI provider returned invalid response type: {type(response)}")
            
            # Verify response has all required fields
            required_fields = ["item1", "item2", "comparison", "visualization", "metadata"]
            for field in required_fields:
                if not hasattr(response, field) or getattr(response, field) is None:
                    violations.append(f"AI provider response missing required field: {field}")
        
        except Exception as e:
            violations.append(f"AI provider request/response contract failed: {e}")
        
        # Test 3: Error handling contract
        try:
            # Configure AI provider to fail
            ai_provider.configure_failure_scenario({"failure_rate": 1.0})
            
            with pytest.raises(Exception) as exc_info:
                await ai_provider.generate_comparison(test_request)
            
            # Verify error follows ERROR_MONITORING_SPEC format
            error = exc_info.value
            if not hasattr(error, "error_category") and not hasattr(error, "error_code"):
                violations.append("AI provider errors don't follow ERROR_MONITORING_SPEC format")
        
        except Exception as e:
            violations.append(f"AI provider error handling contract failed: {e}")
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "component": "backend_ai_provider"
        }
    
    async def _test_backend_config_contract(self, env: Dict[str, Any]) -> Dict[str, Any]:
        """Test contract between backend core and configuration service."""
        violations = []
        
        config_service = env["config_service"]
        
        # Test 1: Configuration interface compliance
        try:
            # Verify CONFIG_SYSTEM_SPEC interface methods
            required_methods = ["get", "set", "reload", "validate"]
            
            for method in required_methods:
                if not hasattr(config_service, method):
                    violations.append(f"Config service missing required method: {method}")
        
        except Exception as e:
            violations.append(f"Config service interface validation failed: {e}")
        
        # Test 2: Configuration key access patterns
        try:
            # Test hierarchical key access (CONFIG_SYSTEM_SPEC requirement)
            test_keys = [
                "application.name",
                "api.providers.openai.timeout_seconds",
                "features.enhanced_visualizations"
            ]
            
            for key in test_keys:
                try:
                    value = config_service.get(key)
                    if value is None:
                        violations.append(f"Config service returned None for required key: {key}")
                except Exception:
                    violations.append(f"Config service failed to retrieve key: {key}")
        
        except Exception as e:
            violations.append(f"Config key access contract failed: {e}")
        
        # Test 3: Hot-reload contract
        try:
            # Test hot-reload doesn't break active connections
            original_timeout = config_service.get("api.providers.openai.timeout_seconds")
            
            # Apply configuration change
            config_service.set("api.providers.openai.timeout_seconds", original_timeout + 5)
            await config_service.reload()
            
            # Verify change was applied
            new_timeout = config_service.get("api.providers.openai.timeout_seconds")
            if new_timeout != original_timeout + 5:
                violations.append("Config hot-reload didn't apply changes correctly")
        
        except Exception as e:
            violations.append(f"Config hot-reload contract failed: {e}")
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "component": "backend_config"
        }
    
    async def _test_api_frontend_contract(self, env: Dict[str, Any]) -> Dict[str, Any]:
        """Test contract between API endpoints and frontend clients."""
        violations = []
        
        test_client = env["test_client"]
        
        # Test 1: API endpoint availability
        try:
            required_endpoints = [
                ("POST", "/api/v1/compare"),
                ("GET", "/api/v1/health"),
                ("GET", "/api/v1/ready"),
                ("GET", "/api/v1/metrics")
            ]
            
            for method, endpoint in required_endpoints:
                if method == "GET":
                    response = test_client.get(endpoint)
                else:
                    response = test_client.post(endpoint, json={})
                
                if response.status_code == 404:
                    violations.append(f"Required endpoint not found: {method} {endpoint}")
        
        except Exception as e:
            violations.append(f"API endpoint availability check failed: {e}")
        
        # Test 2: Request/response format contract
        try:
            # Test valid request format
            valid_request = {
                "item1_name": "Test Item 1",
                "item1_weight": "100 kg",
                "item2_name": "Test Item 2", 
                "item2_weight": "50 kg"
            }
            
            response = test_client.post("/api/v1/compare", json=valid_request)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Verify BACKEND_CORE_SPEC response format
                required_fields = ["item1", "item2", "comparison", "visualization", "metadata"]
                for field in required_fields:
                    if field not in response_data:
                        violations.append(f"API response missing required field: {field}")
            else:
                violations.append(f"API returned unexpected status for valid request: {response.status_code}")
        
        except Exception as e:
            violations.append(f"API request/response contract failed: {e}")
        
        # Test 3: Error response format contract
        try:
            # Test invalid request
            invalid_request = {"invalid": "request"}
            
            response = test_client.post("/api/v1/compare", json=invalid_request)
            
            if response.status_code >= 400:
                error_data = response.json()
                
                # Verify ERROR_MONITORING_SPEC error format
                required_error_fields = ["error_code", "error_category", "message", "request_id"]
                for field in required_error_fields:
                    if field not in error_data:
                        violations.append(f"Error response missing required field: {field}")
            else:
                violations.append("API accepted invalid request (should have returned error)")
        
        except Exception as e:
            violations.append(f"API error response contract failed: {e}")
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "component": "api_frontend"
        }
    
    async def _test_error_monitoring_contract(self, env: Dict[str, Any]) -> Dict[str, Any]:
        """Test contract between components and error monitoring system."""
        violations = []
        
        monitoring_service = env["monitoring_service"]
        test_client = env["test_client"]
        
        # Test 1: Structured logging contract
        try:
            # Make request that should generate logs
            test_client.post("/api/v1/compare", json={
                "item1_name": "Test", "item1_weight": "100 kg",
                "item2_name": "Test", "item2_weight": "50 kg"
            })
            
            # Verify logs were captured
            logs = monitoring_service.get_captured_logs()
            if len(logs) == 0:
                violations.append("No logs were captured during request processing")
            
            # Verify log structure follows ERROR_MONITORING_SPEC
            for log in logs:
                required_log_fields = ["timestamp", "request_id", "service_name", "message"]
                for field in required_log_fields:
                    if field not in log:
                        violations.append(f"Log entry missing required field: {field}")
                        break
        
        except Exception as e:
            violations.append(f"Structured logging contract failed: {e}")
        
        # Test 2: Error categorization contract
        try:
            # Trigger different error categories
            error_scenarios = [
                ({"invalid": "request"}, "CLIENT_ERROR"),
                # Server errors would be tested with mock failures
            ]
            
            for request_data, expected_category in error_scenarios:
                response = test_client.post("/api/v1/compare", json=request_data)
                if response.status_code >= 400:
                    error_data = response.json()
                    
                    if error_data.get("error_category") != expected_category:
                        violations.append(f"Incorrect error category: expected {expected_category}, got {error_data.get('error_category')}")
        
        except Exception as e:
            violations.append(f"Error categorization contract failed: {e}")
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "component": "error_monitoring"
        }
    
    async def _test_health_deployment_contract(self, env: Dict[str, Any]) -> Dict[str, Any]:
        """Test contract between health endpoints and deployment infrastructure."""
        violations = []
        
        test_client = env["test_client"]
        
        # Test 1: Health endpoint DEPLOYMENT_OPS_SPEC compliance
        try:
            response = test_client.get("/api/v1/health")
            
            if response.status_code != 200:
                violations.append(f"Health endpoint returned non-200 status: {response.status_code}")
            
            health_data = response.json()
            
            # Verify DEPLOYMENT_OPS_SPEC health format
            required_health_fields = ["status", "timestamp", "version"]
            for field in required_health_fields:
                if field not in health_data:
                    violations.append(f"Health response missing required field: {field}")
            
            # Verify status values are valid
            valid_statuses = ["healthy", "degraded", "unhealthy"]
            if health_data.get("status") not in valid_statuses:
                violations.append(f"Invalid health status: {health_data.get('status')}")
        
        except Exception as e:
            violations.append(f"Health endpoint contract failed: {e}")
        
        # Test 2: Readiness endpoint contract
        try:
            response = test_client.get("/api/v1/ready")
            
            if response.status_code != 200:
                violations.append(f"Readiness endpoint returned non-200 status: {response.status_code}")
            
            readiness_data = response.json()
            
            # Verify readiness format
            if "ready" not in readiness_data or not isinstance(readiness_data["ready"], bool):
                violations.append("Readiness response missing or invalid 'ready' field")
            
            if "checks" not in readiness_data or not isinstance(readiness_data["checks"], dict):
                violations.append("Readiness response missing or invalid 'checks' field")
        
        except Exception as e:
            violations.append(f"Readiness endpoint contract failed: {e}")
        
        # Test 3: Metrics endpoint contract
        try:
            response = test_client.get("/api/v1/metrics")
            
            if response.status_code != 200:
                violations.append(f"Metrics endpoint returned non-200 status: {response.status_code}")
            
            # Verify Prometheus format
            content_type = response.headers.get("content-type", "")
            if "text/plain" not in content_type:
                violations.append(f"Metrics endpoint wrong content type: {content_type}")
            
            metrics_content = response.text
            if "# HELP" not in metrics_content or "# TYPE" not in metrics_content:
                violations.append("Metrics endpoint doesn't return valid Prometheus format")
        
        except Exception as e:
            violations.append(f"Metrics endpoint contract failed: {e}")
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "component": "health_deployment"
        }
    
    def _generate_contract_recommendations(self, contract_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on contract test results."""
        recommendations = []
        
        for component, result in contract_results.items():
            if not result.get("compliant", False):
                violations = result.get("violations", [])
                
                if component == "backend_ai_provider":
                    recommendations.append("Review AI_PROVIDER_SPEC interface implementation")
                    recommendations.append("Verify BACKEND_CORE_SPEC response model compliance")
                
                elif component == "backend_config":
                    recommendations.append("Review CONFIG_SYSTEM_SPEC interface requirements") 
                    recommendations.append("Test configuration hot-reload mechanisms")
                
                elif component == "api_frontend":
                    recommendations.append("Review API_ENDPOINTS_SPEC request/response formats")
                    recommendations.append("Verify BACKEND_CORE_SPEC Pydantic model usage")
                
                elif component == "error_monitoring":
                    recommendations.append("Review ERROR_MONITORING_SPEC logging requirements")
                    recommendations.append("Verify structured logging field compliance")
                
                elif component == "health_deployment":
                    recommendations.append("Review DEPLOYMENT_OPS_SPEC health endpoint requirements")
                    recommendations.append("Test load balancer compatibility")
        
        if not recommendations:
            recommendations.append("All component contracts are compliant")
        
        return recommendations
```

## Summary

This comprehensive Integration Testing Specification provides a complete framework for validating SizeComparator's component interactions and system-wide contracts. The specification delivers:

### Key Integration Testing Capabilities

1. **Component Integration Testing** - FastAPI test client with dependency injection, realistic AI provider failover scenarios, and configuration hot-reload validation
2. **API Endpoint Testing** - Contract-based testing using exact BACKEND_CORE_SPEC Pydantic models, concurrent request handling, and error response validation  
3. **Database and External Service Integration** - Connection pooling, transaction management, graceful degradation patterns, and external service failure resilience
4. **Test Environment Management** - Complete isolation between tests, deterministic setup/teardown procedures, and environment-specific configuration
5. **Contract Testing** - Cross-component interface validation, API boundary compliance, and specification alignment verification

### Advanced Testing Scenarios

- **AI Provider Failover**: Primary provider failures, circuit breaker state transitions, performance degradation handling, and multi-provider load distribution
- **Configuration Hot-Reload**: Safe configuration changes without restart, validation rollback on errors, feature flag impact testing, and concurrent request stability  
- **Health Endpoint Integration**: Load balancer compatibility, dependency health checking, metrics exposure, and deployment infrastructure compliance
- **Error Handling**: Structured logging validation, error categorization compliance, request ID propagation, and monitoring integration

### Test Quality Assurance

- 95% integration test coverage across all component boundaries
- Contract validation using exact specification models
- Performance validation under concurrent load scenarios  
- Environment isolation ensuring test independence
- Comprehensive cleanup procedures preventing test pollution

The framework ensures reliable component contracts while providing deterministic test execution through controlled environments, supporting both mock-based unit integration testing and real service staging validation scenarios.
