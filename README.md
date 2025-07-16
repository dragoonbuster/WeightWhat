# SizeComparator

A fast, intelligent weight comparison API that converts weight inputs into relatable object comparisons using AI providers with intelligent service routing and sub-2 second response times.

**Example**: "5 kg" → "5 kg is about the weight of a house cat or a bag of flour."

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd SizeComparator
source venv/bin/activate
pip install -r requirements.txt

# Configure API keys (at least one required)
cp .env.example .env
# Edit .env with your AI provider API keys

# Start unified server
python run_unified_server.py

# Test API
curl -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "5 kg"}'

# Open browser to http://localhost:8000
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git
- At least one AI provider API key (OpenAI, Anthropic, or X.ai)

### Detailed Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SizeComparator
   ```

2. **Activate virtual environment** (should already exist)
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your AI provider API keys:
   # SIZECOMPARATOR_OPENAI_API_KEY=sk-your-openai-key-here
   # SIZECOMPARATOR_ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
   # SIZECOMPARATOR_XAI_API_KEY=xai-your-xai-key-here
   ```

5. **Run the unified server**
   ```bash
   python run_unified_server.py
   ```

## Features

- **Unified API**: Single `/api/compare` endpoint with intelligent service routing
- **Multiple AI Providers**: OpenAI GPT-4, Anthropic Claude, X.ai Grok
- **Service Modes**: Basic, Fast Validation (<2s), Full Validation, Comprehensive
- **Weight Support**: kg, lbs, grams, tons, ounces with automatic conversion
- **Fallback System**: Graceful degradation when AI providers unavailable
- **Fast Validation**: Optimized for sub-2 second response times
- **Frontend Demo**: Interactive web interface at http://localhost:8000

## Service Modes

- **Basic**: Static comparisons, always available (~500ms)
- **Fast Validation**: AI-powered with <2s target (~1800ms)
- **Full Validation**: Comprehensive AI validation (~4000ms)
- **Comprehensive**: Most thorough analysis (~6000ms)

## Project Structure

```
SizeComparator/
├── src/
│   ├── api/unified_app.py          # Main unified API application
│   ├── services/
│   │   ├── shared/service_factory.py  # Intelligent service selection
│   │   ├── fast_validation_service.py # Fast AI validation
│   │   └── mvp_comparison.py          # Basic fallback service
│   ├── providers/                  # AI provider implementations
│   ├── core/simple_config.py       # Configuration system
│   └── models/                     # Data models
├── frontend/                       # Web interface
├── docs/                          # Documentation
├── run_unified_server.py          # Server startup script
└── requirements.txt               # Dependencies
```

## API Usage

### Basic Request
```bash
curl -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "25 pounds", "style": "creative"}'
```

### Service Mode Selection
```bash
# Query parameter
curl -X POST http://localhost:8000/api/compare?service_mode=fast_validation \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "5 kg"}'

# Header
curl -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -H "X-Service-Mode: comprehensive" \
  -d '{"weight_input": "500 grams"}'
```

### Response Example
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

## Environment Configuration

### Required Variables
```bash
# At least one AI provider API key
SIZECOMPARATOR_OPENAI_API_KEY=sk-your-openai-key-here
SIZECOMPARATOR_ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
SIZECOMPARATOR_XAI_API_KEY=xai-your-xai-key-here
```

### Optional Configuration
```bash
# Environment
SIZECOMPARATOR_ENV=development
SIZECOMPARATOR_DEBUG=true
SIZECOMPARATOR_LOG_LEVEL=debug

# API Server
SIZECOMPARATOR_API_HOST=127.0.0.1
SIZECOMPARATOR_API_PORT=8000

# Service Factory
SIZECOMPARATOR_SERVICE_STRATEGY=smart_routing
SIZECOMPARATOR_FORCE_BASIC_SERVICE=false

# Cache
SIZECOMPARATOR_CACHE_PROVIDER=memory
SIZECOMPARATOR_CACHE_TTL=3600
```

## Testing

### Running Tests

```bash
# Test service factory
python test_service_factory.py

# Test fast validation
python test_fast_validation.py

# Test unified API
python test_unified_app.py

# Test basic functionality
python test_mvp.py

# Test integration
python test_integration.py

# Test validation service
python test_validation.py
```

### Available Test Files

- `test_service_factory.py` - Service selection and factory logic
- `test_fast_validation.py` - Fast validation service optimization
- `test_unified_app.py` - Unified API endpoint functionality
- `test_mvp.py` - Basic MVP comparison service
- `test_integration.py` - End-to-end integration tests
- `test_validation.py` - AI validation service tests

### Manual Testing

```bash
# Test configuration loading
python -c "from src.core.simple_config import get_config; print('Config loaded successfully')"

# Test weight processor
python demo_weight_processor.py

# Test OpenAI provider
python demo_openai_provider.py
```

## Endpoints

- **Main API**: `POST /api/compare`
- **Health Check**: `GET /health`
- **Service Status**: `GET /api/status`
- **API Documentation**: `GET /docs`
- **Demo Interface**: `GET /demo/fast_validation`

## Documentation

- **API Documentation**: `docs/API_DOCUMENTATION.md`
- **Configuration Guide**: `docs/CONFIGURATION_GUIDE.md`
- **Service Selection Guide**: `docs/SERVICE_SELECTION_GUIDE.md`
- **Development Guide**: `CLAUDE.md`

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

## Production Deployment

### Docker
```bash
# Build image
docker build -t sizecomparator .

# Run with environment variables
docker run -p 8000:8000 \
  -e SIZECOMPARATOR_OPENAI_API_KEY=your_key \
  -e SIZECOMPARATOR_ENV=production \
  sizecomparator
```

### Docker Compose
```bash
# Development
docker-compose up

# Production
docker-compose -f docker-compose.prod.yml up
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SIZECOMPARATOR_OPENAI_API_KEY` | OpenAI API key | Optional |
| `SIZECOMPARATOR_ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `SIZECOMPARATOR_XAI_API_KEY` | X.ai API key | Optional |
| `SIZECOMPARATOR_ENV` | Environment (development/production) | No |
| `SIZECOMPARATOR_SERVICE_STRATEGY` | Service selection strategy | No |

**Note**: At least one AI provider API key is required for full functionality.

### Health Checks

The application includes health check endpoints for monitoring:

- `/health` - Overall application health
- `/api/status` - Service status and metrics
- Service availability monitoring built-in

## Performance

- **Fast Validation**: <2 second response time target
- **Common Weights**: Optimized for 1g-100kg range
- **Extreme Weights**: Enhanced handling for <1g or >100kg
- **Fallback**: Graceful degradation to basic service
- **Caching**: Memory/Redis caching for improved performance

## AI Provider Integration

- **OpenAI GPT-4**: Primary provider for fast validation
- **Anthropic Claude**: Detailed reasoning and technical comparisons
- **X.ai Grok**: Creative and alternative perspectives
- **Shared Components**: Unified prompt building and validation
- **Circuit Breaker**: Automatic failover when providers unavailable

## Contributing

1. Follow the development workflow in `CLAUDE.md`
2. Use the unified API endpoint for all new features
3. Test with multiple service modes
4. Ensure AI provider fallback works correctly
5. Update documentation for API changes

## Troubleshooting

### Common Issues

**Service Won't Start**
1. Check all required environment variables are set
2. Verify API keys are valid and not expired
3. Check port availability
4. Review startup logs for specific errors

**AI Providers Not Available**
1. Verify API keys are correctly set
2. Check internet connectivity
3. Verify API key permissions and quotas
4. Test with basic service mode first

**Performance Issues**
1. Increase timeout values
2. Use fast validation service mode
3. Enable caching with appropriate TTL
4. Monitor service availability patterns

### Getting Help

1. **Check service status**: `GET /api/status`
2. **Enable debug logging**: `SIZECOMPARATOR_LOG_LEVEL=debug`
3. **Test explicit selection**: Use `service_mode` parameter
4. **Check configuration**: Review `docs/CONFIGURATION_GUIDE.md`
5. **Use basic mode**: Test with basic service to isolate issues

## License

[License information here]

## Support

For issues or questions:
1. Check service status at `/api/status`
2. Review configuration in `docs/CONFIGURATION_GUIDE.md`
3. Test with basic service mode first
4. Check logs for detailed error information

---

**Built with simplicity and reliability in mind. Transform any weight into understanding.**