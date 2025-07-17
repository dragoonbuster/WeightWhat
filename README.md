# Weight, What?

A web application that converts weight measurements into relatable, humorous comparisons.

## Overview

Weight, What? transforms mundane weight measurements (kilograms, pounds, etc.) into entertaining comparisons that people can actually understand. Instead of "5 kg," users get "about as heavy as a bowling ball or a house cat."

## Features

- Instant weight conversions to relatable objects
- Support for multiple weight units (kg, lbs, g, oz, tons)
- Two deployment options: static (free) or AI-powered ($6/month)
- Clean, retro terminal-inspired interface
- Mobile-responsive design
- Optional AI integration for dynamic comparisons

## Quick Start

### Option 1: Static Version (No Backend Required)

The simplest way to use Weight, What? is with the standalone HTML file:

```bash
# Open directly in browser
open frontend/simple.html

# Or serve locally
python -m http.server 8000
# Navigate to http://localhost:8000/frontend/simple.html
```

### Option 2: Full Application with AI

For dynamic AI-powered comparisons:

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your API keys to .env

# Run the application
python src/api/unified_app.py

# Access at http://localhost:8000
```

## Deployment

### Static Deployment (Free)

Deploy the static version to any static hosting service:

**GitHub Pages:**
```bash
# Push to GitHub
# Enable GitHub Pages in repository settings
# Access at: https://[username].github.io/WeightWhat/frontend/simple.html
```

**Netlify/Vercel:**
Simply drag and drop the `frontend` folder.

### VPS Deployment with AI

For the full experience with AI-powered comparisons:

```bash
# On a fresh Ubuntu VPS
wget -O - https://raw.githubusercontent.com/dragoonbuster/WeightWhat/main/quick-vps-setup.sh | bash
```

See `DEPLOYMENT.md` for detailed instructions.

## Project Structure

```
WeightWhat/
├── frontend/               # Frontend files
│   ├── simple.html        # Standalone static version
│   ├── index.html         # Full frontend (requires backend)
│   ├── css/               # Stylesheets
│   └── js/                # JavaScript files
├── src/                   # Backend source code
│   ├── api/               # FastAPI application
│   ├── providers/         # AI provider integrations
│   └── services/          # Business logic
├── tests/                 # Test suite
├── quick-vps-setup.sh     # Automated VPS deployment
└── requirements.txt       # Python dependencies
```

## API Documentation

When running the full application, the API is available at:

- `POST /api/v1/compare` - Get weight comparisons
- `GET /api/v1/providers` - List available AI providers
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/compare \
  -H "Content-Type: application/json" \
  -d '{
    "weight": 75,
    "unit": "kg",
    "provider": "openai"
  }'
```

## Configuration

The application uses environment variables for configuration. See `.env.example` for all available options:

- `SIZECOMPARATOR_OPENAI_API_KEY` - OpenAI API key
- `SIZECOMPARATOR_ANTHROPIC_API_KEY` - Anthropic API key
- `SIZECOMPARATOR_XAI_API_KEY` - X.AI API key
- `SIZECOMPARATOR_DEFAULT_PROVIDER` - Default AI provider
- `SIZECOMPARATOR_CACHE_TYPE` - Cache backend (memory/redis)

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/
```

### Code Style

The project follows PEP 8 style guidelines. Format code with:

```bash
# Format code
black src/ tests/

# Check linting
pylint src/
```

## Contributing

This is a simple gag site meant for entertainment. Contributions should maintain the project's simplicity and humor. Please:

1. Keep features simple and focused on the core concept
2. Maintain the clean, professional codebase
3. Avoid over-engineering or adding unnecessary complexity
4. Test your changes thoroughly

## License

MIT License - See LICENSE file for details.

## Acknowledgments

Built with FastAPI, OpenAI GPT-4, and a healthy sense of humor about everyday measurements.