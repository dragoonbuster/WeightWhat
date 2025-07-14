"""
Response Processor for Weight Comparisons

Processes and enhances AI responses, including validation, quality scoring,
and enrichment with additional metadata and suggestions.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...core.config import ConfigLoader
from ...services.weight_processor import WeightItem
from .types import ComparisonObject

logger = logging.getLogger(__name__)


class ParsedResponse:
    """Parsed AI response structure"""
    def __init__(self, comparison_text: str, confidence: float = 0.8):
        self.comparison_text = comparison_text
        self.confidence = confidence


class ValidationResult:
    """Response validation result"""
    def __init__(
        self,
        is_valid: bool,
        errors: List[str],
        warnings: List[str],
        confidence_score: float
    ):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings
        self.confidence_score = confidence_score


class InvalidResponseError(Exception):
    """Raised when response validation fails"""
    pass


class ResponseParser:
    """Parse AI responses into structured format"""
    
    def parse_ai_response(self, raw_response: str) -> ParsedResponse:
        """Parse raw AI response into structured format"""
        
        # Clean up the response
        cleaned = self._clean_response(raw_response)
        
        # Extract main comparison text
        comparison_text = self._extract_comparison_text(cleaned)
        
        # Calculate basic confidence based on response quality
        confidence = self._calculate_basic_confidence(comparison_text)
        
        return ParsedResponse(
            comparison_text=comparison_text,
            confidence=confidence
        )
        
    def _clean_response(self, response: str) -> str:
        """Clean and normalize AI response"""
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', response.strip())
        
        # Remove common AI prefixes/suffixes
        prefixes_to_remove = [
            r'^(Here\'s a comparison|To help you understand|This weight)',
            r'^(A weight of|The weight of)',
            r'^(Comparison:|Weight comparison:)'
        ]
        
        for prefix in prefixes_to_remove:
            cleaned = re.sub(prefix, '', cleaned, flags=re.IGNORECASE).strip()
            
        # Remove trailing AI disclaimers
        suffixes_to_remove = [
            r'(Let me know if you need.*|Please note that.*|I hope this helps.*)',
            r'(This comparison should.*|Feel free to ask.*)'
        ]
        
        for suffix in suffixes_to_remove:
            cleaned = re.sub(suffix + r'.*$', '', cleaned, flags=re.IGNORECASE).strip()
            
        return cleaned
        
    def _extract_comparison_text(self, response: str) -> str:
        """Extract the main comparison text"""
        
        # Look for structured comparison patterns
        patterns = [
            r'Comparison:\s*(.+)',
            r'This weight is\s*(.+)',
            r'(.+?)\s*(?:This comparison|To understand)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
                
        # If no pattern matches, return the whole cleaned response
        return response
        
    def _calculate_basic_confidence(self, text: str) -> float:
        """Calculate basic confidence score based on text quality"""
        
        confidence = 0.8  # Base confidence
        
        # Check length (too short or too long reduces confidence)
        if len(text) < 30:
            confidence -= 0.3
        elif len(text) > 500:
            confidence -= 0.1
            
        # Check for specific comparison elements
        comparison_indicators = [
            r'\d+\s*times',           # "3 times heavier"
            r'equivalent to',         # "equivalent to"
            r'similar to',            # "similar to"
            r'about the same',        # "about the same"
            r'compared to',           # "compared to"
            r'like.*?\d+',           # "like 5 cats"
        ]
        
        indicator_count = 0
        for indicator in comparison_indicators:
            if re.search(indicator, text, re.IGNORECASE):
                indicator_count += 1
                
        # Boost confidence based on comparison indicators
        confidence += min(0.2, indicator_count * 0.05)
        
        # Check for problematic content
        problematic_patterns = [
            r'as an ai',
            r'i cannot',
            r'unable to provide',
            r'error',
            r'please try again'
        ]
        
        for pattern in problematic_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                confidence -= 0.4
                
        return max(0.0, min(1.0, confidence))


class ResponseValidator:
    """Validate AI responses for quality and accuracy"""
    
    def validate(
        self,
        parsed_response: ParsedResponse,
        weight_result: WeightItem,
        expected_objects: List[ComparisonObject]
    ) -> ValidationResult:
        """Comprehensive response validation"""
        
        errors = []
        warnings = []
        
        text = parsed_response.comparison_text
        
        # Check response length
        if len(text) < 20:
            errors.append("Response too short (minimum 20 characters)")
        elif len(text) > 800:
            warnings.append("Response exceeds recommended length")
            
        # Check for actual comparisons
        if not self._contains_comparison(text):
            errors.append("Response does not contain valid comparisons")
            
        # Verify mentioned objects
        mentioned_objects = self._extract_mentioned_objects(text)
        expected_names = {obj.name.lower() for obj in expected_objects}
        mentioned_names = {obj.lower() for obj in mentioned_objects}
        
        if expected_objects and not mentioned_names.intersection(expected_names):
            warnings.append("Response doesn't mention expected comparison objects")
            
        # Check for weight accuracy
        if not self._verify_weight_accuracy(text, weight_result):
            warnings.append("Response may contain inaccurate weight information")
            
        # Check for inappropriate content
        if self._contains_inappropriate_content(text):
            errors.append("Response contains inappropriate content")
            
        # Calculate confidence based on validation results
        confidence = self._calculate_validation_confidence(
            errors, warnings, parsed_response.confidence
        )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=confidence
        )
        
    def _contains_comparison(self, text: str) -> bool:
        """Check if text contains actual comparisons"""
        
        comparison_patterns = [
            r'\d+\s*(times|x)\s*(heavier|lighter|more|less)',
            r'(equivalent|equal|similar)\s*to',
            r'(about|roughly|approximately)\s*the\s*(same|size|weight)',
            r'(like|such as)\s*\w+',
            r'weighs?\s*(about|roughly)?\s*the\s*same'
        ]
        
        for pattern in comparison_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
                
        return False
        
    def _extract_mentioned_objects(self, text: str) -> List[str]:
        """Extract object names mentioned in the text"""
        
        # Common object patterns
        object_patterns = [
            r'\b(cat|dog|elephant|car|truck|piano|book|phone|apple|orange)\b',
            r'\b\w+\s*(ball|phone|laptop|computer|animal|vehicle)\b',
        ]
        
        mentioned = []
        for pattern in object_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            mentioned.extend(matches)
            
        return list(set(mentioned))  # Remove duplicates
        
    def _verify_weight_accuracy(self, text: str, weight_result: WeightItem) -> bool:
        """Basic verification of weight accuracy in response"""
        
        # Look for weight mentions
        weight_patterns = [
            r'(\d+(?:\.\d+)?)\s*(kg|kilogram|pound|lb|gram|g)',
            r'(\d+(?:\.\d+)?)\s*(ton|tonne|ounce|oz)'
        ]
        
        for pattern in weight_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for value, unit in matches:
                try:
                    mentioned_value = float(value)
                    # Basic sanity check - mentioned weight should be in reasonable range
                    if unit.lower() in ['kg', 'kilogram']:
                        expected = float(weight_result.weight_kg)
                        if abs(mentioned_value - expected) / expected > 0.5:  # 50% tolerance
                            return False
                except ValueError:
                    continue
                    
        return True  # Default to valid if we can't verify
        
    def _contains_inappropriate_content(self, text: str) -> bool:
        """Check for inappropriate content"""
        
        inappropriate_patterns = [
            r'\b(offensive|inappropriate|explicit)\b',
            # Add more patterns as needed
        ]
        
        for pattern in inappropriate_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
                
        return False
        
    def _calculate_validation_confidence(
        self,
        errors: List[str],
        warnings: List[str],
        base_confidence: float
    ) -> float:
        """Calculate confidence based on validation results"""
        
        confidence = base_confidence
        
        # Reduce confidence for errors
        confidence -= len(errors) * 0.3
        
        # Reduce confidence for warnings
        confidence -= len(warnings) * 0.1
        
        return max(0.0, min(1.0, confidence))


class ResponseEnhancer:
    """Enhance validated responses with additional data"""
    
    def __init__(self, config: ConfigLoader):
        self._config = config
        
    async def enhance(
        self,
        parsed_response: ParsedResponse,
        weight_result: WeightItem,
        comparison_objects: List[ComparisonObject],
        include_visualization: bool
    ) -> Dict[str, Any]:
        """Enhance response with metadata and suggestions"""
        
        enhanced = {
            'comparison_text': self._polish_comparison_text(
                parsed_response.comparison_text
            ),
            'confidence_score': parsed_response.confidence
        }
        
        # Add visualization if requested
        if include_visualization:
            enhanced['visualization_prompt'] = self._generate_visualization_prompt(
                weight_result, comparison_objects
            )
            enhanced['visualization_suggestions'] = self._get_visualization_suggestions(
                float(weight_result.weight_kg)
            )
            
        return enhanced
        
    def _polish_comparison_text(self, text: str) -> str:
        """Polish the comparison text for better readability"""
        
        # Ensure proper capitalization
        if text and not text[0].isupper():
            text = text[0].upper() + text[1:]
            
        # Ensure proper ending punctuation
        if text and text[-1] not in '.!?':
            text += '.'
            
        # Fix common grammar issues
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces
        text = re.sub(r'\s+([.!?])', r'\1', text)  # Space before punctuation
        
        return text
        
    def _generate_visualization_prompt(
        self,
        weight_result: WeightItem,
        comparison_objects: List[ComparisonObject]
    ) -> str:
        """Generate prompt for visualization creation"""
        
        prompt_parts = [
            f"Create a visual comparison showing {weight_result.weight_display}."
        ]
        
        if comparison_objects:
            object_names = [obj.name for obj in comparison_objects[:2]]
            prompt_parts.append(
                f"Include these objects for scale: {', '.join(object_names)}."
            )
            
        prompt_parts.append(
            "Use a clean, modern style with clear labels and accurate proportions."
        )
        
        return " ".join(prompt_parts)
        
    def _get_visualization_suggestions(self, weight_kg: float) -> List[str]:
        """Get visualization suggestions based on weight"""
        
        suggestions = []
        
        if weight_kg < 0.01:
            suggestions.extend([
                "Microscope view comparison",
                "Scale with magnification indicator",
                "Scientific measurement context"
            ])
        elif weight_kg < 1:
            suggestions.extend([
                "Hand-held objects comparison",
                "Desk or table surface view",
                "Close-up detailed view"
            ])
        elif weight_kg < 100:
            suggestions.extend([
                "Person holding or standing next to objects",
                "Room or indoor environment",
                "Multiple familiar objects grouped"
            ])
        else:
            suggestions.extend([
                "Outdoor or large space setting",
                "Vehicle or building for scale",
                "Aerial or wide-angle view"
            ])
            
        return suggestions[:3]  # Return top 3 suggestions


class ResponseProcessor:
    """Process and enhance AI responses"""
    
    def __init__(self, config: ConfigLoader):
        self._config = config
        self._parser = ResponseParser()
        self._validator = ResponseValidator()
        self._enhancer = ResponseEnhancer(config)
        
    async def process(
        self,
        raw_response: str,
        weight_result: WeightItem,
        comparison_objects: List[ComparisonObject],
        include_visualization: bool
    ) -> Dict[str, Any]:
        """Process raw AI response into structured format"""
        
        # Parse response
        parsed = self._parser.parse_ai_response(raw_response)
        
        # Validate response
        validation_result = self._validator.validate(
            parsed, weight_result, comparison_objects
        )
        
        if not validation_result.is_valid:
            error_msg = "; ".join(validation_result.errors)
            raise InvalidResponseError(f"Response validation failed: {error_msg}")
            
        # Log warnings
        for warning in validation_result.warnings:
            logger.warning(f"Response validation warning: {warning}")
            
        # Update confidence based on validation
        parsed.confidence = validation_result.confidence_score
        
        # Enhance response
        enhanced = await self._enhancer.enhance(
            parsed, weight_result, comparison_objects,
            include_visualization
        )
        
        return enhanced
        
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics and health info"""
        
        return {
            "processor_version": "1.0.0",
            "validation_enabled": True,
            "enhancement_enabled": True,
            "min_response_length": 20,
            "max_response_length": 800,
            "default_confidence": 0.8
        }