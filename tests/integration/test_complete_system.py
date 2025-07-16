"""
Complete system integration tests.

This module consolidates all integration testing scenarios including
end-to-end workflows, service interactions, and real-world usage patterns.
"""

import pytest
import asyncio
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from decimal import Decimal

from src.api.unified_app import create_unified_app
from src.services.shared.service_factory import ComparisonServiceFactory
from src.core.environment import EnvironmentManager, EnvironmentType
from src.models.mvp import MVPComparisonRequest, MVPComparisonResponse


@pytest.mark.integration
class TestCompleteSystemIntegration:
    """Test complete system integration scenarios"""
    
    @pytest.fixture
    def test_app(self, test_env_manager):
        """Create test application"""
        app = create_unified_app(test_env_manager)
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_complete_weight_comparison_workflow(self, test_app):
        """Test complete weight comparison workflow from API to response"""
        test_cases = [
            {
                "weight_input": "5 kg",
                "style": "default",
                "expected_provider": "fallback"
            },
            {
                "weight_input": "10 pounds",
                "style": "creative",
                "expected_provider": "fallback"
            },
            {
                "weight_input": "100 grams",
                "style": "technical",
                "expected_provider": "fallback"
            },
            {
                "weight_input": "2.5 tons",
                "style": "default",
                "expected_provider": "fallback"
            }
        ]
        
        for case in test_cases:
            response = test_app.post(
                "/api/compare",
                json=case
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert "comparison_text" in data
            assert "weight_processed" in data
            assert "provider_used" in data
            assert "response_time_ms" in data
            
            # Validate response structure
            assert len(data["comparison_text"]) > 10
            assert case["weight_input"].split()[1] in data["weight_processed"].lower() or \
                   any(unit in data["weight_processed"].lower() for unit in ["kg", "lb", "g", "ton"])
            assert data["provider_used"] == case["expected_provider"]
            assert data["response_time_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_service_mode_integration(self, test_app):
        """Test service mode integration across all modes"""
        service_modes = ["basic", "fast_validation", "full_validation", "comprehensive"]
        
        for mode in service_modes:
            response = test_app.post(
                f"/api/compare?service_mode={mode}",
                json={
                    "weight_input": "5 kg",
                    "style": "default"
                }
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert "comparison_text" in data
            assert "weight_processed" in data
            assert "provider_used" in data
            
            # Check service mode is tracked
            assert "X-Service-Mode" in response.headers
    
    @pytest.mark.asyncio
    async def test_performance_profile_integration(self, test_app):
        """Test performance profile integration"""
        profiles = ["speed_optimized", "balanced", "accuracy_optimized"]
        
        for profile in profiles:
            response = test_app.post(
                "/api/compare",
                json={
                    "weight_input": "5 kg",
                    "style": "default"
                },
                headers={
                    "X-Performance-Profile": profile
                }
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert "comparison_text" in data
            assert "response_time_ms" in data
            
            # Speed optimized should be faster
            if profile == "speed_optimized":
                assert data["response_time_ms"] < 2000
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, test_app):
        """Test error handling integration"""
        error_cases = [
            {
                "input": {},
                "expected_status": 422,
                "description": "Empty request"
            },
            {
                "input": {"weight_input": ""},
                "expected_status": 422,
                "description": "Empty weight input"
            },
            {
                "input": {"weight_input": "invalid weight"},
                "expected_status": 422,
                "description": "Invalid weight format"
            },
            {
                "input": {"weight_input": "-5 kg"},
                "expected_status": 422,
                "description": "Negative weight"
            }
        ]
        
        for case in error_cases:
            response = test_app.post("/api/compare", json=case["input"])
            
            assert response.status_code == case["expected_status"]
            
            if response.status_code == 422:
                data = response.json()
                assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_health_and_status_integration(self, test_app):
        """Test health and status endpoint integration"""
        # Test health endpoint
        response = test_app.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert "service_factory" in health_data
        assert "metrics" in health_data
        
        # Test status endpoint
        response = test_app.get("/api/status")
        assert response.status_code == 200
        
        status_data = response.json()
        assert "service_factory" in status_data
        assert "app_metrics" in status_data
        assert "startup_time" in status_data
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(self, test_app):
        """Test concurrent requests integration"""
        import concurrent.futures
        
        def make_request():
            return test_app.post(
                "/api/compare",
                json={
                    "weight_input": "5 kg",
                    "style": "default"
                }
            )
        
        # Test with 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "comparison_text" in data
            assert "weight_processed" in data
    
    @pytest.mark.asyncio
    async def test_legacy_endpoint_integration(self, test_app):
        """Test legacy endpoint integration"""
        legacy_endpoints = [
            "/api/compare/single",
            "/api/compare/validated",
            "/api/compare/fast"
        ]
        
        for endpoint in legacy_endpoints:
            response = test_app.post(
                endpoint,
                json={
                    "weight_input": "5 kg",
                    "style": "default"
                }
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert "comparison_text" in data
            assert "weight_processed" in data
    
    @pytest.mark.asyncio
    async def test_static_file_serving_integration(self, test_app):
        """Test static file serving integration"""
        # Test root endpoint
        response = test_app.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Test demo endpoints
        demo_modes = ["basic", "fast_validation", "full_validation", "comprehensive"]
        for mode in demo_modes:
            response = test_app.get(f"/demo/{mode}")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
    
    @pytest.mark.asyncio
    async def test_api_documentation_integration(self, test_app):
        """Test API documentation integration"""
        # Test OpenAPI schema
        response = test_app.get("/openapi.json")
        if response.status_code == 200:  # Only available in development
            data = response.json()
            assert "info" in data
            assert "paths" in data
            assert "/api/compare" in data["paths"]


@pytest.mark.integration
class TestServiceFactoryIntegration:
    """Test service factory integration scenarios"""
    
    def test_service_factory_with_environment_integration(self, test_env_manager):
        """Test service factory integration with environment"""
        factory = ComparisonServiceFactory(test_env_manager)
        
        # Test health status
        health = factory.get_service_health_status()
        assert health["factory_status"] == "healthy"
        assert "availability" in health
        assert "services" in health
        
        # Test all service types can be created
        for service_type in ["basic", "fast_validation", "full_validation", "comprehensive"]:
            assert service_type in health["availability"]
    
    @pytest.mark.asyncio
    async def test_service_selection_integration(self, test_env_manager):
        """Test service selection integration"""
        factory = ComparisonServiceFactory(test_env_manager)
        
        # Test weight-based selection
        weight_scenarios = [
            {"weight": "0.1 kg", "expected_category": "light"},
            {"weight": "5 kg", "expected_category": "common"},
            {"weight": "100 kg", "expected_category": "heavy"},
            {"weight": "1000 kg", "expected_category": "extreme"}
        ]
        
        for scenario in weight_scenarios:
            request = MVPComparisonRequest(weight_input=scenario["weight"])
            service = factory.get_service_from_request(request)
            
            assert service is not None
            assert hasattr(service, 'create_comparison')
            
            # Test the service actually works
            response = await service.create_comparison(request)
            assert isinstance(response, MVPComparisonResponse)
            assert response.comparison_text
    
    @pytest.mark.asyncio
    async def test_service_fallback_integration(self, test_env_manager, disable_ai_providers):
        """Test service fallback integration"""
        factory = ComparisonServiceFactory(test_env_manager)
        
        # Without AI providers, all services should fall back to basic
        for service_type in ["fast_validation", "full_validation", "comprehensive"]:
            if service_type == "basic":
                service = factory.create_basic_service()
            elif service_type == "fast_validation":
                service = factory.create_fast_validation_service()
            elif service_type == "full_validation":
                service = factory.create_full_validation_service()
            elif service_type == "comprehensive":
                service = factory.create_comprehensive_service()
            
            assert service is not None
            
            # Test that service works even without AI providers
            request = MVPComparisonRequest(weight_input="5 kg")
            response = await service.create_comparison(request)
            
            assert response.comparison_text
            assert response.provider_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_service_performance_integration(self, test_env_manager):
        """Test service performance integration"""
        factory = ComparisonServiceFactory(test_env_manager)
        
        # Test basic service performance
        service = factory.create_basic_service()
        request = MVPComparisonRequest(weight_input="5 kg")
        
        start_time = asyncio.get_event_loop().time()
        response = await service.create_comparison(request)
        end_time = asyncio.get_event_loop().time()
        
        actual_time_ms = (end_time - start_time) * 1000
        
        # Basic service should be very fast
        assert actual_time_ms < 1000
        assert response.response_time_ms < 1000
        assert response.comparison_text


@pytest.mark.integration
class TestWeightProcessingIntegration:
    """Test weight processing integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_weight_processing_end_to_end(self, test_app):
        """Test weight processing end-to-end integration"""
        from src.services.weight_processor import WeightProcessor
        
        processor = WeightProcessor()
        
        # Test various weight formats
        test_weights = [
            "5 kg",
            "10 pounds", 
            "100 grams",
            "2.5 lbs",
            "1 ounce",
            "1000 g",
            "1 stone",
            "0.5 ton"
        ]
        
        for weight_input in test_weights:
            # Test processor directly
            processed = processor.process_weight(weight_input)
            assert processed.weight_kg > 0
            assert processed.unit_used
            assert processed.confidence > 0
            
            # Test through API
            response = test_app.post(
                "/api/compare",
                json={
                    "weight_input": weight_input,
                    "style": "default"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "weight_processed" in data
            assert data["weight_processed"]
    
    @pytest.mark.asyncio
    async def test_weight_validation_integration(self, test_app):
        """Test weight validation integration"""
        from src.services.weight_processor import WeightProcessor
        
        processor = WeightProcessor()
        
        # Test valid weights
        valid_weights = [
            "5 kg",
            "10.5 pounds",
            "100 grams",
            "2.5 lbs"
        ]
        
        for weight_input in valid_weights:
            validation_result = processor.validate_weight_input(weight_input)
            assert validation_result.is_valid
            assert len(validation_result.errors) == 0
        
        # Test invalid weights
        invalid_weights = [
            "",
            "invalid",
            "-5 kg",
            "0 kg",
            "abc xyz"
        ]
        
        for weight_input in invalid_weights:
            validation_result = processor.validate_weight_input(weight_input)
            assert not validation_result.is_valid
            assert len(validation_result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_weight_conversion_integration(self, test_app):
        """Test weight conversion integration"""
        from src.services.weight_processor import WeightProcessor, WeightUnit
        
        processor = WeightProcessor()
        
        # Test conversions
        conversion_tests = [
            {
                "value": Decimal('1'),
                "from_unit": WeightUnit.KILOGRAM,
                "to_unit": WeightUnit.POUND,
                "expected_approx": Decimal('2.204')
            },
            {
                "value": Decimal('1000'),
                "from_unit": WeightUnit.GRAM,
                "to_unit": WeightUnit.KILOGRAM,
                "expected_approx": Decimal('1')
            },
            {
                "value": Decimal('16'),
                "from_unit": WeightUnit.OUNCE,
                "to_unit": WeightUnit.POUND,
                "expected_approx": Decimal('1')
            }
        ]
        
        for test in conversion_tests:
            result = processor.convert_weight(
                test["value"],
                test["from_unit"],
                test["to_unit"]
            )
            
            assert abs(result.converted_value - test["expected_approx"]) < Decimal('0.01')
            assert result.original_unit == test["from_unit"]
            assert result.converted_unit == test["to_unit"]


@pytest.mark.integration
@pytest.mark.ai_required
class TestAIIntegration:
    """Test AI integration scenarios (requires real API keys)"""
    
    @pytest.mark.asyncio
    async def test_ai_provider_integration(self, test_app, enable_ai_providers):
        """Test AI provider integration"""
        # Test with AI providers enabled
        response = test_app.post(
            "/api/compare?service_mode=fast_validation",
            json={
                "weight_input": "5 kg",
                "style": "creative"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # With AI providers, should potentially use AI
        assert "comparison_text" in data
        assert "provider_used" in data
        # Provider could be AI or fallback depending on availability
        assert data["provider_used"] in ["openai", "anthropic", "xai", "fallback"]
    
    @pytest.mark.asyncio
    async def test_ai_fallback_integration(self, test_app, disable_ai_providers):
        """Test AI fallback integration"""
        # Test with AI providers disabled
        response = test_app.post(
            "/api/compare?service_mode=fast_validation",
            json={
                "weight_input": "5 kg",
                "style": "creative"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Without AI providers, should use fallback
        assert "comparison_text" in data
        assert data["provider_used"] == "fallback"
    
    @pytest.mark.asyncio
    async def test_ai_provider_selection_integration(self, test_app, enable_ai_providers):
        """Test AI provider selection integration"""
        # Test with specific provider
        response = test_app.post(
            "/api/compare",
            json={
                "weight_input": "5 kg",
                "style": "default",
                "provider": "openai"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should prefer specified provider or fall back
        assert data["provider_used"] in ["openai", "fallback"]


@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceIntegration:
    """Test performance integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_response_time_integration(self, test_app):
        """Test response time integration"""
        import time
        
        # Test response time for different service modes
        service_modes = ["basic", "fast_validation", "full_validation"]
        
        for mode in service_modes:
            start_time = time.time()
            
            response = test_app.post(
                f"/api/compare?service_mode={mode}",
                json={
                    "weight_input": "5 kg",
                    "style": "default"
                }
            )
            
            end_time = time.time()
            actual_time_ms = (end_time - start_time) * 1000
            
            assert response.status_code == 200
            data = response.json()
            
            # Check response time is reasonable
            if mode == "basic":
                assert actual_time_ms < 1000  # Basic should be very fast
            elif mode == "fast_validation":
                assert actual_time_ms < 3000  # Fast validation should be fast
            
            # Check reported response time
            assert data["response_time_ms"] > 0
            assert data["response_time_ms"] < 10000  # Should be reasonable
    
    @pytest.mark.asyncio
    async def test_throughput_integration(self, test_app):
        """Test throughput integration"""
        import time
        import concurrent.futures
        
        def make_request():
            return test_app.post(
                "/api/compare?service_mode=basic",
                json={
                    "weight_input": "5 kg",
                    "style": "default"
                }
            )
        
        # Test throughput with 10 concurrent requests
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Should handle 10 requests reasonably fast
        assert total_time < 10  # 10 seconds max for 10 requests
        
        # Calculate throughput (requests per second)
        throughput = 10 / total_time
        assert throughput > 1  # At least 1 request per second
    
    @pytest.mark.asyncio
    async def test_memory_usage_integration(self, test_app):
        """Test memory usage integration"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make multiple requests
        for i in range(20):
            response = test_app.post(
                "/api/compare?service_mode=basic",
                json={
                    "weight_input": f"{i+1} kg",
                    "style": "default"
                }
            )
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 50MB)
        assert memory_increase < 50 * 1024 * 1024  # 50MB


@pytest.mark.integration
class TestErrorRecoveryIntegration:
    """Test error recovery integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_service_failure_recovery(self, test_app):
        """Test service failure recovery"""
        # Test that system recovers from various failures
        
        # Test with malformed request
        response = test_app.post(
            "/api/compare",
            json={"malformed": "request"}
        )
        assert response.status_code == 422
        
        # Test that subsequent valid requests still work
        response = test_app.post(
            "/api/compare",
            json={
                "weight_input": "5 kg",
                "style": "default"
            }
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_timeout_recovery(self, test_app):
        """Test timeout recovery"""
        # Test that system handles timeouts gracefully
        
        # This would require mocking timeouts, but we can test
        # that the system continues to work after errors
        for i in range(5):
            response = test_app.post(
                "/api/compare?service_mode=basic",
                json={
                    "weight_input": f"{i+1} kg",
                    "style": "default"
                }
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_partial_system_failure_recovery(self, test_app, disable_ai_providers):
        """Test partial system failure recovery"""
        # Test that system works even when AI providers are unavailable
        
        # Test all service modes fall back gracefully
        service_modes = ["basic", "fast_validation", "full_validation", "comprehensive"]
        
        for mode in service_modes:
            response = test_app.post(
                f"/api/compare?service_mode={mode}",
                json={
                    "weight_input": "5 kg",
                    "style": "default"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "comparison_text" in data
            # Should fall back to basic provider
            assert data["provider_used"] == "fallback"