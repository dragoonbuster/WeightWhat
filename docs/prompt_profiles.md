# Prompt Profiles Documentation

## Overview

Weight What? supports multiple prompt profiles to control the verbosity and style of AI-generated comparisons. All profiles enforce a strict NO EMOJI policy.

## Available Profiles

### 1. Verbose Profile
- **Use Case**: When you want detailed, engaging comparisons
- **Response Length**: 3-5 sentences
- **Style**: Educational, with interesting facts and context
- **Good For**: Learning environments, detailed explanations

### 2. Concise Profile (Default)
- **Use Case**: Quick, straightforward comparisons
- **Response Length**: 2-3 sentences
- **Style**: Direct and practical
- **Good For**: Most users, mobile interfaces

### 3. Ultra Concise Profile
- **Use Case**: Minimal responses
- **Response Length**: 1 sentence
- **Style**: Just the essential comparison
- **Good For**: High-volume usage, API integrations

## Configuration

Set the profile using the `SIZECOMPARATOR_PROMPT_PROFILE` environment variable:

```bash
# In .env file
SIZECOMPARATOR_PROMPT_PROFILE=concise  # Options: verbose, concise, ultra_concise
```

Or during setup:
```bash
./scripts/setup_env.sh
# Follow prompts to select profile
```

## Examples

### Verbose Profile Output
```
"A typical housecat weighing 4.5 kg is surprisingly hefty when you consider that's equivalent to carrying around 9 standard soccer balls. To put this in perspective, that's about the same weight as a small microwave oven or a well-stocked backpack for a day hike. This weight allows cats to be agile hunters while still maintaining the muscle mass needed for their impressive jumping abilities."
```

### Concise Profile Output
```
"A 4.5 kg housecat weighs about the same as 9 soccer balls or a small microwave. That's like carrying a fully loaded day backpack."
```

### Ultra Concise Profile Output
```
"A 4.5 kg cat weighs as much as 9 soccer balls."
```

## Provider-Specific Adjustments

Each AI provider (OpenAI, Anthropic, X.AI) receives slightly different instructions optimized for their models, but all maintain the same profile characteristics.

## Switching Profiles

To change profiles on a running server:

1. Update `.env` file
2. Restart the service:
   ```bash
   sudo systemctl restart weightwhat
   ```

## Development Testing

Test different profiles locally:
```bash
# Set profile for testing
export SIZECOMPARATOR_PROMPT_PROFILE=verbose
python run_unified_server.py
```

## Best Practices

1. **Production**: Use `concise` for best balance
2. **Mobile Apps**: Use `ultra_concise` to minimize bandwidth
3. **Educational**: Use `verbose` for detailed learning
4. **High Traffic**: Use `ultra_concise` to reduce API costs