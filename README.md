# SizeComparator

A lightweight web application that converts weight inputs into relatable object comparisons using AI providers. Enter a weight in lbs or kg and receive two AI-generated comparisons to help visualize and understand the measurement.

**Example**: "24 lbs" → "Four medium chickens (6 lbs each)" + "One car tire (24 lbs total)"

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd SizeComparator

# Install dependencies
pip install -r requirements.txt

# Configure AI providers
cp .env.example .env
# Edit .env with your API keys

# Run the application
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Open browser to http://localhost:8000
```

## Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Git
- API keys for AI providers (OpenAI, Anthropic, X.ai)

### Detailed Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SizeComparator
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
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
   # OPENAI_API_KEY=your_openai_key
   # ANTHROPIC_API_KEY=your_anthropic_key
   # XAI_API_KEY=your_xai_key
   ```

5. **Run the application**
   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Project Structure

```
SizeComparator/
├── src/                    # Source code
│   ├── api/               # FastAPI routes and middleware
│   ├── core/              # Business logic and weight processing
│   ├── providers/         # AI provider implementations
│   ├── models/            # Pydantic models and schemas
│   ├── services/          # AI orchestration and validation
│   └── main.py           # Application entry point
├── frontend/              # Static frontend files
│   ├── css/              # Stylesheets with theme system
│   ├── js/               # JavaScript modules
│   └── index.html        # Single page application
├── config/                # Configuration files and templates
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── fixtures/         # Test data
├── docs/                  # Documentation
│   ├── SIZECOMPARATOR_SYSTEM_SPEC.md
│   └── api/              # API documentation
├── scripts/              # Utility scripts
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── CLAUDE.md            # AI assistant context
└── README.md            # This file
```

## Development Workflow

### Setting Up Development Environment

1. Follow the installation steps above
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

### Code Style and Standards

- Follow PEP 8 for Python code
- Use type hints throughout the codebase
- Write self-documenting code with minimal comments
- No emojis or symbols in code, comments, or commit messages
- Prefer configuration over hardcoded values

### Parallel Development Pattern

This project uses a parallel development approach for efficient implementation:

1. **Foundation Phase (Parallel Development)**
   - Frontend UI components (Developer A)
   - AI provider implementations (Developer B)
   - Core backend logic (Developer C)

2. **Integration Phase (Sequential)**
   - API endpoint integration and testing
   - End-to-end user workflow validation
   - Error handling verification across components

3. **Polish Phase (Parallel)**
   - Performance optimization and monitoring
   - Documentation and testing
   - Deployment and infrastructure

### AI Provider Development

When adding new AI providers:

1. **Create provider implementation**
   ```bash
   # Use the abstract provider interface
   cp src/providers/openai_provider.py src/providers/new_provider.py
   ```

2. **Update configuration**
   ```yaml
   # Add to config/application.yaml
   ai_providers:
     enabled: ["openai", "anthropic", "xai", "new_provider"]
   ```

3. **Test integration**
   ```bash
   python scripts/test_providers.py --provider new_provider
   ```

### Git Workflow

1. Create a feature branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the coding standards

3. Commit with clear, descriptive messages:
   ```bash
   git add .
   git commit -m "Add feature: brief description"
   ```

4. Push to remote and create a pull request
   ```bash
   git push origin feature/your-feature-name
   ```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_weight_parser.py

# Run integration tests with real AI providers
pytest tests/integration/ --run-live-providers
```

### Writing Tests

- Write unit tests for all weight processing functions
- Include integration tests for AI provider interactions
- Maintain test coverage above 80%
- Use fixtures for consistent test data
- Mock AI provider responses for reliable testing

### Type Checking

```bash
# Run type checking
mypy src/

# Check specific file
mypy src/services/ai_manager.py
```

### Linting and Formatting

```bash
# Run linter
ruff check src/

# Auto-fix issues
ruff check src/ --fix

# Format code
ruff format src/
```

## Configuration

### AI Provider Configuration

The system supports multiple AI providers with automatic failover:

```yaml
# config/application.yaml
ai_providers:
  enabled: ["openai", "anthropic", "xai"]
  timeout_seconds: 10
  max_retries: 2
  
  openai:
    model: "gpt-4"
    max_tokens: 150
    temperature: 0.7
    
  anthropic:
    model: "claude-3-sonnet-20240229"
    max_tokens: 150
    temperature: 0.7
```

### Prompt Templates

Prompts are configuration-driven and can be updated without code changes:

```bash
# Edit prompt templates
vim config/prompts/weight_comparison.txt

# Restart application to reload
```

### Application Settings

```yaml
# config/application.yaml
application:
  max_weight_lbs: 1000000
  max_weight_kg: 453592
  supported_units: ["lbs", "kg"]
  cache_ttl_seconds: 300
```

## API Documentation

### Compare Weight Endpoint

**POST** `/api/compare`

Request body:
```json
{
    "weight": 24.5,
    "unit": "lbs"
}
```

Response:
```json
{
    "comparisons": [
        {
            "description": "Four medium chickens",
            "individual_weight": "6 lbs each",
            "confidence": 0.9
        },
        {
            "description": "One car tire", 
            "individual_weight": "24 lbs total",
            "confidence": 0.8
        }
    ],
    "request_weight": "24 lbs",
    "response_time_ms": 1250
}
```

### Health Check Endpoint

**GET** `/health`

Returns application and AI provider health status.

## Deployment

### Docker Deployment

```bash
# Build container
docker build -t sizecomparator .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e ANTHROPIC_API_KEY=your_key \
  -e XAI_API_KEY=your_key \
  sizecomparator
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes |
| `XAI_API_KEY` | X.ai API key | Yes |
| `LOG_LEVEL` | Logging level (INFO, DEBUG, ERROR) | No |
| `MAX_WEIGHT_LBS` | Maximum weight in pounds | No |

### Health Checks

The application includes health check endpoints for monitoring:

- `/health` - Overall application health
- `/health/providers` - AI provider connectivity status
- `/health/ready` - Readiness for traffic

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Check existing issues** before creating new ones
2. **Fork the repository** and create a feature branch
3. **Follow the coding standards** outlined above
4. **Write tests** for new functionality
5. **Update documentation** as needed
6. **Submit a pull request** with a clear description

### Pull Request Process

1. Ensure all tests pass and type checking succeeds
2. Update the README.md with details of changes if needed
3. Update API documentation for any endpoint changes
4. Request review from maintainers
5. Address review feedback promptly

### Code Review Checklist

- [ ] Code follows style guidelines and type hints
- [ ] Tests are included and passing
- [ ] AI provider integration is properly tested
- [ ] Error handling is comprehensive
- [ ] Configuration is properly externalized
- [ ] Documentation is updated
- [ ] No sensitive data is exposed
- [ ] Commit messages are clear and descriptive

## Architecture

### Key Design Principles

- **Simplicity**: Minimal dependencies, vanilla frontend
- **Reliability**: Multiple AI providers with automatic failover
- **Maintainability**: Configuration-driven behavior
- **Performance**: Sub-2 second response times
- **Extensibility**: Easy addition of new AI providers

### AI Provider Integration

The system uses a provider abstraction pattern with:

- **Circuit Breaker**: Automatic failure detection and recovery
- **Retry Logic**: Exponential backoff with provider rotation
- **Response Validation**: Quality checks for AI-generated comparisons
- **Fallback Mechanisms**: Graceful degradation when providers fail

### Frontend Architecture

- **Vanilla JavaScript**: No frameworks or build tools required
- **Responsive Design**: Mobile-first CSS Grid layout
- **Theme System**: Light/dark mode with localStorage persistence
- **Progressive Enhancement**: Core functionality works without JavaScript

## Performance

### Response Time Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response | < 2 seconds (95th percentile) | Server-side timing |
| Frontend Load | < 500ms | Browser performance API |
| AI Provider Timeout | 10 seconds maximum | Provider-specific timing |

### Optimization Strategies

- **Parallel AI Calls**: Multiple providers queried simultaneously
- **Response Caching**: Frequently requested weights cached temporarily  
- **Circuit Breakers**: Failed providers bypassed automatically
- **Async Processing**: Non-blocking I/O throughout the application

## Troubleshooting

### Common Issues

**"Service temporarily unavailable"**
- Check AI provider API keys in environment variables
- Verify network connectivity to AI provider endpoints
- Check application logs for specific provider errors

**Slow response times**
- Monitor AI provider response times in logs
- Check if circuit breakers are tripping
- Verify network latency to AI providers

**Invalid weight comparisons**
- Review AI provider responses in debug logs
- Check prompt template configuration
- Verify response validation rules

### Logging

Application logs include:
- Request/response timing
- AI provider selection and fallback
- Error details with request IDs
- Performance metrics

```bash
# View logs in development
tail -f logs/application.log

# Filter for errors
grep ERROR logs/application.log
```

## License

[Choose an appropriate license for your project]

---

**Built with simplicity and reliability in mind. Transform any weight into understanding.**