"""
Test suite for the Anthropic provider implementation.

This module contains unit tests and integration tests for the Anthropic provider,
ensuring compatibility with the SizeComparator architecture.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from .anthropic_provider import AnthropicProvider, ClaudeModel
from .anthropic_config import AnthropicConfigBuilder, AnthropicModel
from ..models.requests import WeightComparisonRequest
from ..models.weight import WeightInput
from ..core.exceptions import AIProviderException, AIProviderRateLimitException


class TestAnthropicProvider:
    """Test cases for AnthropicProvider."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
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
        """Sample weight comparison request."""
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
    
    @pytest.fixture
    def mock_anthropic_response(self):
        """Mock Anthropic API response."""
        return {
            'content': json.dumps({
                "item1": {
                    "name": "African Elephant",
                    "original_input": "5000 kg",
                    "weight_kg": 5000.0,
                    "weight_display": "5,000 kg",
                    "unit_used": "kg",
                    "parsing_confidence": 0.95
                },
                "item2": {
                    "name": "Tesla Model 3",
                    "original_input": "1611.0 kg",
                    "weight_kg": 1611.0,
                    "weight_display": "1,611 kg",
                    "unit_used": "kg",
                    "parsing_confidence": 1.0
                },
                "comparison": {
                    "ratio": 3.105,
                    "explanation": "The elephant weighs about 3.1 times more than the Tesla Model 3.",
                    "confidence": 0.9,
                    "contextual_examples": [
                        "The elephant's weight is equivalent to about 3 Tesla Model 3 cars",
                        "The Tesla weighs similar to a small truck"
                    ]
                },
                "visualization_prompt": "Show an African elephant next to 3 Tesla Model 3 cars",
                "metadata": {
                    "model_used": "claude-3-sonnet-20240229",
                    "analysis_type": "weight_comparison",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }),
            'model': 'claude-3-sonnet-20240229',
            'usage': {
                'input_tokens': 150,
                'output_tokens': 300,
                'total_tokens': 450
            },
            'stop_reason': 'end_turn',
            'id': 'msg_test_123'
        }
    
    def test_provider_initialization(self, mock_config):
        """Test provider initialization."""
        provider = AnthropicProvider(mock_config)
        
        assert provider.provider_name == "anthropic"
        assert provider.api_key == "test-api-key"
        assert provider.default_model == ClaudeModel.SONNET
        assert provider.use_xml_tags is True
        assert provider.safety_enabled is True
    
    def test_capabilities(self, mock_config):
        """Test provider capabilities."""
        provider = AnthropicProvider(mock_config)
        capabilities = provider.capabilities
        
        assert capabilities.supports_vision is True
        assert capabilities.supports_system_prompts is True
        assert capabilities.max_context_tokens == 200000
        assert capabilities.rate_limit_rpm == 1000
        assert capabilities.cost_per_1k_input_tokens > 0
    
    def test_model_selection_simple_request(self, mock_config, sample_request):
        """Test intelligent model selection for simple requests."""
        provider = AnthropicProvider(mock_config)
        
        # Simple request should select Haiku
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
        """Test intelligent model selection for complex requests."""
        provider = AnthropicProvider(mock_config)
        
        # Complex request should select Opus
        selected_model = provider._select_model_for_request(sample_request)
        assert selected_model in [ClaudeModel.SONNET, ClaudeModel.OPUS]
    
    def test_system_message_with_xml_tags(self, mock_config):
        """Test system message generation with XML tags."""
        provider = AnthropicProvider(mock_config)
        system_message = provider._build_system_message()
        
        assert "<instructions>" in system_message
        assert "<output_format>" in system_message
        assert "CORE PRINCIPLES" in system_message
        assert "SAFETY GUIDELINES" in system_message
    
    def test_system_message_without_xml_tags(self, mock_config):
        """Test system message generation without XML tags."""
        mock_config['use_xml_tags'] = False
        provider = AnthropicProvider(mock_config)
        system_message = provider._build_system_message()
        
        assert "<instructions>" not in system_message
        assert "CORE PRINCIPLES" in system_message
        assert "SAFETY GUIDELINES" in system_message
    
    def test_user_message_with_xml_tags(self, mock_config, sample_request):
        """Test user message generation with XML tags."""
        provider = AnthropicProvider(mock_config)
        user_message = provider._build_user_message(sample_request)
        
        assert "<task>" in user_message
        assert "<items>" in user_message
        assert "<item1>" in user_message
        assert "<item2>" in user_message
        assert "<requirements>" in user_message
        assert "<json_format>" in user_message
    
    @patch('anthropic.AsyncAnthropic')
    async def test_generate_completion_success(self, mock_anthropic_client, mock_config, mock_anthropic_response):
        """Test successful completion generation."""
        # Setup mock
        mock_client_instance = AsyncMock()
        mock_anthropic_client.return_value = mock_client_instance
        
        # Mock the messages.create method
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=mock_anthropic_response['content'])]
        mock_response.model = mock_anthropic_response['model']
        mock_response.usage.input_tokens = mock_anthropic_response['usage']['input_tokens']
        mock_response.usage.output_tokens = mock_anthropic_response['usage']['output_tokens']
        mock_response.stop_reason = mock_anthropic_response['stop_reason']
        mock_response.id = mock_anthropic_response['id']
        
        mock_client_instance.messages.create.return_value = mock_response
        
        # Test
        provider = AnthropicProvider(mock_config)
        messages = [{"role": "user", "content": "Test message"}]
        
        result = await provider._generate_completion(messages)
        
        assert result['content'] == mock_anthropic_response['content']
        assert result['model'] == mock_anthropic_response['model']
        assert result['usage']['total_tokens'] == 450
    
    @patch('anthropic.AsyncAnthropic')
    async def test_generate_completion_rate_limit_error(self, mock_anthropic_client, mock_config):
        """Test rate limit error handling."""
        from anthropic import RateLimitError
        
        # Setup mock
        mock_client_instance = AsyncMock()
        mock_anthropic_client.return_value = mock_client_instance
        mock_client_instance.messages.create.side_effect = RateLimitError("Rate limit exceeded")
        
        # Test
        provider = AnthropicProvider(mock_config)
        messages = [{"role": "user", "content": "Test message"}]
        
        with pytest.raises(AIProviderRateLimitException):
            await provider._generate_completion(messages)
    
    def test_json_extraction_from_response(self, mock_config):
        """Test JSON extraction from various response formats."""
        provider = AnthropicProvider(mock_config)
        
        # Test direct JSON
        direct_json = '{"test": "value"}'
        result = provider._extract_json_from_response(direct_json)
        assert result == {"test": "value"}
        
        # Test JSON in code block
        code_block = '```json\n{"test": "value"}\n```'
        result = provider._extract_json_from_response(code_block)
        assert result == {"test": "value"}
        
        # Test JSON with surrounding text
        with_text = 'Here is the result:\n{"test": "value"}\nEnd of response.'
        result = provider._extract_json_from_response(with_text)
        assert result == {"test": "value"}
        
        # Test invalid JSON
        invalid = 'This is not JSON'
        result = provider._extract_json_from_response(invalid)
        assert result is None
    
    def test_significance_determination(self, mock_config):
        """Test significance level determination."""
        provider = AnthropicProvider(mock_config)
        
        assert provider._determine_significance(Decimal('1.005')) == "negligible"
        assert provider._determine_significance(Decimal('1.5')) == "small"
        assert provider._determine_significance(Decimal('5.0')) == "moderate"
        assert provider._determine_significance(Decimal('50.0')) == "large"
        assert provider._determine_significance(Decimal('500.0')) == "extreme"
    
    def test_category_determination(self, mock_config):
        """Test comparison category determination."""
        provider = AnthropicProvider(mock_config)
        
        assert provider._determine_category("elephant", "dog") == "animal_vs_animal"
        assert provider._determine_category("car", "truck") == "vehicle_vs_vehicle"
        assert provider._determine_category("apple", "bread") == "food_vs_food"
        assert provider._determine_category("elephant", "car") == "animal_vs_vehicle"
        assert provider._determine_category("book", "table") == "mixed"
    
    async def test_parse_provider_response(self, mock_config, sample_request, mock_anthropic_response):
        """Test response parsing."""
        provider = AnthropicProvider(mock_config)
        
        result = await provider._parse_provider_response(mock_anthropic_response, sample_request)
        
        assert result.item1.name == "African Elephant"
        assert result.item1.parsed_value == Decimal('5000.0')
        assert result.item2.name == "Tesla Model 3"
        assert result.item2.parsed_value == Decimal('1611.0')
        assert result.analysis.weight_ratio == Decimal('3.105')
        assert result.analysis.heavier_item == "item1"
        assert result.visualization is not None
        assert result.visualization.prompt_text == "Show an African elephant next to 3 Tesla Model 3 cars"


class TestAnthropicConfigBuilder:
    """Test cases for AnthropicConfigBuilder."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = AnthropicConfigBuilder().with_api_key("test-key").build()
        
        assert config['api_key'] == "test-key"
        assert config['model'] == AnthropicModel.SONNET
        assert config['intelligent_model_selection'] is True
        assert config['use_xml_tags'] is True
        assert config['safety_enabled'] is True
        assert config['beta_features'] is False
    
    def test_configuration_chain(self):
        """Test configuration method chaining."""
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
        """Test configuration validation."""
        builder = AnthropicConfigBuilder()
        
        # Missing API key
        with pytest.raises(ValueError, match="API key is required"):
            builder.build()
        
        # Invalid temperature
        with pytest.raises(ValueError, match="Temperature must be between"):
            builder.with_temperature(2.0)
        
        # Invalid max tokens
        with pytest.raises(ValueError, match="Max tokens must be between"):
            builder.with_max_tokens(5000)
        
        # Invalid timeout
        with pytest.raises(ValueError, match="Timeout must be positive"):
            builder.with_timeout(-1.0)
    
    @patch.dict('os.environ', {
        'SIZECOMPARATOR_ANTHROPIC_API_KEY': 'env-api-key',
        'SIZECOMPARATOR_ANTHROPIC_MODEL': 'claude-3-opus-20240229',
        'SIZECOMPARATOR_ANTHROPIC_TEMPERATURE': '0.8',
        'SIZECOMPARATOR_ANTHROPIC_BETA_FEATURES': 'true'
    })
    def test_from_environment(self):
        """Test configuration from environment variables."""
        config = AnthropicConfigBuilder().from_environment().build()
        
        assert config['api_key'] == 'env-api-key'
        assert config['model'] == 'claude-3-opus-20240229'
        assert config['temperature'] == 0.8
        assert config['beta_features'] is True


# Integration test (requires real API key)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_anthropic_integration():
    """Integration test with real Anthropic API (requires API key)."""
    import os
    
    api_key = os.getenv('SIZECOMPARATOR_ANTHROPIC_API_KEY')
    if not api_key:
        pytest.skip("SIZECOMPARATOR_ANTHROPIC_API_KEY not set")
    
    config = (AnthropicConfigBuilder()
              .with_api_key(api_key)
              .with_model(AnthropicModel.HAIKU)  # Use cheapest model for testing
              .with_max_tokens(500)
              .build())
    
    provider = AnthropicProvider(config)
    
    request = WeightComparisonRequest(
        item1="Apple",
        item1_weight=WeightInput(value=0.2, unit="kg"),
        item2="Orange",
        item2_weight=WeightInput(value=0.15, unit="kg"),
        comparison_type="basic",
        include_visualization=True
    )
    
    try:
        response = await provider.generate_comparison(request)
        
        # Basic validation
        assert response.item1.name == "Apple"
        assert response.item2.name == "Orange"
        assert response.analysis.weight_ratio > 0
        assert response.visualization is not None
        
        # Check provider health
        health = provider.get_health()
        assert health.status in ["healthy", "degraded"]
        assert health.success_rate > 0
        
    except Exception as e:
        pytest.fail(f"Integration test failed: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])