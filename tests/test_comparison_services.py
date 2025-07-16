"""
Comprehensive tests for comparison services.

This module consolidates tests for all comparison services including
MVP, fast validation, AI validation, and their shared components.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from src.services.mvp_comparison import MVPComparisonService
from src.services.fast_validation_service import FastValidationService
from src.services.ai_validation_service import AIValidationService
from src.services.shared.interfaces import BaseComparisonService
from src.models.mvp import MVPComparisonRequest, MVPComparisonResponse


class TestMVPComparisonService:
    """Test the MVP comparison service (fallback service)"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.service = MVPComparisonService()
    
    @pytest.mark.asyncio
    async def test_basic_comparison(self, sample_mvp_request):
        """Test basic comparison functionality"""
        response = await self.service.create_comparison(sample_mvp_request)
        
        assert isinstance(response, MVPComparisonResponse)
        assert response.comparison_text
        assert response.weight_processed
        assert response.provider_used == "fallback"
        assert response.response_time_ms > 0
        assert response.cached is False
    
    @pytest.mark.asyncio
    async def test_multiple_weight_formats(self):
        """Test various weight input formats"""
        test_cases = [
            "5 kg",
            "10 pounds",
            "100 grams",
            "2.5 lbs",
            "1 ounce",
            "1000 g"
        ]
        
        for weight_input in test_cases:
            request = MVPComparisonRequest(weight_input=weight_input)
            response = await self.service.create_comparison(request)
            
            assert response.comparison_text
            assert response.weight_processed
            assert weight_input.split()[1] in response.weight_processed.lower() or \
                   weight_input.split()[1] in ["lbs", "pounds"] and "lb" in response.weight_processed.lower()
    
    @pytest.mark.asyncio
    async def test_comparison_styles(self, sample_mvp_request):
        """Test different comparison styles"""
        styles = ["default", "creative", "technical"]
        
        for style in styles:
            request = MVPComparisonRequest(
                weight_input=sample_mvp_request.weight_input,
                style=style
            )
            response = await self.service.create_comparison(request)
            
            assert response.comparison_text
            # Different styles should produce different outputs
            assert len(response.comparison_text) > 10
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for invalid inputs"""
        invalid_requests = [
            MVPComparisonRequest(weight_input=""),
            MVPComparisonRequest(weight_input="invalid"),
            MVPComparisonRequest(weight_input="-5 kg"),
            MVPComparisonRequest(weight_input="0 kg")
        ]
        
        for request in invalid_requests:
            with pytest.raises(Exception):
                await self.service.create_comparison(request)
    
    def test_health_status(self):
        """Test service health status"""
        health = self.service.get_health_status()
        
        assert "status" in health
        assert health["status"] == "healthy"
        assert "capabilities" in health
        assert "performance" in health
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, sample_mvp_request):
        """Test performance metrics"""
        # Make multiple requests to test metrics
        for _ in range(3):
            await self.service.create_comparison(sample_mvp_request)
        
        health = self.service.get_health_status()
        assert "performance" in health
        assert "total_requests" in health["performance"]
        assert health["performance"]["total_requests"] >= 3


class TestFastValidationService:
    """Test the fast validation service"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.service = FastValidationService()
    
    @pytest.mark.asyncio
    async def test_fast_validation_basic(self, sample_mvp_request):
        """Test basic fast validation functionality"""
        response = await self.service.create_comparison(sample_mvp_request)
        
        assert isinstance(response, MVPComparisonResponse)
        assert response.comparison_text
        assert response.weight_processed
        assert response.response_time_ms > 0
        # Fast validation should be reasonably fast
        assert response.response_time_ms < 3000
    
    @pytest.mark.asyncio
    async def test_ai_fallback_behavior(self, sample_mvp_request, disable_ai_providers):
        """Test fallback behavior when AI providers are unavailable"""
        response = await self.service.create_comparison(sample_mvp_request)
        
        # Should fall back to basic comparison
        assert response.comparison_text
        assert response.provider_used == "fallback"
    
    @pytest.mark.ai_required
    @pytest.mark.asyncio
    async def test_ai_integration(self, sample_mvp_request, enable_ai_providers):
        """Test AI integration when providers are available"""
        response = await self.service.create_comparison(sample_mvp_request)
        
        assert response.comparison_text
        # With AI providers, should use AI
        assert response.provider_used in ["openai", "anthropic", "xai"]
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, sample_mvp_request):
        """Test timeout handling"""
        # Test with very short timeout
        with patch.object(self.service, '_timeout_seconds', 0.001):
            response = await self.service.create_comparison(sample_mvp_request)
            # Should still get response via fallback
            assert response.comparison_text
    
    def test_service_capabilities(self):
        """Test service capabilities"""
        health = self.service.get_health_status()
        
        assert "capabilities" in health
        capabilities = health["capabilities"]
        assert "supports_ai" in capabilities
        assert "average_response_time_ms" in capabilities
        assert "fallback_available" in capabilities
        assert capabilities["fallback_available"] is True


class TestAIValidationService:
    """Test the AI validation service"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.service = AIValidationService()
    
    @pytest.mark.asyncio
    async def test_ai_validation_basic(self, sample_mvp_request):
        """Test basic AI validation functionality"""
        response = await self.service.create_comparison(sample_mvp_request)
        
        assert isinstance(response, MVPComparisonResponse)
        assert response.comparison_text
        assert response.weight_processed
        assert response.response_time_ms > 0
    
    @pytest.mark.ai_required
    @pytest.mark.asyncio
    async def test_ai_quality_validation(self, sample_mvp_request, enable_ai_providers):
        """Test AI quality validation"""
        response = await self.service.create_comparison(sample_mvp_request)
        
        # AI validation should provide higher quality responses
        assert len(response.comparison_text) > 50
        assert response.provider_used in ["openai", "anthropic", "xai"]
    
    @pytest.mark.asyncio
    async def test_complex_comparisons(self, enable_ai_providers):
        """Test complex comparison scenarios"""
        complex_requests = [
            MVPComparisonRequest(
                weight_input="1.5 tons",
                style="technical"
            ),
            MVPComparisonRequest(
                weight_input="0.5 grams",
                style="creative"
            ),
            MVPComparisonRequest(
                weight_input="100 kg",
                style="default"
            )
        ]
        
        for request in complex_requests:
            response = await self.service.create_comparison(request)
            assert response.comparison_text
            assert response.weight_processed
    
    @pytest.mark.asyncio
    async def test_provider_selection(self, sample_mvp_request, enable_ai_providers):
        """Test AI provider selection"""
        # Test with specific provider
        request = MVPComparisonRequest(
            weight_input=sample_mvp_request.weight_input,
            provider="openai"
        )
        response = await self.service.create_comparison(request)
        
        assert response.comparison_text
        # Should prefer specified provider if available
        assert response.provider_used in ["openai", "fallback"]
    
    def test_validation_capabilities(self):
        """Test validation capabilities"""
        health = self.service.get_health_status()
        
        assert "validation" in health
        validation_info = health["validation"]
        assert "quality_checks" in validation_info
        assert "ai_providers" in validation_info


class TestBaseComparisonService:
    """Test the base comparison service interface"""
    
    def test_interface_compliance(self):
        """Test that all services implement the base interface"""
        services = [
            MVPComparisonService(),
            FastValidationService(),
            AIValidationService()
        ]
        
        for service in services:
            assert isinstance(service, BaseComparisonService)
            assert hasattr(service, 'create_comparison')
            assert hasattr(service, 'get_health_status')
    
    @pytest.mark.asyncio
    async def test_service_polymorphism(self, sample_mvp_request):
        """Test that all services can be used polymorphically"""
        services = [
            MVPComparisonService(),
            FastValidationService(),
            AIValidationService()
        ]
        
        for service in services:
            response = await service.create_comparison(sample_mvp_request)
            assert isinstance(response, MVPComparisonResponse)
            assert response.comparison_text
            assert response.weight_processed
    
    def test_health_status_consistency(self):
        """Test health status consistency across services"""
        services = [
            MVPComparisonService(),
            FastValidationService(),
            AIValidationService()
        ]
        
        required_keys = ["status", "capabilities", "performance"]
        
        for service in services:
            health = service.get_health_status()
            for key in required_keys:
                assert key in health, f"Service {type(service).__name__} missing {key}"


class TestSharedComponents:
    """Test shared components used by comparison services"""
    
    @pytest.mark.asyncio
    async def test_weight_processing_integration(self):
        """Test weight processing integration"""
        from src.services.weight_processor import WeightProcessor
        
        processor = WeightProcessor()
        
        test_weights = [
            "5 kg",
            "10 pounds",
            "100 grams",
            "2.5 lbs"
        ]
        
        for weight_input in test_weights:
            processed = processor.process_weight(weight_input)
            assert processed.weight_kg > 0
            assert processed.unit_used
            assert processed.confidence > 0
    
    @pytest.mark.asyncio
    async def test_fallback_data_integration(self):
        """Test fallback data integration"""
        from src.services.shared.fallback_data import FallbackDataProvider
        
        provider = FallbackDataProvider()
        
        test_weights = [0.1, 1.0, 10.0, 100.0, 1000.0]
        
        for weight_kg in test_weights:
            comparison = provider.get_comparison_for_weight(weight_kg)
            assert comparison
            assert len(comparison) > 10
    
    @pytest.mark.asyncio
    async def test_ai_provider_manager_integration(self):
        """Test AI provider manager integration"""
        from src.services.shared.ai_provider_manager import AIProviderManager
        
        manager = AIProviderManager()
        
        # Test provider availability
        availability = manager.get_provider_availability()
        assert isinstance(availability, dict)
        
        # Test provider selection
        selected = manager.select_optimal_provider(weight_kg=5.0)
        assert selected  # Should always return a provider (even if fallback)


class TestServicePerformance:
    """Test service performance characteristics"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_mvp_service_performance(self, sample_mvp_request):
        """Test MVP service performance"""
        service = MVPComparisonService()
        
        # Test response time
        start_time = asyncio.get_event_loop().time()
        response = await service.create_comparison(sample_mvp_request)
        end_time = asyncio.get_event_loop().time()
        
        actual_time_ms = (end_time - start_time) * 1000
        
        # MVP service should be very fast
        assert actual_time_ms < 1000  # < 1 second
        assert response.response_time_ms < 1000
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_fast_validation_performance(self, sample_mvp_request):
        """Test fast validation service performance"""
        service = FastValidationService()
        
        start_time = asyncio.get_event_loop().time()
        response = await service.create_comparison(sample_mvp_request)
        end_time = asyncio.get_event_loop().time()
        
        actual_time_ms = (end_time - start_time) * 1000
        
        # Fast validation should meet 2-second target
        assert actual_time_ms < 3000  # < 3 seconds (with buffer)
        assert response.response_time_ms < 3000
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, sample_mvp_requests):
        """Test concurrent request handling"""
        service = MVPComparisonService()
        
        # Test concurrent requests
        tasks = []
        for request in sample_mvp_requests[:3]:  # Test with 3 concurrent requests
            task = asyncio.create_task(service.create_comparison(request))
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All requests should complete successfully
        assert len(responses) == 3
        for response in responses:
            assert response.comparison_text
            assert response.weight_processed
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_usage(self, sample_mvp_request):
        """Test memory usage during operation"""
        import psutil
        import os
        
        service = MVPComparisonService()
        process = psutil.Process(os.getpid())
        
        # Measure initial memory
        initial_memory = process.memory_info().rss
        
        # Make multiple requests
        for _ in range(10):
            await service.create_comparison(sample_mvp_request)
        
        # Measure final memory
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 10MB)
        assert memory_increase < 10 * 1024 * 1024  # 10MB


class TestErrorHandling:
    """Test error handling across services"""
    
    @pytest.mark.asyncio
    async def test_invalid_weight_handling(self):
        """Test handling of invalid weight inputs"""
        services = [
            MVPComparisonService(),
            FastValidationService(),
            AIValidationService()
        ]
        
        invalid_inputs = [
            "",
            "invalid",
            "-5 kg",
            "0 kg",
            "abc kg"
        ]
        
        for service in services:
            for invalid_input in invalid_inputs:
                request = MVPComparisonRequest(weight_input=invalid_input)
                
                with pytest.raises(Exception):
                    await service.create_comparison(request)
    
    @pytest.mark.asyncio
    async def test_service_failure_recovery(self, sample_mvp_request):
        """Test service failure recovery"""
        service = FastValidationService()
        
        # Mock AI provider failure
        with patch.object(service, '_use_ai_provider', side_effect=Exception("AI provider failed")):
            response = await service.create_comparison(sample_mvp_request)
            
            # Should fall back to basic comparison
            assert response.comparison_text
            assert response.provider_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_timeout_recovery(self, sample_mvp_request):
        """Test timeout recovery"""
        service = FastValidationService()
        
        # Mock timeout
        with patch.object(service, '_timeout_seconds', 0.001):
            response = await service.create_comparison(sample_mvp_request)
            
            # Should still get response via fallback
            assert response.comparison_text
    
    @pytest.mark.asyncio
    async def test_partial_service_failure(self, sample_mvp_request):
        """Test partial service failure handling"""
        service = AIValidationService()
        
        # Mock partial failure (e.g., one AI provider fails)
        with patch.object(service, '_primary_provider_available', return_value=False):
            response = await service.create_comparison(sample_mvp_request)
            
            # Should still work with fallback
            assert response.comparison_text