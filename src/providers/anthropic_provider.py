"""
Anthropic Claude Provider for SizeComparator.

This module implements the Anthropic provider with Claude 3 models,
optimized prompting, and Anthropic-specific features as specified in
ANTHROPIC_PROVIDER_SPEC.md.
"""

import os
import asyncio
import json
import re
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from decimal import Decimal

import anthropic
from anthropic import AsyncAnthropic, APIError, APIConnectionError, RateLimitError, APIStatusError

from .base import AIProviderBase, ProviderCapabilities
from ..models.requests import WeightComparisonRequest
from ..models.responses import (
    WeightComparisonResponse,
    ComparisonAnalysis,
    AIVisualizationPrompt,
    ResponseMetadata
)
from ..models.weight import ProcessedWeight
from ..models.providers import AIProviderMetadata
from ..core.exceptions import AIProviderException, AIProviderRateLimitException, ValidationException


class ClaudeModel:
    """Claude model definitions with their properties."""
    # Claude 3 models
    OPUS = "claude-3-opus-20240229"
    SONNET = "claude-3-sonnet-20240229"
    HAIKU = "claude-3-haiku-20240307"
    
    # Model properties
    PROPERTIES = {
        OPUS: {
            "context_window": 200000,
            "max_output": 4096,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "complexity_score": 10  # For intelligent selection
        },
        SONNET: {
            "context_window": 200000,
            "max_output": 4096,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "complexity_score": 5
        },
        HAIKU: {
            "context_window": 200000,
            "max_output": 4096,
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125,
            "complexity_score": 1
        }
    }


class AnthropicProvider(AIProviderBase):
    """
    Anthropic Claude provider implementation.
    
    Features:
    - Claude 3 model support (Opus, Sonnet, Haiku)
    - Intelligent model selection based on complexity
    - XML tag patterns for structured output
    - System prompt optimization
    - Anthropic-specific rate limiting (1000 RPM)
    - Vision capability support
    - Beta features flag support
    """
    
    def __init__(self, config: Dict[str, Any], logger=None):
        """Initialize Anthropic provider with configuration."""
        super().__init__(config, logger)
        
        # Get API key from environment or config
        self.api_key = os.getenv('SIZECOMPARATOR_ANTHROPIC_API_KEY') or config.get('api_key')
        if not self.api_key:
            raise ValueError("Anthropic API key not found in environment or config")
        
        # Initialize Anthropic client
        self.client = AsyncAnthropic(
            api_key=self.api_key,
            base_url=config.get('base_url', 'https://api.anthropic.com'),
            timeout=config.get('timeout_seconds', 60.0),
            max_retries=0  # We handle retries ourselves
        )
        
        # Model selection
        self.default_model = config.get('model', ClaudeModel.SONNET)
        self.enable_intelligent_selection = config.get('intelligent_model_selection', True)
        self.beta_features = config.get('beta_features', False)
        
        # Anthropic-specific settings
        self.use_xml_tags = config.get('use_xml_tags', True)
        self.safety_enabled = config.get('safety_enabled', True)
        
        self._log_structured_event(
            'info',
            'Anthropic provider initialized',
            model=self.default_model,
            beta_features=self.beta_features
        )
    
    def _get_capabilities(self) -> ProviderCapabilities:
        """Get Anthropic provider capabilities."""
        model_props = ClaudeModel.PROPERTIES.get(self.default_model, ClaudeModel.PROPERTIES[ClaudeModel.SONNET])
        
        return ProviderCapabilities(
            supports_streaming=True,
            supports_function_calling=False,  # Claude doesn't have native function calling
            supports_vision=True,  # Claude 3 supports vision
            supports_system_prompts=True,
            max_context_tokens=model_props["context_window"],
            max_output_tokens=model_props["max_output"],
            cost_per_1k_input_tokens=model_props["cost_per_1k_input"],
            cost_per_1k_output_tokens=model_props["cost_per_1k_output"],
            rate_limit_rpm=1000,  # Anthropic's rate limit
            rate_limit_tpm=2000000  # Token limit
        )
    
    def _select_model_for_request(self, request: WeightComparisonRequest) -> str:
        """
        Intelligently select Claude model based on request complexity.
        
        Args:
            request: Weight comparison request
            
        Returns:
            Selected model name
        """
        if not self.enable_intelligent_selection:
            return self.default_model
        
        # Calculate complexity score
        complexity = 0
        
        # Length of item names
        if len(request.item1) > 50 or len(request.item2) > 50:
            complexity += 2
        
        # Complex weight parsing needed
        if isinstance(request.item1_weight.value, str) or isinstance(request.item2_weight.value, str):
            complexity += 2
        
        # Detailed comparison requested
        if request.comparison_type == "detailed":
            complexity += 3
        
        # Visualization requested
        if request.include_visualization:
            complexity += 2
        
        # Select model based on complexity
        if complexity >= 7:
            selected_model = ClaudeModel.OPUS
        elif complexity >= 4:
            selected_model = ClaudeModel.SONNET
        else:
            selected_model = ClaudeModel.HAIKU
        
        self._log_structured_event(
            'debug',
            'Model selected based on complexity',
            complexity_score=complexity,
            selected_model=selected_model
        )
        
        return selected_model
    
    def _build_system_message(self) -> str:
        """Build Claude-optimized system message with constitutional AI principles."""
        base_message = """You are an expert weight comparison analyst with deep knowledge of objects, materials, and measurements. Your task is to provide accurate, helpful, and educational weight comparisons.

CORE PRINCIPLES:
1. Accuracy: Provide scientifically accurate weight information
2. Clarity: Use clear, understandable language
3. Safety: Avoid harmful, dangerous, or inappropriate comparisons
4. Educational value: Help users understand weight relationships intuitively

RESPONSE REQUIREMENTS:
- Always respond with valid JSON in the exact format specified
- Include both metric and imperial measurements when relevant
- Provide confidence scores based on the reliability of your knowledge
- Explain your reasoning clearly
- If uncertain about exact weights, provide reasonable estimates with appropriate confidence levels

SAFETY GUIDELINES:
- Never compare weights of people, body parts, or sensitive personal items
- Avoid comparisons involving weapons, explosives, or dangerous materials
- Do not provide information that could be used for harmful purposes
- Focus on everyday objects, animals, foods, and common materials"""
        
        if self.use_xml_tags:
            # Add XML structure for better Claude performance
            return f"""<instructions>
{base_message}
</instructions>

<output_format>
You must respond with a JSON object containing these exact fields:
- item1: object with parsed weight data
- item2: object with parsed weight data  
- comparison: object with ratio, explanation, and examples
- visualization_prompt: string describing visual comparison
- metadata: object with processing metadata
</output_format>"""
        
        return base_message
    
    def _build_user_message(self, request: WeightComparisonRequest) -> str:
        """Build Claude-optimized user message with XML tags for structure."""
        if self.use_xml_tags:
            return f"""<task>
Compare the weights of these two items and provide a detailed analysis.
</task>

<items>
<item1>
Name: {request.item1}
Weight: {request.item1_weight.value} {getattr(request.item1_weight, 'unit', '')}
Confidence: {getattr(request.item1_weight, 'confidence', 1.0)}
</item1>

<item2>
Name: {request.item2}
Weight: {request.item2_weight.value} {getattr(request.item2_weight, 'unit', '')}
Confidence: {getattr(request.item2_weight, 'confidence', 1.0)}
</item2>
</items>

<requirements>
1. Parse and normalize the weights to kilograms
2. Calculate the weight ratio (item1/item2)
3. Provide a clear explanation of the weight difference
4. Include 2-3 contextual examples to help understand the relationship
5. Generate a visualization prompt for the comparison
6. Return confidence scores for all estimates
</requirements>

<json_format>
{{
    "item1": {{
        "name": "string",
        "original_input": "string",
        "weight_kg": number,
        "weight_display": "string",
        "unit_used": "string",
        "parsing_confidence": number
    }},
    "item2": {{
        "name": "string",
        "original_input": "string", 
        "weight_kg": number,
        "weight_display": "string",
        "unit_used": "string",
        "parsing_confidence": number
    }},
    "comparison": {{
        "ratio": number,
        "explanation": "string",
        "confidence": number,
        "contextual_examples": ["string", "string"]
    }},
    "visualization_prompt": "string",
    "metadata": {{
        "model_used": "string",
        "analysis_type": "weight_comparison",
        "timestamp": "string",
        "request_id": "string"
    }}
}}
</json_format>

Respond ONLY with the JSON object. No additional text or formatting."""
        
        else:
            # Fallback to simpler format without XML tags
            return super()._build_user_message(request)
    
    async def _generate_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion using Anthropic's API.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters (max_tokens, temperature, etc.)
            
        Returns:
            Raw Anthropic response
        """
        model = kwargs.get('model', self.default_model)
        max_tokens = kwargs.get('max_tokens', 1024)
        temperature = kwargs.get('temperature', 0.7)
        
        # Extract system message if present
        system_message = None
        user_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            else:
                user_messages.append(msg)
        
        try:
            # Make API call
            response = await self.client.messages.create(
                model=model,
                system=system_message,
                messages=user_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                # Anthropic-specific parameters
                top_k=kwargs.get('top_k', 0),  # 0 disables top-k sampling
                top_p=kwargs.get('top_p', 1.0),
                stop_sequences=kwargs.get('stop_sequences', None),
                metadata=kwargs.get('metadata', None)
            )
            
            # Return standardized response
            return {
                'content': response.content[0].text if response.content else "",
                'model': response.model,
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                    'total_tokens': response.usage.input_tokens + response.usage.output_tokens
                },
                'stop_reason': response.stop_reason,
                'id': response.id
            }
            
        except RateLimitError as e:
            raise AIProviderRateLimitException(
                f"Anthropic rate limit exceeded: {str(e)}",
                details={"provider": "anthropic", "original_error": str(e)}
            )
        except APIConnectionError as e:
            raise AIProviderException(
                f"Anthropic connection error: {str(e)}",
                details={"provider": "anthropic", "error_type": "connection", "original_error": str(e)}
            )
        except APIStatusError as e:
            raise AIProviderException(
                f"Anthropic API error: {str(e)}",
                details={"provider": "anthropic", "error_type": "api_status", "status_code": e.status_code, "original_error": str(e)}
            )
        except Exception as e:
            raise AIProviderException(
                f"Unexpected Anthropic error: {str(e)}",
                details={"provider": "anthropic", "error_type": "unexpected", "original_error": str(e)}
            )
    
    async def _parse_provider_response(
        self,
        response: Dict[str, Any],
        request: WeightComparisonRequest
    ) -> WeightComparisonResponse:
        """
        Parse Anthropic response into standardized format.
        
        Args:
            response: Raw Anthropic response
            request: Original comparison request
            
        Returns:
            Standardized weight comparison response
        """
        content = response.get('content', '')
        
        # Extract JSON from response
        json_data = self._extract_json_from_response(content)
        
        if not json_data:
            raise AIProviderException(
                "Failed to extract valid JSON from Anthropic response",
                details={"provider": "anthropic", "error_type": "response_parsing"}
            )
        
        # Parse item weights
        item1_data = json_data.get('item1', {})
        item2_data = json_data.get('item2', {})
        comparison_data = json_data.get('comparison', {})
        
        # Create processed weights
        item1 = ProcessedWeight(
            original_input=request.item1_weight,
            parsed_value=Decimal(str(item1_data.get('weight_kg', 0))),
            unit_used=item1_data.get('unit_used', 'kg'),
            display_value=item1_data.get('weight_display', ''),
            parsing_confidence=item1_data.get('parsing_confidence', 0.8),
            name=request.item1
        )
        
        item2 = ProcessedWeight(
            original_input=request.item2_weight,
            parsed_value=Decimal(str(item2_data.get('weight_kg', 0))),
            unit_used=item2_data.get('unit_used', 'kg'),
            display_value=item2_data.get('weight_display', ''),
            parsing_confidence=item2_data.get('parsing_confidence', 0.8),
            name=request.item2
        )
        
        # Create comparison analysis
        weight_ratio = Decimal(str(comparison_data.get('ratio', 1.0)))
        heavier_item = "item1" if weight_ratio > 1 else ("item2" if weight_ratio < 1 else "equal")
        
        analysis = ComparisonAnalysis(
            weight_ratio=weight_ratio,
            percentage_difference=Decimal(str(abs(weight_ratio - 1) * 100)),
            absolute_difference=ProcessedWeight(
                original_input={"value": abs(item1.parsed_value - item2.parsed_value)},
                parsed_value=abs(item1.parsed_value - item2.parsed_value),
                unit_used="kg",
                display_value=f"{abs(item1.parsed_value - item2.parsed_value):.2f} kg",
                parsing_confidence=1.0
            ),
            heavier_item=heavier_item,
            significance_level=self._determine_significance(weight_ratio),
            comparison_category=self._determine_category(request.item1, request.item2),
            equivalent_objects=self._create_equivalent_objects(comparison_data.get('contextual_examples', []))
        )
        
        # Create visualization prompt
        visualization = None
        if request.include_visualization and json_data.get('visualization_prompt'):
            visualization = AIVisualizationPrompt(
                prompt_text=json_data['visualization_prompt'],
                provider_used="anthropic",
                generation_time_ms=int(response.get('usage', {}).get('total_tokens', 0) * 0.5),  # Estimate
                confidence_score=comparison_data.get('confidence', 0.8),
                prompt_metadata={
                    'model': response.get('model', self.default_model),
                    'stop_reason': response.get('stop_reason', 'unknown')
                }
            )
        
        # Create metadata
        metadata = ResponseMetadata(
            request_id=request.request_id,
            processing_time_ms=int(time.time() * 1000),  # Will be updated by caller
            component_timings={
                'ai_generation': int(response.get('usage', {}).get('total_tokens', 0) * 0.5)
            },
            ai_provider_used="anthropic",
            ai_response_time_ms=int(response.get('usage', {}).get('total_tokens', 0) * 0.5),
            cache_hit=False,
            warnings=[],
            api_version="1.0.0",
            timestamp=datetime.utcnow()
        )
        
        return WeightComparisonResponse(
            item1=item1,
            item2=item2,
            analysis=analysis,
            visualization=visualization,
            metadata=metadata
        )
    
    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from Claude's response.
        
        Claude might include additional text or formatting, so we need to
        extract the JSON carefully.
        
        Args:
            content: Raw response content
            
        Returns:
            Parsed JSON data or None
        """
        # Try direct JSON parsing first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from code blocks
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in the content
        json_start = content.find('{')
        json_end = content.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            try:
                return json.loads(content[json_start:json_end + 1])
            except json.JSONDecodeError:
                pass
        
        # Log failure for debugging
        self._log_structured_event(
            'error',
            'Failed to extract JSON from Claude response',
            response_preview=content[:200]
        )
        
        return None
    
    def _determine_significance(self, ratio: Decimal) -> str:
        """Determine significance level based on weight ratio."""
        ratio_float = float(ratio)
        
        if abs(ratio_float - 1) < 0.01:
            return "negligible"
        elif ratio_float < 2:
            return "small"
        elif ratio_float < 10:
            return "moderate"
        elif ratio_float < 100:
            return "large"
        else:
            return "extreme"
    
    def _determine_category(self, item1: str, item2: str) -> str:
        """Determine comparison category based on item types."""
        # Simple heuristic - could be enhanced with more sophisticated classification
        animals = ['elephant', 'dog', 'cat', 'bird', 'fish', 'horse', 'cow']
        vehicles = ['car', 'truck', 'bike', 'plane', 'boat', 'train']
        food = ['apple', 'bread', 'pizza', 'burger', 'rice', 'potato']
        
        item1_lower = item1.lower()
        item2_lower = item2.lower()
        
        item1_is_animal = any(animal in item1_lower for animal in animals)
        item2_is_animal = any(animal in item2_lower for animal in animals)
        
        item1_is_vehicle = any(vehicle in item1_lower for vehicle in vehicles)
        item2_is_vehicle = any(vehicle in item2_lower for vehicle in vehicles)
        
        item1_is_food = any(f in item1_lower for f in food)
        item2_is_food = any(f in item2_lower for f in food)
        
        if item1_is_animal and item2_is_animal:
            return "animal_vs_animal"
        elif item1_is_vehicle and item2_is_vehicle:
            return "vehicle_vs_vehicle"
        elif item1_is_food and item2_is_food:
            return "food_vs_food"
        elif (item1_is_animal and item2_is_vehicle) or (item1_is_vehicle and item2_is_animal):
            return "animal_vs_vehicle"
        else:
            return "mixed"
    
    def _create_equivalent_objects(self, examples: List[str]) -> List[Dict[str, Any]]:
        """Convert contextual examples to equivalent objects format."""
        equivalent_objects = []
        
        for example in examples[:5]:  # Limit to 5 examples
            equivalent_objects.append({
                "description": example,
                "weight_kg": None,  # Could be enhanced to extract weight if mentioned
                "confidence": 0.8
            })
        
        return equivalent_objects
    
    async def generate_comparison(
        self,
        request: WeightComparisonRequest
    ) -> WeightComparisonResponse:
        """
        Generate weight comparison with intelligent model selection.
        
        Overrides base implementation to add model selection.
        """
        # Select appropriate model
        selected_model = self._select_model_for_request(request)
        
        # Store original model and temporarily override
        original_model = self.default_model
        self.default_model = selected_model
        
        try:
            # Call parent implementation
            result = await super().generate_comparison(request)
            
            # Add model info to metadata
            if result.visualization and result.visualization.prompt_metadata:
                result.visualization.prompt_metadata['selected_model'] = selected_model
                result.visualization.prompt_metadata['model_selection_reason'] = 'intelligent_selection'
            
            return result
            
        finally:
            # Restore original model
            self.default_model = original_model