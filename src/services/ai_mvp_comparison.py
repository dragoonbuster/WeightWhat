"""
AI-Enhanced MVP Comparison Service with Real AI Providers
"""

import time
import uuid
import asyncio
import os
from typing import Optional, Dict, Any

from models.mvp import MVPComparisonRequest, MVPComparisonResponse, MVPErrorResponse
from services.weight_processor import WeightProcessor
from services.shared.ai_provider_manager import AIProviderManager
from services.shared.fallback_data import FallbackDataManager
from services.shared.interfaces import BaseComparisonService


class AIEnhancedMVPService(BaseComparisonService):
    """MVP Service with real AI integration"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize shared components
        self.weight_processor = WeightProcessor()
        self.ai_provider_manager = AIProviderManager()
        self.fallback_data_manager = FallbackDataManager()
    
    
    async def create_comparison(self, request: MVPComparisonRequest) -> MVPComparisonResponse:
        """Create AI-powered weight comparison"""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Step 1: Process weight input
            processed_weight = self.weight_processor.process_weight(request.weight_input)
            weight_kg = float(processed_weight.weight_kg)
            
            # Step 2: Try AI providers using shared manager
            prompt = self.ai_provider_manager.build_prompt(
                weight_kg, processed_weight.weight_display, request.style
            )
            comparison_text, provider_used = await self.ai_provider_manager.generate_comparison_with_fallover(
                prompt
            )
            
            # Use shared fallback data if all AI providers fail
            if not comparison_text:
                comparison_text = self.fallback_data_manager.generate_fallback_comparison(
                    weight_kg, processed_weight.weight_display, request.style
                )
                provider_used = "fallback_shared"
            
            # Step 3: Create response
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return MVPComparisonResponse(
                comparison_text=comparison_text,
                weight_processed=processed_weight.weight_display,
                provider_used=provider_used,
                response_time_ms=response_time_ms,
                cached=False,
                request_id=request_id
            )
            
        except Exception as e:
            # Fallback on any error using shared fallback data
            print(f"Error in AI comparison: {e}")
            try:
                processed_weight = self.weight_processor.process_weight(request.weight_input)
                weight_kg = float(processed_weight.weight_kg)
                fallback_text = self.fallback_data_manager.generate_fallback_comparison(
                    weight_kg, processed_weight.weight_display, request.style
                )
                response_time_ms = int((time.time() - start_time) * 1000)
                
                return MVPComparisonResponse(
                    comparison_text=fallback_text,
                    weight_processed=processed_weight.weight_display,
                    provider_used="fallback_due_to_error",
                    response_time_ms=response_time_ms,
                    cached=False,
                    request_id=request_id
                )
            except Exception as fallback_error:
                # Last resort error response
                return MVPComparisonResponse(
                    comparison_text="Unable to process weight comparison at this time.",
                    weight_processed=request.weight_input,
                    provider_used="error_fallback",
                    response_time_ms=int((time.time() - start_time) * 1000),
                    cached=False,
                    request_id=request_id
                )
    
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Enhanced health check with AI provider status using shared components"""
        # Get base health from shared components
        ai_health = await self.ai_provider_manager.get_health_status() if self.ai_provider_manager else {}
        
        status = {
            "status": "healthy",
            "service": "ai_enhanced_mvp",
            "weight_processor": "available",
            "fallback_data": "available",
            "ai_providers": ai_health.get("providers", {}),
            "available_ai_providers": ai_health.get("available_count", 0),
            "primary_mode": ai_health.get("primary_mode", "fallback_only")
        }
        
        return status

    async def cleanup(self):
        """Cleanup resources using shared components"""
        await super().cleanup()