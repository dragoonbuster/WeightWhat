# AI Assistant Guide for Weight, What?

## Project Overview

Weight, What? is a simple gag site that converts weights into funny comparisons. 

- **Purpose**: Make people laugh by comparing "75 kg" to "a golden retriever" 
- **Traffic**: Basically none (it's a gag site)
- **Complexity**: Should be minimal

## Important Style Guidelines

- **NO EMOJIS/SYMBOLS**: Never use emojis, emoticons, or decorative symbols in code, documentation, or comments. Keep everything professional and clean.

### Regex Template for Removing Emojis/Symbols

Use these regex patterns to clean documentation:

```regex
# Comprehensive emoji removal pattern
[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F900}-\u{1F9FF}]|[\u{1F018}-\u{1F270}]|[\u{238C}-\u{2454}]|[\u{20D0}-\u{20FF}]|[\u{FE00}-\u{FE0F}]|[\u{1F0CF}]|[\u{1F18E}]|[\u{1F191}-\u{1F19A}]|[\u{1F201}]|[\u{1F21A}]|[\u{1F22F}]|[\u{1F232}-\u{1F236}]|[\u{1F238}-\u{1F23A}]|[\u{1F250}-\u{1F251}]|[\u{25A0}-\u{25FF}]|[\u{2B00}-\u{2BFF}]|[\u{1F004}]|[\u{1F200}]

# Simple version for common emojis
[😀-🙏]|[🌀-🏿]|[☀-⛿]|[✀-➿]|[🚀-🛿]|[🏀-🏿]|[🐀-🙏]|[🌍-🌿]|[🍀-🍿]|[🎀-🏿]|[🐀-🙏]

# Remove common text emoticons
:\)|:\(|:D|:P|:\||:o|:O|;\)|<3|</3|:'\(|>:\(|>:O|:v|:\*|XD|xD

# Remove decorative bullets and symbols
[▶▷◀◁■□▪▫●○◆◇★☆✓✗✔✘]
```

### Cleaning Commands

```bash
# Remove emojis from a file (backup first)
sed -i.bak 's/[😀-🙏🌀-🏿☀-⛿✀-➿🚀-🛿]//g' filename.md

# Or use Python for better Unicode support
python -c "import re; text = open('file.md').read(); clean = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000026FF\U00002700-\U000027BF]', '', text); open('file.md', 'w').write(clean)"
```

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