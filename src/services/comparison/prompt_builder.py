"""
Prompt Builder for Weight Comparisons

Builds context-aware, provider-specific prompts for weight comparisons
using template management and variable injection.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from ...core.simple_config import SimpleConfig
from ...services.weight_processor import WeightItem
from .types import WeightContext, ComparisonObject
from .prompt_profiles import PromptProfiles

logger = logging.getLogger(__name__)


class TemplateVariable:
    """Template variable with metadata"""
    def __init__(self, name: str, value: Any, description: str = ""):
        self.name = name
        self.value = value
        self.description = description


class SafetyFilter:
    """Ensures appropriate content generation"""
    
    def __init__(self, config: SimpleConfig):
        self._config = config
        self._blocked_terms = set(config.get_section("safety.blocked_terms", []))
        self._sensitive_categories = set(config.get_section("safety.sensitive_categories", []))
        
    def apply_safety_filters(self, prompt: str) -> str:
        """Apply safety filters to prompt"""
        
        # Check for blocked terms
        prompt_lower = prompt.lower()
        for term in self._blocked_terms:
            if term in prompt_lower:
                raise ValueError(f"Blocked term detected: {term}")
                
        # Add safety instructions from profile
        safety_instructions = self._templates.get("safety_instructions", "")
        
        return f"{prompt}\n\n{safety_instructions}"
        
    def validate_comparison_objects(
        self,
        objects: List[ComparisonObject]
    ) -> List[ComparisonObject]:
        """Validate comparison objects for appropriateness"""
        
        validated = []
        for obj in objects:
            if obj.category not in self._sensitive_categories:
                validated.append(obj)
            else:
                logger.info(f"Filtered comparison object: {obj.name}")
                
        return validated


class PromptBuilder:
    """Build provider-specific prompts using templates"""
    
    def __init__(self, config: SimpleConfig):
        self._config = config
        self._safety_filter = SafetyFilter(config)
        
        # Get prompt profile from config (defaults to 'concise')
        self._prompt_profile = config.get('prompt_profile', 'concise')
        logger.info(f"Using prompt profile: {self._prompt_profile}")
        
        # Load templates from profile
        self._templates = PromptProfiles.get_profile(self._prompt_profile)
        
        
    async def build_prompt(
        self,
        weight_result: WeightItem,
        comparison_objects: List[ComparisonObject],
        weight_context: WeightContext,
        comparison_style: str,
        user_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build optimized prompt for weight comparison"""
        
        # Validate and filter comparison objects
        safe_objects = self._safety_filter.validate_comparison_objects(comparison_objects)
        
        # Get appropriate template
        template = self._get_template(comparison_style)
        
        # Prepare template variables
        variables = self._prepare_template_variables(
            weight_result, safe_objects, weight_context, user_context
        )
        
        # Render template
        prompt = self._render_template(template, variables)
        
        # Apply safety filters
        prompt = self._safety_filter.apply_safety_filters(prompt)
        
        # Apply provider-specific adaptations if needed
        if user_context and user_context.get("provider"):
            prompt = self._adapt_for_provider(prompt, user_context["provider"])
            
        return prompt
        
    def _get_template(self, comparison_style: str) -> str:
        """Get appropriate template for comparison style"""
        
        template = self._templates.get(comparison_style)
        if not template:
            logger.warning(f"Template not found for style '{comparison_style}', using default")
            template = self._templates["default"]
            
        return template
        
    def _prepare_template_variables(
        self,
        weight_result: WeightItem,
        comparison_objects: List[ComparisonObject],
        weight_context: WeightContext,
        user_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare all variables for template injection"""
        
        # Core weight variables
        variables = {
            "weight_value": str(weight_result.weight_kg),
            "weight_unit": weight_result.unit_used.value,
            "weight_in_kg": str(weight_result.weight_kg),
            "formatted_weight": weight_result.weight_display,
            
            # Category and context
            "weight_category": weight_context.category.value,
            "scale_context": weight_context.scale_context,
            "measurement_context": weight_context.measurement_context,
            
            # Comparison objects (formatted in different ways)
            "comparison_objects_list": self._format_objects_simple(comparison_objects),
            "comparison_objects_detailed": self._format_objects_detailed(comparison_objects),
            "comparison_objects_educational": self._format_objects_educational(comparison_objects),
            
            # Style directives
            "tone": self._get_tone_directive(user_context),
            "comparison_style": user_context.get("style", "default") if user_context else "default",
            
            # Context-specific instructions
            "context_specific_instructions": self._get_context_instructions(weight_context),
            "provider_specific_instructions": self._get_provider_instructions(user_context),
            
            # User preferences
            "user_locale": user_context.get("locale", "en-US") if user_context else "en-US",
            "expertise_level": user_context.get("expertise_level", "general") if user_context else "general"
        }
        
        # Add calculated ratios for comparison objects
        if comparison_objects:
            variables["object_ratios"] = self._calculate_ratios(weight_result, comparison_objects)
            
        return variables
        
    def _format_objects_simple(self, objects: List[ComparisonObject]) -> str:
        """Format objects as simple list"""
        if not objects:
            return "No specific comparison objects available"
            
        formatted = []
        for obj in objects:
            formatted.append(f"- {obj.name} ({obj.weight_kg} kg)")
            
        return "\n".join(formatted)
        
    def _format_objects_detailed(self, objects: List[ComparisonObject]) -> str:
        """Format objects with detailed information"""
        if not objects:
            return "No reference objects specified"
            
        formatted = []
        for obj in objects:
            formatted.append(
                f"- {obj.name}: {obj.weight_kg} kg ({obj.description})"
            )
            
        return "\n".join(formatted)
        
    def _format_objects_educational(self, objects: List[ComparisonObject]) -> str:
        """Format objects for educational context"""
        if not objects:
            return "Common objects for reference"
            
        formatted = []
        for i, obj in enumerate(objects, 1):
            formatted.append(
                f"{i}. {obj.name} - weighs {obj.weight_kg} kg\n"
                f"   Description: {obj.description}"
            )
            
        return "\n".join(formatted)
        
    def _calculate_ratios(
        self,
        weight_result: WeightItem,
        comparison_objects: List[ComparisonObject]
    ) -> List[Dict[str, Any]]:
        """Calculate ratios between target weight and comparison objects"""
        
        target_weight = float(weight_result.weight_kg)
        ratios = []
        
        for obj in comparison_objects:
            obj_weight = float(obj.weight_kg)
            if obj_weight > 0:
                ratio = target_weight / obj_weight
                inverse_ratio = obj_weight / target_weight
                
                ratios.append({
                    "object": obj.name,
                    "ratio": round(ratio, 2),
                    "inverse_ratio": round(inverse_ratio, 2),
                    "comparison": self._describe_ratio(ratio)
                })
                
        return ratios
        
    def _describe_ratio(self, ratio: float) -> str:
        """Describe ratio in human terms"""
        if ratio < 0.1:
            return "much lighter than"
        elif ratio < 0.5:
            return "lighter than"
        elif ratio < 0.9:
            return "slightly lighter than"
        elif ratio < 1.1:
            return "about the same as"
        elif ratio < 2:
            return "slightly heavier than"
        elif ratio < 5:
            return "heavier than"
        elif ratio < 10:
            return "much heavier than"
        else:
            return "significantly heavier than"
            
    def _get_tone_directive(self, user_context: Optional[Dict[str, Any]]) -> str:
        """Get tone directive based on context"""
        if not user_context:
            return "helpful and engaging"
            
        expertise = user_context.get("expertise_level", "general")
        
        if expertise == "beginner":
            return "simple and encouraging"
        elif expertise == "expert":
            return "professional and precise"
        else:
            return "friendly and informative"
            
    def _get_context_instructions(self, weight_context: WeightContext) -> str:
        """Get context-specific instructions"""
        
        instructions = []
        
        if weight_context.category.value == "microscopic":
            instructions.append("Emphasize the incredibly small scale")
            instructions.append("Use scientific analogies where appropriate")
            
        elif weight_context.category.value == "massive":
            instructions.append("Help conceptualize the enormous scale")
            instructions.append("Use familiar large objects for reference")
            
        elif weight_context.is_metric:
            instructions.append("Maintain metric units in the primary comparison")
        else:
            instructions.append("Include both metric and imperial units for clarity")
            
        return ". ".join(instructions) + "." if instructions else ""
        
    def _get_provider_instructions(self, user_context: Optional[Dict[str, Any]]) -> str:
        """Get provider-specific instructions"""
        if not user_context or "provider" not in user_context:
            return ""
            
        provider = user_context["provider"]
        
        if provider == "openai":
            return "Structure your response clearly with specific numerical details."
        elif provider == "anthropic":
            return "Be creative and engaging while maintaining accuracy."
        elif provider == "xai":
            return "Keep the response concise but informative."
        else:
            return ""
            
    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Render template with variables"""
        
        try:
            # Simple string formatting
            return template.format(**variables)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            # Fill missing variables with placeholders
            safe_variables = variables.copy()
            for match in re.finditer(r'\{([^}]+)\}', template):
                var_name = match.group(1)
                if var_name not in safe_variables:
                    safe_variables[var_name] = f"[{var_name}]"
                    
            return template.format(**safe_variables)
            
    def _adapt_for_provider(self, prompt: str, provider_name: str) -> str:
        """Adapt prompt for specific provider requirements"""
        
        if provider_name == "openai":
            return self._add_openai_directives(prompt)
        elif provider_name == "anthropic":
            return self._add_anthropic_style_markers(prompt)
        elif provider_name == "xai":
            return self._add_conciseness_directive(prompt)
        else:
            return prompt
            
    def _add_openai_directives(self, prompt: str) -> str:
        """Add OpenAI-specific directives"""
        adjustments = PromptProfiles.get_provider_adjustments("openai", self._prompt_profile)
        directive = adjustments.get("provider_specific_instructions", "")
        return f"""{prompt}

{directive}""" if directive else prompt

    def _add_anthropic_style_markers(self, prompt: str) -> str:
        """Add Anthropic-specific style markers"""
        adjustments = PromptProfiles.get_provider_adjustments("anthropic", self._prompt_profile)
        guidelines = adjustments.get("provider_specific_instructions", "")
        return f"""<comparison_request>
{prompt}
</comparison_request>

{guidelines}"""

    def _add_conciseness_directive(self, prompt: str) -> str:
        """Add conciseness directive for X.ai"""
        adjustments = PromptProfiles.get_provider_adjustments("xai", self._prompt_profile)
        directive = adjustments.get("provider_specific_instructions", "")
        return f"""{prompt}

{directive}""" if directive else prompt

    def get_template_variables_info(self) -> Dict[str, List[TemplateVariable]]:
        """Get information about available template variables"""
        
        variables = {
            "weight": [
                TemplateVariable("weight_value", "5.5", "Numeric weight value"),
                TemplateVariable("weight_unit", "kg", "Weight unit"),
                TemplateVariable("weight_in_kg", "5.5", "Weight in kilograms"),
                TemplateVariable("formatted_weight", "5.5 kg", "Formatted weight display"),
            ],
            "context": [
                TemplateVariable("weight_category", "medium", "Weight category"),
                TemplateVariable("scale_context", "objects you can carry", "Scale description"),
                TemplateVariable("measurement_context", "measured in kg", "Measurement context"),
            ],
            "objects": [
                TemplateVariable("comparison_objects_list", "- cat (4.5 kg)", "Simple object list"),
                TemplateVariable("comparison_objects_detailed", "- cat: 4.5 kg (domestic)", "Detailed objects"),
            ],
            "style": [
                TemplateVariable("tone", "friendly", "Communication tone"),
                TemplateVariable("comparison_style", "default", "Comparison style"),
            ]
        }
        
        return variables