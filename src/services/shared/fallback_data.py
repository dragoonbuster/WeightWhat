"""
Fallback Data Manager - Centralized management of fallback comparison data.

This module consolidates fallback comparison data from all comparison services,
providing smart fallback comparisons when AI providers are unavailable.
"""

from typing import Dict, List, Tuple
from .interfaces import FallbackDataInterface, WeightRange, ComparisonObjects


class FallbackDataManager:
    """
    Centralized fallback data management.
    
    Consolidates fallback comparison data from:
    - ai_mvp_comparison.py lines 44-56 (fallback_comparisons)
    - fast_validation_service.py lines 44-53 (weight_ranges)
    - Similar patterns across other services
    """
    
    def __init__(self):
        # Main fallback comparisons by weight range (from ai_mvp_comparison.py)
        self.fallback_comparisons: ComparisonObjects = {
            (0.001, 0.01): {
                "primary": ["a paperclip", "a feather", "a penny"],
                "creative": ["a single grain of rice", "a cotton ball", "a button"],
                "technical": ["0.005 kg standard mass", "typical coin weight", "small electronic component"]
            },
            (0.01, 0.1): {
                "primary": ["a strawberry", "a AAA battery", "a grape"],
                "creative": ["a marble", "a guitar pick", "a tea bag"],
                "technical": ["standard AA battery (24g)", "USB connector", "small hardware screw"]
            },
            (0.1, 0.5): {
                "primary": ["an apple", "a smartphone", "a tennis ball"],
                "creative": ["a deck of cards", "a computer mouse", "a light bulb"],
                "technical": ["iPhone 14 (172g)", "tennis ball (57g)", "standard apple (180g)"]
            },
            (0.5, 2): {
                "primary": ["a pineapple", "a laptop", "a bag of flour"],
                "creative": ["a thick book", "a bottle of wine", "a small houseplant"],
                "technical": ["MacBook Air (1.24kg)", "standard pineapple (1kg)", "1L water bottle"]
            },
            (2, 10): {
                "primary": ["a bowling ball", "a house cat", "a gallon of milk"],
                "creative": ["a watermelon", "a toaster", "a bag of potatoes"],
                "technical": ["bowling ball (7kg)", "average cat (4-5kg)", "gallon of milk (3.8kg)"]
            },
            (10, 50): {
                "primary": ["a medium dog", "a car tire", "a bag of rice"],
                "creative": ["a microwave oven", "a case of beer", "a large turkey"],
                "technical": ["car tire (20-25kg)", "medium dog (20-30kg)", "25kg rice bag"]
            },
            (50, 200): {
                "primary": ["a person", "a bicycle", "a washing machine"],
                "creative": ["a large suitcase", "a refrigerator", "a motorcycle"],
                "technical": ["average person (70kg)", "bicycle (12-15kg)", "washing machine (70-100kg)"]
            },
            (200, 1000): {
                "primary": ["a motorcycle", "a grand piano", "a small car"],
                "creative": ["a vending machine", "a hot tub", "a large aquarium"],
                "technical": ["motorcycle (180-300kg)", "grand piano (300-500kg)", "small car (800-1200kg)"]
            },
            (1000, 5000): {
                "primary": ["a car", "a small elephant", "a speedboat"],
                "creative": ["a hot air balloon basket", "a large tree", "a shipping container"],
                "technical": ["midsize car (1500kg)", "young elephant (2000-3000kg)", "speedboat (1000-2000kg)"]
            },
            (5000, float('inf')): {
                "primary": ["an elephant", "a truck", "a small airplane"],
                "creative": ["a shipping container full of cargo", "a small house", "a large yacht"],
                "technical": ["adult elephant (4000-7000kg)", "semi truck (15000kg)", "small airplane (1000-3000kg)"]
            }
        }
        
        # Validation data for checking reasonableness (from fast_validation_service.py)
        self.weight_validation_ranges = {
            (0.001, 0.01): {
                "max_objects": ["elephant", "car", "piano"], 
                "reasonable": ["paperclip", "feather", "coin"]
            },
            (0.01, 0.1): {
                "max_objects": ["elephant", "car", "person"], 
                "reasonable": ["strawberry", "battery", "grape"]
            },
            (0.1, 1): {
                "max_objects": ["elephant", "car"], 
                "reasonable": ["apple", "phone", "tennis ball"]
            },
            (1, 10): {
                "max_objects": ["elephant herd", "truck"], 
                "reasonable": ["cat", "laptop", "bowling ball"]
            },
            (10, 100): {
                "max_objects": ["blue whale", "airplane"], 
                "reasonable": ["dog", "person", "bicycle"]
            },
            (100, 1000): {
                "max_objects": ["blue whale herd"], 
                "reasonable": ["person group", "motorcycle", "piano"]
            },
            (1000, 10000): {
                "max_objects": [], 
                "reasonable": ["car", "small elephant", "boat"]
            },
        }
    
    def get_comparison_objects(self, weight_kg: float, style: str = "primary") -> List[str]:
        """
        Get appropriate comparison objects for a given weight.
        
        Args:
            weight_kg: Weight in kilograms
            style: Style preference ("primary", "creative", "technical")
            
        Returns:
            List of comparison objects suitable for the weight
        """
        
        # Find appropriate weight range
        for (min_weight, max_weight), objects_dict in self.fallback_comparisons.items():
            if min_weight <= weight_kg < max_weight:
                # Return objects for the requested style, fallback to primary
                return objects_dict.get(style, objects_dict["primary"])
        
        # Fallback for weights outside defined ranges
        return ["a medium-sized object"]
    
    def generate_fallback_comparison(self, weight_kg: float, weight_display: str, style: str = "default") -> str:
        """
        Generate smart fallback comparison text.
        
        Enhanced version of the method from ai_mvp_comparison.py lines 297-314
        (_generate_fallback_comparison).
        """
        
        # Map style to object style
        object_style = "primary"
        if style == "creative":
            object_style = "creative"
        elif style == "technical":
            object_style = "technical"
        
        comparison_objects = self.get_comparison_objects(weight_kg, object_style)
        
        # Create enhanced fallback text based on available objects
        if len(comparison_objects) >= 3:
            obj1, obj2, obj3 = comparison_objects[0], comparison_objects[1], comparison_objects[2]
            
            if style == "creative":
                return f"{weight_display} is about the weight of {obj1}, similar to {obj2}, or roughly equivalent to {obj3}. Picture any of these to get a good sense of this weight!"
            elif style == "technical":
                return f"{weight_display} corresponds to the mass of {obj1}, comparable to {obj2}, or approximately {obj3}. These provide accurate reference points for visualization."
            else:
                return f"{weight_display} is about the weight of {obj1} or {obj2}. You could also think of it as similar to {obj3}. That gives you a good reference point!"
                
        elif len(comparison_objects) >= 2:
            obj1, obj2 = comparison_objects[0], comparison_objects[1]
            
            if style == "creative":
                return f"{weight_display} is about the weight of {obj1} or {obj2}. Imagine holding either one to visualize this weight!"
            elif style == "technical":
                return f"{weight_display} is equivalent to the mass of {obj1} or {obj2}. These provide reliable reference points."
            else:
                return f"{weight_display} is about the weight of {obj1} or {obj2}. That's a pretty good reference point to visualize this weight!"
                
        else:
            obj = comparison_objects[0]
            if style == "creative":
                return f"{weight_display} is about the weight of {obj}. Try to imagine picking it up!"
            elif style == "technical":
                return f"{weight_display} corresponds to the mass of {obj}."
            else:
                return f"{weight_display} is about the weight of {obj}."
    
    def is_reasonable_object(self, weight_kg: float, object_name: str) -> bool:
        """
        Check if an object is reasonable for the given weight.
        
        Extracted from fast_validation_service.py lines 231-261 (_is_response_reasonable).
        """
        
        object_name_lower = object_name.lower()
        
        # Find appropriate validation range
        validation_range = None
        for (min_w, max_w), range_info in self.weight_validation_ranges.items():
            if min_w <= weight_kg < max_w:
                validation_range = range_info
                break
        
        if not validation_range:
            return True  # No range found, assume reasonable
        
        # Check for obviously wrong objects
        for wrong_object in validation_range["max_objects"]:
            if wrong_object in object_name_lower:
                return False
        
        # Additional reasonableness checks
        # Check for extreme size mismatches
        if weight_kg < 1:  # Very light objects
            heavy_objects = ["elephant", "car", "truck", "piano", "person", "dog"]
            for heavy_obj in heavy_objects:
                if heavy_obj in object_name_lower:
                    return False
        
        elif weight_kg > 1000:  # Very heavy objects
            light_objects = ["paperclip", "feather", "grape", "apple", "phone", "battery"]
            for light_obj in light_objects:
                if light_obj in object_name_lower:
                    return False
        
        return True
    
    def get_weight_category(self, weight_kg: float) -> str:
        """Get descriptive category for weight range"""
        
        if weight_kg < 0.01:
            return "ultra_light"
        elif weight_kg < 0.1:
            return "very_light"
        elif weight_kg < 1:
            return "light"
        elif weight_kg < 10:
            return "moderate"
        elif weight_kg < 100:
            return "heavy"
        elif weight_kg < 1000:
            return "very_heavy"
        else:
            return "ultra_heavy"
    
    def get_validation_info(self, weight_kg: float) -> Dict[str, any]:
        """Get validation information for a given weight"""
        
        category = self.get_weight_category(weight_kg)
        reasonable_objects = self.get_comparison_objects(weight_kg, "primary")
        
        # Find validation range
        validation_range = None
        for (min_w, max_w), range_info in self.weight_validation_ranges.items():
            if min_w <= weight_kg < max_w:
                validation_range = range_info
                break
        
        return {
            "weight_kg": weight_kg,
            "category": category,
            "reasonable_objects": reasonable_objects,
            "unreasonable_objects": validation_range["max_objects"] if validation_range else [],
            "needs_careful_validation": weight_kg < 0.1 or weight_kg > 100
        }
    
    def enhance_comparison_with_context(self, base_comparison: str, weight_kg: float) -> str:
        """Add helpful context to a comparison"""
        
        category = self.get_weight_category(weight_kg)
        
        context_additions = {
            "ultra_light": "This is extremely light - barely noticeable when picked up.",
            "very_light": "This is quite light - you'd barely feel it in your hand.",
            "light": "This is relatively light - easy to carry and handle.",
            "moderate": "This has some noticeable weight - you'd feel it when lifting.",
            "heavy": "This is getting heavy - would require some effort to lift.",
            "very_heavy": "This is quite heavy - would need multiple people or equipment to move.",
            "ultra_heavy": "This is extremely heavy - requires specialized equipment to move."
        }
        
        context = context_additions.get(category, "")
        
        if context:
            return f"{base_comparison} {context}"
        else:
            return base_comparison