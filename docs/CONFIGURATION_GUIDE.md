# SizeComparator Configuration Guide

**Version**: 1.0.0  
**Last Updated**: 2025-07-14

## Overview

SizeComparator uses a simplified environment variable-based configuration system that provides all necessary settings for development and production deployment.

## Configuration System

### SimpleConfig Architecture
- **Environment Variables**: Primary configuration source
- **Secure Handling**: Sensitive data (API keys) properly masked
- **Type Validation**: Automatic type conversion and validation
- **Environment Awareness**: Different defaults for development vs production

### Configuration Files
- **Primary**: Environment variables (`SIZECOMPARATOR_*`)
- **Local Override**: `.env` file (git-ignored)
- **Example**: `.env.example` (template for setup)

## Environment Variables

### Core Application Settings

#### SIZECOMPARATOR_ENV
- **Type**: String (enum)
- **Values**: `development`, `staging`, `production`
- **Default**: `development`
- **Description**: Runtime environment
- **Example**: `SIZECOMPARATOR_ENV=production`

#### SIZECOMPARATOR_DEBUG
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable debug mode with verbose logging
- **Example**: `SIZECOMPARATOR_DEBUG=true`

#### SIZECOMPARATOR_LOG_LEVEL
- **Type**: String (enum)
- **Values**: `debug`, `info`, `warn`, `error`
- **Default**: `info`
- **Description**: Application logging level
- **Example**: `SIZECOMPARATOR_LOG_LEVEL=debug`

### API Server Settings

#### SIZECOMPARATOR_API_HOST
- **Type**: String
- **Default**: `0.0.0.0`
- **Description**: Server host address
- **Example**: `SIZECOMPARATOR_API_HOST=127.0.0.1`

#### SIZECOMPARATOR_API_PORT
- **Type**: Integer
- **Default**: `8000`
- **Description**: Server port number
- **Example**: `SIZECOMPARATOR_API_PORT=8080`

#### SIZECOMPARATOR_API_WORKERS
- **Type**: Integer
- **Default**: `1`
- **Description**: Number of worker processes
- **Example**: `SIZECOMPARATOR_API_WORKERS=4`

### AI Provider Configuration

#### OpenAI Provider

##### SIZECOMPARATOR_OPENAI_API_KEY
- **Type**: String
- **Required**: Optional (but recommended)
- **Description**: OpenAI API key for GPT-4 integration
- **Example**: `SIZECOMPARATOR_OPENAI_API_KEY=sk-...`
- **Security**: Masked in logs and responses

##### SIZECOMPARATOR_OPENAI_MODEL
- **Type**: String
- **Default**: `gpt-4`
- **Description**: OpenAI model to use
- **Example**: `SIZECOMPARATOR_OPENAI_MODEL=gpt-4-turbo`

##### SIZECOMPARATOR_OPENAI_TIMEOUT
- **Type**: Integer
- **Default**: `30`
- **Description**: OpenAI API timeout in seconds
- **Example**: `SIZECOMPARATOR_OPENAI_TIMEOUT=45`

##### SIZECOMPARATOR_OPENAI_MAX_TOKENS
- **Type**: Integer
- **Default**: `500`
- **Description**: Maximum tokens for OpenAI responses
- **Example**: `SIZECOMPARATOR_OPENAI_MAX_TOKENS=750`

##### SIZECOMPARATOR_OPENAI_TEMPERATURE
- **Type**: Float
- **Default**: `0.3`
- **Description**: OpenAI temperature setting
- **Example**: `SIZECOMPARATOR_OPENAI_TEMPERATURE=0.7`

#### Anthropic Provider

##### SIZECOMPARATOR_ANTHROPIC_API_KEY
- **Type**: String
- **Required**: Optional
- **Description**: Anthropic API key for Claude integration
- **Example**: `SIZECOMPARATOR_ANTHROPIC_API_KEY=sk-ant-...`
- **Security**: Masked in logs and responses

##### SIZECOMPARATOR_ANTHROPIC_MODEL
- **Type**: String
- **Default**: `claude-3-sonnet-20240229`
- **Description**: Anthropic model to use
- **Example**: `SIZECOMPARATOR_ANTHROPIC_MODEL=claude-3-opus-20240229`

##### SIZECOMPARATOR_ANTHROPIC_TIMEOUT
- **Type**: Integer
- **Default**: `60`
- **Description**: Anthropic API timeout in seconds
- **Example**: `SIZECOMPARATOR_ANTHROPIC_TIMEOUT=90`

##### SIZECOMPARATOR_ANTHROPIC_MAX_TOKENS
- **Type**: Integer
- **Default**: `1000`
- **Description**: Maximum tokens for Anthropic responses
- **Example**: `SIZECOMPARATOR_ANTHROPIC_MAX_TOKENS=1500`

##### SIZECOMPARATOR_ANTHROPIC_TEMPERATURE
- **Type**: Float
- **Default**: `0.0`
- **Description**: Anthropic temperature setting
- **Example**: `SIZECOMPARATOR_ANTHROPIC_TEMPERATURE=0.5`

#### X.ai Provider

##### SIZECOMPARATOR_XAI_API_KEY
- **Type**: String
- **Required**: Optional
- **Description**: X.ai API key for Grok integration
- **Example**: `SIZECOMPARATOR_XAI_API_KEY=xai-...`
- **Security**: Masked in logs and responses

##### SIZECOMPARATOR_XAI_MODEL
- **Type**: String
- **Default**: `grok-beta`
- **Description**: X.ai model to use
- **Example**: `SIZECOMPARATOR_XAI_MODEL=grok-1`

##### SIZECOMPARATOR_XAI_TIMEOUT
- **Type**: Integer
- **Default**: `45`
- **Description**: X.ai API timeout in seconds
- **Example**: `SIZECOMPARATOR_XAI_TIMEOUT=60`

### Cache Configuration

#### SIZECOMPARATOR_CACHE_PROVIDER
- **Type**: String (enum)
- **Values**: `memory`, `redis`
- **Default**: `memory`
- **Description**: Cache provider to use
- **Example**: `SIZECOMPARATOR_CACHE_PROVIDER=redis`

#### SIZECOMPARATOR_CACHE_TTL
- **Type**: Integer
- **Default**: `3600`
- **Description**: Cache time-to-live in seconds
- **Example**: `SIZECOMPARATOR_CACHE_TTL=7200`

#### SIZECOMPARATOR_CACHE_MAX_SIZE
- **Type**: Integer
- **Default**: `1000`
- **Description**: Maximum cache size (for memory cache)
- **Example**: `SIZECOMPARATOR_CACHE_MAX_SIZE=5000`

### Redis Configuration (if using Redis cache)

#### SIZECOMPARATOR_REDIS_HOST
- **Type**: String
- **Default**: `localhost`
- **Description**: Redis server hostname
- **Example**: `SIZECOMPARATOR_REDIS_HOST=redis.example.com`

#### SIZECOMPARATOR_REDIS_PORT
- **Type**: Integer
- **Default**: `6379`
- **Description**: Redis server port
- **Example**: `SIZECOMPARATOR_REDIS_PORT=6380`

#### SIZECOMPARATOR_REDIS_DB
- **Type**: Integer
- **Default**: `0`
- **Description**: Redis database number
- **Example**: `SIZECOMPARATOR_REDIS_DB=1`

#### SIZECOMPARATOR_REDIS_PASSWORD
- **Type**: String
- **Required**: Optional
- **Description**: Redis authentication password
- **Example**: `SIZECOMPARATOR_REDIS_PASSWORD=secure_password`
- **Security**: Masked in logs and responses

#### SIZECOMPARATOR_REDIS_TLS
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable TLS for Redis connection
- **Example**: `SIZECOMPARATOR_REDIS_TLS=true`

### Service Factory Configuration

#### SIZECOMPARATOR_SERVICE_STRATEGY
- **Type**: String (enum)
- **Values**: `smart_routing`, `performance_first`, `accuracy_first`, `basic_only`
- **Default**: `smart_routing`
- **Description**: Service selection strategy
- **Example**: `SIZECOMPARATOR_SERVICE_STRATEGY=performance_first`

#### SIZECOMPARATOR_FORCE_BASIC_SERVICE
- **Type**: Boolean
- **Default**: `false`
- **Description**: Force use of basic service only (for testing)
- **Example**: `SIZECOMPARATOR_FORCE_BASIC_SERVICE=true`

#### SIZECOMPARATOR_REQUIRE_VALIDATION
- **Type**: Boolean
- **Default**: `true`
- **Description**: Require validation services in production
- **Example**: `SIZECOMPARATOR_REQUIRE_VALIDATION=false`

#### SIZECOMPARATOR_SERVICE_TIMEOUT_MS
- **Type**: Integer
- **Default**: `5000`
- **Description**: Default timeout for service operations in milliseconds
- **Example**: `SIZECOMPARATOR_SERVICE_TIMEOUT_MS=10000`

### Security Configuration

#### SIZECOMPARATOR_SECRET_KEY
- **Type**: String
- **Required**: Yes (in production)
- **Description**: Application secret key for encryption and signing
- **Example**: `SIZECOMPARATOR_SECRET_KEY=your-super-secret-key-here`
- **Security**: Masked in logs and responses
- **Note**: Must be changed from default in production

### Feature Flags

#### SIZECOMPARATOR_FEATURE_ENHANCED_VIZ
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable enhanced visualization features
- **Example**: `SIZECOMPARATOR_FEATURE_ENHANCED_VIZ=false`

#### SIZECOMPARATOR_FEATURE_AI_SUGGESTIONS
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable AI-powered suggestions feature
- **Example**: `SIZECOMPARATOR_FEATURE_AI_SUGGESTIONS=true`

### Monitoring and Metrics

#### SIZECOMPARATOR_METRICS_ENABLED
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable metrics collection and exposure
- **Example**: `SIZECOMPARATOR_METRICS_ENABLED=false`

#### SIZECOMPARATOR_LOG_FORMAT
- **Type**: String (enum)
- **Values**: `json`, `text`
- **Default**: `json`
- **Description**: Log output format
- **Example**: `SIZECOMPARATOR_LOG_FORMAT=text`

## Configuration Examples

### Development Environment (.env file)
```bash
# Environment
SIZECOMPARATOR_ENV=development
SIZECOMPARATOR_DEBUG=true
SIZECOMPARATOR_LOG_LEVEL=debug

# API Server
SIZECOMPARATOR_API_HOST=127.0.0.1
SIZECOMPARATOR_API_PORT=8000

# AI Providers (at least one required)
SIZECOMPARATOR_OPENAI_API_KEY=sk-your-openai-key-here
SIZECOMPARATOR_ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Cache
SIZECOMPARATOR_CACHE_PROVIDER=memory
SIZECOMPARATOR_CACHE_TTL=1800

# Service Factory
SIZECOMPARATOR_SERVICE_STRATEGY=smart_routing
SIZECOMPARATOR_FORCE_BASIC_SERVICE=false

# Security
SIZECOMPARATOR_SECRET_KEY=dev-secret-key-change-in-production

# Features
SIZECOMPARATOR_FEATURE_ENHANCED_VIZ=true
SIZECOMPARATOR_FEATURE_AI_SUGGESTIONS=false
```

### Production Environment
```bash
# Environment
SIZECOMPARATOR_ENV=production
SIZECOMPARATOR_DEBUG=false
SIZECOMPARATOR_LOG_LEVEL=info

# API Server
SIZECOMPARATOR_API_HOST=0.0.0.0
SIZECOMPARATOR_API_PORT=8000
SIZECOMPARATOR_API_WORKERS=4

# AI Providers
SIZECOMPARATOR_OPENAI_API_KEY=sk-prod-openai-key-here
SIZECOMPARATOR_ANTHROPIC_API_KEY=sk-ant-prod-anthropic-key-here

# Cache (Redis for production)
SIZECOMPARATOR_CACHE_PROVIDER=redis
SIZECOMPARATOR_CACHE_TTL=3600
SIZECOMPARATOR_REDIS_HOST=redis.yourdomain.com
SIZECOMPARATOR_REDIS_PORT=6379
SIZECOMPARATOR_REDIS_TLS=true
SIZECOMPARATOR_REDIS_PASSWORD=secure-redis-password

# Service Factory
SIZECOMPARATOR_SERVICE_STRATEGY=smart_routing
SIZECOMPARATOR_REQUIRE_VALIDATION=true
SIZECOMPARATOR_SERVICE_TIMEOUT_MS=5000

# Security
SIZECOMPARATOR_SECRET_KEY=your-production-secret-key-32-chars-min

# Features
SIZECOMPARATOR_FEATURE_ENHANCED_VIZ=true
SIZECOMPARATOR_FEATURE_AI_SUGGESTIONS=true

# Monitoring
SIZECOMPARATOR_METRICS_ENABLED=true
SIZECOMPARATOR_LOG_FORMAT=json
```

### Docker Environment
```bash
# For Docker deployments
SIZECOMPARATOR_ENV=production
SIZECOMPARATOR_API_HOST=0.0.0.0
SIZECOMPARATOR_API_PORT=8000

# AI Providers via Docker secrets
SIZECOMPARATOR_OPENAI_API_KEY_FILE=/run/secrets/openai_api_key
SIZECOMPARATOR_ANTHROPIC_API_KEY_FILE=/run/secrets/anthropic_api_key

# Redis service
SIZECOMPARATOR_CACHE_PROVIDER=redis
SIZECOMPARATOR_REDIS_HOST=redis-service
SIZECOMPARATOR_REDIS_PORT=6379
```

## Configuration Validation

### Automatic Validation
The system automatically validates configuration on startup:
- Type checking for all variables
- Required variable presence
- Value range validation
- Pattern matching for API keys
- Environment-specific requirements

### Validation Errors
Common validation errors and solutions:

#### Missing AI Provider Keys
```
ValidationError: At least one AI provider API key must be configured
```
**Solution**: Set at least one of the AI provider API keys

#### Invalid Secret Key in Production
```
ValidationError: SIZECOMPARATOR_SECRET_KEY must be changed in production
```
**Solution**: Set a unique, secure secret key for production

#### Invalid Environment Value
```
ValidationError: Invalid environment value 'prod', expected one of: development, staging, production
```
**Solution**: Use exact values: `development`, `staging`, or `production`

### Configuration Testing
Test your configuration:
```bash
# Test configuration loading
python -c "from src.core.simple_config import get_config; print(get_config().get_all())"

# Test service factory with current config
python test_service_factory.py

# Test unified app startup
python run_unified_server.py
```

## Best Practices

### Development
1. **Use .env file**: Create `.env` file for local development
2. **Start simple**: Begin with just OpenAI API key
3. **Enable debug**: Set `SIZECOMPARATOR_DEBUG=true`
4. **Use memory cache**: Keep `SIZECOMPARATOR_CACHE_PROVIDER=memory`

### Production
1. **Secure secrets**: Use proper secret management for API keys
2. **Enable Redis**: Set `SIZECOMPARATOR_CACHE_PROVIDER=redis`
3. **Monitor logs**: Set `SIZECOMPARATOR_LOG_FORMAT=json`
4. **Scale workers**: Set `SIZECOMPARATOR_API_WORKERS=4` or higher

### Security
1. **Unique secret key**: Always change `SIZECOMPARATOR_SECRET_KEY` in production
2. **Secure API keys**: Never commit API keys to version control
3. **Use TLS**: Enable `SIZECOMPARATOR_REDIS_TLS=true` for Redis
4. **Mask sensitive data**: All sensitive values are automatically masked in logs

### Performance
1. **Tune timeouts**: Adjust `SIZECOMPARATOR_*_TIMEOUT` values based on needs
2. **Cache configuration**: Set appropriate `SIZECOMPARATOR_CACHE_TTL`
3. **Service strategy**: Use `smart_routing` for optimal performance
4. **Worker scaling**: Scale `SIZECOMPARATOR_API_WORKERS` based on load

## Troubleshooting

### Common Issues

#### Service Won't Start
1. Check all required environment variables are set
2. Verify API keys are valid and not expired
3. Check port availability
4. Review startup logs for specific errors

#### AI Providers Not Available
1. Verify API keys are correctly set
2. Check internet connectivity
3. Verify API key permissions and quotas
4. Test with basic service mode first

#### Cache Issues
1. For Redis: Check Redis server connectivity
2. Verify Redis credentials and TLS settings
3. Check Redis server logs
4. Fallback to memory cache for testing

#### Performance Issues
1. Increase timeout values
2. Reduce max tokens for faster responses
3. Use fast validation service mode
4. Enable caching with appropriate TTL

### Getting Help

1. **Check logs**: Enable debug logging for detailed information
2. **Test components**: Use individual test scripts
3. **Validate config**: Check configuration validation output
4. **Use basic mode**: Test with basic service to isolate issues
5. **Check service status**: Use `/api/status` endpoint for service health