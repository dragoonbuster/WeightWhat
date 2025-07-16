"""
Enhanced Fallback Service with Comprehensive Response Repository

This service uses pre-generated AI responses organized by weight ranges and styles
to provide high-quality fallback comparisons when AI providers are unavailable.
"""

import json
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..models.mvp import MVPComparisonRequest, MVPComparisonResponse
from .shared.interfaces import BaseComparisonService
from .shared.fallback_data import FallbackDataManager
from .weight_processor import WeightProcessor
from .fallback_response_generator import FallbackResponse, WeightRange


class EnhancedFallbackService(BaseComparisonService):
    """Enhanced fallback service using comprehensive repository"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.weight_processor = WeightProcessor()
        self.basic_fallback = FallbackDataManager()
        
        # Repository configuration
        self.repository_file = Path("fallback_responses.json")
        self.repository: Dict[str, Dict[str, List[dict]]] = {}
        self.used_responses: Dict[str, List[int]] = {}  # Track used indices per category
        
        # Weight ranges (matching generator)
        self.weight_ranges = [
            WeightRange(0.0001, 0.001, "microscopic"),
            WeightRange(0.001, 0.01, "tiny"),
            WeightRange(0.01, 0.1, "very_small"),
            WeightRange(0.1, 1.0, "small"),
            WeightRange(1.0, 10.0, "light"),
            WeightRange(10.0, 100.0, "moderate"),
            WeightRange(100.0, 1000.0, "medium"),
            WeightRange(1000.0, 10000.0, "heavy"),
            WeightRange(10000.0, 100000.0, "very_heavy"),
            WeightRange(100000.0, float('inf'), "extreme")
        ]
        
        # Load repository on initialization
        self._load_repository()
    
    def _load_repository(self) -> bool:
        """Load the comprehensive fallback repository"""
        
        if not self.repository_file.exists():
            print(f"Enhanced fallback repository not found at {self.repository_file}")
            return False
        
        try:
            with open(self.repository_file, 'r') as f:
                data = json.load(f)
            
            # Extract repository data
            self.repository = data.get("repository", {})
            
            # Initialize used response tracking
            for range_name in self.repository:
                for style in self.repository[range_name]:
                    key = f"{range_name}_{style}"
                    self.used_responses[key] = []
            
            total_responses = data.get("total_responses", 0)
            print(f"Loaded enhanced fallback repository with {total_responses} responses")
            return True
            
        except Exception as e:
            print(f"Error loading enhanced fallback repository: {e}")
            return False
    
    async def create_comparison(self, request: MVPComparisonRequest) -> MVPComparisonResponse:
        """Create comparison using enhanced fallback system"""
        
        start_time = time.time()
        request_id = str(hash(request.weight_input))[:8]
        
        try:
            # Process weight
            processed_weight = self.weight_processor.process_weight(request.weight_input)
            weight_kg = float(processed_weight.weight_kg)
            
            # Get enhanced fallback response
            comparison_text = self._get_enhanced_fallback(
                weight_kg,
                processed_weight.weight_display,
                request.style or "default"
            )
            
            # If no enhanced fallback available, use basic fallback
            if not comparison_text:
                comparison_text = self.basic_fallback.generate_fallback_comparison(
                    weight_kg,
                    processed_weight.weight_display,
                    request.style or "default"
                )
            
            total_time_ms = int((time.time() - start_time) * 1000)
            
            return MVPComparisonResponse(
                comparison_text=comparison_text,
                weight_processed=processed_weight.weight_display,
                provider_used="enhanced_fallback",
                response_time_ms=total_time_ms,
                cached=True,  # Mark as cached since using pre-generated
                request_id=request_id
            )
            
        except Exception as e:
            print(f"Enhanced fallback service error: {e}")
            # Final fallback to basic service
            processed_weight = self.weight_processor.process_weight(request.weight_input)
            comparison_text = self.basic_fallback.generate_fallback_comparison(
                float(processed_weight.weight_kg),
                processed_weight.weight_display,
                request.style or "default"
            )
            
            total_time_ms = int((time.time() - start_time) * 1000)
            
            return MVPComparisonResponse(
                comparison_text=comparison_text,
                weight_processed=processed_weight.weight_display,
                provider_used="basic_fallback",
                response_time_ms=total_time_ms,
                cached=False,
                request_id=request_id
            )
    
    def _get_enhanced_fallback(self, weight_kg: float, weight_display: str, style: str) -> Optional[str]:
        """Get enhanced fallback response from repository"""
        
        # Find appropriate weight range
        weight_range = None
        for range_obj in self.weight_ranges:
            if range_obj.contains(weight_kg):
                weight_range = range_obj
                break
        
        if not weight_range:
            print(f"No weight range found for {weight_kg}kg")
            return None
        
        # Get responses for this range and style
        responses = self.repository.get(weight_range.name, {}).get(style, [])
        
        if not responses:
            # Try default style if requested style not available
            if style != "default":
                responses = self.repository.get(weight_range.name, {}).get("default", [])
        
        if not responses:
            print(f"No responses found for {weight_range.name} {style}")
            return None
        
        # Select response with rotation to avoid repetition
        response_data = self._select_response_with_rotation(
            responses,
            f"{weight_range.name}_{style}"
        )
        
        if not response_data:
            return None
        
        # Adapt response to match requested weight display
        comparison_text = response_data.get("comparison_text", "")
        
        # Replace the weight display in the response if needed
        original_display = response_data.get("weight_display", "")
        if original_display and original_display != weight_display:
            comparison_text = comparison_text.replace(original_display, weight_display)
        
        return comparison_text
    
    def _select_response_with_rotation(self, responses: List[dict], key: str) -> Optional[dict]:
        """Select response with rotation to avoid immediate repetition"""
        
        if not responses:
            return None
        
        # Get list of used indices for this category
        used_indices = self.used_responses.get(key, [])
        
        # If we've used all responses, reset but keep last few to avoid immediate repeat
        if len(used_indices) >= len(responses):
            keep_count = min(len(responses) // 3, 3)  # Keep last 1/3 or 3, whichever is smaller
            self.used_responses[key] = used_indices[-keep_count:] if keep_count > 0 else []
            used_indices = self.used_responses[key]
        
        # Find unused indices
        all_indices = set(range(len(responses)))
        unused_indices = list(all_indices - set(used_indices))
        
        if not unused_indices:
            # All responses used recently, pick from all
            unused_indices = list(all_indices)
        
        # Select random unused index
        selected_index = random.choice(unused_indices)
        
        # Track usage
        self.used_responses[key].append(selected_index)
        
        return responses[selected_index]
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of enhanced fallback service"""
        
        repository_loaded = bool(self.repository)
        total_responses = sum(
            len(responses)
            for styles in self.repository.values()
            for responses in styles.values()
        )
        
        return {
            "status": "healthy" if repository_loaded else "degraded",
            "service": "enhanced_fallback_service",
            "repository_loaded": repository_loaded,
            "repository_file": str(self.repository_file),
            "total_responses": total_responses,
            "weight_ranges": len(self.weight_ranges),
            "basic_fallback_available": True
        }
    
    def get_repository_stats(self) -> Dict[str, Any]:
        """Get statistics about the fallback repository"""
        
        stats = {
            "total_responses": 0,
            "by_range": {},
            "by_style": {},
            "usage_stats": {}
        }
        
        # Count responses
        for range_name, styles in self.repository.items():
            stats["by_range"][range_name] = {}
            
            for style, responses in styles.items():
                count = len(responses)
                stats["total_responses"] += count
                stats["by_range"][range_name][style] = count
                
                if style not in stats["by_style"]:
                    stats["by_style"][style] = 0
                stats["by_style"][style] += count
        
        # Usage statistics
        for key, used_indices in self.used_responses.items():
            range_name, style = key.rsplit('_', 1)
            total_available = len(self.repository.get(range_name, {}).get(style, []))
            stats["usage_stats"][key] = {
                "used": len(used_indices),
                "total": total_available,
                "percentage": (len(used_indices) / total_available * 100) if total_available > 0 else 0
            }
        
        return stats
    
    async def cleanup(self):
        """Cleanup resources"""
        await super().cleanup()