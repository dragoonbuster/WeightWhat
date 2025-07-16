"""
Comprehensive tests for the unified SizeComparator application.

This test module consolidates testing for the unified architecture,
including service factory, unified app, and end-to-end functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from decimal import Decimal

from src.api.unified_app import UnifiedSizeComparatorApp, ServiceMode, create_unified_app
from src.services.shared.service_factory import ComparisonServiceFactory, ServiceType, PerformanceProfile, ServiceRequirements
from src.core.environment import EnvironmentManager, EnvironmentType
from src.models.mvp import MVPComparisonRequest, MVPComparisonResponse


class TestUnifiedApplication:
    """Test the unified application functionality"""
    
    def test_app_initialization(self, test_env_manager):
        """Test unified app initialization"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        
        assert app_instance.env_manager is not None
        assert app_instance.service_factory is not None
        assert app_instance.config is not None
        assert app_instance.config["title"] == "SizeComparator Unified API"
        assert app_instance.config["version"] == "1.0.0"
        assert app_instance.config["default_service_mode"] == ServiceMode.FAST_VALIDATION
    
    def test_service_mode_mapping(self, test_env_manager):
        """Test service mode to service type mapping"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        
        # Test all service modes are defined
        assert ServiceMode.BASIC == "basic"
        assert ServiceMode.FAST_VALIDATION == "fast_validation"
        assert ServiceMode.FULL_VALIDATION == "full_validation"
        assert ServiceMode.COMPREHENSIVE == "comprehensive"
    
    def test_config_loading(self, test_env_manager):
        """Test configuration loading"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        config = app_instance.config
        
        # Check required config keys
        assert "title" in config
        assert "version" in config
        assert "default_service_mode" in config
        assert "serve_frontend" in config
        assert "frontend_path" in config
        assert "cors_origins" in config
        
        # Check environment-specific settings
        if test_env_manager.environment == EnvironmentType.DEVELOPMENT:
            assert config["cors_origins"] == ["*"]
        else:
            assert config["cors_origins"] == []
    
    def test_fastapi_app_creation(self, test_env_manager):
        """Test FastAPI app creation"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        fastapi_app = app_instance.create_app()
        
        assert fastapi_app is not None
        assert fastapi_app.title == "SizeComparator Unified API"
        assert fastapi_app.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_service_mode_determination(self, test_env_manager, sample_mvp_request):
        """Test service mode determination logic"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        
        # Test explicit query mode
        mode = await app_instance._determine_service_mode(
            query_mode=ServiceMode.BASIC,
            header_mode=None,
            performance_profile=None,
            request_data=sample_mvp_request,
            timeout_ms=None
        )
        assert mode == ServiceMode.BASIC
        
        # Test header mode
        mode = await app_instance._determine_service_mode(
            query_mode=None,
            header_mode=ServiceMode.FULL_VALIDATION,
            performance_profile=None,
            request_data=sample_mvp_request,
            timeout_ms=None
        )
        assert mode == ServiceMode.FULL_VALIDATION
        
        # Test performance profile selection
        mode = await app_instance._determine_service_mode(
            query_mode=None,
            header_mode=None,
            performance_profile=PerformanceProfile.SPEED_OPTIMIZED,
            request_data=sample_mvp_request,
            timeout_ms=1500
        )
        assert mode in [ServiceMode.BASIC, ServiceMode.FAST_VALIDATION]
    
    @pytest.mark.asyncio
    async def test_service_creation_and_caching(self, test_env_manager):
        """Test service creation and caching"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        
        # Test service creation
        service1 = await app_instance._get_service_for_mode(ServiceMode.BASIC)
        assert service1 is not None
        
        # Test caching
        service2 = await app_instance._get_service_for_mode(ServiceMode.BASIC)
        assert service2 is service1  # Should be same instance due to caching
        
        # Test different service types
        for mode in ServiceMode:
            service = await app_instance._get_service_for_mode(mode)
            assert service is not None
    
    @pytest.mark.asyncio
    async def test_health_check(self, test_env_manager):
        """Test health check functionality"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        
        health_status = await app_instance._get_health_status()
        
        assert "status" in health_status
        assert "service_factory" in health_status
        assert "metrics" in health_status
        assert "version" in health_status
        assert health_status["version"] == "1.0.0"


class TestUnifiedAppAPI:
    """Test the unified app API endpoints"""
    
    @pytest.fixture
    def test_client(self, test_env_manager):
        """Create test client for API testing"""
        app = create_unified_app(test_env_manager)
        return TestClient(app)
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "service_factory" in data
        assert "metrics" in data
    
    def test_status_endpoint(self, test_client):
        """Test status endpoint"""
        response = test_client.get("/api/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "service_factory" in data
        assert "app_metrics" in data
    
    def test_demo_endpoint(self, test_client):
        """Test demo endpoint"""
        response = test_client.get("/api/demo")
        assert response.status_code == 200
        
        data = response.json()
        assert "service_modes" in data
        assert "examples" in data
        assert "performance_profiles" in data
        assert len(data["service_modes"]) == 4
    
    def test_demo_page_endpoints(self, test_client):
        """Test demo page endpoints"""
        for mode in ServiceMode:
            response = test_client.get(f"/demo/{mode.value}")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
    
    @pytest.mark.asyncio
    async def test_unified_compare_endpoint(self, test_client, sample_mvp_request):
        """Test unified compare endpoint"""
        response = test_client.post(
            "/api/compare",
            json=sample_mvp_request.dict()
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "comparison_text" in data
        assert "weight_processed" in data
        assert "provider_used" in data
        assert "response_time_ms" in data
    
    @pytest.mark.asyncio
    async def test_unified_compare_with_service_mode(self, test_client, sample_mvp_request):
        """Test unified compare with explicit service mode"""
        response = test_client.post(
            "/api/compare?service_mode=basic",
            json=sample_mvp_request.dict()
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "comparison_text" in data
        # Check that basic mode was used in headers
        assert "X-Service-Mode" in response.headers
    
    @pytest.mark.asyncio
    async def test_unified_compare_with_headers(self, test_client, sample_mvp_request):
        """Test unified compare with headers"""
        response = test_client.post(
            "/api/compare",
            json=sample_mvp_request.dict(),
            headers={
                "X-Service-Mode": "fast_validation",
                "X-Performance-Profile": "speed_optimized"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "comparison_text" in data
    
    def test_legacy_endpoints(self, test_client, sample_mvp_request):
        """Test legacy endpoint compatibility"""
        # Test legacy single compare
        response = test_client.post(
            "/api/compare/single",
            json=sample_mvp_request.dict()
        )
        assert response.status_code == 200
        
        # Test legacy validated compare
        response = test_client.post(
            "/api/compare/validated",
            json=sample_mvp_request.dict()
        )
        assert response.status_code == 200
        
        # Test legacy fast compare
        response = test_client.post(
            "/api/compare/fast",
            json=sample_mvp_request.dict()
        )
        assert response.status_code == 200
    
    def test_error_handling(self, test_client):
        """Test error handling"""
        # Test 404 error
        response = test_client.get("/nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        assert "available_endpoints" in data
        
        # Test invalid request
        response = test_client.post("/api/compare", json={})
        assert response.status_code == 422  # Validation error


class TestServiceFactory:
    """Test the service factory functionality"""
    
    def test_factory_initialization(self, test_env_manager):
        """Test service factory initialization"""
        factory = ComparisonServiceFactory(test_env_manager)
        
        assert factory.env_manager is not None
        assert factory.service_capabilities is not None
        assert factory.performance_config is not None
        assert len(factory.service_capabilities) == 4
    
    def test_service_capabilities(self, test_env_manager):
        """Test service capabilities definition"""
        factory = ComparisonServiceFactory(test_env_manager)
        capabilities = factory.service_capabilities
        
        # Check all service types are defined
        for service_type in ServiceType:
            assert service_type in capabilities
            cap = capabilities[service_type]
            assert cap.avg_response_time_ms > 0
            assert 0 <= cap.accuracy_score <= 1
            assert cap.resource_intensity >= 1
    
    def test_basic_service_creation(self, test_env_manager):
        """Test basic service creation"""
        factory = ComparisonServiceFactory(test_env_manager)
        service = factory.create_basic_service()
        
        assert service is not None
        # Basic service should always be available
        assert hasattr(service, 'create_comparison')
    
    def test_service_selection_logic(self, test_env_manager):
        """Test intelligent service selection"""
        factory = ComparisonServiceFactory(test_env_manager)
        
        # Test speed-optimized selection
        requirements = ServiceRequirements(
            weight_kg=1.0,
            timeout_ms=1000,
            performance_profile=PerformanceProfile.SPEED_OPTIMIZED
        )
        service = factory.get_optimal_service(requirements)
        assert service is not None
        
        # Test accuracy-optimized selection
        requirements = ServiceRequirements(
            weight_kg=100.0,
            timeout_ms=8000,
            performance_profile=PerformanceProfile.ACCURACY_OPTIMIZED
        )
        service = factory.get_optimal_service(requirements)
        assert service is not None
        
        # Test balanced selection
        requirements = ServiceRequirements(
            weight_kg=5.0,
            timeout_ms=3000,
            performance_profile=PerformanceProfile.BALANCED
        )
        service = factory.get_optimal_service(requirements)
        assert service is not None
    
    def test_weight_based_selection(self, test_env_manager):
        """Test weight-based service selection"""
        factory = ComparisonServiceFactory(test_env_manager)
        
        # Test with different weight ranges
        test_weights = [
            ("0.1 kg", "light"),
            ("5 kg", "common"),
            ("100 kg", "heavy"),
            ("1000 kg", "extreme")
        ]
        
        for weight_input, description in test_weights:
            from src.models.mvp import MVPComparisonRequest
            request = MVPComparisonRequest(weight_input=weight_input)
            service = factory.get_service_from_request(request)
            assert service is not None
    
    def test_service_availability_checking(self, test_env_manager):
        """Test service availability checking"""
        factory = ComparisonServiceFactory(test_env_manager)
        
        # Basic service should always be available
        assert factory._is_service_available(ServiceType.BASIC) is True
        
        # Check all service types
        for service_type in ServiceType:
            availability = factory._is_service_available(service_type)
            assert isinstance(availability, bool)
    
    def test_fallback_logic(self, test_env_manager):
        """Test fallback service selection"""
        factory = ComparisonServiceFactory(test_env_manager)
        
        # Test fallback chain
        fallback_map = {
            ServiceType.COMPREHENSIVE: ServiceType.FULL_VALIDATION,
            ServiceType.FULL_VALIDATION: ServiceType.FAST_VALIDATION,
            ServiceType.FAST_VALIDATION: ServiceType.BASIC,
            ServiceType.BASIC: ServiceType.BASIC
        }
        
        for preferred, expected_fallback in fallback_map.items():
            fallback = factory._get_fallback_service_type(preferred)
            assert fallback == expected_fallback or fallback == ServiceType.BASIC
    
    def test_health_status(self, test_env_manager):
        """Test factory health status"""
        factory = ComparisonServiceFactory(test_env_manager)
        health = factory.get_service_health_status()
        
        assert "factory_status" in health
        assert "services" in health
        assert "availability" in health
        assert "performance_config" in health
        assert health["factory_status"] == "healthy"
    
    def test_cache_management(self, test_env_manager):
        """Test availability cache management"""
        factory = ComparisonServiceFactory(test_env_manager)
        
        # Clear cache
        factory.clear_availability_cache()
        assert len(factory._service_availability_cache) == 0
        
        # Check availability (should populate cache)
        factory._is_service_available(ServiceType.BASIC)
        assert len(factory._service_availability_cache) > 0


class TestConvenienceFunctions:
    """Test convenience functions for service creation"""
    
    def test_create_service_for_weight(self, test_env_manager):
        """Test weight-based service creation"""
        from src.services.shared.service_factory import create_service_for_weight
        
        service = create_service_for_weight("5 kg", env_manager=test_env_manager)
        assert service is not None
        assert hasattr(service, 'create_comparison')
    
    def test_create_fast_service(self, test_env_manager):
        """Test fast service creation"""
        from src.services.shared.service_factory import create_fast_service
        
        service = create_fast_service(env_manager=test_env_manager)
        assert service is not None
        assert hasattr(service, 'create_comparison')
    
    def test_create_accurate_service(self, test_env_manager):
        """Test accurate service creation"""
        from src.services.shared.service_factory import create_accurate_service
        
        service = create_accurate_service(env_manager=test_env_manager)
        assert service is not None
        assert hasattr(service, 'create_comparison')
    
    def test_create_default_service(self, test_env_manager):
        """Test default service creation"""
        from src.services.shared.service_factory import create_default_service
        
        service = create_default_service(env_manager=test_env_manager)
        assert service is not None
        assert hasattr(service, 'create_comparison')
    
    def test_global_factory(self, test_env_manager):
        """Test global factory singleton"""
        from src.services.shared.service_factory import get_global_factory, reset_global_factory
        
        # Reset to ensure clean state
        reset_global_factory()
        
        # Get factory
        factory1 = get_global_factory(test_env_manager)
        factory2 = get_global_factory(test_env_manager)
        
        # Should be same instance
        assert factory1 is factory2
        
        # Reset and test again
        reset_global_factory()
        factory3 = get_global_factory(test_env_manager)
        assert factory3 is not factory1


@pytest.mark.integration
class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_complete_comparison_flow(self, test_env_manager, sample_mvp_requests):
        """Test complete comparison flow from request to response"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        
        for request in sample_mvp_requests:
            try:
                # Get service
                service = await app_instance._get_service_for_mode(ServiceMode.BASIC)
                
                # Process request
                response = await service.create_comparison(request)
                
                # Validate response
                assert isinstance(response, MVPComparisonResponse)
                assert response.comparison_text
                assert response.weight_processed
                assert response.provider_used
                assert response.response_time_ms > 0
                
            except Exception as e:
                pytest.fail(f"Complete flow failed for {request.weight_input}: {e}")
    
    @pytest.mark.asyncio
    async def test_service_mode_switching(self, test_env_manager, sample_mvp_request):
        """Test switching between service modes"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        
        # Test all service modes
        for mode in ServiceMode:
            try:
                service = await app_instance._get_service_for_mode(mode)
                response = await service.create_comparison(sample_mvp_request)
                
                assert response.comparison_text
                assert response.weight_processed
                
            except Exception as e:
                pytest.fail(f"Service mode {mode.value} failed: {e}")
    
    @pytest.mark.asyncio
    async def test_fallback_behavior(self, test_env_manager, sample_mvp_request, disable_ai_providers):
        """Test fallback behavior when AI providers are unavailable"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        
        # Even without AI providers, basic service should work
        service = await app_instance._get_service_for_mode(ServiceMode.BASIC)
        response = await service.create_comparison(sample_mvp_request)
        
        assert response.comparison_text
        assert response.weight_processed
        assert response.provider_used == "fallback"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_requirements(self, test_env_manager, performance_test_weights):
        """Test performance requirements across weight ranges"""
        app_instance = UnifiedSizeComparatorApp(test_env_manager)
        
        for weight_input in performance_test_weights:
            request = MVPComparisonRequest(weight_input=weight_input)
            
            # Test fast service meets speed requirements
            service = await app_instance._get_service_for_mode(ServiceMode.FAST_VALIDATION)
            
            start_time = asyncio.get_event_loop().time()
            response = await service.create_comparison(request)
            end_time = asyncio.get_event_loop().time()
            
            actual_time_ms = (end_time - start_time) * 1000
            
            # Fast validation should be reasonably fast
            assert actual_time_ms < 5000  # 5 seconds max
            assert response.comparison_text
    
    def test_api_documentation_generation(self, test_env_manager):
        """Test API documentation generation"""
        app = create_unified_app(test_env_manager)
        
        # Check that OpenAPI schema is generated
        openapi_schema = app.openapi()
        assert openapi_schema is not None
        assert "info" in openapi_schema
        assert "paths" in openapi_schema
        
        # Check main endpoints are documented
        assert "/api/compare" in openapi_schema["paths"]
        assert "/health" in openapi_schema["paths"]
        assert "/api/status" in openapi_schema["paths"]