#!/bin/bash
# Production startup script for SizeComparator

# Exit on error
set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check required environment variables
if [ "$SIZECOMPARATOR_ENV" != "production" ]; then
    echo "ERROR: SIZECOMPARATOR_ENV must be set to 'production'"
    exit 1
fi

if [ "$SIZECOMPARATOR_SECRET_KEY" == "dev-secret-key-change-in-production" ]; then
    echo "ERROR: SIZECOMPARATOR_SECRET_KEY must be changed from default value"
    exit 1
fi

# Check for at least one AI provider
if [ -z "$SIZECOMPARATOR_OPENAI_API_KEY" ] && [ -z "$SIZECOMPARATOR_ANTHROPIC_API_KEY" ] && [ -z "$SIZECOMPARATOR_XAI_API_KEY" ]; then
    echo "WARNING: No AI provider API keys found. Service will use fallback responses only."
fi

# Set production defaults
export WORKERS=${WORKERS:-4}
export PORT=${PORT:-8000}
export HOST=${HOST:-0.0.0.0}
export LOG_LEVEL=${LOG_LEVEL:-info}

# Start gunicorn with production settings
echo "Starting SizeComparator in production mode..."
echo "Workers: $WORKERS"
echo "Port: $PORT"
echo "Log Level: $LOG_LEVEL"

exec gunicorn src.api.unified_app:create_unified_app \
    --factory \
    --bind $HOST:$PORT \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level $LOG_LEVEL \
    --capture-output