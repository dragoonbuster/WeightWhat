# OpenAI Provider Implementation Specification

## 1. Overview

The OpenAI Provider implementation for SizeComparator provides a robust, production-ready integration with OpenAI's GPT-4 API featuring structured output, advanced rate limiting, comprehensive error handling, and seamless integration with the SizeComparator system architecture. This specification defines the complete implementation requirements, optimization strategies, and integration patterns necessary for reliable weight comparison generation.

### 1.1 Integration Points

This specification must align with:
- **PROVIDER_INTERFACE_SPEC**: Abstract provider interface and base contracts
- **CONFIG_SYSTEM_SPEC**: Configuration management, prompt templates, and hot-reload
- **BACKEND_CORE_SPEC**: Pydantic models, FastAPI async patterns, and response formatting
- **ERROR_MONITORING_SPEC**: Structured logging, error categorization, and monitoring integration

### 1.2 Key Features

- GPT-4 structured output with JSON schema validation
- Advanced rate limiting with 3500 RPM compliance
- Intelligent prompt engineering optimized for weight comparisons
- Comprehensive error handling with circuit breaker integration
- Response parsing and validation specific to OpenAI format
- Token usage optimization and response caching strategies
- Production-ready security and monitoring integration

## 2. OpenAI API Client Implementation

### 2.1 Core Provider Class

```python
import openai
import json
import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid
import logging

from backend.models.requests import WeightComparisonRequest
from backend.models.responses import WeightComparisonResponse, WeightItem, ComparisonResult
from providers.base import AIProvider, ProviderHealth, ProviderStatus, AIProviderRequest


class OpenAIConfiguration(BaseModel):
    """OpenAI provider configuration with validation."""
    api_key: str = Field(..., min_length=20, description="OpenAI API key")
    endpoint: str = Field(default="https://api.openai.com/v1", description="API endpoint")
    model: str = Field(default="gpt-4", description="GPT model to use")
    timeout_seconds: float = Field(default=30.0, ge=5.0, le=120.0, description="Request timeout")
    max_tokens: int = Field(default=500, ge=100, le=4000, description="Maximum tokens per request")
    temperature: float = Field(default=0.3, ge=0.0, le=1.0, description="Model temperature")
    rate_limit_rpm: int = Field(default=3500, ge=100, le=10000, description="Rate limit per minute")
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    backoff_factor: float = Field(default=2.0, ge=1.1, le=5.0, description="Exponential backoff factor")
    structured_output: bool = Field(default=True, description="Use structured JSON output")
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl_seconds: int = Field(default=3600, ge=300, le=86400, description="Cache TTL")


class OpenAIProvider(AIProvider):
    """Production OpenAI provider with advanced features."""
    
    def __init__(self, config: OpenAIConfiguration, logger: logging.Logger = None):
        super().__init__(config.dict(), logger)
        self.config = config
        self.name = "OpenAI"
        
        # Initialize OpenAI client with proper configuration
        self.client = openai.AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.endpoint,
            timeout=self.config.timeout_seconds,
            max_retries=0  # We handle retries ourselves for better control
        )
        
        # Rate limiting and performance tracking
        self.rate_limiter = OpenAIRateLimiter(self.config.rate_limit_rpm)
        self.token_tracker = TokenUsageTracker()
        self.response_cache = ResponseCache(enabled=self.config.enable_caching)
        
        # Error tracking for circuit breaker integration
        self.error_tracker = ErrorTracker()
        self.last_api_call = None
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens_used": 0,
            "avg_response_time_ms": 0.0,
            "cache_hit_rate": 0.0
        }
        
        self._log_structured_event(
            "info", 
            "OpenAI provider initialized",
            model=self.config.model,
            rate_limit=self.config.rate_limit_rpm,
            structured_output=self.config.structured_output
        )
    
    async def generate_comparison(self, request: AIProviderRequest) -> WeightComparisonResponse:
        """Generate weight comparison using OpenAI GPT-4 with structured output."""
        request_start = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # Check rate limiting before making request
            await self.rate_limiter.acquire_token()
            
            # Check cache first if enabled
            cache_key = self._generate_cache_key(request)
            if self.config.enable_caching:
                cached_response = await self.response_cache.get(cache_key)
                if cached_response:
                    self._log_structured_event(
                        "debug",
                        "Cache hit for OpenAI request",
                        request_id=request.request_id,
                        cache_key=cache_key
                    )
                    return cached_response
            
            # Build the OpenAI request
            openai_request = await self._build_openai_request(request)
            
            # Execute API call with timeout and retry handling
            response = await self._execute_api_call(openai_request, request.request_id)
            
            # Validate and parse response
            if not self.validate_response(response):
                raise ValueError("Invalid response format from OpenAI API")
            
            parsed_response = self.parse_response(response, request)
            
            # Update metrics and cache
            response_time = (time.time() - request_start) * 1000
            self._update_metrics(response, response_time, success=True)
            
            # Cache successful response
            if self.config.enable_caching:
                await self.response_cache.set(cache_key, parsed_response, self.config.cache_ttl_seconds)
            
            self._log_structured_event(
                "info",
                "OpenAI comparison generated successfully",
                request_id=request.request_id,
                response_time_ms=response_time,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                model=self.config.model
            )
            
            return parsed_response
            
        except openai.RateLimitError as e:
            self.metrics["failed_requests"] += 1
            await self._handle_rate_limit_error(e, request.request_id)
            raise
        except openai.APIError as e:
            self.metrics["failed_requests"] += 1
            await self._handle_api_error(e, request.request_id)
            raise
        except Exception as e:
            self.metrics["failed_requests"] += 1
            self._log_structured_event(
                "error",
                "Unexpected error in OpenAI provider",
                request_id=request.request_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
    
    async def _build_openai_request(self, request: AIProviderRequest) -> Dict[str, Any]:
        """Build OpenAI API request with structured output configuration."""
        
        # Get the optimized prompt from CONFIG_SYSTEM_SPEC template
        prompt = await self._get_optimized_prompt(request)
        
        # Base request configuration
        openai_request = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": await self._get_system_prompt()
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": min(request.max_tokens, self.config.max_tokens),
            "temperature": min(request.temperature, self.config.temperature),
            "timeout": request.timeout_seconds
        }
        
        # Add structured output configuration for GPT-4
        if self.config.structured_output and self._supports_structured_output():
            openai_request["response_format"] = {
                "type": "json_object"
            }
            # Ensure the prompt explicitly requests JSON
            openai_request["messages"][0]["content"] += "\n\nYou must respond with valid JSON only."
        
        return openai_request
    
    async def _execute_api_call(self, openai_request: Dict[str, Any], request_id: str) -> Any:
        """Execute OpenAI API call with retry logic and error handling."""
        
        for attempt in range(self.config.max_retries):
            try:
                self._log_structured_event(
                    "debug",
                    "Making OpenAI API call",
                    request_id=request_id,
                    attempt=attempt + 1,
                    model=self.config.model
                )
                
                response = await self.client.chat.completions.create(**openai_request)
                self.last_api_call = datetime.now()
                return response
                
            except openai.RateLimitError as e:
                if attempt == self.config.max_retries - 1:
                    raise
                
                # Extract retry-after from headers if available
                retry_after = getattr(e, 'retry_after', None) or 60
                backoff_delay = min(retry_after, (2 ** attempt) * self.config.backoff_factor)
                
                self._log_structured_event(
                    "warning",
                    "Rate limit hit, backing off",
                    request_id=request_id,
                    attempt=attempt + 1,
                    backoff_delay=backoff_delay,
                    retry_after=retry_after
                )
                
                await asyncio.sleep(backoff_delay)
                
            except (openai.APIConnectionError, openai.APITimeoutError) as e:
                if attempt == self.config.max_retries - 1:
                    raise
                
                backoff_delay = (2 ** attempt) * self.config.backoff_factor
                self._log_structured_event(
                    "warning",
                    "Connection error, retrying",
                    request_id=request_id,
                    attempt=attempt + 1,
                    backoff_delay=backoff_delay,
                    error_type=type(e).__name__
                )
                
                await asyncio.sleep(backoff_delay)
            
            except openai.BadRequestError as e:
                # Don't retry bad requests
                self._log_structured_event(
                    "error",
                    "Bad request to OpenAI API",
                    request_id=request_id,
                    error_message=str(e)
                )
                raise
    
    def validate_response(self, response: Any) -> bool:
        """Validate OpenAI response structure and content."""
        try:
            # Check basic response structure
            if not hasattr(response, 'choices') or not response.choices:
                return False
            
            choice = response.choices[0]
            if not hasattr(choice, 'message') or not choice.message.content:
                return False
            
            content = choice.message.content.strip()
            
            # If structured output is enabled, validate JSON
            if self.config.structured_output:
                try:
                    json_data = json.loads(content)
                    return self._validate_json_structure(json_data)
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown or other formatting
                    json_content = self._extract_json_from_content(content)
                    if json_content:
                        try:
                            json_data = json.loads(json_content)
                            return self._validate_json_structure(json_data)
                        except json.JSONDecodeError:
                            return False
                    return False
            
            # For non-structured output, check for basic content presence
            return len(content) > 10
            
        except Exception as e:
            self._log_structured_event(
                "error",
                "Error validating OpenAI response",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return False
    
    def parse_response(self, response: Any, request: AIProviderRequest) -> WeightComparisonResponse:
        """Parse OpenAI response into standardized WeightComparisonResponse format."""
        try:
            content = response.choices[0].message.content.strip()
            
            if self.config.structured_output:
                # Parse JSON response
                try:
                    json_data = json.loads(content)
                except json.JSONDecodeError:
                    # Extract JSON from formatted content
                    json_content = self._extract_json_from_content(content)
                    json_data = json.loads(json_content)
                
                return self._parse_structured_response(json_data, request, response)
            else:
                # Parse unstructured text response
                return self._parse_text_response(content, request, response)
                
        except Exception as e:
            self._log_structured_event(
                "error",
                "Error parsing OpenAI response",
                request_id=request.request_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise ValueError(f"Failed to parse OpenAI response: {str(e)}")
    
    def _parse_structured_response(
        self, 
        json_data: Dict[str, Any], 
        request: AIProviderRequest,
        response: Any
    ) -> WeightComparisonResponse:
        """Parse structured JSON response from OpenAI."""
        
        # Extract item weights with validation
        item1_weight = self._extract_weight_value(json_data.get("item1", {}))
        item2_weight = self._extract_weight_value(json_data.get("item2", {}))
        
        # Calculate ratio
        ratio = item1_weight / item2_weight if item2_weight > 0 else 1.0
        
        # Build response objects
        item1 = WeightItem(
            name=request.item1_name,
            original_input=request.item1_weight,
            weight_kg=item1_weight,
            weight_display=json_data.get("item1", {}).get("display_weight", f"{item1_weight} kg"),
            unit_used=json_data.get("item1", {}).get("unit", "kg")
        )
        
        item2 = WeightItem(
            name=request.item2_name,
            original_input=request.item2_weight,
            weight_kg=item2_weight,
            weight_display=json_data.get("item2", {}).get("display_weight", f"{item2_weight} kg"),
            unit_used=json_data.get("item2", {}).get("unit", "kg")
        )
        
        comparison = ComparisonResult(
            ratio=ratio,
            explanation=json_data.get("comparison", {}).get("explanation", "Weight comparison generated"),
            confidence=json_data.get("comparison", {}).get("confidence", 0.8)
        )
        
        return WeightComparisonResponse(
            item1=item1,
            item2=item2,
            comparison=comparison,
            visualization_prompt=json_data.get("visualization_prompt", ""),
            metadata={
                "provider": "openai",
                "model": self.config.model,
                "request_id": request.request_id,
                "finish_reason": response.choices[0].finish_reason,
                "usage": response.usage.model_dump() if response.usage else {},
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

## 3. Prompt Engineering for Weight Comparisons

### 3.1 Optimized System Prompt

```python
async def _get_system_prompt(self) -> str:
    """Get the optimized system prompt for weight comparisons."""
    return """You are a precise weight comparison expert with deep knowledge of object weights and measurements. Your role is to provide accurate, helpful weight comparisons that users can easily understand and visualize.

CORE PRINCIPLES:
1. Accuracy: All weight calculations must be mathematically correct
2. Clarity: Use familiar, easily visualized objects for comparisons
3. Consistency: Always use standard units and formatting
4. Reliability: Provide confidence scores based on data certainty

RESPONSE REQUIREMENTS:
- Always respond with valid JSON in the exact format specified
- Include both metric (kg) and display units as requested
- Provide confidence scores from 0.0 to 1.0
- Give clear, engaging explanations
- Suggest visualization prompts when helpful

WEIGHT KNOWLEDGE:
- Common household items (smartphone ~200g, laptop ~2kg)
- Animals (house cat ~4kg, large dog ~30kg)  
- Food items (apple ~150g, watermelon ~5kg)
- Sports equipment (basketball ~600g, bowling ball ~7kg)
- Vehicles (bicycle ~15kg, small car ~1200kg)

QUALITY STANDARDS:
- Use objects most people can visualize
- Avoid inappropriate or offensive comparisons
- Prefer everyday items over obscure references
- Include variety in comparison categories
- Ensure mathematical relationships are correct"""

async def _get_optimized_prompt(self, request: AIProviderRequest) -> str:
    """Generate optimized prompt based on CONFIG_SYSTEM_SPEC templates."""
    
    # Get base template from CONFIG_SYSTEM_SPEC
    template = await self._get_prompt_template(request.prompt_template_id)
    
    # Apply weight-specific optimizations
    optimized_prompt = f"""
Compare the weights of these two items and provide a detailed analysis:

Item 1: {request.item1_name} ({request.item1_weight})
Item 2: {request.item2_name} ({request.item2_weight})

Please analyze each item's weight and provide your response in this exact JSON format:

{{
    "item1": {{
        "name": "{request.item1_name}",
        "estimated_weight_kg": <weight in kg as float>,
        "display_weight": "<weight with appropriate unit>",
        "unit": "<unit used>",
        "confidence": <confidence 0.0-1.0>,
        "reasoning": "<brief explanation of weight estimate>"
    }},
    "item2": {{
        "name": "{request.item2_name}",
        "estimated_weight_kg": <weight in kg as float>,
        "display_weight": "<weight with appropriate unit>",
        "unit": "<unit used>",
        "confidence": <confidence 0.0-1.0>,
        "reasoning": "<brief explanation of weight estimate>"
    }},
    "comparison": {{
        "ratio": <item1_weight / item2_weight as float>,
        "explanation": "<clear explanation of which is heavier and by how much>",
        "confidence": <overall confidence 0.0-1.0>,
        "real_world_context": "<help users visualize the difference>"
    }},
    "visualization_prompt": "<suggestion for visualizing this comparison>"
}}

IMPORTANT GUIDELINES:
1. Convert all weights to kilograms for calculations
2. Use appropriate display units (grams for light items, kg for heavy items)
3. Provide confidence based on how well-known the object weights are
4. Give practical, relatable explanations
5. Ensure the ratio calculation is mathematically correct
6. Focus on everyday objects people can visualize

{template.get('additional_instructions', '')}
"""
    
    return optimized_prompt.strip()
```

### 3.2 Advanced Prompt Techniques

```python
class PromptOptimizer:
    """Advanced prompt optimization for OpenAI weight comparisons."""
    
    def __init__(self):
        self.weight_categories = {
            "very_light": (0, 0.1),      # < 100g
            "light": (0.1, 1.0),         # 100g - 1kg
            "medium": (1.0, 10.0),       # 1kg - 10kg
            "heavy": (10.0, 100.0),      # 10kg - 100kg
            "very_heavy": (100.0, float('inf'))  # > 100kg
        }
        
        self.prompt_variations = {
            "precision_focused": "Focus on precise measurements and technical accuracy",
            "relatable_focused": "Use everyday comparisons people can easily visualize", 
            "educational_focused": "Provide educational context about weights and measurements",
            "visual_focused": "Emphasize visual and tactile understanding of weight differences"
        }
    
    def optimize_prompt_for_items(self, item1: str, item2: str) -> str:
        """Optimize prompt based on the specific items being compared."""
        
        # Determine weight categories
        item1_category = self._categorize_item(item1)
        item2_category = self._categorize_item(item2)
        
        # Select appropriate prompt variation
        if item1_category != item2_category:
            # Different categories - focus on relatable comparisons
            variation = "relatable_focused"
        elif "technical" in item1.lower() or "technical" in item2.lower():
            # Technical items - focus on precision
            variation = "precision_focused"
        else:
            # Similar categories - focus on visual understanding
            variation = "visual_focused"
        
        return self.prompt_variations[variation]
    
    def _categorize_item(self, item: str) -> str:
        """Categorize item by likely weight range."""
        item_lower = item.lower()
        
        # Light items
        if any(word in item_lower for word in ["coin", "paper", "feather", "card", "pill"]):
            return "very_light"
        elif any(word in item_lower for word in ["phone", "book", "apple", "cup"]):
            return "light"
        
        # Medium items  
        elif any(word in item_lower for word in ["laptop", "cat", "bottle", "shoe"]):
            return "medium"
        
        # Heavy items
        elif any(word in item_lower for word in ["dog", "suitcase", "chair", "microwave"]):
            return "heavy"
        elif any(word in item_lower for word in ["car", "refrigerator", "piano", "motorcycle"]):
            return "very_heavy"
        
        return "medium"  # Default
```

## 4. Rate Limiting and Cost Optimization

### 4.1 Advanced Rate Limiter

```python
import asyncio
import time
from collections import deque
from typing import Optional


class OpenAIRateLimiter:
    """Advanced rate limiter specifically designed for OpenAI's 3500 RPM limit."""
    
    def __init__(self, requests_per_minute: int = 3500, burst_allowance: int = 100):
        self.requests_per_minute = requests_per_minute
        self.burst_allowance = burst_allowance
        
        # Token bucket algorithm implementation
        self.tokens = float(requests_per_minute)
        self.max_tokens = float(requests_per_minute + burst_allowance)
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.last_refill = time.time()
        
        # Request timing tracking
        self.request_times = deque(maxlen=requests_per_minute)
        self.minute_start = time.time()
        
        # Adaptive rate limiting
        self.success_rate = 1.0
        self.rate_limit_hits = 0
        self.adaptive_factor = 1.0
        
        self._lock = asyncio.Lock()
    
    async def acquire_token(self, tokens_needed: int = 1) -> bool:
        """Acquire tokens for API request with adaptive rate limiting."""
        async with self._lock:
            # Refill tokens based on elapsed time
            self._refill_tokens()
            
            # Check if we have enough tokens
            if self.tokens >= tokens_needed:
                self.tokens -= tokens_needed
                self._record_request()
                return True
            
            # Calculate wait time
            wait_time = self._calculate_wait_time(tokens_needed)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                return await self.acquire_token(tokens_needed)
            
            return False
    
    def _refill_tokens(self):
        """Refill token bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on refill rate
        tokens_to_add = elapsed * self.refill_rate * self.adaptive_factor
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
        
        # Clean old request times
        cutoff_time = now - 60.0
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()
    
    def _record_request(self):
        """Record request timestamp for tracking."""
        self.request_times.append(time.time())
    
    def _calculate_wait_time(self, tokens_needed: int) -> float:
        """Calculate how long to wait for tokens to be available."""
        if self.tokens >= tokens_needed:
            return 0.0
        
        tokens_shortage = tokens_needed - self.tokens
        wait_time = tokens_shortage / (self.refill_rate * self.adaptive_factor)
        
        # Add small buffer to account for timing precision
        return wait_time + 0.1
    
    def record_rate_limit_hit(self):
        """Record that we hit a rate limit for adaptive adjustment."""
        self.rate_limit_hits += 1
        
        # Reduce adaptive factor to be more conservative
        self.adaptive_factor = max(0.5, self.adaptive_factor * 0.9)
        
        # Log the adjustment
        logging.warning(
            f"Rate limit hit #{self.rate_limit_hits}, "
            f"adjusting rate to {self.adaptive_factor:.2f} of maximum"
        )
    
    def record_success(self):
        """Record successful request for adaptive rate adjustment."""
        # Gradually increase adaptive factor on success
        if self.adaptive_factor < 1.0:
            self.adaptive_factor = min(1.0, self.adaptive_factor * 1.01)
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get current rate limiting statistics."""
        now = time.time()
        requests_in_last_minute = len([t for t in self.request_times if now - t < 60])
        
        return {
            "requests_per_minute_limit": self.requests_per_minute,
            "requests_in_last_minute": requests_in_last_minute,
            "available_tokens": self.tokens,
            "adaptive_factor": self.adaptive_factor,
            "rate_limit_hits": self.rate_limit_hits,
            "utilization_percentage": (requests_in_last_minute / self.requests_per_minute) * 100
        }


class TokenUsageTracker:
    """Track and optimize token usage for cost control."""
    
    def __init__(self):
        self.usage_history = deque(maxlen=1000)
        self.total_tokens_used = 0
        self.total_cost = 0.0
        
        # OpenAI pricing (as of 2024 - update as needed)
        self.pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},      # per 1K tokens
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
        }
    
    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int):
        """Record token usage and calculate cost."""
        total_tokens = prompt_tokens + completion_tokens
        
        # Calculate cost
        model_pricing = self.pricing.get(model, self.pricing["gpt-4"])
        cost = (
            (prompt_tokens / 1000) * model_pricing["input"] +
            (completion_tokens / 1000) * model_pricing["output"]
        )
        
        # Record usage
        usage_record = {
            "timestamp": time.time(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost
        }
        
        self.usage_history.append(usage_record)
        self.total_tokens_used += total_tokens
        self.total_cost += cost
    
    def get_usage_stats(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get usage statistics for specified time window."""
        cutoff_time = time.time() - (time_window_hours * 3600)
        recent_usage = [u for u in self.usage_history if u["timestamp"] > cutoff_time]
        
        if not recent_usage:
            return {"error": "No usage data in specified time window"}
        
        total_tokens = sum(u["total_tokens"] for u in recent_usage)
        total_cost = sum(u["cost"] for u in recent_usage)
        avg_tokens_per_request = total_tokens / len(recent_usage)
        
        return {
            "time_window_hours": time_window_hours,
            "total_requests": len(recent_usage),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "avg_tokens_per_request": round(avg_tokens_per_request, 1),
            "estimated_monthly_cost": round(total_cost * (720 / time_window_hours), 2)
        }
```

## 5. Response Parsing and Validation

### 5.1 Comprehensive Response Validator

```python
import re
from typing import Dict, Any, List, Optional


class OpenAIResponseValidator:
    """Comprehensive validation for OpenAI responses."""
    
    def __init__(self):
        self.required_fields = {
            "item1": ["name", "estimated_weight_kg", "display_weight", "confidence"],
            "item2": ["name", "estimated_weight_kg", "display_weight", "confidence"],
            "comparison": ["ratio", "explanation", "confidence"]
        }
        
        self.validation_rules = {
            "weight_kg": lambda x: isinstance(x, (int, float)) and 0 < x < 100000,
            "confidence": lambda x: isinstance(x, (int, float)) and 0.0 <= x <= 1.0,
            "ratio": lambda x: isinstance(x, (int, float)) and x > 0,
            "explanation": lambda x: isinstance(x, str) and len(x.strip()) > 10
        }
    
    def validate_json_structure(self, json_data: Dict[str, Any]) -> bool:
        """Validate JSON response structure."""
        try:
            # Check top-level structure
            for section in ["item1", "item2", "comparison"]:
                if section not in json_data:
                    return False
                
                # Check required fields in each section
                for field in self.required_fields[section]:
                    if field not in json_data[section]:
                        return False
            
            # Validate field values
            if not self._validate_field_values(json_data):
                return False
            
            # Validate mathematical relationships
            if not self._validate_mathematical_consistency(json_data):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_field_values(self, json_data: Dict[str, Any]) -> bool:
        """Validate individual field values."""
        
        # Validate item weights
        for item in ["item1", "item2"]:
            weight = json_data[item].get("estimated_weight_kg")
            confidence = json_data[item].get("confidence")
            
            if not self.validation_rules["weight_kg"](weight):
                return False
            if not self.validation_rules["confidence"](confidence):
                return False
        
        # Validate comparison fields
        comparison = json_data["comparison"]
        if not self.validation_rules["ratio"](comparison.get("ratio")):
            return False
        if not self.validation_rules["confidence"](comparison.get("confidence")):
            return False
        if not self.validation_rules["explanation"](comparison.get("explanation")):
            return False
        
        return True
    
    def _validate_mathematical_consistency(self, json_data: Dict[str, Any]) -> bool:
        """Validate mathematical relationships in the response."""
        try:
            item1_weight = json_data["item1"]["estimated_weight_kg"]
            item2_weight = json_data["item2"]["estimated_weight_kg"]
            stated_ratio = json_data["comparison"]["ratio"]
            
            # Calculate expected ratio
            expected_ratio = item1_weight / item2_weight
            
            # Allow for small floating point differences
            ratio_difference = abs(stated_ratio - expected_ratio) / expected_ratio
            
            # Ratio should be within 5% of calculated value
            return ratio_difference < 0.05
            
        except (ZeroDivisionError, KeyError, TypeError):
            return False
    
    def extract_json_from_content(self, content: str) -> Optional[str]:
        """Extract JSON from OpenAI response that may include formatting."""
        
        # Remove common markdown formatting
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*$', '', content)
        
        # Find JSON object boundaries
        json_start = content.find('{')
        json_end = content.rfind('}')
        
        if json_start == -1 or json_end == -1 or json_start >= json_end:
            return None
        
        return content[json_start:json_end + 1]
    
    def get_validation_errors(self, json_data: Dict[str, Any]) -> List[str]:
        """Get detailed validation errors for debugging."""
        errors = []
        
        try:
            # Check structure
            for section in ["item1", "item2", "comparison"]:
                if section not in json_data:
                    errors.append(f"Missing section: {section}")
                    continue
                
                for field in self.required_fields[section]:
                    if field not in json_data[section]:
                        errors.append(f"Missing field: {section}.{field}")
            
            # Check field values
            for item in ["item1", "item2"]:
                if item in json_data:
                    weight = json_data[item].get("estimated_weight_kg")
                    if weight and not self.validation_rules["weight_kg"](weight):
                        errors.append(f"Invalid weight for {item}: {weight}")
                    
                    confidence = json_data[item].get("confidence")
                    if confidence and not self.validation_rules["confidence"](confidence):
                        errors.append(f"Invalid confidence for {item}: {confidence}")
            
            # Check mathematical consistency
            if not self._validate_mathematical_consistency(json_data):
                errors.append("Mathematical inconsistency in weight ratio")
                
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return errors
```

## 6. Error Handling and Circuit Breaker Integration

### 6.1 OpenAI-Specific Error Handling

```python
import openai
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class OpenAIErrorType(Enum):
    """OpenAI-specific error categorization."""
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    INVALID_REQUEST = "invalid_request"
    CONTENT_FILTER = "content_filter"
    MODEL_UNAVAILABLE = "model_unavailable"
    CONTEXT_LENGTH = "context_length"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNKNOWN = "unknown"


class OpenAIErrorHandler:
    """Comprehensive error handling for OpenAI API."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.error_counts = {}
        self.last_errors = {}
        
        # Error classification mapping
        self.error_mapping = {
            openai.RateLimitError: OpenAIErrorType.RATE_LIMIT,
            openai.AuthenticationError: OpenAIErrorType.AUTHENTICATION,
            openai.BadRequestError: OpenAIErrorType.INVALID_REQUEST,
            openai.ConflictError: OpenAIErrorType.INVALID_REQUEST,
            openai.NotFoundError: OpenAIErrorType.MODEL_UNAVAILABLE,
            openai.UnprocessableEntityError: OpenAIErrorType.CONTENT_FILTER,
            openai.APIConnectionError: OpenAIErrorType.CONNECTION,
            openai.APITimeoutError: OpenAIErrorType.TIMEOUT,
            openai.InternalServerError: OpenAIErrorType.UNKNOWN
        }
        
        # Retry configuration by error type
        self.retry_config = {
            OpenAIErrorType.RATE_LIMIT: {"retryable": True, "max_delay": 300},
            OpenAIErrorType.CONNECTION: {"retryable": True, "max_delay": 60},
            OpenAIErrorType.TIMEOUT: {"retryable": True, "max_delay": 30},
            OpenAIErrorType.MODEL_UNAVAILABLE: {"retryable": True, "max_delay": 120},
            OpenAIErrorType.AUTHENTICATION: {"retryable": False, "max_delay": 0},
            OpenAIErrorType.INVALID_REQUEST: {"retryable": False, "max_delay": 0},
            OpenAIErrorType.CONTENT_FILTER: {"retryable": False, "max_delay": 0},
            OpenAIErrorType.QUOTA_EXCEEDED: {"retryable": False, "max_delay": 0}
        }
    
    async def handle_error(self, error: Exception, request_id: str) -> Dict[str, Any]:
        """Handle OpenAI API error with appropriate strategy."""
        
        error_type = self._classify_error(error)
        error_info = self._extract_error_info(error, error_type)
        
        # Record error for monitoring
        self._record_error(error_type, error_info)
        
        # Log structured error event
        self._log_error_event(error, error_type, error_info, request_id)
        
        # Determine retry strategy
        retry_info = self._get_retry_strategy(error_type, error_info)
        
        return {
            "error_type": error_type.value,
            "error_info": error_info,
            "retry_info": retry_info,
            "request_id": request_id
        }
    
    def _classify_error(self, error: Exception) -> OpenAIErrorType:
        """Classify error into specific OpenAI error type."""
        error_class = type(error)
        
        # Direct mapping
        if error_class in self.error_mapping:
            return self.error_mapping[error_class]
        
        # Special cases based on error message
        error_message = str(error).lower()
        
        if "context length" in error_message or "token limit" in error_message:
            return OpenAIErrorType.CONTEXT_LENGTH
        elif "quota" in error_message or "billing" in error_message:
            return OpenAIErrorType.QUOTA_EXCEEDED
        elif "content policy" in error_message or "safety" in error_message:
            return OpenAIErrorType.CONTENT_FILTER
        
        return OpenAIErrorType.UNKNOWN
    
    def _extract_error_info(self, error: Exception, error_type: OpenAIErrorType) -> Dict[str, Any]:
        """Extract detailed error information."""
        error_info = {
            "message": str(error),
            "type": error_type.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Extract OpenAI-specific information
        if hasattr(error, 'response'):
            response = error.response
            error_info.update({
                "status_code": getattr(response, 'status_code', None),
                "headers": dict(getattr(response, 'headers', {}))
            })
            
            # Extract retry-after header for rate limits
            if error_type == OpenAIErrorType.RATE_LIMIT:
                retry_after = response.headers.get('retry-after')
                if retry_after:
                    error_info["retry_after_seconds"] = int(retry_after)
        
        # Extract additional context based on error type
        if error_type == OpenAIErrorType.CONTEXT_LENGTH:
            error_info["suggested_action"] = "Reduce prompt length or max_tokens"
        elif error_type == OpenAIErrorType.QUOTA_EXCEEDED:
            error_info["suggested_action"] = "Check billing and usage limits"
        elif error_type == OpenAIErrorType.MODEL_UNAVAILABLE:
            error_info["suggested_action"] = "Try alternative model or wait for availability"
        
        return error_info
    
    def _get_retry_strategy(self, error_type: OpenAIErrorType, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Determine retry strategy for error type."""
        config = self.retry_config.get(error_type, {"retryable": False, "max_delay": 0})
        
        if not config["retryable"]:
            return {"should_retry": False, "reason": f"{error_type.value} errors are not retryable"}
        
        # Calculate delay based on error type
        if error_type == OpenAIErrorType.RATE_LIMIT:
            # Use retry-after header if available
            delay = error_info.get("retry_after_seconds", 60)
            delay = min(delay, config["max_delay"])
        else:
            # Use exponential backoff
            error_count = self.error_counts.get(error_type, 0)
            delay = min(2 ** error_count, config["max_delay"])
        
        return {
            "should_retry": True,
            "delay_seconds": delay,
            "max_delay": config["max_delay"],
            "error_count": self.error_counts.get(error_type, 0)
        }
    
    def _record_error(self, error_type: OpenAIErrorType, error_info: Dict[str, Any]):
        """Record error for tracking and monitoring."""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.last_errors[error_type] = error_info
    
    def _log_error_event(
        self, 
        error: Exception, 
        error_type: OpenAIErrorType, 
        error_info: Dict[str, Any],
        request_id: str
    ):
        """Log structured error event for monitoring."""
        log_level = "warning" if error_type in [
            OpenAIErrorType.RATE_LIMIT, 
            OpenAIErrorType.CONNECTION,
            OpenAIErrorType.TIMEOUT
        ] else "error"
        
        self.logger.log(
            getattr(logging, log_level.upper()),
            f"OpenAI API error: {error_type.value}",
            extra={
                "provider": "openai",
                "error_type": error_type.value,
                "error_class": type(error).__name__,
                "request_id": request_id,
                "error_count": self.error_counts.get(error_type, 0),
                **error_info
            }
        )
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        return {
            "error_counts": {k.value: v for k, v in self.error_counts.items()},
            "last_errors": {k.value: v for k, v in self.last_errors.items()},
            "total_errors": sum(self.error_counts.values())
        }
```

## 7. Token Usage Optimization and Response Caching

### 7.1 Advanced Caching Strategy

```python
import hashlib
import json
import pickle
from typing import Optional, Any, Dict
from datetime import datetime, timedelta


class ResponseCache:
    """Advanced response caching for OpenAI provider."""
    
    def __init__(self, enabled: bool = True, max_size: int = 1000):
        self.enabled = enabled
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
        self.hit_count = 0
        self.miss_count = 0
    
    async def get(self, cache_key: str) -> Optional[WeightComparisonResponse]:
        """Get cached response if available and valid."""
        if not self.enabled or cache_key not in self.cache:
            self.miss_count += 1
            return None
        
        cache_entry = self.cache[cache_key]
        
        # Check if cache entry is still valid
        if self._is_cache_entry_valid(cache_entry):
            self.hit_count += 1
            self.access_times[cache_key] = datetime.now()
            return cache_entry["response"]
        else:
            # Remove expired entry
            self._remove_cache_entry(cache_key)
            self.miss_count += 1
            return None
    
    async def set(self, cache_key: str, response: WeightComparisonResponse, ttl_seconds: int):
        """Cache response with TTL."""
        if not self.enabled:
            return
        
        # Ensure cache size limit
        if len(self.cache) >= self.max_size:
            self._evict_lru_entry()
        
        cache_entry = {
            "response": response,
            "created_at": datetime.now(),
            "ttl_seconds": ttl_seconds,
            "access_count": 1
        }
        
        self.cache[cache_key] = cache_entry
        self.access_times[cache_key] = datetime.now()
    
    def _is_cache_entry_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid."""
        created_at = cache_entry["created_at"]
        ttl_seconds = cache_entry["ttl_seconds"]
        
        expiry_time = created_at + timedelta(seconds=ttl_seconds)
        return datetime.now() < expiry_time
    
    def _evict_lru_entry(self):
        """Evict least recently used cache entry."""
        if not self.access_times:
            return
        
        # Find least recently accessed entry
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove_cache_entry(lru_key)
    
    def _remove_cache_entry(self, cache_key: str):
        """Remove cache entry and associated metadata."""
        self.cache.pop(cache_key, None)
        self.access_times.pop(cache_key, None)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            "enabled": self.enabled,
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": round(hit_rate, 3),
            "memory_usage_bytes": self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of cache."""
        try:
            return len(pickle.dumps(self.cache))
        except:
            return len(self.cache) * 1024  # Rough estimate


def generate_cache_key(request: AIProviderRequest) -> str:
    """Generate cache key for request."""
    # Create deterministic cache key based on request parameters
    key_data = {
        "item1_name": request.item1_name.lower().strip(),
        "item1_weight": request.item1_weight.lower().strip(),
        "item2_name": request.item2_name.lower().strip(),
        "item2_weight": request.item2_weight.lower().strip(),
        "prompt_template_id": request.prompt_template_id,
        "temperature": round(request.temperature, 2),
        "max_tokens": request.max_tokens
    }
    
    # Create hash from normalized data
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]
```

### 7.2 Token Optimization Strategies

```python
class TokenOptimizer:
    """Optimize token usage for cost efficiency."""
    
    def __init__(self):
        self.optimization_strategies = {
            "compress_prompts": True,
            "use_abbreviations": True,
            "remove_redundancy": True,
            "optimize_json_schema": True
        }
        
        # Common weight units and their abbreviations
        self.unit_abbreviations = {
            "kilogram": "kg", "kilograms": "kg",
            "gram": "g", "grams": "g",
            "pound": "lb", "pounds": "lbs",
            "ounce": "oz", "ounces": "oz",
            "ton": "t", "tons": "t"
        }
    
    def optimize_prompt(self, prompt: str) -> str:
        """Optimize prompt to reduce token usage."""
        if not any(self.optimization_strategies.values()):
            return prompt
        
        optimized = prompt
        
        if self.optimization_strategies["compress_prompts"]:
            optimized = self._compress_prompt(optimized)
        
        if self.optimization_strategies["use_abbreviations"]:
            optimized = self._apply_abbreviations(optimized)
        
        if self.optimization_strategies["remove_redundancy"]:
            optimized = self._remove_redundancy(optimized)
        
        return optimized
    
    def _compress_prompt(self, prompt: str) -> str:
        """Compress prompt by removing unnecessary words."""
        # Remove excessive whitespace
        prompt = re.sub(r'\s+', ' ', prompt)
        
        # Remove common filler words
        filler_words = ["please", "kindly", "very", "really", "quite", "rather"]
        for word in filler_words:
            prompt = re.sub(rf'\b{word}\b\s*', '', prompt, flags=re.IGNORECASE)
        
        # Simplify common phrases
        replacements = {
            "in order to": "to",
            "due to the fact that": "because",
            "for the purpose of": "to",
            "in the event that": "if",
            "at this point in time": "now"
        }
        
        for old, new in replacements.items():
            prompt = re.sub(old, new, prompt, flags=re.IGNORECASE)
        
        return prompt.strip()
    
    def _apply_abbreviations(self, prompt: str) -> str:
        """Apply standard abbreviations to reduce tokens."""
        for full, abbrev in self.unit_abbreviations.items():
            prompt = re.sub(rf'\b{full}\b', abbrev, prompt, flags=re.IGNORECASE)
        
        return prompt
    
    def _remove_redundancy(self, prompt: str) -> str:
        """Remove redundant information from prompt."""
        # Remove repeated instructions
        lines = prompt.split('\n')
        seen_lines = set()
        filtered_lines = []
        
        for line in lines:
            line_normalized = re.sub(r'\s+', ' ', line.strip().lower())
            if line_normalized not in seen_lines:
                filtered_lines.append(line)
                seen_lines.add(line_normalized)
        
        return '\n'.join(filtered_lines)
    
    def estimate_token_count(self, text: str) -> int:
        """Estimate token count for text (approximation)."""
        # Rough estimation: 1 token ≈ 4 characters for English
        return len(text) // 4
    
    def get_optimization_savings(self, original: str, optimized: str) -> Dict[str, Any]:
        """Calculate token and cost savings from optimization."""
        original_tokens = self.estimate_token_count(original)
        optimized_tokens = self.estimate_token_count(optimized)
        
        token_savings = original_tokens - optimized_tokens
        percentage_savings = (token_savings / original_tokens * 100) if original_tokens > 0 else 0
        
        # Estimate cost savings (using GPT-4 pricing)
        cost_per_token = 0.00003  # $0.03 per 1K tokens
        cost_savings = token_savings * cost_per_token
        
        return {
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "token_savings": token_savings,
            "percentage_savings": round(percentage_savings, 2),
            "estimated_cost_savings": round(cost_savings, 6)
        }
```

## 8. Health Checks and Monitoring Integration

### 8.1 Health Check Implementation

```python
from datetime import datetime, timedelta
from typing import Dict, Any, List


class OpenAIHealthChecker:
    """Comprehensive health checking for OpenAI provider."""
    
    def __init__(self, provider: OpenAIProvider):
        self.provider = provider
        self.health_history = []
        self.last_health_check = None
        
        # Health thresholds
        self.thresholds = {
            "max_response_time_ms": 10000,
            "min_success_rate": 0.95,
            "max_error_rate": 0.05,
            "max_consecutive_failures": 3
        }
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_start = time.time()
        
        health_result = {
            "provider": "openai",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "checks": {},
            "metrics": {},
            "errors": []
        }
        
        try:
            # 1. API connectivity check
            connectivity_result = await self._check_api_connectivity()
            health_result["checks"]["connectivity"] = connectivity_result
            
            # 2. Model availability check
            model_result = await self._check_model_availability()
            health_result["checks"]["model_availability"] = model_result
            
            # 3. Rate limiting status check
            rate_limit_result = self._check_rate_limit_status()
            health_result["checks"]["rate_limiting"] = rate_limit_result
            
            # 4. Performance metrics check
            performance_result = self._check_performance_metrics()
            health_result["checks"]["performance"] = performance_result
            
            # 5. Error rate check
            error_rate_result = self._check_error_rates()
            health_result["checks"]["error_rates"] = error_rate_result
            
            # Determine overall health status
            health_result["status"] = self._determine_overall_health(health_result["checks"])
            
            # Add performance metrics
            health_result["metrics"] = self._get_health_metrics()
            
        except Exception as e:
            health_result["status"] = "unhealthy"
            health_result["errors"].append({
                "type": "health_check_failure",
                "message": str(e)
            })
        
        # Record health check duration
        health_duration = (time.time() - health_start) * 1000
        health_result["health_check_duration_ms"] = health_duration
        
        # Store in history
        self.health_history.append(health_result)
        self.last_health_check = datetime.now()
        
        # Keep only last 100 health checks
        self.health_history = self.health_history[-100:]
        
        return health_result
    
    async def _check_api_connectivity(self) -> Dict[str, Any]:
        """Check basic API connectivity."""
        try:
            # Simple API call to check connectivity
            start_time = time.time()
            
            test_request = {
                "model": self.provider.config.model,
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 5,
                "temperature": 0
            }
            
            response = await self.provider.client.chat.completions.create(**test_request)
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "details": "API connectivity confirmed"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def _check_model_availability(self) -> Dict[str, Any]:
        """Check if the configured model is available."""
        try:
            # Try to list available models or make a minimal request
            models_response = await self.provider.client.models.list()
            available_models = [model.id for model in models_response.data]
            
            model_available = self.provider.config.model in available_models
            
            return {
                "status": "healthy" if model_available else "degraded",
                "model": self.provider.config.model,
                "available": model_available,
                "total_models_available": len(available_models)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.provider.config.model
            }
    
    def _check_rate_limit_status(self) -> Dict[str, Any]:
        """Check current rate limiting status."""
        rate_stats = self.provider.rate_limiter.get_rate_limit_stats()
        
        utilization = rate_stats["utilization_percentage"]
        status = "healthy"
        
        if utilization > 90:
            status = "degraded"
        elif utilization > 95:
            status = "unhealthy"
        
        return {
            "status": status,
            "utilization_percentage": utilization,
            "available_tokens": rate_stats["available_tokens"],
            "requests_in_last_minute": rate_stats["requests_in_last_minute"],
            "rate_limit_hits": rate_stats["rate_limit_hits"]
        }
    
    def _check_performance_metrics(self) -> Dict[str, Any]:
        """Check performance metrics against thresholds."""
        metrics = self.provider.metrics
        
        avg_response_time = metrics["avg_response_time_ms"]
        status = "healthy"
        
        if avg_response_time > self.thresholds["max_response_time_ms"]:
            status = "degraded"
        elif avg_response_time > self.thresholds["max_response_time_ms"] * 1.5:
            status = "unhealthy"
        
        return {
            "status": status,
            "avg_response_time_ms": avg_response_time,
            "threshold_ms": self.thresholds["max_response_time_ms"],
            "total_requests": metrics["total_requests"]
        }
    
    def _check_error_rates(self) -> Dict[str, Any]:
        """Check error rates against thresholds."""
        metrics = self.provider.metrics
        
        total_requests = metrics["total_requests"]
        failed_requests = metrics["failed_requests"]
        
        error_rate = failed_requests / total_requests if total_requests > 0 else 0
        status = "healthy"
        
        if error_rate > self.thresholds["max_error_rate"]:
            status = "degraded"
        elif error_rate > self.thresholds["max_error_rate"] * 2:
            status = "unhealthy"
        
        return {
            "status": status,
            "error_rate": round(error_rate, 4),
            "failed_requests": failed_requests,
            "total_requests": total_requests,
            "threshold": self.thresholds["max_error_rate"]
        }
    
    def _determine_overall_health(self, checks: Dict[str, Any]) -> str:
        """Determine overall health status from individual checks."""
        statuses = [check["status"] for check in checks.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        else:
            return "healthy"
    
    def _get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics."""
        return {
            "provider_metrics": self.provider.metrics,
            "rate_limit_stats": self.provider.rate_limiter.get_rate_limit_stats(),
            "token_usage_stats": self.provider.token_tracker.get_usage_stats(24),
            "cache_stats": self.provider.response_cache.get_cache_stats(),
            "last_api_call": self.provider.last_api_call.isoformat() if self.provider.last_api_call else None
        }
    
    def get_health_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get health summary for specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_checks = [
            check for check in self.health_history 
            if datetime.fromisoformat(check["timestamp"]) > cutoff_time
        ]
        
        if not recent_checks:
            return {"error": "No health data available"}
        
        # Calculate health statistics
        healthy_count = sum(1 for check in recent_checks if check["status"] == "healthy")
        degraded_count = sum(1 for check in recent_checks if check["status"] == "degraded")
        unhealthy_count = sum(1 for check in recent_checks if check["status"] == "unhealthy")
        
        total_checks = len(recent_checks)
        uptime_percentage = (healthy_count / total_checks * 100) if total_checks > 0 else 0
        
        return {
            "time_period_hours": hours,
            "total_health_checks": total_checks,
            "healthy_checks": healthy_count,
            "degraded_checks": degraded_count,
            "unhealthy_checks": unhealthy_count,
            "uptime_percentage": round(uptime_percentage, 2),
            "last_check_time": recent_checks[-1]["timestamp"] if recent_checks else None,
            "current_status": recent_checks[-1]["status"] if recent_checks else "unknown"
        }
```

This comprehensive OpenAI Provider Specification provides:

1. **Complete GPT-4 integration** with structured output and advanced error handling
2. **Sophisticated rate limiting** designed specifically for OpenAI's 3500 RPM limits
3. **Optimized prompt engineering** with token usage optimization strategies
4. **Comprehensive response validation** with mathematical consistency checks
5. **Advanced caching system** for cost optimization and performance
6. **Detailed error handling** with OpenAI-specific error classification
7. **Production-ready monitoring** integration with health checks and metrics
8. **Security best practices** for API key management and data handling

The specification ensures seamless integration with all SizeComparator system components while providing robust, scalable, and cost-effective OpenAI API integration for weight comparison generation.