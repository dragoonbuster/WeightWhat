"""
Base interfaces and protocols for AI provider management and comparison services.

These interfaces define the common contracts that all comparison services and
AI providers should implement, enabling shared components and consistent behavior.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

from ...models.mvp import MVPComparisonRequest, MVPComparisonResponse


@dataclass
class AIProviderConfig:
    """Configuration for AI provider setup"""
    name: str
    api_key: Optional[str]
    model: str
    max_tokens: int = 150
    temperature: float = 0.7
    timeout: float = 10.0
    enabled: bool = True


@dataclass
class AIProviderResponse:
    """Response from an AI provider"""
    content: str
    provider_name: str
    model_used: str
    success: bool
    error_message: Optional[str] = None
    response_time_ms: int = 0


class AIProviderInterface(Protocol):
    """Protocol for AI provider implementations"""
    
    @property
    def name(self) -> str:
        """Get the provider name"""
        ...
    
    @property
    def is_available(self) -> bool:
        """Check if provider is available and configured"""
        ...
    
    async def generate_comparison(self, prompt: str, **kwargs) -> AIProviderResponse:
        """Generate a comparison using this AI provider"""
        ...
    
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health status"""
        ...


class FallbackDataInterface(Protocol):
    """Protocol for fallback data management"""
    
    def get_comparison_objects(self, weight_kg: float) -> List[str]:
        """Get appropriate comparison objects for a given weight"""
        ...
    
    def generate_fallback_comparison(self, weight_kg: float, weight_display: str) -> str:
        """Generate fallback comparison text"""
        ...
    
    def is_reasonable_object(self, weight_kg: float, object_name: str) -> bool:
        """Check if an object is reasonable for the given weight"""
        ...


class BaseComparisonService(ABC):
    """Base class for all comparison services with common functionality"""
    
    def __init__(self):
        self.ai_provider_manager: Optional['AIProviderManager'] = None
        self.fallback_data_manager: Optional['FallbackDataManager'] = None
    
    @abstractmethod
    async def create_comparison(self, request: MVPComparisonRequest) -> MVPComparisonResponse:
        """Create a weight comparison - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status - must be implemented by subclasses"""
        pass
    
    async def cleanup(self):
        """Cleanup resources - can be overridden by subclasses"""
        if self.ai_provider_manager:
            await self.ai_provider_manager.cleanup()
    
    def _clean_weight_display(self, weight_kg: float, weight_display: str) -> str:
        """
        Clean weight display to prevent AI misinterpretation
        
        Shared utility method for all comparison services.
        Converts "100.000 kg" to "100 kg" to avoid decimal confusion.
        """
        import re
        
        # Try to extract number and unit
        match = re.match(r'^(\d+(?:\.\d+)?)\s*(.+)$', weight_display.strip())
        if not match:
            return weight_display  # Return as-is if can't parse
        
        number_str, unit = match.groups()
        
        try:
            # Convert to float and back to remove unnecessary decimals
            number = float(number_str)
            
            # Format cleanly - remove trailing zeros and unnecessary decimals
            if number == int(number):
                # Whole number
                clean_number = str(int(number))
            elif number < 10:
                # Small number - keep 1 decimal if needed
                clean_number = f"{number:.1f}".rstrip('0').rstrip('.')
            else:
                # Larger number - round to reasonable precision
                clean_number = f"{number:.0f}" if number > 100 else f"{number:.1f}".rstrip('0').rstrip('.')
            
            return f"{clean_number} {unit.strip()}"
            
        except ValueError:
            # If conversion fails, return original
            return weight_display


# Type hints for common patterns
AIProviderCallResult = Tuple[Optional[str], str]  # (content, provider_name)
WeightRange = Tuple[float, float]  # (min_weight, max_weight)
ComparisonObjects = Dict[WeightRange, Dict[str, List[str]]]  # weight_ranges with object categories