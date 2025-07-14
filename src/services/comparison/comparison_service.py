"""
Main Comparison Service Orchestrator

Coordinates all aspects of weight comparison including weight processing,
provider selection, prompt generation, and response enhancement.
"""

import asyncio
import logging
import time
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple
from uuid import UUID, uuid4

from ...core.config import ConfigLoader
from ...models.providers import AIProvider
from ...services.weight_processor import WeightProcessor, WeightItem, WeightUnit
from .types import (
    WeightCategory, UnitSystem, WeightContext, ComparisonObject, 
    ComparisonMetadata, WeightComparisonResponse
)

logger = logging.getLogger(__name__)

# Forward declarations for components we'll import later
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .provider_selector import ProviderSelector
    from .prompt_builder import PromptBuilder  
    from .response_processor import ResponseProcessor
        

class ICacheService(Protocol):
    """Cache service interface"""
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        ...
        
    async def set(self, key: str, value: Any, ttl: int = 86400) -> None:
        """Set item in cache with TTL"""
        ...


class IAIProviderFactory(Protocol):
    """AI Provider factory interface"""
    async def get_provider(self, name: str) -> Any:
        """Get AI provider by name"""
        ...


class IMetricsCollector(Protocol):
    """Metrics collector interface"""
    def increment(self, metric: str, tags: Dict[str, str] = None) -> None:
        """Increment counter metric"""
        ...
        
    def histogram(self, metric: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record histogram metric"""
        ...


class ComparisonService:
    """Central orchestrator for weight comparison operations"""
    
    def __init__(
        self,
        weight_processor: WeightProcessor,
        provider_factory: IAIProviderFactory,
        cache_service: ICacheService,
        config: ConfigLoader,
        metrics: IMetricsCollector,
        logger: logging.Logger
    ):
        self._weight_processor = weight_processor
        self._provider_factory = provider_factory
        self._cache_service = cache_service
        self._config = config
        self._metrics = metrics
        self._logger = logger
        
        # Initialize sub-components (import at runtime to avoid circular imports)
        from .provider_selector import ProviderSelector
        from .prompt_builder import PromptBuilder
        from .response_processor import ResponseProcessor
        
        self._provider_selector = ProviderSelector(provider_factory, config)
        self._prompt_builder = PromptBuilder(config)
        self._response_processor = ResponseProcessor(config)
        
        # Performance settings
        self._timeout_ms = config.get_section(
            "comparison_service.performance.provider_timeout_ms", 1500
        )
        self._cache_ttl = config.get_section(
            "comparison_service.performance.cache_ttl_seconds", 86400
        )
        
        # Comparison object database (simplified for now)
        self._comparison_database = self._initialize_comparison_database()
        
    def _initialize_comparison_database(self) -> Dict[str, List[ComparisonObject]]:
        """Initialize database of comparison objects"""
        return {
            'microscopic': [
                ComparisonObject('grain of salt', Decimal('0.000058'), 'A single grain of table salt', 'food'),
                ComparisonObject('dust mite', Decimal('0.000002'), 'A common household dust mite', 'organism'),
            ],
            'very_light': [
                ComparisonObject('paper clip', Decimal('0.001'), 'A standard metal paper clip', 'object'),
                ComparisonObject('raisin', Decimal('0.0005'), 'A single dried raisin', 'food'),
                ComparisonObject('aspirin tablet', Decimal('0.0005'), 'A standard aspirin pill', 'medicine'),
            ],
            'light': [
                ComparisonObject('smartphone', Decimal('0.175'), 'An average smartphone', 'technology'),
                ComparisonObject('apple', Decimal('0.182'), 'A medium-sized apple', 'food'),
                ComparisonObject('hamster', Decimal('0.120'), 'An adult hamster', 'animal'),
            ],
            'medium': [
                ComparisonObject('house cat', Decimal('4.5'), 'An average domestic cat', 'animal'),
                ComparisonObject('bowling ball', Decimal('7.0'), 'A standard bowling ball', 'sports'),
                ComparisonObject('watermelon', Decimal('9.0'), 'A large watermelon', 'food'),
            ],
            'heavy': [
                ComparisonObject('small car', Decimal('1200'), 'A compact car', 'vehicle'),
                ComparisonObject('grand piano', Decimal('400'), 'A concert grand piano', 'instrument'),
                ComparisonObject('adult horse', Decimal('600'), 'An adult riding horse', 'animal'),
            ],
            'massive': [
                ComparisonObject('blue whale', Decimal('150000'), 'The largest animal on Earth', 'animal'),
                ComparisonObject('space shuttle', Decimal('78000'), 'NASA space shuttle (empty)', 'vehicle'),
                ComparisonObject('locomotive', Decimal('180000'), 'A diesel locomotive', 'vehicle'),
            ]
        }
        
    async def create_comparison(
        self,
        weight_input: str,
        preferred_provider: Optional[AIProvider] = None,
        comparison_style: str = "default",
        include_visualization: bool = True,
        user_context: Optional[Dict[str, Any]] = None
    ) -> WeightComparisonResponse:
        """Create weight comparison with timeout protection"""
        
        timeout = self._timeout_ms / 1000  # Convert to seconds
        
        try:
            async with asyncio.timeout(timeout):
                return await self._process_comparison_request(
                    weight_input, preferred_provider, comparison_style,
                    include_visualization, user_context
                )
        except asyncio.TimeoutError:
            self._logger.warning(f"Comparison request timed out after {timeout}s")
            self._metrics.increment("comparison.timeouts")
            # Return fallback response
            return await self._get_fallback_response(weight_input)
            
    async def _process_comparison_request(
        self,
        weight_input: str,
        preferred_provider: Optional[AIProvider],
        comparison_style: str,
        include_visualization: bool,
        user_context: Optional[Dict[str, Any]]
    ) -> WeightComparisonResponse:
        """Core comparison processing pipeline"""
        
        start_time = time.time()
        
        # Step 1: Parse and validate weight input
        try:
            weight_result = self._weight_processor.process_weight(weight_input)
        except Exception as e:
            self._logger.error(f"Weight processing failed: {e}")
            raise ValueError(f"Invalid weight input: {str(e)}")
        
        # Step 2: Determine weight context
        weight_context = self._determine_weight_context(weight_result)
        
        # Step 3: Check cache
        cache_key = self._generate_cache_key(weight_result, comparison_style)
        cached_response = await self._cache_service.get(cache_key)
        
        if cached_response:
            self._metrics.increment("comparison.cache_hit")
            return self._enrich_cached_response(cached_response, weight_result)
        
        self._metrics.increment("comparison.cache_miss")
        
        # Step 4: Select comparison objects
        comparison_objects = self._select_comparison_objects(
            weight_result, weight_context, comparison_style
        )
        
        # Step 5: Build provider-specific prompt
        prompt = await self._prompt_builder.build_prompt(
            weight_result, comparison_objects, weight_context,
            comparison_style, user_context
        )
        
        # Step 6: Select and query provider
        provider = await self._provider_selector.select_provider(
            preferred_provider, weight_context, comparison_style
        )
        
        try:
            raw_response = await self._generate_with_provider(provider, prompt)
        except Exception as e:
            self._logger.error(f"Provider {provider} failed: {e}")
            self._metrics.increment("comparison.provider_errors", tags={"provider": str(provider)})
            return await self._get_fallback_response(weight_input)
        
        # Step 7: Process and enhance response
        processed_response = await self._response_processor.process(
            raw_response, weight_result, comparison_objects,
            include_visualization
        )
        
        # Step 8: Create final response
        response_time_ms = int((time.time() - start_time) * 1000)
        
        response = WeightComparisonResponse(
            comparison_text=processed_response['comparison_text'],
            weight_value=weight_result.weight_kg,
            weight_unit=weight_result.unit_used,
            weight_in_kg=weight_result.weight_kg,
            weight_category=weight_context.category,
            comparison_objects=[obj.name for obj in comparison_objects],
            visualization_prompt=processed_response.get('visualization_prompt'),
            metadata=ComparisonMetadata(
                provider_used=str(provider),
                model_used="gpt-4",  # This would come from provider
                response_time_ms=response_time_ms,
                cache_hit=False,
                confidence_score=processed_response.get('confidence_score', 0.8),
                comparison_style=comparison_style,
                locale=user_context.get('locale', 'en-US') if user_context else 'en-US',
                generated_at=datetime.utcnow().isoformat()
            ),
            fun_facts=self._get_weight_fun_facts(weight_result, weight_context)
        )
        
        # Cache the response
        await self._cache_service.set(cache_key, response, ttl=self._cache_ttl)
        
        # Track metrics
        self._metrics.histogram(
            "comparison.response_time_ms",
            response_time_ms,
            tags={
                "provider": str(provider),
                "style": comparison_style,
                "cache_hit": "false"
            }
        )
        
        return response
        
    def _determine_weight_context(self, weight_result: WeightItem) -> WeightContext:
        """Determine contextual information for the weight"""
        
        weight_kg = float(weight_result.weight_kg)
        
        # Categorize weight
        if weight_kg < 0.001:  # Less than 1 gram
            category = WeightCategory.MICROSCOPIC
            scale_context = "microscopic scale, like cells or dust particles"
            measurement_context = "typically measured in milligrams or micrograms"
        elif weight_kg < 0.1:  # Less than 100 grams
            category = WeightCategory.VERY_LIGHT
            scale_context = "everyday small objects"
            measurement_context = "commonly measured in grams"
        elif weight_kg < 10:  # Less than 10 kg
            category = WeightCategory.LIGHT
            scale_context = "objects you can easily carry"
            measurement_context = "typically measured in kilograms or pounds"
        elif weight_kg < 1000:  # Less than 1 tonne
            category = WeightCategory.MEDIUM
            scale_context = "furniture or large appliances"
            measurement_context = "measured in kilograms or pounds"
        elif weight_kg < 100000:  # Less than 100 tonnes
            category = WeightCategory.HEAVY
            scale_context = "vehicles or large animals"
            measurement_context = "measured in tonnes or tons"
        else:
            category = WeightCategory.MASSIVE
            scale_context = "buildings or large structures"
            measurement_context = "measured in thousands of tonnes"
        
        # Determine unit system
        is_metric = weight_result.unit_used in [
            WeightUnit.KILOGRAM, WeightUnit.GRAM, 
            WeightUnit.METRIC_TON, WeightUnit.MILLIGRAM
        ]
        
        return WeightContext(
            category=category,
            scale_context=scale_context,
            measurement_context=measurement_context,
            original_unit=weight_result.unit_used,
            is_metric=is_metric
        )
        
    def _select_comparison_objects(
        self,
        weight_result: WeightItem,
        weight_context: WeightContext,
        comparison_style: str
    ) -> List[ComparisonObject]:
        """Select appropriate objects for comparison"""
        
        # Get objects from the appropriate category
        category_objects = self._comparison_database.get(
            weight_context.category.value, []
        )
        
        if not category_objects:
            # Fallback to adjacent categories
            return self._get_cross_category_objects(weight_result.weight_kg)
        
        # For now, return up to 3 objects from the category
        # In a real implementation, this would be more sophisticated
        selected = []
        weight_kg = float(weight_result.weight_kg)
        
        # Find closest match
        closest = min(
            category_objects,
            key=lambda obj: abs(float(obj.weight_kg) - weight_kg)
        )
        selected.append(closest)
        
        # Add variety
        for obj in category_objects:
            if obj != closest and len(selected) < 3:
                selected.append(obj)
                
        return selected
        
    def _get_cross_category_objects(
        self, 
        weight_kg: Decimal
    ) -> List[ComparisonObject]:
        """Get objects from multiple categories for comparison"""
        all_objects = []
        for objects in self._comparison_database.values():
            all_objects.extend(objects)
            
        # Sort by proximity to target weight
        weight_float = float(weight_kg)
        sorted_objects = sorted(
            all_objects,
            key=lambda obj: abs(float(obj.weight_kg) - weight_float)
        )
        
        return sorted_objects[:3]
        
    def _generate_cache_key(
        self,
        weight_result: WeightItem,
        comparison_style: str
    ) -> str:
        """Generate normalized cache key"""
        
        # Normalize weight to reduce cache misses
        weight_kg = float(weight_result.weight_kg)
        
        if weight_kg < 0.01:
            normalized_kg = round(weight_kg, 4)
        elif weight_kg < 1:
            normalized_kg = round(weight_kg, 3)
        elif weight_kg < 100:
            normalized_kg = round(weight_kg, 2)
        elif weight_kg < 10000:
            normalized_kg = round(weight_kg, 1)
        else:
            normalized_kg = round(weight_kg, 0)
            
        return f"comparison:v1:{normalized_kg}:{comparison_style}"
        
    def _enrich_cached_response(
        self,
        cached_response: Any,
        weight_result: WeightItem
    ) -> WeightComparisonResponse:
        """Enrich cached response with current context"""
        
        # Update metadata to indicate cache hit
        if hasattr(cached_response, 'metadata'):
            cached_response.metadata.cache_hit = True
            
        # Update weight values to match current input
        cached_response.weight_value = weight_result.weight_kg
        cached_response.weight_unit = weight_result.unit_used
        
        return cached_response
        
    async def _generate_with_provider(
        self,
        provider: AIProvider,
        prompt: str
    ) -> str:
        """Generate comparison with selected provider"""
        
        # This is a simplified implementation
        # In reality, this would call the actual provider
        
        # For now, return a mock response
        return f"""
        This weight is equivalent to approximately 3 adult house cats or 
        about half the weight of a bowling ball. To put it in perspective, 
        you could carry this weight comfortably in a backpack, and it's 
        similar to what a medium-sized watermelon weighs.
        """
        
    async def _get_fallback_response(
        self,
        weight_input: str
    ) -> WeightComparisonResponse:
        """Get fallback response when providers fail"""
        
        try:
            weight_result = self._weight_processor.process_weight(weight_input)
            weight_kg = float(weight_result.weight_kg)
            
            # Generate basic mathematical comparison
            comparison_text = f"{weight_result.weight_display} is "
            
            if weight_kg < 0.001:
                comparison_text += "extremely light, less than a paperclip."
            elif weight_kg < 0.1:
                comparison_text += "very light, about the weight of a few coins."
            elif weight_kg < 1:
                comparison_text += "light, similar to a small book or smartphone."
            elif weight_kg < 10:
                comparison_text += "moderate, like a house cat or small dog."
            elif weight_kg < 100:
                comparison_text += "substantial, similar to an adult person."
            elif weight_kg < 1000:
                comparison_text += "heavy, like a small motorcycle or piano."
            else:
                comparison_text += "very heavy, comparable to a vehicle."
                
            return WeightComparisonResponse(
                comparison_text=comparison_text,
                weight_value=weight_result.weight_kg,
                weight_unit=weight_result.unit_used,
                weight_in_kg=weight_result.weight_kg,
                weight_category=self._determine_weight_context(weight_result).category,
                comparison_objects=[],
                metadata=ComparisonMetadata(
                    provider_used="fallback",
                    model_used="mathematical",
                    response_time_ms=10,
                    cache_hit=False,
                    confidence_score=0.5,
                    comparison_style="default",
                    locale="en-US",
                    generated_at=datetime.utcnow().isoformat(),
                    is_fallback=True
                )
            )
        except Exception as e:
            self._logger.error(f"Fallback generation failed: {e}")
            # Ultimate fallback
            return WeightComparisonResponse(
                comparison_text="Unable to generate comparison at this time.",
                weight_value=Decimal(0),
                weight_unit=WeightUnit.KILOGRAM,
                weight_in_kg=Decimal(0),
                weight_category=WeightCategory.MEDIUM,
                comparison_objects=[],
                metadata=ComparisonMetadata(
                    provider_used="error",
                    model_used="none",
                    response_time_ms=0,
                    cache_hit=False,
                    confidence_score=0,
                    comparison_style="default",
                    locale="en-US",
                    generated_at=datetime.utcnow().isoformat(),
                    is_fallback=True
                )
            )
            
    def _get_weight_fun_facts(
        self,
        weight_result: WeightItem,
        weight_context: WeightContext
    ) -> List[str]:
        """Get interesting facts about the weight"""
        
        facts = []
        weight_kg = float(weight_result.weight_kg)
        
        # Add facts based on weight category
        if weight_context.category == WeightCategory.MICROSCOPIC:
            facts.append("This weight is invisible to the naked eye!")
            facts.append("A single human cell weighs about 1 nanogram.")
            
        elif weight_context.category == WeightCategory.LIGHT:
            facts.append(f"You could easily carry {int(70 / weight_kg)} of these in a backpack.")
            
        elif weight_context.category == WeightCategory.HEAVY:
            facts.append("This weight requires special equipment to move safely.")
            
        return facts[:2]  # Limit to 2 facts


def create_comparison_service(
    weight_processor: WeightProcessor,
    provider_factory: IAIProviderFactory,
    cache_service: ICacheService,
    config: ConfigLoader,
    metrics: IMetricsCollector,
    logger: Optional[logging.Logger] = None
) -> ComparisonService:
    """Factory function to create comparison service"""
    
    if logger is None:
        logger = logging.getLogger(__name__)
        
    return ComparisonService(
        weight_processor=weight_processor,
        provider_factory=provider_factory,
        cache_service=cache_service,
        config=config,
        metrics=metrics,
        logger=logger
    )