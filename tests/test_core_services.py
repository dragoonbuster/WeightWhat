"""
Test the simplified core services.
"""

import pytest
import time
from decimal import Decimal

from src.core_services import WeightProcessor, ComparisonEngine, CacheManager


class TestWeightProcessor:
    """Test the simplified weight processor."""
    
    def setup_method(self):
        self.processor = WeightProcessor()
    
    def test_valid_weights(self):
        """Test processing valid weights."""
        test_cases = [
            ("5 kg", 5.0, "kg", "5 kg"),
            ("100.5 lbs", 45.587924, "lb", "1.005E+2 lb"),
            ("2.5 g", 0.0025, "g", "2.5 g"),
            ("10 oz", 0.283495, "oz", "10 oz"),
        ]
        
        for input_str, expected_kg, unit, display in test_cases:
            result = self.processor.process(input_str)
            assert result is not None
            assert abs(result['weight_kg'] - expected_kg) < 0.01
            assert result['unit'] == unit
            assert result['original_input'] == input_str
    
    def test_invalid_weights(self):
        """Test invalid weight inputs."""
        invalid_inputs = [
            "",
            "   ",
            "abc",
            "kg 5",
            "-5 kg",
            "0 kg",
            "5 xyz",
            "five kilograms"
        ]
        
        for input_str in invalid_inputs:
            result = self.processor.process(input_str)
            assert result is None
    
    def test_weight_categories(self):
        """Test weight categorization."""
        test_cases = [
            (0.0001, 'microscopic'),  # 0.1g
            (0.05, 'very_light'),     # 50g
            (5.0, 'light'),           # 5kg
            (100.0, 'medium'),        # 100kg
            (5000.0, 'heavy'),        # 5 tons
            (500000.0, 'very_heavy')  # 500 tons
        ]
        
        for weight_kg, expected_category in test_cases:
            category = self.processor.get_weight_category(weight_kg)
            assert category == expected_category


class TestCacheManager:
    """Test the cache manager."""
    
    def setup_method(self):
        self.cache = CacheManager()
    
    def test_cache_operations(self):
        """Test basic cache operations."""
        # Test get on missing key
        assert self.cache.get('missing') is None
        
        # Test set and get
        self.cache.set('test_key', 'test_value', ttl=10)
        assert self.cache.get('test_key') == 'test_value'
        
        # Test delete
        self.cache.delete('test_key')
        assert self.cache.get('test_key') is None
    
    def test_cache_expiration(self):
        """Test cache TTL."""
        self.cache.set('expire_test', 'value', ttl=0.1)  # 100ms
        assert self.cache.get('expire_test') == 'value'
        
        time.sleep(0.2)  # Wait for expiration
        assert self.cache.get('expire_test') is None
    
    def test_counter_operations(self):
        """Test counter functionality."""
        initial = self.cache.get_counter()
        assert isinstance(initial, int)
        
        new_value = self.cache.increment_counter()
        assert new_value == initial + 1
        assert self.cache.get_counter() == new_value
    
    def test_cache_key_building(self):
        """Test cache key generation."""
        test_cases = [
            (0.0005, 'default', 'comparison:0.0005:default'),
            (5.123, 'creative', 'comparison:5.12:creative'),
            (100.789, 'technical', 'comparison:100.8:technical'),
            (5000.123, 'default', 'comparison:5000.0:default'),
        ]
        
        for weight_kg, style, expected_key in test_cases:
            key = self.cache.build_cache_key(weight_kg, style)
            assert key == expected_key


class TestComparisonEngine:
    """Test the comparison engine."""
    
    def setup_method(self):
        self.engine = ComparisonEngine()
    
    def test_fallback_responses(self):
        """Test fallback response generation."""
        # Should always return a response
        response = self.engine._get_fallback_response('medium')
        assert isinstance(response, str)
        assert len(response) > 10
        
        # Test all categories have responses
        categories = ['microscopic', 'very_light', 'light', 'medium', 'heavy', 'very_heavy']
        for category in categories:
            response = self.engine._get_fallback_response(category)
            assert isinstance(response, str)
    
    def test_response_cleaning(self):
        """Test response cleaning."""
        test_cases = [
            ("That weighs about as heavy as a cat", "That's about as heavy as a cat"),
            ("'approximately 5 golden retrievers'", "That's approximately 5 golden retrievers"),
            ("It's roughly the same as a laptop", "That's roughly the same as a laptop"),
            ("about the weight of a car", "That's about the weight of a car"),
        ]
        
        for input_text, expected in test_cases:
            cleaned = self.engine._clean_response(input_text)
            assert cleaned == expected
    
    def test_prompt_building(self):
        """Test prompt generation."""
        prompt = self.engine._build_prompt(75.5, 'medium', 'creative')
        assert '75.50 kg' in prompt
        assert 'humorous' in prompt
        
        prompt = self.engine._build_prompt(0.01, 'microscopic', 'technical')
        assert '0.01 kg' in prompt
        assert 'scientific' in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])