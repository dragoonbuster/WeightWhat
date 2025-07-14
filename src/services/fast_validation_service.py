"""
Fast AI Validation Service - Optimized for <2 second response time
"""

import asyncio
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from models.mvp import MVPComparisonRequest, MVPComparisonResponse
from services.weight_processor import WeightProcessor
from services.shared.ai_provider_manager import AIProviderManager
from services.shared.fallback_data import FallbackDataManager
from services.shared.interfaces import BaseComparisonService


@dataclass
class FastValidationResult:
    """Fast validation result"""
    final_comparison: str
    validation_method: str
    total_time_ms: int
    calls_made: int
    confidence_score: float


class FastValidationService(BaseComparisonService):
    """Optimized AI validation service for <2 second responses"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize shared components
        self.weight_processor = WeightProcessor()
        self.ai_provider_manager = AIProviderManager()
        self.fallback_data_manager = FallbackDataManager()
        
        # Performance configuration
        self.fast_validation_enabled = True
        self.parallel_calls = 2  # Reduced from 3
        self.max_call_timeout = 4000  # 4 seconds max per call
        self.validation_timeout = 2000  # 2 seconds for validation
        
        # Pre-validation patterns (detect obviously wrong responses)
        self.error_patterns = [
            (r'(\d{1,3}),(\d{3})', r'\1\2'),  # "100,000" -> "100000" for detection
            (r'(\d+)\s*million', lambda m: str(int(m.group(1)) * 1000000)),
            (r'(\d+)\s*thousand', lambda m: str(int(m.group(1)) * 1000)),
        ]
    
    async def create_comparison(self, request: MVPComparisonRequest) -> MVPComparisonResponse:
        """Create comparison - required by BaseComparisonService"""
        return await self.create_fast_validated_comparison(request)
    
    async def create_fast_validated_comparison(self, request: MVPComparisonRequest) -> MVPComparisonResponse:
        """Create comparison with fast validation optimizations"""
        
        start_time = time.time()
        request_id = str(hash(request.weight_input))[:8]
        
        try:
            # Step 1: Process weight (fast)
            processed_weight = self.weight_processor.process_weight(request.weight_input)
            weight_kg = float(processed_weight.weight_kg)
            
            # Step 2: Smart validation strategy based on weight
            if weight_kg < 0.1 or weight_kg > 100:
                # For extreme weights, use full validation (higher error risk)
                result = await self._full_validation_flow(request, weight_kg, processed_weight.weight_display)
            else:
                # For common weights, use fast flow
                result = await self._fast_validation_flow(request, weight_kg, processed_weight.weight_display)
            
            total_time_ms = int((time.time() - start_time) * 1000)
            
            return MVPComparisonResponse(
                comparison_text=result.final_comparison,
                weight_processed=processed_weight.weight_display,
                provider_used=f"fast_validated_{result.validation_method}_{result.calls_made}_calls",
                response_time_ms=total_time_ms,
                cached=False,
                request_id=request_id
            )
            
        except Exception as e:
            print(f"Fast validation failed, using fallback: {e}")
            # Fallback to basic comparison using fallback data
            processed_weight = self.weight_processor.process_weight(request.weight_input)
            weight_kg = float(processed_weight.weight_kg)
            fallback_text = self.fallback_data_manager.generate_fallback_comparison(
                weight_kg, processed_weight.weight_display, request.style
            )
            total_time_ms = int((time.time() - start_time) * 1000)
            
            return MVPComparisonResponse(
                comparison_text=fallback_text,
                weight_processed=processed_weight.weight_display,
                provider_used="fast_validation_fallback",
                response_time_ms=total_time_ms,
                cached=False,
                request_id=request_id
            )
    
    async def _fast_validation_flow(self, request: MVPComparisonRequest, weight_kg: float, weight_display: str) -> FastValidationResult:
        """Fast validation for common weights (1-2 calls + rule-based validation)"""
        
        # Strategy: Get 2 responses, use rules to validate, pick best
        responses = await self._get_fast_responses(request, weight_kg, weight_display)
        
        if len(responses) == 0:
            # Fallback to shared fallback data
            fallback_text = self.fallback_data_manager.generate_fallback_comparison(
                weight_kg, weight_display, "default"
            )
            return FastValidationResult(
                final_comparison=fallback_text,
                validation_method="fallback_shared",
                total_time_ms=0,
                calls_made=0,
                confidence_score=0.5
            )
        
        # Rule-based validation (very fast)
        validated_responses = self._rule_based_validation(weight_kg, responses)
        
        if len(validated_responses) > 0:
            # Pick best validated response
            best_response = self._select_best_response(validated_responses)
            return FastValidationResult(
                final_comparison=best_response,
                validation_method="rule_based",
                total_time_ms=0,
                calls_made=len(responses),
                confidence_score=0.8
            )
        else:
            # All responses failed rules, return first one
            return FastValidationResult(
                final_comparison=responses[0],
                validation_method="rule_fallback",
                total_time_ms=0,
                calls_made=len(responses),
                confidence_score=0.3
            )
    
    async def _full_validation_flow(self, request: MVPComparisonRequest, weight_kg: float, weight_display: str) -> FastValidationResult:
        """Full validation for extreme weights (3 calls + AI validation)"""
        
        # Use original validation logic but with timeouts
        responses = await self._get_multiple_responses(request, 3)
        
        if len(responses) >= 2:
            # Quick AI validation with shorter prompt
            validation_result = await self._quick_ai_validation(weight_kg, weight_display, responses)
            return FastValidationResult(
                final_comparison=validation_result,
                validation_method="ai_validated",
                total_time_ms=0,
                calls_made=len(responses) + 1,
                confidence_score=0.9
            )
        else:
            # Not enough responses, use rule-based
            validated = self._rule_based_validation(weight_kg, responses)
            return FastValidationResult(
                final_comparison=validated[0] if validated else responses[0],
                validation_method="mixed_fallback",
                total_time_ms=0,
                calls_made=len(responses),
                confidence_score=0.6
            )
    
    async def _get_fast_responses(self, request: MVPComparisonRequest, weight_kg: float, weight_display: str) -> List[str]:
        """Get 2 responses quickly with aggressive timeout"""
        
        tasks = []
        for i in range(self.parallel_calls):
            task = self._single_fast_call(request, f"fast_{i+1}")
            tasks.append(task)
        
        try:
            # Aggressive timeout - fail fast
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=3.0  # 3 seconds max for both calls
            )
            
            successful_responses = []
            for result in results:
                if isinstance(result, str) and result and len(result) > 20:
                    successful_responses.append(result)
            
            return successful_responses
            
        except asyncio.TimeoutError:
            print("Fast validation timed out")
            return []
    
    async def _get_multiple_responses(self, request: MVPComparisonRequest, count: int) -> List[str]:
        """Get multiple responses with timeout"""
        
        tasks = []
        for i in range(count):
            task = self._single_fast_call(request, f"full_{i+1}")
            tasks.append(task)
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=4.0  # 4 seconds max for all calls
            )
            
            successful_responses = []
            for result in results:
                if isinstance(result, str) and result and len(result) > 20:
                    successful_responses.append(result)
            
            return successful_responses
            
        except asyncio.TimeoutError:
            print("Multiple response calls timed out")
            return []
    
    async def _single_fast_call(self, request: MVPComparisonRequest, call_id: str) -> str:
        """Single AI call with aggressive timeout using shared provider manager"""
        try:
            # Process weight to get clean values
            processed_weight = self.weight_processor.process_weight(request.weight_input)
            weight_kg = float(processed_weight.weight_kg)
            
            # Build prompt using shared manager
            prompt = self.ai_provider_manager.build_prompt(
                weight_kg, processed_weight.weight_display, request.style
            )
            
            # Make single provider call (OpenAI preferred for fast validation)
            content = await self.ai_provider_manager._single_provider_call(
                prompt, call_id, timeout=3.0
            )
            
            return content if content else ""
            
        except Exception as e:
            print(f"Fast call {call_id} failed: {e}")
            return ""
    
    def _rule_based_validation(self, weight_kg: float, responses: List[str]) -> List[str]:
        """Fast rule-based validation using shared fallback data manager"""
        
        valid_responses = []
        
        for response in responses:
            if self._is_response_reasonable(weight_kg, response):
                valid_responses.append(response)
        
        return valid_responses
    
    def _is_response_reasonable(self, weight_kg: float, response: str) -> bool:
        """Check if response is reasonable using shared fallback data manager"""
        
        response_lower = response.lower()
        
        # Use shared validation logic for reasonableness
        # Extract potential object names and check each one
        common_objects = ["apple", "phone", "car", "elephant", "person", "cat", "dog", 
                         "piano", "bicycle", "laptop", "feather", "paperclip", "grape"]
        
        found_objects = []
        for obj in common_objects:
            if obj in response_lower:
                found_objects.append(obj)
        
        # If we found objects, check if any are reasonable
        if found_objects:
            for obj in found_objects:
                if not self.fallback_data_manager.is_reasonable_object(weight_kg, obj):
                    print(f"Rejecting response mentioning unreasonable '{obj}' for {weight_kg}kg")
                    return False
        
        # Check for number magnitude errors
        numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', response)
        for number_str in numbers:
            number = int(number_str.replace(',', ''))
            if number > weight_kg * 1000:  # More than 1000x the actual weight
                print(f"Rejecting response with number {number} for {weight_kg}kg")
                return False
        
        return True
    
    def _select_best_response(self, responses: List[str]) -> str:
        """Select best response from validated ones"""
        
        if len(responses) == 1:
            return responses[0]
        
        # Simple heuristic: prefer longer, more detailed responses
        scored_responses = []
        for response in responses:
            score = 0
            score += len(response) * 0.1  # Length bonus
            score += response.count(',') * 5  # Multiple objects bonus
            score += response.count(' or ') * 10  # Alternatives bonus
            scored_responses.append((score, response))
        
        # Return highest scoring
        return max(scored_responses, key=lambda x: x[0])[1]
    
    async def _quick_ai_validation(self, weight_kg: float, weight_display: str, responses: List[str]) -> str:
        """Quick AI validation using shared provider manager"""
        
        # Use shared AI validation method
        try:
            result = await self.ai_provider_manager.validate_responses_with_ai(
                weight_kg, weight_display, responses
            )
            return result
            
        except Exception as e:
            print(f"Quick AI validation failed: {e}")
            # Fallback to first response
            return responses[0]
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status using shared components"""
        # Get base health from shared components
        ai_health = await self.ai_provider_manager.get_health_status() if self.ai_provider_manager else {}
        
        health_status = {
            "status": "healthy",
            "service": "fast_validation_service",
            "fast_validation_enabled": self.fast_validation_enabled,
            "parallel_calls": self.parallel_calls,
            "validation_mode": "fast_optimized",
            "target_response_time": "< 2 seconds",
            "weight_processor": "available",
            "fallback_data": "available",
            "ai_providers": ai_health.get("providers", {}),
            "available_ai_providers": ai_health.get("available_count", 0)
        }
        
        return health_status
    
    async def cleanup(self):
        """Cleanup resources using shared components"""
        await super().cleanup()