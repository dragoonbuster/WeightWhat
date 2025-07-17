# Weight, What?

A web application that converts weight measurements into relatable, humorous comparisons.

## What It Does

Weight, What? takes any weight measurement and instantly converts it into comparisons people can actually understand and laugh about. Instead of abstract numbers like "75 kg" or "165 lbs", you get vivid comparisons like:

- "That's about as heavy as a golden retriever"
- "Roughly the weight of 15,000 bees"
- "Like carrying around a small motorcycle"

The app supports multiple weight units (kg, lbs, g, oz, tons) and provides instant, entertaining comparisons that make weights tangible and fun.

## Features

- **Instant Comparisons**: Type any weight and get immediate, relatable comparisons
- **Multiple Units**: Supports kilograms, pounds, grams, ounces, and tons
- **Two Modes**:
  - Static mode with pre-written humorous comparisons
  - AI-powered mode for dynamic, creative comparisons
- **Clean Interface**: Retro terminal-inspired design that's easy to use
- **Mobile Friendly**: Works great on phones, tablets, and desktops

## How It Works

### Static Version
The simple HTML version includes a curated collection of funny comparisons for common weight ranges. It works entirely in your browser with no server required.

### AI-Powered Version
The full version uses AI language models (OpenAI GPT-4, Anthropic Claude, or X.AI Grok) to generate creative, contextual comparisons on the fly. Each comparison is unique and tailored to the specific weight entered.

## Examples

**Input**: 5 kg  
**Output**: "That's about as heavy as a bowling ball or a house cat who's been hitting the treats pretty hard"

**Input**: 200 lbs  
**Output**: "That's roughly the weight of a full-grown kangaroo, or what it feels like carrying your entire wardrobe at once"

**Input**: 1 ton  
**Output**: "That's about as heavy as a small car, or approximately 400,000 quarters if you're planning the world's worst piggy bank"

## Technical Details

- **Frontend**: Vanilla HTML/CSS/JavaScript (no build tools required)
- **Backend**: FastAPI (Python) with async support
- **AI Integration**: Supports multiple providers with fallback options
- **Caching**: Redis-based caching to improve response times and reduce API costs
- **Architecture**: Clean separation between static and dynamic versions

## Development

To run locally:

```bash
# Static version (no setup required)
python -m http.server 8000
# Open http://localhost:8000/frontend/simple.html

# Full version with AI
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
python src/api/unified_app.py
```

## Why?

Because weight measurements are boring and life is too short not to know that your laptop weighs about the same as a chihuahua.

## License

MIT - Do whatever makes you happy.