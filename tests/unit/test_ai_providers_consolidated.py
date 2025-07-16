"""
Consolidated unit tests for AI providers.

This module consolidates tests for OpenAI, Anthropic, and XAI providers
including their configurations, responses, and error handling.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from uuid import uuid4

from src.providers.openai_provider import (
    OpenAIProvider,
    OpenAIRateLimiter,
    TokenUsageTracker,
    ResponseCache
)
from src.providers.anthropic_provider import AnthropicProvider, ClaudeModel
from src.providers.anthropic_config import AnthropicConfigBuilder, AnthropicModel
from src.providers.xai_provider import XAIProvider
from src.providers.base import ProviderError, ValidationError, BaseAIProvider
from src.models.providers import AIProviderRequest, TemplateVariables
from src.models.requests import WeightComparisonRequest
from src.models.weight import WeightInput
from src.core.exceptions import AIProviderException, AIProviderRateLimitException


class TestOpenAIProvider:
    """Test cases for OpenAI Provider"""
    
    @pytest.fixture
    def provider_config(self):
        """Provider configuration for testing"""
        return {
            "api_key": "sk-test-key-for-unit-tests",
            "endpoint": "https://api.openai.com/v1",
            "model": "gpt-4",
            "timeout_seconds": 30.0,
            "max_tokens": 500,
            "temperature": 0.3,
            "rate_limit_rpm": 100,
            "max_retries": 2,
            "structured_output": True,
            "enable_caching": True,
            "cache_ttl_seconds": 300
        }
    
    @pytest.fixture
    def provider(self, provider_config, mock_logger):
        """OpenAI provider instance for testing"""
        return OpenAIProvider(provider_config, mock_logger)
    
    @pytest.fixture
    def sample_request(self):
        """Sample AI provider request"""
        template_variables = TemplateVariables(
            item1_name="Test Item 1",
            item1_weight="5 kg",
            item2_name="Test Item 2",
            item2_weight="10 kg",
            weight_ratio=0.5,
            percentage_difference=100.0,
            heavier_item="item2",
            comparison_category="test",
            significance_level="moderate",
            output_unit="kg",
            locale="en-US"
        )
        
        return AIProviderRequest(
            prompt_template_id="test_template",
            template_variables=template_variables.dict(),
            weight_data={
                "item1": {"name": "Test Item 1", "weight": "5 kg"},
                "item2": {"name": "Test Item 2", "weight": "10 kg"}
            },
            max_tokens=300,
            temperature=0.2,
            timeout_seconds=20.0,
            request_id=uuid4()
        )
    
    def test_provider_initialization(self, provider_config, mock_logger):
        """Test provider initialization"""
        provider = OpenAIProvider(provider_config, mock_logger)
        
        assert provider.name == "OpenAI"
        assert provider.api_key == "sk-test-key-for-unit-tests"
        assert provider.model == "gpt-4"
        assert provider.structured_output is True
        assert provider.enable_caching is True
        assert isinstance(provider.rate_limiter, OpenAIRateLimiter)
        assert isinstance(provider.token_tracker, TokenUsageTracker)
        assert isinstance(provider.response_cache, ResponseCache)
    
    def test_supports_structured_output(self, provider):
        """Test structured output support detection"""
        provider.model = "gpt-4"
        assert provider._supports_structured_output() is True
        
        provider.model = "gpt-3.5-turbo"
        assert provider._supports_structured_output() is True
        
        provider.model = "unknown-model"
        assert provider._supports_structured_output() is False
    
    @pytest.mark.asyncio
    async def test_get_system_prompt(self, provider):
        """Test system prompt generation"""
        prompt = await provider._get_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "weight comparison expert" in prompt.lower()
        assert "json" in prompt.lower()
        assert "accuracy" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_get_optimized_prompt(self, provider, sample_request):
        """Test optimized prompt generation"""
        prompt = await provider._get_optimized_prompt(sample_request)
        
        assert isinstance(prompt, str)
        assert "Test Item 1" in prompt
        assert "Test Item 2" in prompt
        assert "5 kg" in prompt
        assert "10 kg" in prompt
        assert "JSON" in prompt
    
    @pytest.mark.asyncio
    async def test_build_openai_request(self, provider, sample_request):
        """Test OpenAI request building"""
        openai_request = await provider._build_openai_request(sample_request)
        
        assert openai_request["model"] == "gpt-4"
        assert len(openai_request["messages"]) == 2
        assert openai_request["messages"][0]["role"] == "system"
        assert openai_request["messages"][1]["role"] == "user"
        assert openai_request["max_tokens"] == 300
        assert openai_request["temperature"] == 0.2
        assert "response_format" in openai_request
        assert openai_request["response_format"]["type"] == "json_object"
    
    def test_generate_cache_key(self, provider, sample_request):
        """Test cache key generation"""
        key1 = provider._generate_cache_key(sample_request)
        key2 = provider._generate_cache_key(sample_request)
        
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 16
        
        sample_request.temperature = 0.5
        key3 = provider._generate_cache_key(sample_request)
        assert key1 != key3
    
    def test_extract_json_from_content(self, provider):
        """Test JSON extraction from formatted content"""
        json_content = '{"test": "value"}'
        result = provider._extract_json_from_content(json_content)
        assert result == '{"test": "value"}'
        
        markdown_content = '```json\n{"test": "value"}\n```'
        result = provider._extract_json_from_content(markdown_content)
        assert result == '{"test": "value"}'
        
        mixed_content = 'Here is the result: {"test": "value"} end'
        result = provider._extract_json_from_content(mixed_content)
        assert result == '{"test": "value"}'
        
        invalid_content = 'No JSON here'
        result = provider._extract_json_from_content(invalid_content)
        assert result is None
    
    def test_validate_json_structure(self, provider):
        """Test JSON structure validation"""
        valid_json = {
            "item1": {
                "estimated_weight_kg": 5.0,
                "display_weight": "5 kg",
                "confidence": 0.9
            },
            "item2": {
                "estimated_weight_kg": 10.0,
                "display_weight": "10 kg",
                "confidence": 0.9
            },
            "comparison": {
                "ratio": 0.5,
                "explanation": "Item 2 is heavier",
                "confidence": 0.8
            }
        }
        assert provider._validate_json_structure(valid_json) is True
        
        invalid_json = {
            "item1": {
                "estimated_weight_kg": 5.0,
                "display_weight": "5 kg",
                "confidence": 0.9
            }
        }
        assert provider._validate_json_structure(invalid_json) is False
    
    def test_determine_significance(self, provider):
        """Test significance level determination"""
        assert provider._determine_significance(1.0) == "negligible"
        assert provider._determine_significance(1.5) == "small"
        assert provider._determine_significance(5.0) == "moderate"
        assert provider._determine_significance(50.0) == "large"
        assert provider._determine_significance(500.0) == "extreme"


class TestAnthropicProvider:
    """Test cases for Anthropic Provider"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        return {
            'api_key': 'test-api-key',
            'model': ClaudeModel.SONNET,
            'intelligent_model_selection': True,
            'use_xml_tags': True,
            'safety_enabled': True,
            'beta_features': False,
            'timeout_seconds': 60.0,
            'rate_limit_rpm': 1000
        }
    
    @pytest.fixture
    def sample_request(self):
        """Sample weight comparison request"""
        return WeightComparisonRequest(
            item1="African Elephant",
            item1_weight=WeightInput(
                value="5000 kg",
                confidence=0.95
            ),
            item2="Tesla Model 3",
            item2_weight=WeightInput(
                value=1611.0,
                unit="kg",
                confidence=1.0
            ),
            comparison_type="detailed",
            include_visualization=True
        )
    
    def test_provider_initialization(self, mock_config):
        """Test provider initialization"""
        provider = AnthropicProvider(mock_config)
        
        assert provider.provider_name == "anthropic"
        assert provider.api_key == "test-api-key"
        assert provider.default_model == ClaudeModel.SONNET
        assert provider.use_xml_tags is True
        assert provider.safety_enabled is True
    
    def test_capabilities(self, mock_config):
        """Test provider capabilities"""
        provider = AnthropicProvider(mock_config)
        capabilities = provider.capabilities
        
        assert capabilities.supports_vision is True
        assert capabilities.supports_system_prompts is True
        assert capabilities.max_context_tokens == 200000
        assert capabilities.rate_limit_rpm == 1000
        assert capabilities.cost_per_1k_input_tokens > 0
    
    def test_model_selection_simple_request(self, mock_config):
        """Test intelligent model selection for simple requests"""
        provider = AnthropicProvider(mock_config)
        
        simple_request = WeightComparisonRequest(
            item1="Apple",
            item1_weight=WeightInput(value=0.2, unit="kg"),
            item2="Orange", 
            item2_weight=WeightInput(value=0.15, unit="kg"),
            comparison_type="basic",
            include_visualization=False
        )
        
        selected_model = provider._select_model_for_request(simple_request)
        assert selected_model == ClaudeModel.HAIKU
    
    def test_model_selection_complex_request(self, mock_config, sample_request):
        """Test intelligent model selection for complex requests"""
        provider = AnthropicProvider(mock_config)
        
        selected_model = provider._select_model_for_request(sample_request)
        assert selected_model in [ClaudeModel.SONNET, ClaudeModel.OPUS]
    
    def test_system_message_with_xml_tags(self, mock_config):
        """Test system message generation with XML tags"""
        provider = AnthropicProvider(mock_config)
        system_message = provider._build_system_message()
        
        assert "<instructions>" in system_message
        assert "<output_format>" in system_message
        assert "CORE PRINCIPLES" in system_message
        assert "SAFETY GUIDELINES" in system_message
    
    def test_system_message_without_xml_tags(self, mock_config):
        """Test system message generation without XML tags"""
        mock_config['use_xml_tags'] = False
        provider = AnthropicProvider(mock_config)
        system_message = provider._build_system_message()
        
        assert "<instructions>" not in system_message
        assert "CORE PRINCIPLES" in system_message
        assert "SAFETY GUIDELINES" in system_message
    
    def test_user_message_with_xml_tags(self, mock_config, sample_request):
        """Test user message generation with XML tags"""
        provider = AnthropicProvider(mock_config)
        user_message = provider._build_user_message(sample_request)
        
        assert "<task>" in user_message
        assert "<items>" in user_message
        assert "<item1>" in user_message
        assert "<item2>" in user_message
        assert "<requirements>" in user_message
    
    def test_json_extraction_from_response(self, mock_config):
        """Test JSON extraction from various response formats"""
        provider = AnthropicProvider(mock_config)
        
        direct_json = '{"test": "value"}'
        result = provider._extract_json_from_response(direct_json)
        assert result == {"test": "value"}
        
        code_block = '```json\n{"test": "value"}\n```'
        result = provider._extract_json_from_response(code_block)
        assert result == {"test": "value"}
        
        invalid = 'This is not JSON'
        result = provider._extract_json_from_response(invalid)
        assert result is None
    
    def test_significance_determination(self, mock_config):
        """Test significance level determination"""
        provider = AnthropicProvider(mock_config)
        
        assert provider._determine_significance(Decimal('1.005')) == "negligible"
        assert provider._determine_significance(Decimal('1.5')) == "small"
        assert provider._determine_significance(Decimal('5.0')) == "moderate"
        assert provider._determine_significance(Decimal('50.0')) == "large"
        assert provider._determine_significance(Decimal('500.0')) == "extreme"
    
    def test_category_determination(self, mock_config):
        """Test comparison category determination"""
        provider = AnthropicProvider(mock_config)
        
        assert provider._determine_category("elephant", "dog") == "animal_vs_animal"
        assert provider._determine_category("car", "truck") == "vehicle_vs_vehicle"
        assert provider._determine_category("apple", "bread") == "food_vs_food"
        assert provider._determine_category("elephant", "car") == "animal_vs_vehicle"
        assert provider._determine_category("book", "table") == "mixed"


class TestAnthropicConfigBuilder:
    """Test cases for Anthropic Configuration Builder"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = AnthropicConfigBuilder().with_api_key("test-key").build()
        
        assert config['api_key'] == "test-key"
        assert config['model'] == AnthropicModel.SONNET
        assert config['intelligent_model_selection'] is True
        assert config['use_xml_tags'] is True
        assert config['safety_enabled'] is True
        assert config['beta_features'] is False
    
    def test_configuration_chain(self):
        """Test configuration method chaining"""
        config = (AnthropicConfigBuilder()
                  .with_api_key("test-key")
                  .with_model(AnthropicModel.OPUS)
                  .with_temperature(0.5)
                  .with_max_tokens(2048)
                  .with_safety(False)
                  .with_beta_features(True)
                  .build())
        
        assert config['api_key'] == "test-key"
        assert config['model'] == AnthropicModel.OPUS.value
        assert config['temperature'] == 0.5
        assert config['max_tokens'] == 2048
        assert config['safety_enabled'] is False
        assert config['beta_features'] is True
    
    def test_validation_errors(self):
        """Test configuration validation"""
        builder = AnthropicConfigBuilder()
        
        with pytest.raises(ValueError, match="API key is required"):
            builder.build()
        
        with pytest.raises(ValueError, match="Temperature must be between"):
            builder.with_temperature(2.0)
        
        with pytest.raises(ValueError, match="Max tokens must be between"):
            builder.with_max_tokens(5000)
        
        with pytest.raises(ValueError, match="Timeout must be positive"):
            builder.with_timeout(-1.0)


class TestXAIProvider:
    """Test cases for XAI Provider"""
    
    @pytest.fixture
    def xai_config(self):
        """XAI provider configuration"""
        return {
            "api_key": "xai-test-key",
            "model": "grok-1",
            "endpoint": "https://api.x.ai/v1",
            "temperature": 0.3,
            "max_tokens": 1000,
            "timeout_seconds": 30.0
        }
    
    @pytest.fixture
    def xai_provider(self, xai_config, mock_logger):
        """XAI provider instance"""
        return XAIProvider(xai_config, mock_logger)
    
    def test_xai_provider_initialization(self, xai_config, mock_logger):
        """Test XAI provider initialization"""
        provider = XAIProvider(xai_config, mock_logger)
        
        assert provider.provider_name == "xai"
        assert provider.api_key == "xai-test-key"
        assert provider.model == "grok-1"
        assert provider.endpoint == "https://api.x.ai/v1"
    
    def test_xai_capabilities(self, xai_provider):
        """Test XAI provider capabilities"""
        capabilities = xai_provider.get_capabilities()
        
        assert capabilities["supports_streaming"] is True
        assert capabilities["supports_json_mode"] is True
        assert capabilities["max_context_length"] > 0
        assert capabilities["rate_limit_rpm"] > 0
    
    @pytest.mark.asyncio
    async def test_xai_request_building(self, xai_provider, sample_request):
        """Test XAI request building"""
        request = await xai_provider._build_request(sample_request)
        
        assert request["model"] == "grok-1"
        assert "messages" in request
        assert len(request["messages"]) >= 1
        assert request["temperature"] == 0.3
        assert request["max_tokens"] == 1000


class TestBaseAIProvider:
    """Test base AI provider functionality"""
    
    def test_base_provider_interface(self):
        """Test that all providers implement the base interface"""
        providers = [
            OpenAIProvider,
            AnthropicProvider,
            XAIProvider
        ]
        
        for provider_class in providers:
            assert issubclass(provider_class, BaseAIProvider)
    
    def test_provider_method_requirements(self):
        """Test that all providers have required methods"""
        required_methods = [
            'generate_comparison',
            'get_capabilities',
            'get_health',
            'validate_response'
        ]
        
        providers = [
            OpenAIProvider,
            AnthropicProvider,
            XAIProvider
        ]
        
        for provider_class in providers:
            for method in required_methods:
                assert hasattr(provider_class, method)


class TestAIProviderRateLimiting:
    """Test AI provider rate limiting"""
    
    def test_openai_rate_limiter(self):
        """Test OpenAI rate limiter"""
        limiter = OpenAIRateLimiter(requests_per_minute=60, burst_allowance=10)
        
        assert limiter.requests_per_minute == 60
        assert limiter.burst_allowance == 10
        assert limiter.tokens >= 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_token(self):
        """Test rate limiter token acquisition"""
        limiter = OpenAIRateLimiter(requests_per_minute=60, burst_allowance=10)
        
        success = await limiter.acquire_token(1)
        assert success is True
        assert limiter.tokens < limiter.max_tokens
    
    def test_rate_limiter_stats(self):
        """Test rate limiter statistics"""
        limiter = OpenAIRateLimiter(requests_per_minute=60, burst_allowance=10)
        stats = limiter.get_rate_limit_stats()
        
        assert "requests_per_minute_limit" in stats
        assert "requests_in_last_minute" in stats
        assert "available_tokens" in stats
        assert "adaptive_factor" in stats
        assert "utilization_percentage" in stats


class TestAIProviderCaching:
    """Test AI provider caching"""
    
    def test_response_cache_initialization(self):
        """Test response cache initialization"""
        cache = ResponseCache(enabled=True, max_size=10)
        
        assert cache.enabled is True
        assert cache.max_size == 10
        assert cache.hit_count == 0
        assert cache.miss_count == 0
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test cache set and get operations"""
        cache = ResponseCache(enabled=True, max_size=10)
        
        result = await cache.get("test_key")
        assert result is None
        assert cache.miss_count == 1
        
        await cache.set("test_key", {"test": "data"}, 300)
        
        result = await cache.get("test_key")
        assert result is not None
        assert cache.hit_count == 1
    
    def test_cache_stats(self):
        """Test cache statistics"""
        cache = ResponseCache(enabled=True, max_size=10)
        stats = cache.get_cache_stats()
        
        assert "enabled" in stats
        assert "cache_size" in stats
        assert "max_size" in stats
        assert "hit_count" in stats
        assert "miss_count" in stats
        assert "hit_rate" in stats
        assert "memory_usage_bytes" in stats


class TestAIProviderErrorHandling:
    """Test AI provider error handling"""
    
    def test_provider_error_creation(self):
        """Test provider error creation"""
        error = ProviderError("Test error", error_code="TEST_001")
        
        assert str(error) == "Test error"
        assert error.error_code == "TEST_001"
    
    def test_validation_error_creation(self):
        """Test validation error creation"""
        error = ValidationError("Validation failed", field="test_field")
        
        assert str(error) == "Validation failed"
        assert error.field == "test_field"
    
    def test_ai_provider_exception(self):
        """Test AI provider exception"""
        exception = AIProviderException("Provider failed", provider="test_provider")
        
        assert str(exception) == "Provider failed"
        assert exception.provider == "test_provider"
    
    def test_ai_provider_rate_limit_exception(self):
        """Test AI provider rate limit exception"""
        exception = AIProviderRateLimitException("Rate limit exceeded", retry_after=60)
        
        assert str(exception) == "Rate limit exceeded"
        assert exception.retry_after == 60


class TestAIProviderTokenUsage:
    """Test AI provider token usage tracking"""
    
    def test_token_usage_tracker_initialization(self):
        """Test token usage tracker initialization"""
        tracker = TokenUsageTracker()
        
        assert tracker.total_tokens_used == 0
        assert tracker.total_cost == 0.0
        assert len(tracker.usage_history) == 0
    
    def test_token_usage_recording(self):
        """Test token usage recording"""
        tracker = TokenUsageTracker()
        
        initial_total = tracker.total_tokens_used
        initial_cost = tracker.total_cost
        
        tracker.record_usage("gpt-4", 100, 50)
        
        assert tracker.total_tokens_used == initial_total + 150
        assert tracker.total_cost > initial_cost
        assert len(tracker.usage_history) == 1
    
    def test_token_usage_stats(self):
        """Test token usage statistics"""
        tracker = TokenUsageTracker()
        
        tracker.record_usage("gpt-4", 100, 50)
        tracker.record_usage("gpt-4", 80, 40)
        
        stats = tracker.get_usage_stats(1)
        
        assert "total_requests" in stats
        assert "total_tokens" in stats
        assert "total_cost_usd" in stats
        assert "avg_tokens_per_request" in stats
        assert "estimated_monthly_cost" in stats
        
        assert stats["total_requests"] == 2
        assert stats["total_tokens"] == 270
        assert stats["avg_tokens_per_request"] == 135.0


@pytest.mark.integration
class TestAIProviderIntegration:
    """Integration tests for AI providers"""
    
    @pytest.mark.ai_required
    @pytest.mark.asyncio
    async def test_openai_integration(self, real_ai_api_key):
        """Test OpenAI integration with real API"""
        if not real_ai_api_key or not real_ai_api_key.startswith("sk-"):
            pytest.skip("OpenAI API key not available")
        
        config = {
            "api_key": real_ai_api_key,
            "model": "gpt-3.5-turbo",
            "max_tokens": 100,
            "temperature": 0.3
        }
        
        provider = OpenAIProvider(config, Mock())
        
        # Test basic functionality
        health = provider.get_health()
        assert health.status in ["healthy", "degraded"]
    
    @pytest.mark.ai_required
    @pytest.mark.asyncio
    async def test_anthropic_integration(self, real_ai_api_key):
        """Test Anthropic integration with real API"""
        if not real_ai_api_key or not real_ai_api_key.startswith("sk-ant-"):
            pytest.skip("Anthropic API key not available")
        
        config = {
            "api_key": real_ai_api_key,
            "model": ClaudeModel.HAIKU,
            "max_tokens": 100,
            "temperature": 0.3
        }
        
        provider = AnthropicProvider(config)
        
        # Test basic functionality
        health = provider.get_health()
        assert health.status in ["healthy", "degraded"]
    
    @pytest.mark.ai_required
    @pytest.mark.asyncio
    async def test_provider_fallback_chain(self, enable_ai_providers):
        """Test provider fallback chain"""
        from src.services.shared.ai_provider_manager import AIProviderManager
        
        manager = AIProviderManager()
        
        # Test that fallback works when providers fail
        availability = manager.get_provider_availability()
        assert isinstance(availability, dict)
        
        # Should always have at least fallback available
        assert len(availability) > 0