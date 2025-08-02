"""
Simplified comparison engine for SizeComparator.
Handles AI providers, fallback responses, and comparison generation.
"""

import os
import time
import random
import logging
import httpx
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Fallback responses by weight category
FALLBACK_RESPONSES = {
    'microscopic': [
        "That's about as heavy as a grain of salt",
        "That weighs roughly the same as a small ant",
        "That's approximately the weight of a dust particle"
    ],
    'very_light': [
        "That's about as heavy as a paperclip",
        "That weighs roughly the same as a few grains of rice",
        "That's approximately the weight of a small pill"
    ],
    'light': [
        "That's about as heavy as a smartphone",
        "That weighs roughly the same as a hardcover book",
        "That's approximately the weight of a laptop"
    ],
    'medium': [
        "That's about as heavy as a golden retriever",
        "That weighs roughly the same as a large suitcase",
        "That's approximately the weight of a small child"
    ],
    'heavy': [
        "That's about as heavy as a small car",
        "That weighs roughly the same as an elephant",
        "That's approximately the weight of a pickup truck"
    ],
    'very_heavy': [
        "That's about as heavy as a commercial airplane",
        "That weighs roughly the same as a blue whale",
        "That's approximately the weight of a small building"
    ]
}


class ComparisonEngine:
    """Handles comparison generation with AI providers and fallbacks."""
    
    def __init__(self):
        # API configuration
        self.openai_key = os.getenv('SIZECOMPARATOR_OPENAI_API_KEY')
        self.anthropic_key = os.getenv('SIZECOMPARATOR_ANTHROPIC_API_KEY')
        self.xai_key = os.getenv('SIZECOMPARATOR_XAI_API_KEY')
        
        # HTTP client
        self.client = httpx.Client(timeout=10.0)
        
    def generate_comparison(self, weight_kg: float, category: str, style: str = 'default') -> str:
        """
        Generate a comparison for the given weight.
        Tries AI providers first, falls back to static responses.
        """
        # Build prompt
        prompt = self._build_prompt(weight_kg, category, style)
        
        # Try AI providers in order
        providers = []
        if self.xai_key:
            providers.append(('xai', self._call_xai))
        if self.openai_key:
            providers.append(('openai', self._call_openai))
        if self.anthropic_key:
            providers.append(('anthropic', self._call_anthropic))
        
        for provider_name, provider_func in providers:
            try:
                response = provider_func(prompt)
                if response:
                    logger.info(f"Generated comparison using {provider_name}")
                    return self._clean_response(response)
            except Exception as e:
                logger.warning(f"{provider_name} failed: {e}")
                continue
        
        # Fall back to static responses
        logger.info("Using fallback response")
        return self._get_fallback_response(category)
    
    def _build_prompt(self, weight_kg: float, category: str, style: str) -> str:
        """Build prompt for AI providers."""
        base_prompt = f"Generate a brief, creative comparison for something that weighs {weight_kg:.2f} kg. "
        
        if style == 'creative':
            base_prompt += "Be humorous and unexpected. "
        elif style == 'technical':
            base_prompt += "Use scientific or technical comparisons. "
        
        base_prompt += "Keep it under 100 characters. Don't mention the exact weight."
        
        return base_prompt
    
    def _call_openai(self, prompt: str) -> Optional[str]:
        """Call OpenAI API."""
        if not self.openai_key:
            return None
            
        headers = {
            'Authorization': f'Bearer {self.openai_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-4',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 100,
            'temperature': 0.8
        }
        
        response = self.client.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return None
    
    def _call_anthropic(self, prompt: str) -> Optional[str]:
        """Call Anthropic API."""
        if not self.anthropic_key:
            return None
            
        headers = {
            'x-api-key': self.anthropic_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 100,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        
        response = self.client.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()['content'][0]['text']
        return None
    
    def _call_xai(self, prompt: str) -> Optional[str]:
        """Call X.AI API."""
        if not self.xai_key:
            return None
            
        headers = {
            'Authorization': f'Bearer {self.xai_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'grok-2',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 100,
            'temperature': 0.8
        }
        
        response = self.client.post(
            'https://api.x.ai/v1/chat/completions',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return None
    
    def _clean_response(self, response: str) -> str:
        """Clean up AI response."""
        # Remove quotes
        response = response.strip('"\'')
        
        # Remove common prefixes
        prefixes = ['That weighs ', 'That\'s ', 'It\'s ', 'This is ']
        for prefix in prefixes:
            if response.lower().startswith(prefix.lower()):
                response = response[len(prefix):]
        
        # Ensure it starts with "That's "
        if not response.lower().startswith('about'):
            response = f"That's {response}"
        else:
            response = f"That's {response}"
        
        return response.strip()
    
    def _get_fallback_response(self, category: str) -> str:
        """Get a random fallback response for the category."""
        responses = FALLBACK_RESPONSES.get(category, FALLBACK_RESPONSES['medium'])
        return random.choice(responses)
    
    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()