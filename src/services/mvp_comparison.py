"""
MVP Comparison Service - Simplified for demo
"""

import time
import uuid
from typing import Optional, Dict, Any

from ..models.mvp import MVPComparisonRequest, MVPComparisonResponse, MVPErrorResponse
from .weight_processor import WeightProcessor
from .shared.interfaces import BaseComparisonService


class MVPComparisonService(BaseComparisonService):
    """Simplified comparison service for MVP demo"""
    
    def __init__(self):
        super().__init__()
        self.weight_processor = WeightProcessor()
        # Fallback comparisons for demo when AI providers unavailable
        self.fallback_comparisons = {
            # Weight ranges in kg with comparison objects
            (0.001, 0.01): ["a paperclip", "a feather", "a penny"],
            (0.01, 0.1): ["a strawberry", "a AAA battery", "a grape"],
            (0.1, 0.5): ["an apple", "a smartphone", "a tennis ball"],
            (0.5, 2): ["a pineapple", "a laptop", "a bag of flour"],
            (2, 10): ["a bowling ball", "a house cat", "a gallon of milk"],
            (10, 50): ["a medium dog", "a car tire", "a bag of rice"],
            (50, 200): ["a person", "a bicycle", "a washing machine"],
            (200, 1000): ["a motorcycle", "a grand piano", "a small car"],
            (1000, 5000): ["a car", "a small elephant", "a speedboat"],
            (5000, float('inf')): ["an elephant", "a truck", "a small airplane"]
        }
    
    async def create_comparison(self, request: MVPComparisonRequest) -> MVPComparisonResponse:
        """Create weight comparison - simplified MVP version"""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Step 1: Process weight input
            processed_weight = self.weight_processor.process_weight(request.weight_input)
            weight_kg = float(processed_weight.weight_kg)
            
            # Step 2: Generate comparison (fallback for MVP)
            comparison_text = self._generate_fallback_comparison(weight_kg, processed_weight.weight_display)
            
            # Step 3: Create response
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return MVPComparisonResponse(
                comparison_text=comparison_text,
                weight_processed=processed_weight.weight_display,
                provider_used="fallback",
                response_time_ms=response_time_ms,
                cached=False,
                request_id=request_id
            )
            
        except Exception as e:
            # Simple error handling for MVP
            raise MVPComparisonError(
                error=f"Failed to process weight: {str(e)}",
                error_code="WEIGHT_PROCESSING_ERROR",
                request_id=request_id,
                suggestions=[
                    "Try a format like '5 kg' or '10 pounds'",
                    "Make sure the weight is a positive number",
                    "Include a unit (kg, lbs, grams, etc.)"
                ]
            )
    
    def _generate_fallback_comparison(self, weight_kg: float, display_value: str) -> str:
        """Generate fallback comparison when AI providers unavailable"""
        
        # Find appropriate weight range
        comparison_objects = ["a medium-sized object"]  # default
        
        for (min_weight, max_weight), objects in self.fallback_comparisons.items():
            if min_weight <= weight_kg < max_weight:
                comparison_objects = objects
                break
        
        # Create comparison text
        if len(comparison_objects) == 1:
            obj = comparison_objects[0]
            return f"{display_value} is about the weight of {obj}."
        else:
            obj1, obj2 = comparison_objects[0], comparison_objects[1]
            return f"{display_value} is about the weight of {obj1} or {obj2}."
    
    def get_health_status(self) -> Dict[str, Any]:
        """Simple health check for MVP"""
        return {
            "status": "healthy",
            "service": "mvp_comparison",
            "weight_processor": "available",
            "ai_providers": "fallback_mode"
        }


class MVPComparisonError(Exception):
    """MVP-specific comparison error"""
    
    def __init__(self, error: str, error_code: str, request_id: str, suggestions: Optional[list[str]] = None):
        self.error = error
        self.error_code = error_code
        self.request_id = request_id
        self.suggestions = suggestions or []
        super().__init__(error)
    
    def to_response(self) -> MVPErrorResponse:
        """Convert to MVP error response"""
        return MVPErrorResponse(
            error=self.error,
            error_code=self.error_code,
            request_id=self.request_id,
            suggestions=self.suggestions
        )