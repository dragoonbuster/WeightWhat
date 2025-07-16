"""
Fallback Response Generator

Generates and manages a comprehensive repository of AI-generated fallback responses
organized by weight ranges and styles for use when AI providers are unavailable.
"""

import asyncio
import json
import random
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

from .shared.ai_provider_manager import AIProviderManager
from .weight_processor import WeightProcessor


@dataclass
class FallbackResponse:
    """Single fallback response with metadata"""
    weight_kg: float
    weight_display: str
    style: str
    comparison_text: str
    provider_used: str
    generated_at: str
    quality_score: float = 0.8
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class WeightRange:
    """Weight range definition for organizing responses"""
    
    def __init__(self, min_kg: float, max_kg: float, name: str):
        self.min_kg = min_kg
        self.max_kg = max_kg
        self.name = name
    
    def contains(self, weight_kg: float) -> bool:
        return self.min_kg <= weight_kg < self.max_kg
    
    def get_test_weights(self) -> List[float]:
        """Get representative test weights for this range"""
        if self.max_kg == float('inf'):
            return [self.min_kg, self.min_kg * 2, self.min_kg * 5]
        
        range_size = self.max_kg - self.min_kg
        if range_size <= 0.01:  # Very small ranges
            return [self.min_kg, self.min_kg + range_size * 0.5, self.max_kg * 0.99]
        else:
            return [
                self.min_kg,
                self.min_kg + range_size * 0.3,
                self.min_kg + range_size * 0.7,
                self.max_kg * 0.99
            ]


class FallbackResponseGenerator:
    """Generates comprehensive fallback response repository"""
    
    def __init__(self):
        self.ai_provider_manager = AIProviderManager()
        self.weight_processor = WeightProcessor()
        
        # Define weight ranges
        self.weight_ranges = [
            WeightRange(0.0001, 0.001, "microscopic"),      # 0.1mg-1mg
            WeightRange(0.001, 0.01, "tiny"),               # 1mg-10mg  
            WeightRange(0.01, 0.1, "very_small"),           # 10mg-100mg
            WeightRange(0.1, 1.0, "small"),                 # 100mg-1g
            WeightRange(1.0, 10.0, "light"),                # 1g-10g
            WeightRange(10.0, 100.0, "moderate"),           # 10g-100g
            WeightRange(100.0, 1000.0, "medium"),           # 100g-1kg
            WeightRange(1000.0, 10000.0, "heavy"),          # 1kg-10kg
            WeightRange(10000.0, 100000.0, "very_heavy"),   # 10kg-100kg
            WeightRange(100000.0, float('inf'), "extreme")  # 100kg+
        ]
        
        # Define styles
        self.styles = ["default", "creative", "technical"]
        
        # Target responses per weight range per style
        self.responses_per_combination = 8
        
        # Repository storage
        self.repository_file = Path("fallback_responses.json")
        self.repository: Dict[str, Dict[str, List[FallbackResponse]]] = {}
    
    async def generate_comprehensive_repository(self) -> Dict[str, Any]:
        """Generate a comprehensive repository of fallback responses"""
        
        print(f"🚀 Generating comprehensive fallback response repository...")
        print(f"📊 Targeting {len(self.weight_ranges)} weight ranges × {len(self.styles)} styles × {self.responses_per_combination} responses = {len(self.weight_ranges) * len(self.styles) * self.responses_per_combination} total responses")
        
        total_generated = 0
        total_failed = 0
        
        for weight_range in self.weight_ranges:
            print(f"\n🎯 Processing weight range: {weight_range.name} ({weight_range.min_kg}-{weight_range.max_kg}kg)")
            
            # Initialize range in repository
            if weight_range.name not in self.repository:
                self.repository[weight_range.name] = {}
            
            for style in self.styles:
                print(f"  📝 Style: {style}")
                
                # Initialize style in repository
                if style not in self.repository[weight_range.name]:
                    self.repository[weight_range.name][style] = []
                
                # Generate responses for this range/style combination
                test_weights = weight_range.get_test_weights()
                responses_per_weight = max(1, self.responses_per_combination // len(test_weights))
                
                for weight_kg in test_weights:
                    for i in range(responses_per_weight):
                        try:
                            response = await self._generate_single_response(weight_kg, style)
                            if response:
                                self.repository[weight_range.name][style].append(response)
                                total_generated += 1
                                print(f"    ✅ Generated response {i+1}/{responses_per_weight} for {weight_kg}kg")
                            else:
                                total_failed += 1
                                print(f"    ❌ Failed to generate response {i+1}/{responses_per_weight} for {weight_kg}kg")
                        except Exception as e:
                            total_failed += 1
                            print(f"    ❌ Error generating response for {weight_kg}kg: {e}")
                
                # Add some buffer time between styles
                await asyncio.sleep(0.5)
        
        # Save repository
        self._save_repository()
        
        print(f"\n🎉 Repository generation complete!")
        print(f"✅ Generated: {total_generated} responses")
        print(f"❌ Failed: {total_failed} responses")
        print(f"📁 Saved to: {self.repository_file}")
        
        return {
            "total_generated": total_generated,
            "total_failed": total_failed,
            "repository_file": str(self.repository_file),
            "ranges": len(self.weight_ranges),
            "styles": len(self.styles)
        }
    
    async def _generate_single_response(self, weight_kg: float, style: str) -> Optional[FallbackResponse]:
        """Generate a single fallback response for given weight and style"""
        
        try:
            # Format weight for display
            if weight_kg < 0.001:
                weight_display = f"{weight_kg * 1000000:.1f} mg"
            elif weight_kg < 1.0:
                weight_display = f"{weight_kg * 1000:.1f} g"
            else:
                weight_display = f"{weight_kg:.1f} kg"
            
            # Build prompt
            prompt = self.ai_provider_manager.build_prompt(weight_kg, weight_display, style)
            
            # Generate response
            comparison_text = await self.ai_provider_manager._single_provider_call(
                prompt, f"fallback_{style}_{weight_kg}", weight_kg=weight_kg, style=style
            )
            
            if not comparison_text:
                return None
            
            # Create response object
            response = FallbackResponse(
                weight_kg=weight_kg,
                weight_display=weight_display,
                style=style,
                comparison_text=comparison_text,
                provider_used="generated_fallback",
                generated_at=datetime.now().isoformat(),
                quality_score=0.8,
                tags=self._extract_tags(comparison_text)
            )
            
            return response
            
        except Exception as e:
            print(f"Error generating response for {weight_kg}kg {style}: {e}")
            return None
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract tags from response text for categorization"""
        tags = []
        
        # Common object categories
        animals = ["cat", "dog", "elephant", "bird", "fish", "horse", "cow", "pig", "chicken", "mouse", "whale", "lion", "tiger", "bear", "panda", "hippo"]
        food = ["apple", "banana", "orange", "bread", "rice", "flour", "sugar", "milk", "water", "meat", "cheese", "chocolate"]
        objects = ["phone", "laptop", "car", "bike", "book", "pen", "paper", "ball", "chair", "table", "cup", "plate"]
        scientific = ["atom", "molecule", "cell", "brain", "gram", "kilogram", "pound", "liter", "density", "mass", "weight"]
        
        text_lower = text.lower()
        
        for animal in animals:
            if animal in text_lower:
                tags.append(f"animal:{animal}")
        
        for food_item in food:
            if food_item in text_lower:
                tags.append(f"food:{food_item}")
        
        for obj in objects:
            if obj in text_lower:
                tags.append(f"object:{obj}")
        
        for sci in scientific:
            if sci in text_lower:
                tags.append("scientific")
                break
        
        return tags
    
    def _save_repository(self):
        """Save repository to JSON file"""
        
        # Convert to serializable format
        serializable_repo = {}
        for range_name, styles in self.repository.items():
            serializable_repo[range_name] = {}
            for style, responses in styles.items():
                serializable_repo[range_name][style] = [asdict(response) for response in responses]
        
        # Save to file
        with open(self.repository_file, 'w') as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "version": "1.0.0",
                "total_responses": sum(len(responses) for styles in serializable_repo.values() for responses in styles.values()),
                "repository": serializable_repo
            }, f, indent=2)
    
    def load_repository(self) -> bool:
        """Load repository from JSON file"""
        
        if not self.repository_file.exists():
            return False
        
        try:
            with open(self.repository_file, 'r') as f:
                data = json.load(f)
            
            # Convert back to objects
            repo_data = data.get("repository", {})
            for range_name, styles in repo_data.items():
                if range_name not in self.repository:
                    self.repository[range_name] = {}
                
                for style, responses in styles.items():
                    self.repository[range_name][style] = [
                        FallbackResponse(**response_data) for response_data in responses
                    ]
            
            print(f"✅ Loaded {data.get('total_responses', 0)} fallback responses from {self.repository_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading repository: {e}")
            return False
    
    def get_random_response(self, weight_kg: float, style: str = "default") -> Optional[FallbackResponse]:
        """Get a random fallback response for the given weight and style"""
        
        # Find appropriate weight range
        weight_range = None
        for range_obj in self.weight_ranges:
            if range_obj.contains(weight_kg):
                weight_range = range_obj
                break
        
        if not weight_range:
            return None
        
        # Get responses for this range and style
        responses = self.repository.get(weight_range.name, {}).get(style, [])
        
        if not responses:
            # Try default style if requested style not available
            if style != "default":
                responses = self.repository.get(weight_range.name, {}).get("default", [])
        
        if not responses:
            return None
        
        # Return random response
        return random.choice(responses)
    
    def get_repository_stats(self) -> Dict[str, Any]:
        """Get statistics about the current repository"""
        
        stats = {
            "total_responses": 0,
            "by_range": {},
            "by_style": {},
            "coverage": {}
        }
        
        for range_name, styles in self.repository.items():
            range_total = 0
            stats["by_range"][range_name] = {}
            
            for style, responses in styles.items():
                count = len(responses)
                range_total += count
                stats["total_responses"] += count
                
                stats["by_range"][range_name][style] = count
                
                if style not in stats["by_style"]:
                    stats["by_style"][style] = 0
                stats["by_style"][style] += count
        
        # Calculate coverage
        target_total = len(self.weight_ranges) * len(self.styles) * self.responses_per_combination
        stats["coverage"]["percentage"] = (stats["total_responses"] / target_total) * 100 if target_total > 0 else 0
        stats["coverage"]["target"] = target_total
        
        return stats


# CLI functions for generating responses
async def generate_fallback_repository():
    """Generate comprehensive fallback response repository"""
    generator = FallbackResponseGenerator()
    results = await generator.generate_comprehensive_repository()
    return results


async def test_fallback_responses():
    """Test fallback response system"""
    generator = FallbackResponseGenerator()
    
    # Load existing repository
    if generator.load_repository():
        # Test some responses
        test_weights = [0.5, 5.0, 50.0, 500.0]
        test_styles = ["default", "creative", "technical"]
        
        print("\n🧪 Testing fallback responses:")
        for weight in test_weights:
            for style in test_styles:
                response = generator.get_random_response(weight, style)
                if response:
                    print(f"  {weight}kg {style}: {response.comparison_text[:60]}...")
                else:
                    print(f"  {weight}kg {style}: No response available")
        
        # Show stats
        stats = generator.get_repository_stats()
        print(f"\n📊 Repository Statistics:")
        print(f"  Total responses: {stats['total_responses']}")
        print(f"  Coverage: {stats['coverage']['percentage']:.1f}%")
        print(f"  By style: {stats['by_style']}")
    
    else:
        print("❌ No repository found. Run generate_fallback_repository() first.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        asyncio.run(generate_fallback_repository())
    else:
        asyncio.run(test_fallback_responses())