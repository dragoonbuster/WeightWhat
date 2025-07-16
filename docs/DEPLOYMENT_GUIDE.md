# SizeComparator Deployment Guide

Complete guide for deploying SizeComparator to production with weightwhat.xyz domain.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Domain Configuration](#domain-configuration)
4. [Application Deployment](#application-deployment)
5. [SSL Certificate Setup](#ssl-certificate-setup)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Cost Management](#cost-management)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Services
- **VPS/Cloud Server**: 2GB RAM, 2 CPU cores, 20GB storage minimum
- **Domain**: weightwhat.xyz (already purchased)
- **AI Provider API Keys**: OpenAI, Anthropic, or X.ai accounts
- **Email**: For SSL certificates and cost alerts

### Recommended Hosting Providers
1. **DigitalOcean** ($10-20/month)
   - Easy setup, good documentation
   - Pre-configured Docker images
   - Built-in monitoring
   
2. **AWS Lightsail** ($10-20/month)
   - Integration with AWS services
   - Automatic scaling options
   - Load balancer support
   
3. **Linode** ($10-20/month)
   - Excellent performance
   - Simple pricing
   - Good customer support

4. **Vultr** ($6-12/month)
   - Budget-friendly option
   - Good performance
   - Multiple data centers

## Server Setup

### 1. Initial Server Configuration

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y curl wget git nginx certbot python3-certbot-nginx

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login to apply docker group changes
exit
```

### 2. Setup Application Directory

```bash
# Create application directory
sudo mkdir -p /opt/sizecomparator
sudo chown -R $USER:$USER /opt/sizecomparator
cd /opt/sizecomparator

# Clone repository
git clone https://github.com/your-username/SizeComparator.git app
cd app

# Copy environment configuration
cp .env.production .env

# Edit environment variables
nano .env
```

### 3. Configure Environment Variables

Edit `.env` file with your production values:

```bash
# Environment
SIZECOMPARATOR_ENV=production
SIZECOMPARATOR_DEBUG=false

# API Keys (REQUIRED)
SIZECOMPARATOR_OPENAI_API_KEY=sk-your-actual-openai-key
SIZECOMPARATOR_ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key
SIZECOMPARATOR_XAI_API_KEY=xai-your-actual-xai-key

# Security (REQUIRED)
SIZECOMPARATOR_SECRET_KEY=your-random-32-character-secret-key

# Cost Management (IMPORTANT)
SIZECOMPARATOR_DAILY_COST_LIMIT=25.0
SIZECOMPARATOR_MONTHLY_COST_LIMIT=500.0
SIZECOMPARATOR_COST_ALERT_EMAIL=admin@weightwhat.xyz

# Redis (for production caching)
SIZECOMPARATOR_REDIS_HOST=redis
SIZECOMPARATOR_REDIS_PORT=6379
```

## Domain Configuration

### 1. DNS Settings

Configure your domain (weightwhat.xyz) DNS records:

```
Type    Name    Value                   TTL
A       @       YOUR_SERVER_IP         300
A       www     YOUR_SERVER_IP         300
CNAME   api     weightwhat.xyz         300
```

### 2. Verify DNS Propagation

```bash
# Check DNS propagation
dig weightwhat.xyz
dig www.weightwhat.xyz

# Should return your server IP
```

## Application Deployment

### 1. Automated Deployment

Use the provided deployment script:

```bash
# Full deployment with SSL, monitoring, and nginx
./deploy.sh --full
```

### 2. Manual Deployment

If you prefer manual deployment:

```bash
# Build and start services
docker-compose build
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f sizecomparator
```

### 3. Verify Deployment

```bash
# Test local application
curl http://localhost:8000/health

# Test API endpoint
curl -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "5 kg"}'
```

## SSL Certificate Setup

### 1. Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx
```

### 2. Generate SSL Certificate

```bash
sudo certbot --nginx -d weightwhat.xyz -d www.weightwhat.xyz
```

### 3. Auto-renewal Setup

```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab
sudo crontab -e
```

Add this line to crontab:
```
0 12 * * * /usr/bin/certbot renew --quiet
```

## Monitoring and Maintenance

### 1. Application Monitoring

```bash
# Start monitoring stack
docker-compose --profile monitoring up -d

# Access Grafana
# http://YOUR_SERVER_IP:3000
# Username: admin, Password: admin
```

### 2. Log Monitoring

```bash
# View application logs
docker-compose logs -f sizecomparator

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 3. Cost Monitoring

```bash
# Check cost tracking file
cat cost_tracking.json

# Monitor daily costs
curl http://localhost:8000/api/status | jq '.cost_summary'
```

### 4. Performance Monitoring

```bash
# Check container stats
docker stats

# Monitor system resources
htop
df -h
```

## Cost Management

### 1. Setting Up Cost Alerts

Configure cost alerts in your environment:

```bash
# Set alert thresholds
SIZECOMPARATOR_DAILY_COST_LIMIT=25.0
SIZECOMPARATOR_MONTHLY_COST_LIMIT=500.0
SIZECOMPARATOR_COST_ALERT_THRESHOLD=0.8
SIZECOMPARATOR_COST_ALERT_EMAIL=admin@weightwhat.xyz
```

### 2. Cost Optimization Settings

```bash
# Optimize for cost
SIZECOMPARATOR_SERVICE_STRATEGY=cost_optimized
SIZECOMPARATOR_MAX_PARALLEL_CALLS=1
SIZECOMPARATOR_OPENAI_MODEL=gpt-4o-mini
SIZECOMPARATOR_ANTHROPIC_MODEL=claude-3-haiku-20240307
```

### 3. Rate Limiting

```bash
# Set conservative rate limits
SIZECOMPARATOR_RATE_LIMIT_PER_MINUTE=60
SIZECOMPARATOR_RATE_LIMIT_PER_HOUR=1000
```

## Nginx Configuration

### 1. Custom Nginx Configuration

Create `/etc/nginx/sites-available/weightwhat.xyz`:

```nginx
server {
    listen 80;
    server_name weightwhat.xyz www.weightwhat.xyz;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name weightwhat.xyz www.weightwhat.xyz;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/weightwhat.xyz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/weightwhat.xyz/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

### 2. Enable Configuration

```bash
sudo ln -s /etc/nginx/sites-available/weightwhat.xyz /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Backup and Recovery

### 1. Automated Backups

```bash
# Create backup script
cat > /opt/sizecomparator/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/sizecomparator/backups"

mkdir -p $BACKUP_DIR

# Backup application
tar -czf "$BACKUP_DIR/app_$DATE.tar.gz" -C /opt/sizecomparator app

# Backup database volumes
docker run --rm -v sizecomparator_redis_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/redis_$DATE.tar.gz /data
docker run --rm -v sizecomparator_cost_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/cost_$DATE.tar.gz /data

# Keep only last 7 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /opt/sizecomparator/backup.sh

# Add to crontab
crontab -e
```

Add backup schedule:
```
0 2 * * * /opt/sizecomparator/backup.sh
```

### 2. Recovery Process

```bash
# Stop services
docker-compose down

# Restore application
tar -xzf /opt/sizecomparator/backups/app_YYYYMMDD_HHMMSS.tar.gz -C /opt/sizecomparator

# Restore volumes
docker run --rm -v sizecomparator_redis_data:/data -v /opt/sizecomparator/backups:/backup alpine tar xzf /backup/redis_YYYYMMDD_HHMMSS.tar.gz -C /

# Restart services
docker-compose up -d
```

## Security Considerations

### 1. Firewall Configuration

```bash
# Install UFW
sudo apt install ufw

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Security Updates

```bash
# Enable automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 3. SSL Security

```bash
# Test SSL configuration
https://www.ssllabs.com/ssltest/analyze.html?d=weightwhat.xyz
```

## Troubleshooting

### Common Issues

1. **Application won't start**
   ```bash
   # Check logs
   docker-compose logs sizecomparator
   
   # Check environment variables
   docker-compose exec sizecomparator env | grep SIZECOMPARATOR
   ```

2. **SSL certificate issues**
   ```bash
   # Check certificate status
   sudo certbot certificates
   
   # Renew certificate
   sudo certbot renew
   ```

3. **High API costs**
   ```bash
   # Check cost tracking
   cat cost_tracking.json
   
   # Reduce limits
   # Edit .env and reduce SIZECOMPARATOR_DAILY_COST_LIMIT
   ```

4. **Performance issues**
   ```bash
   # Check system resources
   htop
   df -h
   
   # Check container stats
   docker stats
   
   # Optimize cache settings
   # Increase SIZECOMPARATOR_CACHE_TTL
   ```

### Health Checks

```bash
# Application health
curl https://weightwhat.xyz/health

# API functionality
curl -X POST https://weightwhat.xyz/api/compare \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "5 kg"}'

# SSL certificate
curl -I https://weightwhat.xyz

# DNS resolution
dig weightwhat.xyz
```

## Post-Deployment Checklist

- [ ] DNS records point to server IP
- [ ] SSL certificate is valid and auto-renewing
- [ ] Application responds to health checks
- [ ] API endpoints function correctly
- [ ] Cost monitoring is active
- [ ] Backups are configured
- [ ] Monitoring is set up
- [ ] Firewall is configured
- [ ] Logs are being rotated
- [ ] Domain redirects work (www to non-www)

## Maintenance Schedule

### Daily
- [ ] Check application health
- [ ] Review cost tracking
- [ ] Monitor system resources

### Weekly
- [ ] Review logs for errors
- [ ] Check backup integrity
- [ ] Update AI usage statistics

### Monthly
- [ ] Update system packages
- [ ] Review cost reports
- [ ] Check SSL certificate expiration
- [ ] Clean up old log files

## Support and Resources

- **Application Status**: https://weightwhat.xyz/health
- **API Documentation**: https://weightwhat.xyz/docs
- **Monitoring**: https://weightwhat.xyz:3000 (if enabled)
- **GitHub Repository**: https://github.com/your-username/SizeComparator
- **Cost Tracking**: Review `cost_tracking.json` file

---

**Ready to deploy!** Follow this guide step by step to get weightwhat.xyz running in production.