"""
Unit tests for OpenAI Provider implementation.

Tests the OpenAI provider functionality including:
- Provider initialization
- Request building
- Response parsing
- Error handling
- Rate limiting
- Caching
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from src.providers.openai_provider import (
    OpenAIProvider,
    OpenAIRateLimiter,
    TokenUsageTracker,
    ResponseCache
)
from src.providers.base import ProviderError, ValidationError
from src.models.providers import AIProviderRequest, TemplateVariables


class TestOpenAIProvider:
    """Test cases for OpenAI Provider."""
    
    @pytest.fixture
    def provider_config(self):
        """Provider configuration for testing."""
        return {
            "api_key": "sk-test-key-for-unit-tests",
            "endpoint": "https://api.openai.com/v1",
            "model": "gpt-4",
            "timeout_seconds": 30.0,
            "max_tokens": 500,
            "temperature": 0.3,
            "rate_limit_rpm": 100,  # Lower for testing
            "max_retries": 2,
            "structured_output": True,
            "enable_caching": True,
            "cache_ttl_seconds": 300
        }
    
    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing."""
        return Mock()
    
    @pytest.fixture
    def provider(self, provider_config, mock_logger):
        """OpenAI provider instance for testing."""
        return OpenAIProvider(provider_config, mock_logger)
    
    @pytest.fixture
    def sample_request(self):
        """Sample AI provider request."""
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
        """Test provider initialization."""
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
        """Test structured output support detection."""
        provider.model = "gpt-4"
        assert provider._supports_structured_output() is True
        
        provider.model = "gpt-3.5-turbo"
        assert provider._supports_structured_output() is True
        
        provider.model = "gpt-4o"
        assert provider._supports_structured_output() is True
        
        provider.model = "unknown-model"
        assert provider._supports_structured_output() is False
    
    @pytest.mark.asyncio
    async def test_get_system_prompt(self, provider):
        """Test system prompt generation."""
        prompt = await provider._get_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "weight comparison expert" in prompt.lower()
        assert "json" in prompt.lower()
        assert "accuracy" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_get_optimized_prompt(self, provider, sample_request):
        """Test optimized prompt generation."""
        prompt = await provider._get_optimized_prompt(sample_request)
        
        assert isinstance(prompt, str)
        assert "Test Item 1" in prompt
        assert "Test Item 2" in prompt
        assert "5 kg" in prompt
        assert "10 kg" in prompt
        assert "JSON" in prompt
    
    @pytest.mark.asyncio
    async def test_build_openai_request(self, provider, sample_request):
        """Test OpenAI request building."""
        openai_request = await provider._build_openai_request(sample_request)
        
        assert openai_request["model"] == "gpt-4"
        assert len(openai_request["messages"]) == 2
        assert openai_request["messages"][0]["role"] == "system"
        assert openai_request["messages"][1]["role"] == "user"
        assert openai_request["max_tokens"] == 300  # From sample_request
        assert openai_request["temperature"] == 0.2  # From sample_request
        assert "response_format" in openai_request
        assert openai_request["response_format"]["type"] == "json_object"
    
    def test_generate_cache_key(self, provider, sample_request):
        """Test cache key generation."""
        key1 = provider._generate_cache_key(sample_request)
        key2 = provider._generate_cache_key(sample_request)
        
        # Same request should generate same key
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 16  # Truncated SHA256
        
        # Different request should generate different key
        sample_request.temperature = 0.5
        key3 = provider._generate_cache_key(sample_request)
        assert key1 != key3
    
    def test_extract_json_from_content(self, provider):
        """Test JSON extraction from formatted content."""
        # Test clean JSON
        json_content = '{"test": "value"}'
        result = provider._extract_json_from_content(json_content)
        assert result == '{"test": "value"}'
        
        # Test markdown formatted JSON
        markdown_content = '```json\n{"test": "value"}\n```'
        result = provider._extract_json_from_content(markdown_content)
        assert result == '{"test": "value"}'
        
        # Test text with JSON embedded
        mixed_content = 'Here is the result: {"test": "value"} end'
        result = provider._extract_json_from_content(mixed_content)
        assert result == '{"test": "value"}'
        
        # Test invalid content
        invalid_content = 'No JSON here'
        result = provider._extract_json_from_content(invalid_content)
        assert result is None
    
    def test_validate_json_structure(self, provider):
        """Test JSON structure validation."""
        # Valid structure
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
        
        # Missing section
        invalid_json = {
            "item1": {
                "estimated_weight_kg": 5.0,
                "display_weight": "5 kg",
                "confidence": 0.9
            }
            # Missing item2 and comparison
        }
        assert provider._validate_json_structure(invalid_json) is False
        
        # Missing required field
        invalid_json2 = {
            "item1": {
                "display_weight": "5 kg",
                "confidence": 0.9
                # Missing estimated_weight_kg
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
        assert provider._validate_json_structure(invalid_json2) is False
    
    def test_extract_weight_value(self, provider):
        """Test weight value extraction."""
        # Valid weight
        item_data = {"estimated_weight_kg": 5.5}
        assert provider._extract_weight_value(item_data) == 5.5
        
        # String weight (should convert)
        item_data = {"estimated_weight_kg": "10.0"}
        assert provider._extract_weight_value(item_data) == 10.0
        
        # Missing weight
        item_data = {}
        assert provider._extract_weight_value(item_data) == 0.0
        
        # Invalid weight
        item_data = {"estimated_weight_kg": "invalid"}
        assert provider._extract_weight_value(item_data) == 0.0
    
    def test_determine_significance(self, provider):
        """Test significance level determination."""
        assert provider._determine_significance(1.0) == "negligible"
        assert provider._determine_significance(1.005) == "negligible"
        assert provider._determine_significance(1.5) == "small"
        assert provider._determine_significance(5.0) == "moderate"
        assert provider._determine_significance(50.0) == "large"
        assert provider._determine_significance(500.0) == "extreme"
    
    def test_validate_response(self, provider):
        """Test response validation."""
        # Mock valid response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '{"item1": {"estimated_weight_kg": 5.0, "display_weight": "5 kg", "confidence": 0.9}, "item2": {"estimated_weight_kg": 10.0, "display_weight": "10 kg", "confidence": 0.9}, "comparison": {"ratio": 0.5, "explanation": "test", "confidence": 0.8}}'
        
        assert provider.validate_response(mock_response) is True
        
        # Mock invalid response - no choices
        mock_response.choices = []
        assert provider.validate_response(mock_response) is False
        
        # Mock invalid response - no content
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = ""
        assert provider.validate_response(mock_response) is False


class TestOpenAIRateLimiter:
    """Test cases for OpenAI Rate Limiter."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Rate limiter for testing."""
        return OpenAIRateLimiter(requests_per_minute=60, burst_allowance=10)  # 1 per second for easy testing
    
    @pytest.mark.asyncio
    async def test_acquire_token_success(self, rate_limiter):
        """Test successful token acquisition."""
        success = await rate_limiter.acquire_token(1)
        assert success is True
        assert rate_limiter.tokens < rate_limiter.max_tokens
    
    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self, rate_limiter):
        """Test acquiring multiple tokens."""
        success = await rate_limiter.acquire_token(5)
        assert success is True
        
        tokens_remaining = rate_limiter.tokens
        assert tokens_remaining > 0
    
    def test_record_rate_limit_hit(self, rate_limiter):
        """Test rate limit hit recording."""
        initial_factor = rate_limiter.adaptive_factor
        initial_hits = rate_limiter.rate_limit_hits
        
        rate_limiter.record_rate_limit_hit()
        
        assert rate_limiter.rate_limit_hits == initial_hits + 1
        assert rate_limiter.adaptive_factor < initial_factor
    
    def test_record_success(self, rate_limiter):
        """Test success recording."""
        # First reduce factor
        rate_limiter.adaptive_factor = 0.8
        
        rate_limiter.record_success()
        
        # Should increase factor slightly
        assert rate_limiter.adaptive_factor > 0.8
    
    def test_get_rate_limit_stats(self, rate_limiter):
        """Test rate limit statistics."""
        stats = rate_limiter.get_rate_limit_stats()
        
        assert "requests_per_minute_limit" in stats
        assert "requests_in_last_minute" in stats
        assert "available_tokens" in stats
        assert "adaptive_factor" in stats
        assert "rate_limit_hits" in stats
        assert "utilization_percentage" in stats
        
        assert stats["requests_per_minute_limit"] == 60
        assert isinstance(stats["utilization_percentage"], float)


class TestTokenUsageTracker:
    """Test cases for Token Usage Tracker."""
    
    @pytest.fixture
    def token_tracker(self):
        """Token usage tracker for testing."""
        return TokenUsageTracker()
    
    def test_record_usage(self, token_tracker):
        """Test usage recording."""
        initial_total = token_tracker.total_tokens_used
        initial_cost = token_tracker.total_cost
        
        token_tracker.record_usage("gpt-4", 100, 50)
        
        assert token_tracker.total_tokens_used == initial_total + 150
        assert token_tracker.total_cost > initial_cost
        assert len(token_tracker.usage_history) == 1
    
    def test_get_usage_stats(self, token_tracker):
        """Test usage statistics."""
        # Record some usage
        token_tracker.record_usage("gpt-4", 100, 50)
        token_tracker.record_usage("gpt-4", 80, 40)
        
        stats = token_tracker.get_usage_stats(1)  # Last 1 hour
        
        assert "total_requests" in stats
        assert "total_tokens" in stats
        assert "total_cost_usd" in stats
        assert "avg_tokens_per_request" in stats
        assert "estimated_monthly_cost" in stats
        
        assert stats["total_requests"] == 2
        assert stats["total_tokens"] == 270  # 150 + 120
        assert stats["avg_tokens_per_request"] == 135.0


class TestResponseCache:
    """Test cases for Response Cache."""
    
    @pytest.fixture
    def response_cache(self):
        """Response cache for testing."""
        return ResponseCache(enabled=True, max_size=10)
    
    @pytest.fixture
    def sample_response(self):
        """Sample response for caching."""
        from src.models.responses import WeightComparisonResponse, ResponseMetadata
        from src.models.weight import ProcessedWeight, WeightUnit
        from decimal import Decimal
        
        return WeightComparisonResponse(
            item1=ProcessedWeight(
                original_input={"value": "5 kg"},
                parsed_value=Decimal("5.0"),
                display_value="5 kg",
                unit_used=WeightUnit.KG,
                parsing_confidence=1.0
            ),
            item2=ProcessedWeight(
                original_input={"value": "10 kg"},
                parsed_value=Decimal("10.0"),
                display_value="10 kg",
                unit_used=WeightUnit.KG,
                parsing_confidence=1.0
            ),
            analysis=Mock(),  # Mock for simplicity
            metadata=ResponseMetadata(
                request_id=uuid4(),
                processing_time_ms=100,
                api_version="1.0.0"
            )
        )
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, response_cache, sample_response):
        """Test cache set and get operations."""
        cache_key = "test_key"
        
        # Cache miss initially
        result = await response_cache.get(cache_key)
        assert result is None
        assert response_cache.miss_count == 1
        
        # Set cache
        await response_cache.set(cache_key, sample_response, 300)
        
        # Cache hit
        result = await response_cache.get(cache_key)
        assert result is not None
        assert response_cache.hit_count == 1
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, response_cache, sample_response):
        """Test cache expiration."""
        cache_key = "test_key"
        
        # Set cache with very short TTL
        await response_cache.set(cache_key, sample_response, 0)  # Immediate expiration
        
        # Should be expired
        result = await response_cache.get(cache_key)
        assert result is None
        assert response_cache.miss_count == 1
    
    def test_cache_stats(self, response_cache):
        """Test cache statistics."""
        stats = response_cache.get_cache_stats()
        
        assert "enabled" in stats
        assert "cache_size" in stats
        assert "max_size" in stats
        assert "hit_count" in stats
        assert "miss_count" in stats
        assert "hit_rate" in stats
        assert "memory_usage_bytes" in stats
        
        assert stats["enabled"] is True
        assert stats["max_size"] == 10
        assert isinstance(stats["hit_rate"], float)