# Multi-stage build for SizeComparator
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Labels for metadata
LABEL maintainer="Chris Jones <jones.chris7@gmail.com>" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="sizecomparator" \
      org.label-schema.description="AI-powered weight comparison service" \
      org.label-schema.version=$VERSION \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.schema-version="1.0"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -g 1001 sizecomparator && \
    useradd -r -u 1001 -g sizecomparator sizecomparator

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to app user
RUN chown -R sizecomparator:sizecomparator /app

# Switch to non-root user
USER sizecomparator

# Create directories for logs and data
RUN mkdir -p logs data

# Expose ports
EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "run_unified_server.py"]