"""
AI Provider Manager - Centralized management of AI providers with failover and health monitoring.

This module extracts common AI provider logic from all comparison services,
providing a unified interface for calling multiple AI providers with automatic
failover and health monitoring.
"""

import os
import time
import asyncio
import httpx
from typing import Optional, Dict, Any, List, Tuple

from .interfaces import AIProviderInterface, AIProviderConfig, AIProviderResponse
from src.core.simple_config import get_config

# AI Provider imports with availability checks
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class OpenAIProvider:
    """OpenAI GPT provider implementation"""
    
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.client = None
        if config.api_key and OPENAI_AVAILABLE:
            self.client = openai.AsyncOpenAI(api_key=config.api_key)
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def is_available(self) -> bool:
        return self.client is not None
    
    async def generate_comparison(self, prompt: str, **kwargs) -> AIProviderResponse:
        """Generate comparison using OpenAI GPT"""
        if not self.is_available:
            return AIProviderResponse(
                content="",
                provider_name=self.name,
                model_used=self.config.model,
                success=False,
                error_message="OpenAI client not available"
            )
        
        start_time = time.time()
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system", 
                        "content": kwargs.get("system_message", "You are a helpful assistant that creates engaging weight comparisons. Be concise, accurate, and fun.")
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            content = response.choices[0].message.content.strip()
            
            return AIProviderResponse(
                content=content,
                provider_name=self.name,
                model_used=self.config.model,
                success=True,
                response_time_ms=response_time_ms
            )
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return AIProviderResponse(
                content="",
                provider_name=self.name,
                model_used=self.config.model,
                success=False,
                error_message=str(e),
                response_time_ms=response_time_ms
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI provider health"""
        return {
            "available": self.is_available,
            "model": self.config.model,
            "configured": bool(self.config.api_key),
            "library_available": OPENAI_AVAILABLE
        }


class AnthropicProvider:
    """Anthropic Claude provider implementation"""
    
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.client = None
        if config.api_key and ANTHROPIC_AVAILABLE:
            self.client = anthropic.AsyncAnthropic(api_key=config.api_key)
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def is_available(self) -> bool:
        return self.client is not None
    
    async def generate_comparison(self, prompt: str, **kwargs) -> AIProviderResponse:
        """Generate comparison using Anthropic Claude"""
        if not self.is_available:
            return AIProviderResponse(
                content="",
                provider_name=self.name,
                model_used=self.config.model,
                success=False,
                error_message="Anthropic client not available"
            )
        
        start_time = time.time()
        try:
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=kwargs.get("system_message", "You are a helpful assistant that creates engaging weight comparisons. Be concise, accurate, and fun."),
                messages=[
                    {"role": "user", "content": prompt}
                ],
                timeout=self.config.timeout
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            content = response.content[0].text.strip()
            
            return AIProviderResponse(
                content=content,
                provider_name=self.name,
                model_used=self.config.model,
                success=True,
                response_time_ms=response_time_ms
            )
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return AIProviderResponse(
                content="",
                provider_name=self.name,
                model_used=self.config.model,
                success=False,
                error_message=str(e),
                response_time_ms=response_time_ms
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Anthropic provider health"""
        return {
            "available": self.is_available,
            "model": self.config.model,
            "configured": bool(self.config.api_key),
            "library_available": ANTHROPIC_AVAILABLE
        }


class XAIProvider:
    """X.ai Grok provider implementation"""
    
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.client = httpx.AsyncClient()
    
    @property
    def name(self) -> str:
        return "xai"
    
    @property
    def is_available(self) -> bool:
        return bool(self.config.api_key)
    
    async def generate_comparison(self, prompt: str, **kwargs) -> AIProviderResponse:
        """Generate comparison using X.ai Grok"""
        if not self.is_available:
            return AIProviderResponse(
                content="",
                provider_name=self.name,
                model_used=self.config.model,
                success=False,
                error_message="X.ai API key not configured"
            )
        
        start_time = time.time()
        try:
            # X.ai API endpoint
            url = "https://api.x.ai/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            print(f"X.AI API request - Model: {self.config.model}, URL: {url}")
            
            data = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": kwargs.get("system_message", "Create engaging weight comparisons with Grok's unique style.")},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature
            }
            
            response = await self.client.post(url, json=data, headers=headers, timeout=self.config.timeout)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                return AIProviderResponse(
                    content=content,
                    provider_name=self.name,
                    model_used=self.config.model,
                    success=True,
                    response_time_ms=response_time_ms
                )
            else:
                error_body = response.text[:500] if response.text else "No response body"
                print(f"X.AI API Error - Status: {response.status_code}, Body: {error_body}")
                return AIProviderResponse(
                    content="",
                    provider_name=self.name,
                    model_used=self.config.model,
                    success=False,
                    error_message=f"API error: {response.status_code}",
                    response_time_ms=response_time_ms
                )
                
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return AIProviderResponse(
                content="",
                provider_name=self.name,
                model_used=self.config.model,
                success=False,
                error_message=str(e),
                response_time_ms=response_time_ms
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check X.ai provider health"""
        return {
            "available": self.is_available,
            "model": self.config.model,
            "configured": bool(self.config.api_key),
            "library_available": True  # Uses httpx which is always available
        }


class AIProviderManager:
    """
    Centralized AI provider management with failover and health monitoring.
    
    Extracted from ai_mvp_comparison.py lines 58-71 (_setup_ai_providers) and
    lines 220-295 (provider calling methods).
    """
    
    def __init__(self):
        self.providers: Dict[str, AIProviderInterface] = {}
        self.provider_order = ["openai", "anthropic", "xai"]  # Default preference order
        self._setup_providers()
        
        # Intelligent routing configuration
        self.routing_config = {
            "simple_weights": {  # 1-100kg
                "preferred_providers": ["xai", "openai", "anthropic"],
                "preferred_models": {
                    "xai": "grok-3-mini",
                    "openai": "gpt-3.5-turbo",
                    "anthropic": "claude-3-haiku"
                }
            },
            "complex_weights": {  # <1kg or >100kg
                "preferred_providers": ["openai", "anthropic", "xai"],
                "preferred_models": {
                    "xai": "grok-2",
                    "openai": "gpt-4",
                    "anthropic": "claude-3-opus"
                }
            },
            "style_preferences": {
                "technical": ["openai", "xai", "anthropic"],
                "creative": ["anthropic", "xai", "openai"],
                "default": ["xai", "openai", "anthropic"]
            }
        }
    
    def _setup_providers(self):
        """Initialize AI provider clients - extracted from ai_mvp_comparison.py"""
        
        # Get simplified configuration
        config = get_config()
        
        # OpenAI setup
        openai_config = AIProviderConfig(
            name="openai",
            api_key=config.get('openai_api_key'),
            model=config.get('openai_model'),
            max_tokens=config.get('openai_max_tokens'),
            temperature=config.get('openai_temperature'),
            timeout=config.get('openai_timeout'),
            enabled=bool(config.get('openai_api_key'))
        )
        self.providers["openai"] = OpenAIProvider(openai_config)
        
        # Anthropic setup
        anthropic_config = AIProviderConfig(
            name="anthropic",
            api_key=config.get('anthropic_api_key'),
            model=config.get('anthropic_model'),
            max_tokens=config.get('anthropic_max_tokens'),
            temperature=config.get('anthropic_temperature'),
            timeout=config.get('anthropic_timeout'),
            enabled=bool(config.get('anthropic_api_key'))
        )
        self.providers["anthropic"] = AnthropicProvider(anthropic_config)
        
        # X.ai setup
        xai_config = AIProviderConfig(
            name="xai",
            api_key=config.get('xai_api_key'),
            model=config.get('xai_model'),
            max_tokens=config.get('xai_max_tokens', 150),
            temperature=config.get('xai_temperature', 0.8),  # Slightly higher for Grok's creativity
            timeout=config.get('xai_timeout'),
            enabled=bool(config.get('xai_api_key'))
        )
        self.providers["xai"] = XAIProvider(xai_config)
    
    def _get_provider_order(self, weight_kg: float = None, style: str = "default") -> List[str]:
        """
        Determine provider order based on weight complexity and style.
        
        Args:
            weight_kg: Weight in kilograms (for complexity determination)
            style: Comparison style (default, technical, creative)
            
        Returns:
            Ordered list of provider names to try
        """
        # Determine weight complexity
        if weight_kg is not None:
            is_simple_weight = 1 <= weight_kg <= 100
            weight_config = self.routing_config["simple_weights" if is_simple_weight else "complex_weights"]
            base_order = weight_config["preferred_providers"]
        else:
            base_order = self.provider_order
            
        # Apply style preferences
        style_order = self.routing_config["style_preferences"].get(style, self.provider_order)
        
        # Combine preferences: prioritize style within weight category
        final_order = []
        for provider in style_order:
            if provider in base_order and provider not in final_order:
                final_order.append(provider)
        
        # Add any remaining providers from base_order
        for provider in base_order:
            if provider not in final_order:
                final_order.append(provider)
                
        # Filter to only available providers
        available_order = [p for p in final_order if p in self.providers and self.providers[p].is_available]
        
        return available_order if available_order else ["xai", "openai", "anthropic"]
    
    async def generate_comparison_with_fallover(self, prompt: str, weight_kg: float = None, style: str = "default", **kwargs) -> Tuple[Optional[str], str]:
        """
        Try AI providers in order of preference until one succeeds.
        
        Extracted and consolidated from:
        - ai_mvp_comparison.py lines 118-156 (_generate_ai_comparison)
        - fast_validation_service.py similar patterns
        - ai_validation_service.py similar patterns
        
        Returns:
            Tuple of (comparison_text, provider_used)
        """
        
        # Get intelligent provider order based on weight and style
        provider_order = self._get_provider_order(weight_kg, style)
        
        for provider_name in provider_order:
            provider = self.providers.get(provider_name)
            if not provider or not provider.is_available:
                continue
            
            try:
                response = await provider.generate_comparison(prompt, **kwargs)
                if response.success and response.content:
                    provider_display = f"{provider_name}_{response.model_used.replace('-', '_')}"
                    return response.content, provider_display
                else:
                    print(f"{provider_name} failed: {response.error_message}")
                    
            except Exception as e:
                print(f"{provider_name} exception: {e}")
        
        # All providers failed
        return None, "all_providers_failed"
    
    async def generate_multiple_responses(self, prompt: str, count: int, timeout: float = 8.0, **kwargs) -> List[str]:
        """
        Generate multiple responses in parallel for validation.
        
        Extracted from ai_validation_service.py lines 77-104 (_generate_parallel_responses)
        and fast_validation_service.py lines 156-180 (_get_fast_responses).
        """
        
        tasks = []
        for i in range(count):
            task = self._single_provider_call(prompt, f"parallel_{i+1}", **kwargs)
            tasks.append(task)
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
            
            successful_responses = []
            for result in results:
                if isinstance(result, str) and result and len(result) > 20:
                    successful_responses.append(result)
            
            return successful_responses
            
        except asyncio.TimeoutError:
            print(f"Parallel AI calls timed out after {timeout}s")
            return []
    
    async def _single_provider_call(self, prompt: str, call_id: str, weight_kg: float = None, style: str = "default", **kwargs) -> str:
        """Single provider call for parallel execution with intelligent routing"""
        
        # Get provider order based on weight and style
        provider_order = self._get_provider_order(weight_kg, style)
        
        # Try providers in order
        for provider_name in provider_order:
            provider = self.providers.get(provider_name)
            if not provider:
                print(f"Provider {provider_name} not found in providers dict")
                continue
            if not provider.is_available:
                print(f"Provider {provider_name} is not available")
                continue
                
            try:
                print(f"Trying provider {provider_name} for call {call_id}")
                response = await provider.generate_comparison(prompt, **kwargs)
                if response.success and response.content:
                    print(f"Provider call {call_id} succeeded with {provider_name}")
                    return response.content
                else:
                    print(f"Provider {provider_name} returned empty or failed response: {response.error_message}")
            except Exception as e:
                print(f"Provider {provider_name} call {call_id} failed with exception: {e}")
                continue
        
        print(f"All providers failed for call {call_id}")
        return ""
    
    async def validate_responses_with_ai(self, weight_kg: float, weight_display: str, responses: List[str]) -> str:
        """
        Use AI to validate and select best response from multiple candidates.
        
        Extracted from ai_validation_service.py lines 119-164 (_validate_responses)
        and lines 234-255 (_call_openai_validation).
        """
        
        if len(responses) <= 1:
            return responses[0] if responses else ""
        
        # Build validation prompt
        responses_text = "\n".join(f"{i+1}. {resp[:100]}..." for i, resp in enumerate(responses))
        
        prompt = f"""Weight: {weight_display} (exactly {weight_kg} kg). Pick the most accurate comparison:

{responses_text}

Reply with just the number (1, 2, or 3) of the best one:"""
        
        provider = self.providers.get("openai")
        if not provider or not provider.is_available:
            return responses[0]  # Fallback to first response
        
        try:
            response = await provider.generate_comparison(
                prompt, 
                max_tokens=10,
                temperature=0.1,
                timeout=2.0,
                system_message="You are an expert at validating weight comparisons for accuracy. Be strict and precise."
            )
            
            if response.success:
                import re
                choice_match = re.search(r'\d+', response.content)
                if choice_match:
                    choice_num = int(choice_match.group())
                    if 1 <= choice_num <= len(responses):
                        return responses[choice_num - 1]
            
        except Exception as e:
            print(f"AI validation failed: {e}")
        
        # Fallback to first response
        return responses[0]
    
    def build_prompt(self, weight_kg: float, weight_display: str, style: str = "default") -> str:
        """
        Build AI prompt based on style and weight.
        
        Extracted from ai_mvp_comparison.py lines 158-183 (_build_prompt).
        """
        
        # Clean up weight display to avoid AI confusion
        clean_weight = self._clean_weight_display(weight_kg, weight_display)
        
        base_prompt = f"Create a fun and engaging comparison for {clean_weight}. "
        
        if style == "creative":
            return (base_prompt + 
                   "Be creative and imaginative! Use interesting, unexpected objects. "
                   "Make it memorable and fun. Compare it to 2-3 different things. "
                   "Keep it under 100 words and make it engaging.")
        
        elif style == "technical":
            return (base_prompt +
                   "Provide precise, technical comparisons. Include scientific context "
                   "where relevant. Compare to common reference objects with exact weights. "
                   "Be informative and educational. Keep it under 100 words.")
        
        else:  # default
            return (base_prompt +
                   "Compare it to common everyday objects that people can easily visualize. "
                   "Make it relatable and interesting. Use 2-3 comparison objects. "
                   "Keep it conversational and under 80 words.")
    
    def _clean_weight_display(self, weight_kg: float, weight_display: str) -> str:
        """
        Clean weight display to prevent AI misinterpretation
        
        Shared utility method for weight display formatting.
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
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all AI providers"""
        
        provider_health = {}
        available_count = 0
        
        for name, provider in self.providers.items():
            health = await provider.health_check()
            provider_health[name] = health
            if health["available"]:
                available_count += 1
        
        return {
            "providers": provider_health,
            "available_count": available_count,
            "total_providers": len(self.providers),
            "primary_mode": "ai_powered" if available_count > 0 else "fallback_only"
        }
    
    async def cleanup(self):
        """Cleanup AI provider resources"""
        for provider in self.providers.values():
            if hasattr(provider, 'client') and hasattr(provider.client, 'aclose'):
                try:
                    await provider.client.aclose()
                except Exception as e:
                    print(f"Error closing provider client: {e}")