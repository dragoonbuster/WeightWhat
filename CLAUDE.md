# AI Assistant Guide for Weight, What?

## Project Overview

Weight, What? is a simple gag site that converts weights into funny comparisons. 

- **Purpose**: Make people laugh by comparing "75 kg" to "a golden retriever" 
- **Traffic**: Basically none (it's a gag site)
- **Complexity**: Should be minimal

## Two Deployment Options

1. **Static** (`frontend/simple.html`) - Free, no backend
2. **VPS** (full app) - $6/month, real AI responses

## If Asked to Add Features

Keep it simple! This is a gag site, not a product. Reasonable additions:
- More funny comparisons
- Different themes (space, animals, food)
- Sound effects (maybe)

Avoid:
- User accounts
- Analytics
- Complex features
- "Enterprise" anything

## Quick Commands

```bash
# Test locally
python -m http.server 8000
# Open http://localhost:8000/frontend/simple.html

# Deploy to production
./quick-vps-setup.sh  # Run on VPS
```

## API Keys

Only needed for VPS deployment:
- `SIZECOMPARATOR_OPENAI_API_KEY` - For GPT-4 comparisons

## Remember

This is meant to be fun and simple. Don't over-engineer it!