"""
Simple AI Provider Factory

Basic implementation for development and testing.
In production, this would integrate with actual AI provider APIs.
"""

import asyncio
import random
from typing import List

from ...models.providers import AIProvider


class MockAIProvider:
    """Mock AI provider for testing"""
    
    def __init__(self, name: str):
        self.name = name
        self._available = True
        
    async def generate(self, prompt: str, context: dict = None) -> str:
        """Generate mock response"""
        await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate API delay
        
        if not self._available:
            raise Exception(f"Provider {self.name} is not available")
            
        # Generate different styles based on provider
        if self.name == "anthropic":
            return """This weight is like carrying a medium-sized house cat, or about the same as a large hardcover book. 
            To put it in perspective, you could comfortably hold this weight in one hand, and it's roughly equivalent 
            to three smartphones stacked together."""
            
        elif self.name == "openai":
            return """Weighing approximately 1.5 kilograms, this is equivalent to 1.5 times the weight of a standard 
            laptop computer. For comparison, it's about 33% of the weight of an adult house cat (typically 4.5kg), 
            or roughly the same as 8-10 apples."""
            
        else:  # xai
            return """This weight is similar to a large book or small laptop. About the same as 3 smartphones 
            or half a house cat."""
            
    def set_availability(self, available: bool):
        """Set provider availability for testing"""
        self._available = available


class SimpleAIProviderFactory:
    """Simple AI provider factory for testing"""
    
    def __init__(self):
        self._providers = {
            "openai": MockAIProvider("openai"),
            "anthropic": MockAIProvider("anthropic"),
            "xai": MockAIProvider("xai")
        }
        
    async def get_provider(self, name: str) -> MockAIProvider:
        """Get AI provider by name"""
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")
        return self._providers[name]
        
    async def get_available_providers(self) -> List[AIProvider]:
        """Get list of available providers"""
        available = []
        for name, provider in self._providers.items():
            if provider._available:
                available.append(AIProvider(name))
        return available
        
    def set_provider_availability(self, name: str, available: bool):
        """Set provider availability for testing"""
        if name in self._providers:
            self._providers[name].set_availability(available)