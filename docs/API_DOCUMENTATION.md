# SizeComparator API Documentation

**Version**: 1.0.0  
**Last Updated**: 2025-07-14

## Overview

The SizeComparator API provides intelligent weight comparison services through a unified endpoint that automatically selects the optimal service based on request parameters, performance requirements, and AI provider availability.

## Base URL

```
http://localhost:8000/api
```

## Unified Comparison Endpoint

### POST /api/compare

Convert a weight input into relatable object comparisons using AI providers with intelligent service routing.

#### Request Parameters

**Query Parameters:**
- `service_mode` (optional): Override service mode selection
  - `basic` - Basic fallback comparisons (always available)
  - `fast_validation` - AI-powered with <2s response time target
  - `full_validation` - Full AI validation and quality checks
  - `comprehensive` - Most comprehensive AI analysis
- `timeout_ms` (optional): Request timeout in milliseconds

**Headers:**
- `X-Service-Mode` (optional): Alternative way to specify service mode
- `X-Performance-Profile` (optional): Performance optimization profile
  - `speed_optimized` - Prioritize fast response
  - `balanced` - Balance speed and accuracy
  - `accuracy_optimized` - Prioritize accuracy

**Request Body:**
```json
{
  "weight_input": "5 kg",
  "style": "default",
  "provider": "auto"
}
```

**Request Body Fields:**
- `weight_input` (required): Weight value with unit (e.g., "5 kg", "10 pounds", "500 grams")
- `style` (optional): Comparison style
  - `default` - Standard comparisons
  - `creative` - More creative and detailed
  - `technical` - Precise and technical
- `provider` (optional): AI provider preference
  - `auto` - Automatic selection
  - `openai` - Prefer OpenAI GPT-4
  - `anthropic` - Prefer Anthropic Claude
  - `xai` - Prefer X.ai Grok

#### Response

**Success Response (200 OK):**
```json
{
  "comparison_text": "5 kg is about the weight of a house cat or a bag of flour.",
  "weight_processed": "5 kg",
  "provider_used": "fast_validated_rule_based_2_calls",
  "response_time_ms": 1250,
  "cached": false,
  "request_id": "abc123ef"
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Invalid weight input",
  "error_code": "WEIGHT_VALIDATION_ERROR",
  "request_id": "abc123ef",
  "suggestions": [
    "Try a format like '5 kg' or '10 pounds'",
    "Make sure the weight is a positive number",
    "Include a unit (kg, lbs, grams, etc.)"
  ]
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "error": "Service temporarily unavailable",
  "error_code": "SERVICE_ERROR",
  "service_mode": "fast_validation",
  "fallback_attempted": true
}
```

#### Service Mode Selection Priority

1. **Query Parameter**: `?service_mode=fast_validation`
2. **Header**: `X-Service-Mode: full_validation`
3. **Intelligent Selection**: Based on request characteristics
4. **Environment Defaults**: Production uses validation, development uses basic
5. **Application Default**: fast_validation

#### Example Requests

**Basic Mode:**
```bash
curl -X POST http://localhost:8000/api/compare?service_mode=basic \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "5 kg", "style": "default"}'
```

**Fast Validation with Creative Style:**
```bash
curl -X POST http://localhost:8000/api/compare?service_mode=fast_validation \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "25 pounds", "style": "creative"}'
```

**Header-Based Service Selection:**
```bash
curl -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -H "X-Service-Mode: comprehensive" \
  -H "X-Performance-Profile: accuracy_optimized" \
  -d '{"weight_input": "500 grams", "style": "technical"}'
```

## Legacy Endpoints (Backward Compatibility)

### POST /api/compare/single
Maps to `service_mode=basic`

### POST /api/compare/validated  
Maps to `service_mode=full_validation`

### POST /api/compare/fast
Maps to `service_mode=fast_validation`

## Status and Health Endpoints

### GET /health
```json
{
  "status": "healthy",
  "service_factory": {
    "factory_status": "healthy",
    "services": {...},
    "availability": {...}
  },
  "metrics": {...},
  "uptime_seconds": 3600,
  "version": "1.0.0"
}
```

### GET /api/status
```json
{
  "service_factory": {
    "factory_status": "healthy",
    "services": {
      "basic": {
        "avg_response_time_ms": 500,
        "accuracy_score": 0.6,
        "resource_intensity": 1
      },
      "fast_validation": {
        "avg_response_time_ms": 1800,
        "accuracy_score": 0.8,
        "resource_intensity": 3
      }
    },
    "availability": {
      "basic": true,
      "fast_validation": true,
      "full_validation": true,
      "comprehensive": false
    },
    "ai_providers_available": true
  },
  "app_metrics": {
    "requests_total": 1250,
    "requests_by_mode": {
      "basic": 200,
      "fast_validation": 800,
      "full_validation": 200,
      "comprehensive": 50
    },
    "response_times": [...],
    "errors_total": 15
  },
  "startup_time": "2025-07-14T10:00:00Z",
  "uptime_seconds": 3600
}
```

## Service Modes

### Basic Mode
- **Description**: Always available fallback with static comparisons
- **Response Time**: ~500ms
- **Accuracy**: 60%
- **Requirements**: None
- **Use Case**: Fallback when AI providers unavailable

### Fast Validation Mode  
- **Description**: AI-powered with <2s response time target
- **Response Time**: ~1800ms
- **Accuracy**: 80%
- **Requirements**: AI provider available
- **Strategy**: 
  - Common weights: 2 parallel calls + rule validation
  - Extreme weights: 3 calls + quick AI validation

### Full Validation Mode
- **Description**: Full AI validation and quality checks
- **Response Time**: ~4000ms
- **Accuracy**: 95%
- **Requirements**: AI provider available
- **Strategy**: Multiple AI calls with comprehensive validation

### Comprehensive Mode
- **Description**: Most comprehensive AI analysis available
- **Response Time**: ~6000ms
- **Accuracy**: 98%
- **Requirements**: AI provider available
- **Strategy**: Multiple validation rounds with quality scoring

## Performance Profiles

### Speed Optimized
- Prioritizes fast response times
- Uses basic service for common weights
- Aggressive timeouts and fallbacks

### Balanced
- Balances speed and accuracy
- Considers weight complexity and timeout
- Default profile for most requests

### Accuracy Optimized  
- Prioritizes accuracy over speed
- Uses comprehensive validation
- Longer timeouts for better results

## Weight Input Formats

### Supported Units
- **Kilograms**: kg, kilograms, kilogram
- **Pounds**: lbs, pounds, pound, lb
- **Grams**: g, grams, gram
- **Tons**: tons, ton, tonnes, tonne
- **Ounces**: oz, ounces, ounce

### Input Examples
```
"5 kg"
"10 pounds"
"500 grams"
"2.5 tons"
"1 ounce"
"75kg"
"25 lbs"
"0.5 tonnes"
```

### Weight Ranges
- **Minimum**: 0.001g
- **Maximum**: 1,000,000kg
- **Common Range**: 1g - 100kg (optimal for fast validation)
- **Extreme Range**: <1g or >100kg (uses full validation)

## Error Codes

### WEIGHT_VALIDATION_ERROR
Weight input format is invalid or out of range.

### SERVICE_ERROR
Service temporarily unavailable, fallback may have been attempted.

### TIMEOUT_ERROR
Request timed out waiting for AI provider response.

### AI_PROVIDER_ERROR
All AI providers failed to respond.

### INTERNAL_ERROR
Unexpected server error occurred.

## Rate Limiting

Currently no rate limiting implemented. API is public and free to use.

## Authentication

No authentication required. API is publicly accessible.

## Environment Variables

### AI Provider Configuration
- `SIZECOMPARATOR_OPENAI_API_KEY`: OpenAI API key
- `SIZECOMPARATOR_ANTHROPIC_API_KEY`: Anthropic API key  
- `SIZECOMPARATOR_XAI_API_KEY`: X.ai API key

### Service Configuration
- `SIZECOMPARATOR_SERVICE_STRATEGY`: Service selection strategy
- `SIZECOMPARATOR_FORCE_BASIC_SERVICE`: Force basic service only
- `SIZECOMPARATOR_REQUIRE_VALIDATION`: Require validation in production

## Demo and Testing

### Demo Interface
Visit `http://localhost:8000/demo/fast_validation` for an interactive demo.

### Test Examples
```bash
# Test basic functionality
curl -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "5 kg"}'

# Test with specific service mode
curl -X POST http://localhost:8000/api/compare?service_mode=fast_validation \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "25 pounds", "style": "creative"}'

# Test error handling
curl -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "invalid"}'
```

## Development Setup

### Requirements
- Python 3.8+
- FastAPI
- At least one AI provider API key

### Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SIZECOMPARATOR_OPENAI_API_KEY=your_key_here

# Start server
python run_unified_server.py
```

### Available Endpoints
- Main API: `http://localhost:8000/api/compare`
- Health check: `http://localhost:8000/health`
- API status: `http://localhost:8000/api/status`
- API docs: `http://localhost:8000/docs`
- Demo: `http://localhost:8000/demo/fast_validation`

## Support

For issues or questions:
1. Check the logs at startup for configuration issues
2. Verify AI provider API keys are set correctly
3. Test with basic mode first to isolate AI provider issues
4. Check service status at `/api/status`