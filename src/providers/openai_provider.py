"""
OpenAI Provider implementation for SizeComparator.

This module implements the OpenAI GPT-4 integration with structured output,
advanced rate limiting, error handling, and response caching as specified
in OPENAI_PROVIDER_SPEC.md.
"""

import openai
import json
import asyncio
import time
import re
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import deque
from decimal import Decimal
import logging
import uuid

from .base import AIProviderBase
from ..core.exceptions import AIProviderException, ValidationException
from ..models.providers import (
    AIProviderRequest,
    ProviderHealth,
    ProviderStatus,
    CircuitBreakerState,
    AIProviderMetadata,
    AIProviderResponse
)
from ..models.requests import WeightComparisonRequest
from ..models.responses import (
    WeightComparisonResponse,
    ProcessedWeight,
    ComparisonAnalysis,
    AIVisualizationPrompt,
    ResponseMetadata
)
from ..models.weight import WeightUnit
from ..core.environment import APIProviderConfigInterface


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
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4o": {"input": 0.005, "output": 0.015}
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
            import pickle
            return len(pickle.dumps(self.cache))
        except:
            return len(self.cache) * 1024  # Rough estimate


class OpenAIProvider(AIProviderBase):
    """Production OpenAI provider with advanced features."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None,
                 env_config: Optional[APIProviderConfigInterface] = None):
        super().__init__(config, logger)
        
        self.env_config = env_config
        self.name = "OpenAI"
        
        # Configuration with defaults
        self.api_key = config.get("api_key") or (env_config.get_api_key() if env_config else None)
        self.endpoint = config.get("endpoint", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4")
        self.timeout_seconds = config.get("timeout_seconds", 30.0)
        self.max_tokens = config.get("max_tokens", 500)
        self.temperature = config.get("temperature", 0.3)
        self.rate_limit_rpm = config.get("rate_limit_rpm", 3500)
        self.max_retries = config.get("max_retries", 3)
        self.backoff_factor = config.get("backoff_factor", 2.0)
        self.structured_output = config.get("structured_output", True)
        self.enable_caching = config.get("enable_caching", True)
        self.cache_ttl_seconds = config.get("cache_ttl_seconds", 3600)
        
        # Initialize OpenAI client
        self.client = None
        
        # Rate limiting and performance tracking
        self.rate_limiter = OpenAIRateLimiter(self.rate_limit_rpm)
        self.token_tracker = TokenUsageTracker()
        self.response_cache = ResponseCache(enabled=self.enable_caching)
        
        # Error tracking
        self.error_tracker = {}
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
            model=self.model,
            rate_limit=self.rate_limit_rpm,
            structured_output=self.structured_output
        )
    
    async def initialize(self) -> None:
        """Initialize OpenAI client and validate configuration."""
        if not self.api_key:
            raise AIProviderException("OpenAI API key not configured", self.name)
        
        # Initialize OpenAI client with proper configuration
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.endpoint,
            timeout=self.timeout_seconds,
            max_retries=0  # We handle retries ourselves for better control
        )
        
        # Perform initial health check
        try:
            await self.health_check()
            self._log_structured_event("info", "OpenAI provider initialized successfully")
        except Exception as e:
            self._log_structured_event("error", f"OpenAI provider initialization failed: {e}")
            raise
    
    async def generate_comparison(self, request: AIProviderRequest) -> WeightComparisonResponse:
        """Generate weight comparison using OpenAI GPT-4 with structured output."""
        request_start = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # Check rate limiting before making request
            await self.rate_limiter.acquire_token()
            
            # Check cache first if enabled
            cache_key = self._generate_cache_key(request)
            if self.enable_caching:
                cached_response = await self.response_cache.get(cache_key)
                if cached_response:
                    self._log_structured_event(
                        "debug",
                        "Cache hit for OpenAI request",
                        request_id=str(request.request_id),
                        cache_key=cache_key
                    )
                    return cached_response
            
            # Build the OpenAI request
            openai_request = await self._build_openai_request(request)
            
            # Execute API call with timeout and retry handling
            response = await self._execute_api_call(openai_request, str(request.request_id))
            
            # Validate and parse response
            if not self.validate_response(response):
                raise ValueError("Invalid response format from OpenAI API")
            
            parsed_response = self.parse_response(response, request)
            
            # Update metrics and cache
            response_time = (time.time() - request_start) * 1000
            self._update_metrics(response, response_time, success=True)
            
            # Cache successful response
            if self.enable_caching:
                await self.response_cache.set(cache_key, parsed_response, self.cache_ttl_seconds)
            
            self._log_structured_event(
                "info",
                "OpenAI comparison generated successfully",
                request_id=str(request.request_id),
                response_time_ms=response_time,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                model=self.model
            )
            
            return parsed_response
            
        except openai.RateLimitError as e:
            self.metrics["failed_requests"] += 1
            await self._handle_rate_limit_error(e, str(request.request_id))
            raise
        except openai.APIError as e:
            self.metrics["failed_requests"] += 1
            await self._handle_api_error(e, str(request.request_id))
            raise
        except Exception as e:
            self.metrics["failed_requests"] += 1
            self._log_structured_event(
                "error",
                "Unexpected error in OpenAI provider",
                request_id=str(request.request_id),
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
    
    async def _build_openai_request(self, request: AIProviderRequest) -> Dict[str, Any]:
        """Build OpenAI API request with structured output configuration."""
        
        # Get the optimized prompt
        prompt = await self._get_optimized_prompt(request)
        
        # Base request configuration
        openai_request = {
            "model": self.model,
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
            "max_tokens": min(request.max_tokens, self.max_tokens),
            "temperature": min(request.temperature, self.temperature),
            "timeout": request.timeout_seconds
        }
        
        # Add structured output configuration for GPT-4
        if self.structured_output and self._supports_structured_output():
            openai_request["response_format"] = {
                "type": "json_object"
            }
            # Ensure the prompt explicitly requests JSON
            openai_request["messages"][0]["content"] += "\n\nYou must respond with valid JSON only."
        
        return openai_request
    
    async def _execute_api_call(self, openai_request: Dict[str, Any], request_id: str) -> Any:
        """Execute OpenAI API call with retry logic and error handling."""
        
        for attempt in range(self.max_retries):
            try:
                self._log_structured_event(
                    "debug",
                    "Making OpenAI API call",
                    request_id=request_id,
                    attempt=attempt + 1,
                    model=self.model
                )
                
                response = await self.client.chat.completions.create(**openai_request)
                self.last_api_call = datetime.now()
                self.rate_limiter.record_success()
                return response
                
            except openai.RateLimitError as e:
                if attempt == self.max_retries - 1:
                    raise
                
                # Extract retry-after from headers if available
                retry_after = getattr(e, 'retry_after', None) or 60
                backoff_delay = min(retry_after, (2 ** attempt) * self.backoff_factor)
                
                self._log_structured_event(
                    "warning",
                    "Rate limit hit, backing off",
                    request_id=request_id,
                    attempt=attempt + 1,
                    backoff_delay=backoff_delay,
                    retry_after=retry_after
                )
                
                self.rate_limiter.record_rate_limit_hit()
                await asyncio.sleep(backoff_delay)
                
            except (openai.APIConnectionError, openai.APITimeoutError) as e:
                if attempt == self.max_retries - 1:
                    raise
                
                backoff_delay = (2 ** attempt) * self.backoff_factor
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
            if self.structured_output:
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
            
            if self.structured_output:
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
                request_id=str(request.request_id),
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
        
        # Extract template variables for item information
        template_vars = request.template_variables
        
        # Extract item weights with validation
        item1_weight = self._extract_weight_value(json_data.get("item1", {}))
        item2_weight = self._extract_weight_value(json_data.get("item2", {}))
        
        # Calculate ratio
        ratio = item1_weight / item2_weight if item2_weight > 0 else 1.0
        
        # Build response objects
        item1 = ProcessedWeight(
            original_input={"value": template_vars.get("item1_weight", "")},
            parsed_value=Decimal(str(item1_weight)),
            display_value=json_data.get("item1", {}).get("display_weight", f"{item1_weight} kg"),
            unit_used=WeightUnit(json_data.get("item1", {}).get("unit", "kg")),
            parsing_confidence=json_data.get("item1", {}).get("confidence", 0.8)
        )
        
        item2 = ProcessedWeight(
            original_input={"value": template_vars.get("item2_weight", "")},
            parsed_value=Decimal(str(item2_weight)),
            display_value=json_data.get("item2", {}).get("display_weight", f"{item2_weight} kg"),
            unit_used=WeightUnit(json_data.get("item2", {}).get("unit", "kg")),
            parsing_confidence=json_data.get("item2", {}).get("confidence", 0.8)
        )
        
        # Build analysis
        analysis = ComparisonAnalysis(
            weight_ratio=Decimal(str(ratio)),
            percentage_difference=Decimal(str(abs(ratio - 1) * 100)),
            absolute_difference=ProcessedWeight(
                original_input={"value": abs(item1_weight - item2_weight)},
                parsed_value=Decimal(str(abs(item1_weight - item2_weight))),
                display_value=f"{abs(item1_weight - item2_weight):.2f} kg",
                unit_used=WeightUnit.KG,
                parsing_confidence=1.0
            ),
            heavier_item="item1" if item1_weight > item2_weight else ("item2" if item2_weight > item1_weight else "equal"),
            significance_level=self._determine_significance(ratio),
            comparison_category=json_data.get("comparison", {}).get("category", "object_vs_object")
        )
        
        # Build visualization if available
        visualization = None
        if json_data.get("visualization_prompt"):
            visualization = AIVisualizationPrompt(
                prompt_text=json_data["visualization_prompt"],
                provider_used="openai",
                generation_time_ms=int((time.time() - self.last_api_call.timestamp()) * 1000) if self.last_api_call else 0,
                confidence_score=json_data.get("comparison", {}).get("confidence", 0.8),
                prompt_metadata={"model": self.model}
            )
        
        # Build metadata
        metadata = ResponseMetadata(
            request_id=request.request_id,
            processing_time_ms=int((time.time() - self.last_api_call.timestamp()) * 1000) if self.last_api_call else 0,
            component_timings={"openai_api": response.usage.total_tokens if response.usage else 0},
            ai_provider_used="openai",
            ai_response_time_ms=int((time.time() - self.last_api_call.timestamp()) * 1000) if self.last_api_call else 0,
            cache_hit=False,
            warnings=[],
            api_version="1.0.0",
            timestamp=datetime.utcnow()
        )
        
        return WeightComparisonResponse(
            item1=item1,
            item2=item2,
            analysis=analysis,
            visualization=visualization,
            metadata=metadata
        )
    
    async def health_check(self) -> ProviderHealth:
        """Perform active health check on the provider."""
        health_start = time.time()
        
        try:
            # Simple API call to check connectivity
            test_request = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 5,
                "temperature": 0
            }
            
            response = await self.client.chat.completions.create(**test_request)
            response_time = (time.time() - health_start) * 1000
            
            # Update health status
            self._update_health_status(ProviderStatus.HEALTHY)
            self._health.avg_response_time_ms = response_time
            
            return self._health
            
        except Exception as e:
            self._update_health_status(ProviderStatus.UNHEALTHY, str(e))
            return self._health
    
    async def shutdown(self) -> None:
        """Gracefully shutdown provider and cleanup resources."""
        self._accepting_requests = False
        
        # Log final statistics
        self._log_structured_event(
            "info",
            "OpenAI provider shutting down",
            total_requests=self.metrics["total_requests"],
            cache_stats=self.response_cache.get_cache_stats(),
            token_usage=self.token_tracker.get_usage_stats(24),
            rate_limit_stats=self.rate_limiter.get_rate_limit_stats()
        )
        
        # Clear caches
        self.response_cache.cache.clear()
    
    async def _apply_config_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """Apply provider-specific configuration changes."""
        # Update rate limiter if RPM changed
        if old_config.get("rate_limit_rpm") != new_config.get("rate_limit_rpm"):
            self.rate_limiter = OpenAIRateLimiter(new_config.get("rate_limit_rpm", 3500))
        
        # Update model
        self.model = new_config.get("model", self.model)
        
        # Update caching
        self.enable_caching = new_config.get("enable_caching", self.enable_caching)
        self.cache_ttl_seconds = new_config.get("cache_ttl_seconds", self.cache_ttl_seconds)
    
    def _supports_structured_output(self) -> bool:
        """Check if current model supports structured output."""
        return self.model in ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo"]
    
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
        """Generate optimized prompt based on request."""
        
        template_vars = request.template_variables
        
        optimized_prompt = f"""
Compare the weights of these two items and provide a detailed analysis:

Item 1: {template_vars.get('item1_name', '')} ({template_vars.get('item1_weight', '')})
Item 2: {template_vars.get('item2_name', '')} ({template_vars.get('item2_weight', '')})

Please analyze each item's weight and provide your response in this exact JSON format:

{{
    "item1": {{
        "name": "{template_vars.get('item1_name', '')}",
        "estimated_weight_kg": <weight in kg as float>,
        "display_weight": "<weight with appropriate unit>",
        "unit": "<unit used>",
        "confidence": <confidence 0.0-1.0>,
        "reasoning": "<brief explanation of weight estimate>"
    }},
    "item2": {{
        "name": "{template_vars.get('item2_name', '')}",
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
        "real_world_context": "<help users visualize the difference>",
        "category": "<comparison category like animal_vs_vehicle>"
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
"""
        
        return optimized_prompt.strip()
    
    def _extract_weight_value(self, item_data: Dict[str, Any]) -> float:
        """Extract weight value in kg from item data."""
        weight_kg = item_data.get("estimated_weight_kg", 0)
        
        # Ensure it's a valid number
        try:
            return float(weight_kg)
        except (TypeError, ValueError):
            return 0.0
    
    def _determine_significance(self, ratio: float) -> str:
        """Determine significance level based on weight ratio."""
        if abs(ratio - 1) < 0.01:
            return "negligible"
        elif ratio < 2:
            return "small"
        elif ratio < 10:
            return "moderate"
        elif ratio < 100:
            return "large"
        else:
            return "extreme"
    
    def _generate_cache_key(self, request: AIProviderRequest) -> str:
        """Generate cache key for request."""
        # Create deterministic cache key based on request parameters
        key_data = {
            "template_id": request.prompt_template_id,
            "variables": request.template_variables,
            "temperature": round(request.temperature, 2),
            "max_tokens": request.max_tokens
        }
        
        # Create hash from normalized data
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def _extract_json_from_content(self, content: str) -> Optional[str]:
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
    
    def _validate_json_structure(self, json_data: Dict[str, Any]) -> bool:
        """Validate JSON response structure."""
        required_sections = ["item1", "item2", "comparison"]
        
        # Check top-level structure
        for section in required_sections:
            if section not in json_data:
                return False
        
        # Check item fields
        item_fields = ["estimated_weight_kg", "display_weight", "confidence"]
        for item in ["item1", "item2"]:
            for field in item_fields:
                if field not in json_data.get(item, {}):
                    return False
        
        # Check comparison fields
        comparison_fields = ["ratio", "explanation", "confidence"]
        for field in comparison_fields:
            if field not in json_data.get("comparison", {}):
                return False
        
        return True
    
    def _update_metrics(self, response: Any, response_time_ms: float, success: bool):
        """Update provider metrics."""
        if success:
            self.metrics["successful_requests"] += 1
        
        # Update average response time
        total_requests = self.metrics["successful_requests"]
        if total_requests > 0:
            current_avg = self.metrics["avg_response_time_ms"]
            self.metrics["avg_response_time_ms"] = (
                (current_avg * (total_requests - 1) + response_time_ms) / total_requests
            )
        
        # Update token usage
        if hasattr(response, 'usage') and response.usage:
            self.metrics["total_tokens_used"] += response.usage.total_tokens
            self.token_tracker.record_usage(
                self.model,
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )
        
        # Update cache hit rate
        cache_stats = self.response_cache.get_cache_stats()
        self.metrics["cache_hit_rate"] = cache_stats["hit_rate"]
    
    async def _handle_rate_limit_error(self, error: openai.RateLimitError, request_id: str):
        """Handle rate limit error."""
        self._log_structured_event(
            "warning",
            "OpenAI rate limit error",
            request_id=request_id,
            error_message=str(error),
            retry_after=getattr(error, 'retry_after', None)
        )
        
        # Update health status
        self._update_health_status(ProviderStatus.DEGRADED, "Rate limit reached")
        
        raise AIProviderException(
            "OpenAI rate limit reached",
            self.name,
            retry_after=getattr(error, 'retry_after', None)
        )
    
    async def _handle_api_error(self, error: openai.APIError, request_id: str):
        """Handle general API error."""
        self._log_structured_event(
            "error",
            "OpenAI API error",
            request_id=request_id,
            error_type=type(error).__name__,
            error_message=str(error)
        )
        
        # Update health status
        self._update_health_status(ProviderStatus.UNHEALTHY, str(error))
        
        raise AIProviderException(f"OpenAI API error: {str(error)}", self.name)
    
    def _parse_text_response(self, content: str, request: AIProviderRequest, response: Any) -> WeightComparisonResponse:
        """Parse unstructured text response (fallback)."""
        # This is a simplified fallback parser
        # In production, you would implement more sophisticated parsing
        
        template_vars = request.template_variables
        
        # Create basic response
        item1 = ProcessedWeight(
            original_input={"value": template_vars.get("item1_weight", "")},
            parsed_value=Decimal("1.0"),
            display_value="1 kg",
            unit_used=WeightUnit.KG,
            parsing_confidence=0.5
        )
        
        item2 = ProcessedWeight(
            original_input={"value": template_vars.get("item2_weight", "")},
            parsed_value=Decimal("1.0"),
            display_value="1 kg",
            unit_used=WeightUnit.KG,
            parsing_confidence=0.5
        )
        
        analysis = ComparisonAnalysis(
            weight_ratio=Decimal("1.0"),
            percentage_difference=Decimal("0.0"),
            absolute_difference=ProcessedWeight(
                original_input={"value": 0},
                parsed_value=Decimal("0.0"),
                display_value="0 kg",
                unit_used=WeightUnit.KG,
                parsing_confidence=1.0
            ),
            heavier_item="equal",
            significance_level="negligible",
            comparison_category="unknown"
        )
        
        visualization = AIVisualizationPrompt(
            prompt_text=content[:200],  # Use first 200 chars as prompt
            provider_used="openai",
            generation_time_ms=0,
            confidence_score=0.5,
            prompt_metadata={"model": self.model, "fallback": True}
        )
        
        metadata = ResponseMetadata(
            request_id=request.request_id,
            processing_time_ms=0,
            component_timings={},
            ai_provider_used="openai",
            warnings=["Fallback parser used - structured output unavailable"],
            api_version="1.0.0",
            timestamp=datetime.utcnow()
        )
        
        return WeightComparisonResponse(
            item1=item1,
            item2=item2,
            analysis=analysis,
            visualization=visualization,
            metadata=metadata
        )