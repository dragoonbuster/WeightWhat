"""
X.ai (Grok) provider implementation for SizeComparator.

This module implements the X.ai Grok integration following XAI_PROVIDER_SPEC.md,
providing weight comparison generation with robust error handling, quality validation,
and rate limiting specifically tuned for X.ai's API characteristics.
"""

import asyncio
import json
import re
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import random
import httpx
from enum import Enum

from ..models.responses import WeightComparisonResponse, ComparisonAnalysis, AIVisualizationPrompt, ResponseMetadata
from ..models.weight import ProcessedWeight, WeightUnit
from ..models.providers import AIProviderRequest, AIProviderHealth, ProviderStatus, CircuitBreakerState
from ..models.errors import ErrorCategory, ErrorSeverity
from ..core.monitoring import get_logger, get_metrics
from ..core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState as CBState
from ..core.exceptions import SizeComparatorException, ValidationException


class RetryErrorCategory(Enum):
    """Error categories for retry decisions."""
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION = "authentication"


class APIError(SizeComparatorException):
    """API communication error."""
    category = ErrorCategory.INTEGRATION_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "API_ERROR"


class RateLimitError(SizeComparatorException):
    """Rate limit exceeded error."""
    category = ErrorCategory.INTEGRATION_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "RATE_LIMIT_ERROR"
    
    def __init__(self, message: str, request_id: str, retry_after: float = None):
        super().__init__(message, {"retry_after": retry_after}, request_id)
        self.retry_after = retry_after


class QualityValidationError(SizeComparatorException):
    """Response quality validation error."""
    category = ErrorCategory.BUSINESS_LOGIC_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "QUALITY_VALIDATION_ERROR"


class TokenBucketRateLimiter:
    """Token bucket rate limiter optimized for X.ai's 500 RPM limit."""
    
    def __init__(self, capacity: int, refill_rate: float, burst_capacity: int = None):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.burst_capacity = burst_capacity or capacity
        self.tokens = float(capacity)
        self.last_refill = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()
        
        # X.ai specific tracking
        self.requests_this_minute = 0
        self.minute_window_start = datetime.utcnow()
        
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens with X.ai specific rate limiting."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(
                self.burst_capacity,
                self.tokens + (elapsed * self.refill_rate)
            )
            self.last_refill = now
            
            # Check minute-based rate limit (X.ai enforces per-minute limits)
            current_time = datetime.utcnow()
            if (current_time - self.minute_window_start).total_seconds() >= 60:
                # Reset minute window
                self.minute_window_start = current_time
                self.requests_this_minute = 0
            
            # Check both token bucket and per-minute limit
            if self.tokens >= tokens and self.requests_this_minute < 500:
                self.tokens -= tokens
                self.requests_this_minute += 1
                return True
            
            return False
    
    async def wait_and_acquire(self, tokens: int = 1) -> None:
        """Wait until tokens are available."""
        while True:
            if await self.acquire(tokens):
                return
            
            # Calculate optimal wait time
            needed_tokens = tokens - self.tokens
            token_wait = needed_tokens / self.refill_rate if needed_tokens > 0 else 0
            
            # Check minute-based limit
            current_time = datetime.utcnow()
            minute_remaining = 60 - (current_time - self.minute_window_start).total_seconds()
            minute_wait = minute_remaining if self.requests_this_minute >= 500 else 0
            
            wait_time = max(token_wait, minute_wait, 0.1)  # Minimum 100ms wait
            await asyncio.sleep(wait_time)


class GrokResponseValidator:
    """Comprehensive validation for Grok responses with quality scoring."""
    
    def __init__(self, config: Dict[str, Any]):
        self.min_confidence = config.get("min_confidence_threshold", 0.6)
        self.max_response_time = config.get("max_response_time_ms", 30000)
        
    async def validate_response_quality(
        self, 
        response: Dict[str, Any], 
        request: AIProviderRequest
    ) -> float:
        """Comprehensive quality validation returning score 0.0-1.0."""
        
        quality_checks = {
            "structure_validity": self._validate_structure(response),
            "data_consistency": self._validate_data_consistency(response),
            "mathematical_accuracy": self._validate_math(response),
            "confidence_realism": self._validate_confidence_scores(response),
            "response_completeness": self._validate_completeness(response),
            "weight_reasonableness": self._validate_weight_reasonableness(response, request)
        }
        
        # Calculate weighted quality score
        weights = {
            "structure_validity": 0.25,
            "data_consistency": 0.20,
            "mathematical_accuracy": 0.25,
            "confidence_realism": 0.10,
            "response_completeness": 0.10,
            "weight_reasonableness": 0.10
        }
        
        quality_score = sum(
            quality_checks[check] * weights[check] 
            for check in quality_checks
        )
        
        return quality_score
    
    def _validate_structure(self, response: Dict[str, Any]) -> float:
        """Validate response structure matches expected format."""
        required_fields = {
            "item1": ["name", "weight_kg", "weight_display", "confidence"],
            "item2": ["name", "weight_kg", "weight_display", "confidence"], 
            "comparison": ["ratio", "heavier_item", "explanation"],
            "visualization": ["prompt", "confidence"]
        }
        
        missing_fields = []
        for section, fields in required_fields.items():
            if section not in response:
                missing_fields.append(section)
                continue
                
            for field in fields:
                if field not in response[section]:
                    missing_fields.append(f"{section}.{field}")
        
        if missing_fields:
            return max(0.0, 1.0 - (len(missing_fields) * 0.1))
        
        return 1.0
    
    def _validate_data_consistency(self, response: Dict[str, Any]) -> float:
        """Validate internal data consistency."""
        try:
            item1_weight = float(response["item1"]["weight_kg"])
            item2_weight = float(response["item2"]["weight_kg"])
            calculated_ratio = item1_weight / item2_weight if item2_weight > 0 else 0
            stated_ratio = float(response["comparison"]["ratio"])
            
            # Check ratio accuracy (within 5% tolerance)
            ratio_accuracy = 1.0 - min(1.0, abs(calculated_ratio - stated_ratio) / max(calculated_ratio, 0.001))
            
            # Check heavier item consistency
            heavier_item_name = response["comparison"]["heavier_item"]
            actual_heavier = response["item1"]["name"] if item1_weight > item2_weight else response["item2"]["name"]
            heavier_accuracy = 1.0 if heavier_item_name == actual_heavier else 0.0
            
            return (ratio_accuracy * 0.7) + (heavier_accuracy * 0.3)
            
        except (KeyError, ValueError, TypeError, ZeroDivisionError):
            return 0.0
    
    def _validate_math(self, response: Dict[str, Any]) -> float:
        """Validate mathematical calculations."""
        try:
            # Validate weight values are positive and reasonable
            weights = [
                float(response["item1"]["weight_kg"]),
                float(response["item2"]["weight_kg"])
            ]
            
            if any(w <= 0 for w in weights):
                return 0.0
            
            if any(w > 1000000 for w in weights):  # 1M kg limit
                return 0.3  # Unreasonably large but not impossible
            
            # Validate ratio calculation
            ratio = float(response["comparison"]["ratio"])
            expected_ratio = weights[0] / weights[1]
            
            ratio_error = abs(ratio - expected_ratio) / max(expected_ratio, 0.001)
            ratio_score = max(0.0, 1.0 - ratio_error)
            
            return ratio_score
            
        except (KeyError, ValueError, TypeError, ZeroDivisionError):
            return 0.0
    
    def _validate_confidence_scores(self, response: Dict[str, Any]) -> float:
        """Validate confidence scores are realistic."""
        try:
            confidences = [
                float(response["item1"]["confidence"]),
                float(response["item2"]["confidence"]),
                float(response["visualization"]["confidence"])
            ]
            
            # All confidence scores should be between 0 and 1
            if not all(0 <= c <= 1 for c in confidences):
                return 0.0
            
            # Confidence scores shouldn't be too high for uncertain items
            # or too low for common items
            avg_confidence = sum(confidences) / len(confidences)
            
            # Penalize unrealistic confidence patterns
            if avg_confidence > 0.95:  # Too confident
                return 0.7
            elif avg_confidence < 0.3:  # Too uncertain
                return 0.5
            
            return 1.0
            
        except (KeyError, ValueError, TypeError):
            return 0.0
    
    def _validate_completeness(self, response: Dict[str, Any]) -> float:
        """Validate all required fields have meaningful values."""
        try:
            # Check if important fields are not empty
            essential_fields = [
                response["item1"]["name"],
                response["item2"]["name"],
                response["item1"]["weight_display"],
                response["item2"]["weight_display"],
                response["comparison"]["explanation"],
                response["visualization"]["prompt"]
            ]
            
            empty_fields = sum(1 for field in essential_fields if not field or field.strip() == "")
            
            return max(0.0, 1.0 - (empty_fields * 0.2))
            
        except (KeyError, AttributeError):
            return 0.0
    
    def _validate_weight_reasonableness(
        self, 
        response: Dict[str, Any], 
        request: AIProviderRequest
    ) -> float:
        """Validate weights are reasonable for given items."""
        try:
            # Extract item names from template variables
            item1_name = request.template_variables.get("item1_name", "")
            item2_name = request.template_variables.get("item2_name", "")
            
            item1_weight = float(response["item1"]["weight_kg"])
            item2_weight = float(response["item2"]["weight_kg"])
            
            # Basic sanity checks
            if item1_weight < 0.001 or item2_weight < 0.001:  # Too light
                return 0.2
            
            # Check for known item patterns
            reasonableness_score = (
                self._check_item_weight_patterns(item1_name, item1_weight) * 0.5 + 
                self._check_item_weight_patterns(item2_name, item2_weight) * 0.5
            )
            
            return reasonableness_score
            
        except (KeyError, ValueError, TypeError):
            return 0.5  # Neutral score if unable to validate
    
    def _check_item_weight_patterns(self, item_name: str, weight_kg: float) -> float:
        """Check if weight is reasonable for a given item type."""
        item_lower = item_name.lower()
        
        # Known weight ranges for common items
        weight_patterns = {
            "elephant": (3000, 7000),
            "car": (800, 3000),
            "person": (40, 150),
            "phone": (0.1, 0.3),
            "book": (0.2, 2.0),
            "feather": (0.00001, 0.001),
            "coin": (0.002, 0.03)
        }
        
        for pattern, (min_weight, max_weight) in weight_patterns.items():
            if pattern in item_lower:
                if min_weight <= weight_kg <= max_weight:
                    return 1.0
                elif weight_kg < min_weight:
                    return max(0.3, min_weight / weight_kg)
                else:  # weight_kg > max_weight
                    return max(0.3, max_weight / weight_kg)
        
        # Unknown item - neutral score
        return 0.8


class GrokResponseRecovery:
    """Attempts to recover malformed Grok responses."""
    
    def attempt_recovery(self, raw_response: str, max_attempts: int = 3) -> Dict[str, Any]:
        """Multi-stage recovery process for malformed responses."""
        
        recovery_strategies = [
            self._strategy_json_cleanup,
            self._strategy_pattern_extraction,
            self._strategy_minimal_reconstruction
        ]
        
        for i, strategy in enumerate(recovery_strategies[:max_attempts]):
            try:
                recovered = strategy(raw_response)
                if self._is_valid_recovery(recovered):
                    return recovered
            except Exception:
                continue  # Try next strategy
        
        # Final fallback: minimal valid response
        return self._create_fallback_response(raw_response)
    
    def _strategy_json_cleanup(self, response: str) -> Dict[str, Any]:
        """Clean and parse JSON with common Grok formatting issues."""
        # Remove markdown formatting
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'\s*```', '', response)
        
        # Fix common JSON issues
        response = re.sub(r',(\s*[}\]])', r'\1', response)  # Remove trailing commas
        response = re.sub(r'(\w+):', r'"\1":', response)    # Quote unquoted keys
        response = response.replace("'", '"')                # Single to double quotes
        
        # Remove comments that Grok sometimes includes
        response = re.sub(r'//.*?\n', '\n', response)
        response = re.sub(r'/\*.*?\*/', '', response, flags=re.DOTALL)
        
        return json.loads(response)
    
    def _strategy_pattern_extraction(self, response: str) -> Dict[str, Any]:
        """Extract data using regex patterns."""
        # Try to find JSON-like structure
        json_pattern = re.compile(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL)
        json_match = json_pattern.search(response)
        
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                # Try with cleanup
                cleaned = self._strategy_json_cleanup(json_match.group(0))
                return cleaned
        
        raise ValueError("No JSON structure found")
    
    def _strategy_minimal_reconstruction(self, response: str) -> Dict[str, Any]:
        """Reconstruct minimal response from text patterns."""
        # Extract weight values using patterns
        weight_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(kg|g|lb|ton)', re.IGNORECASE)
        weights = weight_pattern.findall(response)
        
        if len(weights) >= 2:
            # Convert to kg
            weight1_kg = self._convert_to_kg(float(weights[0][0]), weights[0][1])
            weight2_kg = self._convert_to_kg(float(weights[1][0]), weights[1][1])
            
            return {
                "item1": {
                    "name": "Item 1",
                    "weight_kg": weight1_kg,
                    "weight_display": f"{weights[0][0]} {weights[0][1]}",
                    "confidence": 0.3
                },
                "item2": {
                    "name": "Item 2", 
                    "weight_kg": weight2_kg,
                    "weight_display": f"{weights[1][0]} {weights[1][1]}",
                    "confidence": 0.3
                },
                "comparison": {
                    "ratio": weight1_kg / weight2_kg if weight2_kg > 0 else 1.0,
                    "heavier_item": "Item 1" if weight1_kg > weight2_kg else "Item 2",
                    "explanation": "Reconstructed from partial response"
                },
                "visualization": {
                    "prompt": "Unable to generate visualization",
                    "confidence": 0.1
                }
            }
        
        raise ValueError("Unable to extract weight information")
    
    def _convert_to_kg(self, value: float, unit: str) -> float:
        """Convert weight to kilograms."""
        unit_lower = unit.lower()
        if unit_lower == 'kg':
            return value
        elif unit_lower == 'g':
            return value / 1000
        elif unit_lower == 'lb':
            return value * 0.453592
        elif unit_lower == 'ton':
            return value * 1000
        else:
            return value  # Assume kg if unknown
    
    def _is_valid_recovery(self, recovered: Dict[str, Any]) -> bool:
        """Check if recovered response has minimum required structure."""
        required_sections = ["item1", "item2", "comparison", "visualization"]
        return all(section in recovered for section in required_sections)
    
    def _create_fallback_response(self, original: str) -> Dict[str, Any]:
        """Create minimal valid response when all recovery fails."""
        return {
            "item1": {
                "name": "Item 1",
                "weight_kg": 1.0,
                "weight_display": "1.0 kg",
                "confidence": 0.1
            },
            "item2": {
                "name": "Item 2", 
                "weight_kg": 1.0,
                "weight_display": "1.0 kg",
                "confidence": 0.1
            },
            "comparison": {
                "ratio": 1.0,
                "heavier_item": "Item 1",
                "explanation": "Response recovery failed - using fallback data"
            },
            "visualization": {
                "prompt": "Unable to generate visualization",
                "confidence": 0.1
            },
            "_recovery_failed": True,
            "_original_response": original[:200]
        }


class XAIProvider:
    """X.ai Grok provider implementation with stability and quality focus."""
    
    def __init__(self, config: Dict[str, Any], logger=None):
        self.name = "XAI_Grok"
        self.api_endpoint = config.get("api_config", {}).get("endpoint", "https://api.x.ai/v1")
        self.api_key = config.get("api_config", {}).get("api_key")
        self.model = config.get("api_config", {}).get("model", "grok-beta")
        
        if not self.api_key:
            raise ValueError("XAI API key is required")
        
        self.logger = logger or get_logger()
        self.config = config
        
        # Initialize rate limiter with X.ai specific limits
        self.rate_limiter = TokenBucketRateLimiter(
            capacity=config.get("rate_limiting", {}).get("requests_per_minute", 500),
            refill_rate=config.get("rate_limiting", {}).get("requests_per_minute", 500) / 60.0,
            burst_capacity=config.get("rate_limiting", {}).get("burst_allowance", 50)
        )
        
        # Quality validation configuration
        self.quality_config = config.get("quality_validation", {})
        self.min_confidence = self.quality_config.get("min_confidence_threshold", 0.6)
        self.enable_fallback = self.quality_config.get("fallback_on_quality_issues", True)
        
        # Response processing configuration
        self.response_config = config.get("response_processing", {})
        self.enable_normalization = self.response_config.get("enable_response_normalization", True)
        self.enable_format_recovery = self.response_config.get("enable_format_recovery", True)
        self.max_recovery_attempts = self.response_config.get("max_recovery_attempts", 3)
        
        # HTTP client configuration
        self.timeout = config.get("reliability", {}).get("timeout_seconds", 45)
        self.max_retries = config.get("reliability", {}).get("max_retries", 2)
        
        # Initialize components
        self.validator = GrokResponseValidator(self.quality_config)
        self.recovery = GrokResponseRecovery()
        
        # Circuit breaker
        cb_config = config.get("reliability", {}).get("circuit_breaker", {})
        circuit_config = CircuitBreakerConfig(
            failure_threshold=cb_config.get("failure_threshold", 3),
            success_threshold=cb_config.get("success_threshold", 2),
            timeout_seconds=cb_config.get("recovery_timeout", 120),
            half_open_max_calls=cb_config.get("half_open_calls", 1),
            expected_exception=SizeComparatorException
        )
        self.circuit_breaker = CircuitBreaker(
            name=f"xai_provider_{self.name}",
            config=circuit_config,
            logger=self.logger,
            metrics=get_metrics()
        )
        
        # Quality metrics tracking
        self.quality_metrics = {
            "total_requests": 0,
            "successful_responses": 0,
            "quality_failures": 0,
            "format_recoveries": 0,
            "avg_confidence": 0.0
        }

    async def generate_comparison(self, request: AIProviderRequest) -> WeightComparisonResponse:
        """Generate weight comparison using Grok with quality validation."""
        request_start = datetime.utcnow()
        
        try:
            # Rate limiting check
            await self._check_rate_limit(request.request_id)
            
            # Format prompt for Grok's style
            formatted_prompt = self._format_grok_prompt(request)
            
            # Make API request with retry logic
            raw_response = await self._make_api_request(formatted_prompt, request)
            
            # Validate and parse response
            parsed_response = await self._parse_and_validate_response(raw_response, request)
            
            # Quality validation
            quality_score = await self.validator.validate_response_quality(parsed_response, request)
            
            if quality_score < self.min_confidence and self.enable_fallback:
                self._log_quality_issue(request.request_id, quality_score, "Low quality score")
                raise QualityValidationError(
                    f"Response quality score {quality_score} below threshold {self.min_confidence}",
                    request.request_id
                )
            
            # Update quality metrics
            self._update_quality_metrics(quality_score, True)
            
            # Convert to response model
            response = self._create_response_model(parsed_response, request, request_start)
            
            # Add XAI-specific metadata
            response.metadata.ai_provider_used = self.name
            response.metadata.component_timings["xai_quality_score"] = int(quality_score * 1000)
            response.metadata.component_timings["xai_rate_limit_remaining"] = int(self.rate_limiter.tokens)
            
            return response
            
        except RateLimitError:
            self.logger.warning(
                "Rate limit exceeded for XAI provider",
                request_id=request.request_id,
                rate_limit_remaining=self.rate_limiter.tokens
            )
            raise
            
        except Exception as e:
            self._update_quality_metrics(0.0, False)
            self.logger.error(
                f"XAI provider request failed: {str(e)}",
                request_id=request.request_id,
                error_type=type(e).__name__
            )
            raise
    
    async def _check_rate_limit(self, request_id: str):
        """Check and enforce X.ai rate limits."""
        if not await self.rate_limiter.acquire():
            # Calculate wait time
            needed_tokens = 1
            wait_time = needed_tokens / self.rate_limiter.refill_rate
            
            self.logger.warning(
                f"Rate limit exceeded, waiting {wait_time:.2f} seconds",
                request_id=request_id,
                wait_time_seconds=wait_time
            )
            
            raise RateLimitError(
                f"Rate limit exceeded. Wait {wait_time:.2f} seconds before retrying.",
                request_id,
                wait_time
            )
    
    def _format_grok_prompt(self, request: AIProviderRequest) -> Dict[str, Any]:
        """Format prompt specifically for Grok's response style."""
        # Extract weight data from request
        item1_name = request.template_variables.get("item1_name", "Item 1")
        item1_weight = request.template_variables.get("item1_weight", "unknown")
        item2_name = request.template_variables.get("item2_name", "Item 2")
        item2_weight = request.template_variables.get("item2_weight", "unknown")
        
        # Grok responds better to conversational, direct prompts
        system_prompt = """You are Grok, an AI assistant that provides accurate weight comparisons with a touch of wit. 
Your responses should be precise, mathematically correct, and presented in a structured format.

Always respond with EXACTLY this JSON structure:
{
    "item1": {
        "name": "item name",
        "weight_kg": numeric_value,
        "weight_display": "formatted weight with unit",
        "confidence": confidence_score
    },
    "item2": {
        "name": "item name", 
        "weight_kg": numeric_value,
        "weight_display": "formatted weight with unit",
        "confidence": confidence_score
    },
    "comparison": {
        "ratio": numeric_ratio,
        "heavier_item": "item1_name or item2_name",
        "explanation": "comparison explanation"
    },
    "visualization": {
        "prompt": "visualization description",
        "confidence": confidence_score
    }
}"""
        
        user_prompt = f"""Compare the weights of these items and provide the comparison data:

Item 1: {item1_name} weighing {item1_weight}
Item 2: {item2_name} weighing {item2_weight}

Convert both weights to kilograms for comparison. Be precise with your calculations and provide realistic confidence scores based on the certainty of weight estimates for each item."""
        
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": request.max_tokens,
            "temperature": 0.3,  # Lower temperature for consistency
            "response_format": {"type": "json_object"}  # If supported
        }
    
    async def _make_api_request(self, prompt: Dict[str, Any], request: AIProviderRequest) -> Dict[str, Any]:
        """Make API request to X.ai with error handling."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "SizeComparator/1.0",
            "X-Request-ID": str(request.request_id)
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Execute with circuit breaker
                response = await self.circuit_breaker.call(
                    self._execute_request,
                    client,
                    headers,
                    prompt
                )
                
                return response
                
            except asyncio.TimeoutError:
                raise APIError(
                    "Request timeout to XAI API",
                    "integration_error", 
                    "XAI_TIMEOUT",
                    str(request.request_id)
                )
    
    async def _execute_request(self, client: httpx.AsyncClient, headers: Dict[str, Any], prompt: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual HTTP request."""
        response = await client.post(
            f"{self.api_endpoint}/chat/completions",
            json=prompt,
            headers=headers
        )
        
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "60"))
            raise RateLimitError(
                "Rate limit exceeded",
                str(headers.get("X-Request-ID", "unknown")),
                retry_after
            )
        
        if response.status_code >= 400:
            error_text = response.text
            raise APIError(
                f"XAI API error: {response.status_code} - {error_text}",
                "integration_error",
                f"XAI_API_ERROR_{response.status_code}",
                str(headers.get("X-Request-ID", "unknown"))
            )
        
        return response.json()
    
    async def _parse_and_validate_response(self, raw_response: Dict[str, Any], request: AIProviderRequest) -> Dict[str, Any]:
        """Parse and validate X.ai response."""
        try:
            # Extract content from response
            if "choices" in raw_response and len(raw_response["choices"]) > 0:
                content = raw_response["choices"][0].get("message", {}).get("content", "")
            else:
                raise ValueError("Invalid response structure from X.ai")
            
            # Try to parse JSON
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # Attempt recovery if enabled
                if self.enable_format_recovery:
                    self.logger.warning(
                        "JSON parsing failed, attempting recovery",
                        request_id=request.request_id
                    )
                    parsed = self.recovery.attempt_recovery(content, self.max_recovery_attempts)
                    self.quality_metrics["format_recoveries"] += 1
                else:
                    raise
            
            return parsed
            
        except Exception as e:
            self.logger.error(
                f"Failed to parse XAI response: {str(e)}",
                request_id=request.request_id,
                response_preview=str(raw_response)[:500]
            )
            raise
    
    def _create_response_model(
        self, 
        parsed_response: Dict[str, Any], 
        request: AIProviderRequest,
        request_start: datetime
    ) -> WeightComparisonResponse:
        """Convert parsed response to WeightComparisonResponse model."""
        
        # Extract item weights
        item1_data = parsed_response["item1"]
        item2_data = parsed_response["item2"]
        comparison_data = parsed_response["comparison"]
        visualization_data = parsed_response["visualization"]
        
        # Create ProcessedWeight objects
        item1 = ProcessedWeight(
            original_input=request.weight_data.get("item1", {"value": item1_data["weight_display"]}),
            parsed_value=Decimal(str(item1_data["weight_kg"])),
            confidence=item1_data["confidence"],
            unit_used=WeightUnit.KILOGRAM,
            display_value=item1_data["weight_display"],
            parsing_confidence=item1_data["confidence"]
        )
        
        item2 = ProcessedWeight(
            original_input=request.weight_data.get("item2", {"value": item2_data["weight_display"]}),
            parsed_value=Decimal(str(item2_data["weight_kg"])),
            confidence=item2_data["confidence"],
            unit_used=WeightUnit.KILOGRAM,
            display_value=item2_data["weight_display"],
            parsing_confidence=item2_data["confidence"]
        )
        
        # Create analysis
        analysis = ComparisonAnalysis(
            weight_ratio=Decimal(str(comparison_data["ratio"])),
            percentage_difference=Decimal(str((comparison_data["ratio"] - 1) * 100)),
            absolute_difference=ProcessedWeight(
                original_input={"value": abs(item1_data["weight_kg"] - item2_data["weight_kg"])},
                parsed_value=Decimal(str(abs(item1_data["weight_kg"] - item2_data["weight_kg"]))),
                confidence=min(item1_data["confidence"], item2_data["confidence"]),
                unit_used=WeightUnit.KILOGRAM,
                display_value=f"{abs(item1_data['weight_kg'] - item2_data['weight_kg']):.2f} kg",
                parsing_confidence=1.0
            ),
            heavier_item="item1" if item1_data["weight_kg"] > item2_data["weight_kg"] else "item2",
            significance_level=self._determine_significance(comparison_data["ratio"]),
            comparison_category=request.template_variables.get("comparison_category", "general")
        )
        
        # Create visualization
        visualization = AIVisualizationPrompt(
            prompt_text=visualization_data["prompt"],
            provider_used=self.name,
            generation_time_ms=int((datetime.utcnow() - request_start).total_seconds() * 1000),
            confidence_score=visualization_data["confidence"],
            prompt_metadata={
                "model": self.model,
                "quality_validated": True
            }
        )
        
        # Create metadata
        metadata = ResponseMetadata(
            request_id=request.request_id,
            processing_time_ms=int((datetime.utcnow() - request_start).total_seconds() * 1000),
            component_timings={
                "xai_api_call": int((datetime.utcnow() - request_start).total_seconds() * 1000)
            },
            ai_provider_used=self.name,
            ai_response_time_ms=int((datetime.utcnow() - request_start).total_seconds() * 1000),
            cache_hit=False,
            api_version="1.0.0"
        )
        
        return WeightComparisonResponse(
            item1=item1,
            item2=item2,
            analysis=analysis,
            visualization=visualization,
            metadata=metadata
        )
    
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
    
    def _update_quality_metrics(self, quality_score: float, success: bool):
        """Update internal quality metrics."""
        self.quality_metrics["total_requests"] += 1
        
        if success:
            self.quality_metrics["successful_responses"] += 1
            
        # Update running average of confidence
        total = self.quality_metrics["total_requests"]
        current_avg = self.quality_metrics["avg_confidence"]
        self.quality_metrics["avg_confidence"] = (
            (current_avg * (total - 1) + quality_score) / total
        )
    
    def _log_quality_issue(self, request_id: str, quality_score: float, reason: str):
        """Log quality validation issues."""
        self.quality_metrics["quality_failures"] += 1
        
        self.logger.warning(
            f"Quality validation failed: {reason}",
            request_id=request_id,
            quality_score=quality_score,
            threshold=self.min_confidence,
            provider=self.name
        )
    
    async def health_check(self) -> AIProviderHealth:
        """Perform health check on X.ai provider."""
        try:
            # Simple health check request
            test_request = AIProviderRequest(
                prompt_template_id="health_check",
                template_variables={
                    "item1_name": "1 kilogram",
                    "item1_weight": "1 kg",
                    "item2_name": "1 pound",
                    "item2_weight": "1 lb"
                },
                weight_data={
                    "item1": {"value": "1 kg"},
                    "item2": {"value": "1 lb"}
                },
                max_tokens=500,
                temperature=0.3
            )
            
            start_time = time.time()
            await self.generate_comparison(test_request)
            latency_ms = (time.time() - start_time) * 1000
            
            # Get circuit breaker state
            cb_state = self.circuit_breaker.get_state()
            if cb_state == CBState.OPEN:
                status = ProviderStatus.CIRCUIT_OPEN
            elif cb_state == CBState.HALF_OPEN:
                status = ProviderStatus.DEGRADED
            else:
                status = ProviderStatus.HEALTHY
            
            success_rate = (
                self.quality_metrics["successful_responses"] / 
                max(1, self.quality_metrics["total_requests"])
            )
            
            return AIProviderHealth(
                provider_name=self.name,
                status=status,
                circuit_breaker_state=CircuitBreakerState(cb_state.value),
                success_rate=success_rate,
                avg_response_time_ms=latency_ms,
                error_count=self.quality_metrics["total_requests"] - self.quality_metrics["successful_responses"],
                last_success=datetime.utcnow(),
                requests_per_minute=self.rate_limiter.requests_this_minute,
                rate_limit_quota=500,
                circuit_breaker_config={
                    "failure_threshold": self.circuit_breaker.config.failure_threshold,
                    "recovery_timeout": self.circuit_breaker.config.timeout_seconds,
                    "failure_count": self.circuit_breaker.stats.failure_count
                }
            )
            
        except Exception as e:
            cb_state = self.circuit_breaker.get_state()
            return AIProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.UNHEALTHY,
                circuit_breaker_state=CircuitBreakerState(cb_state.value),
                success_rate=0.0,
                avg_response_time_ms=0.0,
                error_count=self.quality_metrics["total_requests"] - self.quality_metrics["successful_responses"],
                last_error=str(e),
                requests_per_minute=self.rate_limiter.requests_this_minute,
                rate_limit_quota=500,
                circuit_breaker_config={
                    "failure_threshold": self.circuit_breaker.config.failure_threshold,
                    "recovery_timeout": self.circuit_breaker.config.timeout_seconds,
                    "failure_count": self.circuit_breaker.stats.failure_count
                }
            )
    
    async def shutdown(self):
        """Cleanup resources on shutdown."""
        self.logger.info(
            f"Shutting down {self.name} provider",
            total_requests=self.quality_metrics["total_requests"],
            success_rate=self.quality_metrics["successful_responses"] / max(1, self.quality_metrics["total_requests"]),
            avg_confidence=self.quality_metrics["avg_confidence"]
        )