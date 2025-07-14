"""
AI Validation Service - Improves accuracy through consensus and validation
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from models.mvp import MVPComparisonRequest, MVPComparisonResponse
from services.weight_processor import WeightProcessor
from services.shared.ai_provider_manager import AIProviderManager
from services.shared.fallback_data import FallbackDataManager
from services.shared.interfaces import BaseComparisonService


@dataclass
class ValidationResult:
    """Result of AI validation process"""
    final_comparison: str
    selected_responses: List[str]
    discarded_responses: List[str]
    validation_reasoning: str
    total_time_ms: int
    calls_made: int


class AIValidationService(BaseComparisonService):
    """Enhanced AI service with validation and consensus"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize shared components
        self.weight_processor = WeightProcessor()
        self.ai_provider_manager = AIProviderManager()
        self.fallback_data_manager = FallbackDataManager()
        
        # Configuration
        self.validation_enabled = True  # Can be configured
        self.parallel_calls = 3
        self.max_timeout_per_call = 8000  # 8 seconds max per call
        
    async def create_comparison(self, request: MVPComparisonRequest) -> MVPComparisonResponse:
        """Create comparison - required by BaseComparisonService"""
        return await self.create_validated_comparison(request)
    
    async def create_validated_comparison(self, request: MVPComparisonRequest) -> MVPComparisonResponse:
        """Create comparison with AI validation for improved accuracy"""
        
        start_time = time.time()
        
        if not self.validation_enabled:
            # Fall back to single call using shared manager if validation disabled
            processed_weight = self.weight_processor.process_weight(request.weight_input)
            weight_kg = float(processed_weight.weight_kg)
            
            # Try AI providers with fallback
            prompt = self.ai_provider_manager.build_prompt(
                weight_kg, processed_weight.weight_display, request.style
            )
            comparison_text, provider_used = await self.ai_provider_manager.generate_comparison_with_fallover(
                prompt
            )
            
            # Use fallback if AI failed
            if not comparison_text:
                comparison_text = self.fallback_data_manager.generate_fallback_comparison(
                    weight_kg, processed_weight.weight_display, request.style
                )
                provider_used = "fallback_data"
            
            total_time_ms = int((time.time() - start_time) * 1000)
            
            return MVPComparisonResponse(
                comparison_text=comparison_text,
                weight_processed=processed_weight.weight_display,
                provider_used=provider_used,
                response_time_ms=total_time_ms,
                cached=False,
                request_id=str(hash(request.weight_input))[:8]
            )
        
        request_id = request.weight_input  # Use for tracking
        
        try:
            # Step 1: Process weight to get accurate value
            processed_weight = self.weight_processor.process_weight(request.weight_input)
            weight_kg = float(processed_weight.weight_kg)
            
            # Step 2: Generate 3 parallel AI responses
            responses = await self._generate_parallel_responses(request, weight_kg, processed_weight.weight_display)
            
            if len(responses) == 0:
                # All AI calls failed, use fallback data
                fallback_text = self.fallback_data_manager.generate_fallback_comparison(
                    weight_kg, processed_weight.weight_display, request.style
                )
                total_time_ms = int((time.time() - start_time) * 1000)
                
                return MVPComparisonResponse(
                    comparison_text=fallback_text,
                    weight_processed=processed_weight.weight_display,
                    provider_used="ai_validation_fallback",
                    response_time_ms=total_time_ms,
                    cached=False,
                    request_id=str(hash(request.weight_input))[:8]
                )
            
            # Step 3: Validate responses with AI
            validation_result = await self._validate_responses(weight_kg, processed_weight.weight_display, responses, request.style)
            
            total_time_ms = int((time.time() - start_time) * 1000)
            
            return MVPComparisonResponse(
                comparison_text=validation_result.final_comparison,
                weight_processed=processed_weight.weight_display,
                provider_used=f"validated_consensus_{validation_result.calls_made}_calls",
                response_time_ms=total_time_ms,
                cached=False,
                request_id=str(hash(request_id))[:8]
            )
            
        except Exception as e:
            print(f"Validation failed, falling back to fallback data: {e}")
            # Fall back to fallback data on any error
            try:
                processed_weight = self.weight_processor.process_weight(request.weight_input)
                weight_kg = float(processed_weight.weight_kg)
                fallback_text = self.fallback_data_manager.generate_fallback_comparison(
                    weight_kg, processed_weight.weight_display, request.style
                )
                total_time_ms = int((time.time() - start_time) * 1000)
                
                return MVPComparisonResponse(
                    comparison_text=fallback_text,
                    weight_processed=processed_weight.weight_display,
                    provider_used="ai_validation_error_fallback",
                    response_time_ms=total_time_ms,
                    cached=False,
                    request_id=str(hash(request.weight_input))[:8]
                )
            except Exception as fallback_error:
                # Last resort error response
                return MVPComparisonResponse(
                    comparison_text="Unable to process weight comparison at this time.",
                    weight_processed=request.weight_input,
                    provider_used="error_fallback",
                    response_time_ms=int((time.time() - start_time) * 1000),
                    cached=False,
                    request_id=str(hash(request.weight_input))[:8]
                )
    
    async def _generate_parallel_responses(self, request: MVPComparisonRequest, weight_kg: float, weight_display: str) -> List[str]:
        """Generate 3 parallel AI responses using shared provider manager"""
        
        # Build prompt using shared manager
        prompt = self.ai_provider_manager.build_prompt(
            weight_kg, weight_display, request.style
        )
        
        # Use shared manager for parallel responses
        try:
            responses = await self.ai_provider_manager.generate_multiple_responses(
                prompt, 
                count=self.parallel_calls,
                timeout=self.max_timeout_per_call / 1000.0
            )
            
            print(f"Generated {len(responses)} successful responses from {self.parallel_calls} attempts")
            return responses
            
        except Exception as e:
            print(f"Parallel AI calls failed: {e}")
            return []
    
    async def _single_ai_call(self, request: MVPComparisonRequest, call_id: str) -> str:
        """Make a single AI call using shared provider manager"""
        try:
            # Process weight to get clean values
            processed_weight = self.weight_processor.process_weight(request.weight_input)
            weight_kg = float(processed_weight.weight_kg)
            
            # Build prompt using shared manager
            prompt = self.ai_provider_manager.build_prompt(
                weight_kg, processed_weight.weight_display, request.style
            )
            
            # Make single provider call
            content = await self.ai_provider_manager._single_provider_call(
                prompt, call_id
            )
            
            return content if content else ""
            
        except Exception as e:
            print(f"AI call {call_id} failed: {e}")
            return ""
    
    async def _validate_responses(self, weight_kg: float, weight_display: str, responses: List[str], style: str) -> ValidationResult:
        """Use AI to validate and select best responses"""
        
        if len(responses) == 1:
            # Only one response, return it
            return ValidationResult(
                final_comparison=responses[0],
                selected_responses=responses,
                discarded_responses=[],
                validation_reasoning="Only one response available",
                total_time_ms=0,
                calls_made=1
            )
        
        # Use shared AI validation from provider manager
        try:
            validated_response = await self.ai_provider_manager.validate_responses_with_ai(
                weight_kg, weight_display, responses
            )
            
            return ValidationResult(
                final_comparison=validated_response,
                selected_responses=[validated_response],
                discarded_responses=[r for r in responses if r != validated_response],
                validation_reasoning="AI validation using shared provider manager",
                total_time_ms=0,
                calls_made=len(responses) + 1
            )
            
        except Exception as e:
            print(f"Validation failed: {e}")
            # Fallback: return first response
            return ValidationResult(
                final_comparison=responses[0],
                selected_responses=[responses[0]],
                discarded_responses=responses[1:],
                validation_reasoning=f"Validation error: {e}",
                total_time_ms=0,
                calls_made=len(responses)
            )
    
    
    def _clean_weight_display(self, weight_kg: float, weight_display: str) -> str:
        """Clean weight display - delegated to shared base class"""
        # Use the shared method from base class
        return super()._clean_weight_display(weight_kg, weight_display)
    
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status including validation info using shared components"""
        # Get base health from shared components
        ai_health = await self.ai_provider_manager.get_health_status() if self.ai_provider_manager else {}
        
        health_status = {
            "status": "healthy",
            "service": "ai_validation_service",
            "validation_enabled": self.validation_enabled,
            "parallel_calls": self.parallel_calls,
            "validation_mode": "consensus_validation" if self.validation_enabled else "single_call",
            "weight_processor": "available",
            "fallback_data": "available",
            "ai_providers": ai_health.get("providers", {}),
            "available_ai_providers": ai_health.get("available_count", 0)
        }
        
        return health_status
    
    async def cleanup(self):
        """Cleanup resources using shared components"""
        await super().cleanup()