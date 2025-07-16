# SizeComparator Deployment Checklist

## Pre-Deployment Requirements

### 1. Environment Configuration ⚠️ REQUIRED
- [ ] Copy `.env.example` to `.env`
- [ ] Set `SIZECOMPARATOR_ENV=production`
- [ ] Change `SIZECOMPARATOR_SECRET_KEY` from default value
- [ ] Add at least one AI provider API key:
  - [ ] `SIZECOMPARATOR_OPENAI_API_KEY`
  - [ ] `SIZECOMPARATOR_ANTHROPIC_API_KEY`
  - [ ] `SIZECOMPARATOR_XAI_API_KEY`
- [ ] Set production CORS origins: `SIZECOMPARATOR_CORS_ORIGINS=https://yourdomain.com`
- [ ] Review and adjust cost limits:
  - [ ] `SIZECOMPARATOR_DAILY_API_COST_LIMIT`
  - [ ] `SIZECOMPARATOR_MONTHLY_API_COST_LIMIT`

### 2. Generate Fallback Repository 📦 RECOMMENDED
```bash
# Generate comprehensive fallback responses
python generate_fallback_repository.py
```
This ensures quality responses even when AI providers are unavailable.

### 3. Docker Production Build 🐳 REQUIRED
```bash
# Build production image
docker build -t sizecomparator:latest .

# Or use docker-compose
docker-compose build sizecomparator
```

### 4. Test Production Configuration 🧪 REQUIRED
```bash
# Start services
docker-compose up -d sizecomparator redis

# Check health
curl http://localhost:8000/health

# Test API endpoints
curl -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "5 kg", "style": "default"}'

# Check metrics
curl http://localhost:8000/api/status
```

### 5. Performance Optimization 🚀 RECOMMENDED
- [ ] Enable Redis caching (already in docker-compose)
- [ ] Add gunicorn to requirements.txt for production:
  ```
  gunicorn==21.2.0
  ```
- [ ] Configure reverse proxy (nginx/caddy) for:
  - [ ] SSL/TLS termination
  - [ ] Request/response compression
  - [ ] Static file serving
  - [ ] Rate limiting

### 6. Monitoring Setup 📊 RECOMMENDED
```bash
# Deploy with monitoring stack
docker-compose --profile monitoring up -d

# Access monitoring:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
```

### 7. Security Hardening 🔒 REQUIRED
- [ ] Ensure all secrets are set via environment variables
- [ ] Verify no sensitive data in logs
- [ ] Set up firewall rules
- [ ] Configure rate limiting at reverse proxy
- [ ] Review CORS configuration
- [ ] Enable HTTPS/TLS

### 8. Domain and Hosting Setup 🌐 REQUIRED
- [ ] Choose hosting provider (AWS, GCP, Azure, DigitalOcean, etc.)
- [ ] Set up domain/subdomain
- [ ] Configure DNS records
- [ ] Set up SSL certificates (Let's Encrypt recommended)
- [ ] Configure reverse proxy

## Deployment Commands

### Option 1: Docker Compose (Recommended)
```bash
# Production deployment
docker-compose up -d sizecomparator redis

# With monitoring
docker-compose --profile monitoring up -d

# View logs
docker-compose logs -f sizecomparator

# Scale if needed
docker-compose up -d --scale sizecomparator=3
```

### Option 2: Direct Docker
```bash
# Run with environment file
docker run -d \
  --name sizecomparator \
  --env-file .env \
  -p 8000:8000 \
  --restart unless-stopped \
  sizecomparator:latest
```

### Option 3: Cloud Platform Specific
```bash
# AWS ECS, Google Cloud Run, Azure Container Instances
# See platform-specific documentation
```

## Post-Deployment Verification

### 1. Health Checks
```bash
# Basic health
curl https://yourdomain.com/health

# Detailed status
curl https://yourdomain.com/api/status

# Test all service modes
for mode in basic fast_validation full_validation comprehensive; do
  echo "Testing $mode..."
  curl -X POST https://yourdomain.com/api/compare?service_mode=$mode \
    -H "Content-Type: application/json" \
    -d '{"weight_input": "10 kg", "style": "default"}'
done
```

### 2. Monitor Logs
```bash
# Application logs
docker-compose logs -f sizecomparator

# Error monitoring
docker-compose logs sizecomparator | grep ERROR
```

### 3. Performance Testing
```bash
# Basic load test
ab -n 1000 -c 10 -p test_payload.json -T application/json \
  https://yourdomain.com/api/compare
```

## Maintenance Tasks

### Daily
- [ ] Check application health endpoint
- [ ] Review error logs
- [ ] Monitor API costs

### Weekly
- [ ] Review performance metrics
- [ ] Check disk usage
- [ ] Update fallback repository if needed

### Monthly
- [ ] Security updates
- [ ] Dependency updates
- [ ] Cost analysis
- [ ] Performance optimization review

## Rollback Plan

If issues occur:
```bash
# Stop current deployment
docker-compose down

# Restore previous version
docker-compose pull sizecomparator:previous-tag
docker-compose up -d

# Or restore from backup
git checkout previous-commit
docker-compose build && docker-compose up -d
```

## Support Resources

- API Documentation: `/docs` (if enabled)
- Health Check: `/health`
- Metrics: `/api/status`
- Logs: `docker-compose logs`

## Final Notes

1. Always test in staging environment first
2. Keep backups of `.env` file securely
3. Monitor costs daily initially
4. Set up alerts for errors and high latency
5. Document any custom configurations