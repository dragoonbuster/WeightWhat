"""
Prompt Profiles for Weight Comparisons

This module provides different prompt profiles (verbose vs concise) that can be
selected via environment variables. All profiles enforce NO EMOJI policy.
"""

from typing import Dict, Any


class PromptProfiles:
    """Manages different prompt profiles for various verbosity levels"""
    
    # Shared anti-emoji instruction that goes in ALL prompts
    NO_EMOJI_INSTRUCTION = "IMPORTANT: Use NO emojis, emoticons, symbols, or decorative characters. Plain text only."
    
    @staticmethod
    def get_profiles() -> Dict[str, Dict[str, str]]:
        """Get all available prompt profiles"""
        return {
            "verbose": PromptProfiles._get_verbose_profile(),
            "concise": PromptProfiles._get_concise_profile(),
            "ultra_concise": PromptProfiles._get_ultra_concise_profile()
        }
    
    @staticmethod
    def _get_verbose_profile() -> Dict[str, str]:
        """Original verbose prompts (pre-brevity update) but with NO EMOJI rule"""
        return {
            "default": f"""
You are an expert at creating engaging weight comparisons. Given the following weight information, create a vivid and relatable comparison that helps people understand the weight in everyday terms.

{PromptProfiles.NO_EMOJI_INSTRUCTION}

Weight to compare: {{weight_value}} {{weight_unit}} ({{weight_in_kg}} kg)
Weight category: {{weight_category}}
Context: {{scale_context}}

Available comparison objects:
{{comparison_objects_list}}

Instructions:
- Create an engaging comparison using the provided objects
- Use specific numbers and ratios where helpful
- Make it relatable and easy to understand
- Keep it informative and educational
- Include interesting details or facts when relevant
- Tone: {{tone}}
- Style: {{comparison_style}}

{{context_specific_instructions}}

Comparison:""",

            "creative": f"""
You are a creative writer specializing in weight comparisons. Transform this technical weight measurement into a captivating and memorable comparison.

{PromptProfiles.NO_EMOJI_INSTRUCTION}

Weight: {{weight_value}} {{weight_unit}} ({{weight_in_kg}} kg)
Scale: {{scale_context}}

Comparison objects to consider:
{{comparison_objects_list}}

Creative Guidelines:
- Use vivid imagery and metaphors
- Make unexpected but accurate connections
- Include interesting ratios or multiples
- Paint a picture that sticks in memory
- Be playful yet educational
- Feel free to elaborate with interesting details

{{provider_specific_instructions}}

Creative comparison:""",

            "technical": f"""
You are a technical expert providing precise weight comparisons for an educated audience.

{PromptProfiles.NO_EMOJI_INSTRUCTION}

Weight specification: {{weight_value}} {{weight_unit}} (equivalent to {{weight_in_kg}} kg)
Measurement context: {{measurement_context}}
Category: {{weight_category}}

Reference objects with known weights:
{{comparison_objects_detailed}}

Technical requirements:
- Provide exact ratios and calculations
- Include relevant scientific context
- Mention measurement precision where appropriate
- Use appropriate technical terminology
- Be comprehensive and thorough
- Include additional context that aids understanding

Technical comparison:""",

            "educational": f"""
You are an educator creating a weight comparison lesson for students.

{PromptProfiles.NO_EMOJI_INSTRUCTION}

Learning objective: Understanding the weight of {{weight_value}} {{weight_unit}}
Weight in standard units: {{weight_in_kg}} kg
Real-world context: {{scale_context}}

Teaching materials (comparison objects):
{{comparison_objects_educational}}

Educational approach:
- Make it age-appropriate and engaging
- Use familiar objects students know
- Include simple math when helpful
- Encourage hands-on understanding
- Build from known to unknown
- Provide context that helps learning

Educational comparison:""",

            "safety_instructions": f"""
Note: Please ensure all comparisons are:
- Family-friendly and appropriate for all ages
- Factually accurate and educational
- Free from potentially offensive content
- Respectful of all cultures and backgrounds
- {PromptProfiles.NO_EMOJI_INSTRUCTION}
"""
        }
    
    @staticmethod
    def _get_concise_profile() -> Dict[str, str]:
        """Concise prompts with strict length limits and NO EMOJI rule"""
        return {
            "default": f"""
Create a simple weight comparison for {{weight_value}} {{weight_unit}} ({{weight_in_kg}} kg).

{PromptProfiles.NO_EMOJI_INSTRUCTION}

Available objects:
{{comparison_objects_list}}

Rules:
- Maximum 2-3 sentences
- Use specific numbers
- Make it relatable
- Plain text only

Comparison:""",

            "creative": f"""
Create a creative weight comparison for {{weight_value}} {{weight_unit}}.

{PromptProfiles.NO_EMOJI_INSTRUCTION}

Objects: {{comparison_objects_list}}

Rules:
- Be creative but concise (max 3 sentences)
- Use vivid imagery
- Include ratios
- Plain text only

Creative comparison:""",

            "technical": f"""
Technical comparison for {{weight_value}} {{weight_unit}} ({{weight_in_kg}} kg).

{PromptProfiles.NO_EMOJI_INSTRUCTION}

References: {{comparison_objects_detailed}}

Requirements:
- Exact ratios only
- Maximum 3 sentences
- Technical accuracy
- Plain text only

Technical comparison:""",

            "educational": f"""
Educational comparison for {{weight_value}} {{weight_unit}}.

{PromptProfiles.NO_EMOJI_INSTRUCTION}

Objects: {{comparison_objects_educational}}

Guidelines:
- Simple, clear language
- Maximum 2-3 sentences
- Include basic math
- Plain text only

Educational comparison:""",

            "safety_instructions": f"""
Requirements: Family-friendly, accurate, no offensive content. {PromptProfiles.NO_EMOJI_INSTRUCTION}
"""
        }
    
    @staticmethod
    def _get_ultra_concise_profile() -> Dict[str, str]:
        """Ultra-concise prompts for minimal response length"""
        return {
            "default": f"""
Compare {{weight_value}} {{weight_unit}} to: {{comparison_objects_list}}

{PromptProfiles.NO_EMOJI_INSTRUCTION}
One sentence. Include numbers.

Comparison:""",

            "creative": f"""
Creative comparison for {{weight_value}} {{weight_unit}} using: {{comparison_objects_list}}

{PromptProfiles.NO_EMOJI_INSTRUCTION}
One vivid sentence.

Comparison:""",

            "technical": f"""
Technical: {{weight_value}} {{weight_unit}} vs {{comparison_objects_detailed}}

{PromptProfiles.NO_EMOJI_INSTRUCTION}
One sentence with exact ratio.

Comparison:""",

            "educational": f"""
Explain {{weight_value}} {{weight_unit}} using: {{comparison_objects_educational}}

{PromptProfiles.NO_EMOJI_INSTRUCTION}
One simple sentence.

Comparison:""",

            "safety_instructions": f"""
{PromptProfiles.NO_EMOJI_INSTRUCTION} Family-friendly.
"""
        }
    
    @staticmethod
    def get_profile(profile_name: str = "concise") -> Dict[str, str]:
        """
        Get a specific prompt profile by name.
        
        Args:
            profile_name: Name of the profile (verbose, concise, ultra_concise)
            
        Returns:
            Dictionary of prompts for the selected profile
        """
        profiles = PromptProfiles.get_profiles()
        if profile_name not in profiles:
            logger.warning(f"Unknown prompt profile '{profile_name}', using 'concise'")
            return profiles["concise"]
        return profiles[profile_name]
    
    @staticmethod
    def get_provider_adjustments(provider: str, profile: str) -> Dict[str, str]:
        """
        Get provider-specific adjustments for prompts.
        
        Different providers may need slightly different instructions.
        """
        adjustments = {
            "openai": {
                "verbose": "Please structure your response clearly and ensure all comparisons are factually accurate. Use specific numbers and ratios where applicable.",
                "concise": "Structure clearly. Use specific numbers. NO EMOJIS.",
                "ultra_concise": "Be direct. NO EMOJIS."
            },
            "anthropic": {
                "verbose": """<guidelines>
- Be creative but accurate
- Use vivid imagery where appropriate
- Maintain a helpful and engaging tone
- NO EMOJIS or symbols allowed
</guidelines>""",
                "concise": """<guidelines>
- Be creative but accurate
- Keep it concise (2-3 sentences)
- NO EMOJIS or symbols
</guidelines>""",
                "ultra_concise": "<guidelines>One sentence. NO EMOJIS.</guidelines>"
            },
            "xai": {
                "verbose": "Keep your response informative but not overly long. Focus on clarity and accuracy.",
                "concise": "Keep response under 3 sentences. NO EMOJIS.",
                "ultra_concise": "One sentence only. NO EMOJIS."
            }
        }
        
        if provider in adjustments and profile in adjustments[provider]:
            return {"provider_specific_instructions": adjustments[provider][profile]}
        return {"provider_specific_instructions": ""}


import logging
logger = logging.getLogger(__name__)