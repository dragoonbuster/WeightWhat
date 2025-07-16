#!/bin/bash

# SizeComparator Production Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 SizeComparator Production Deployment${NC}"
echo "=========================================="

# Configuration
DOMAIN="weightwhat.xyz"
APP_NAME="sizecomparator"
DOCKER_IMAGE="sizecomparator:latest"
CONTAINER_NAME="sizecomparator_prod"
BACKUP_DIR="/opt/sizecomparator/backups"
LOG_DIR="/opt/sizecomparator/logs"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   warn "This script should not be run as root"
fi

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    if ! command -v nginx &> /dev/null; then
        warn "Nginx is not installed. You may need to install it for reverse proxy."
    fi
    
    log "✓ Dependencies check passed"
}

# Setup directories
setup_directories() {
    log "Setting up directories..."
    
    sudo mkdir -p "$BACKUP_DIR" "$LOG_DIR"
    sudo chown -R $(whoami):$(whoami) "$BACKUP_DIR" "$LOG_DIR"
    
    log "✓ Directories created"
}

# Backup existing deployment
backup_deployment() {
    if [ -d "/opt/sizecomparator/app" ]; then
        log "Creating backup of existing deployment..."
        
        BACKUP_NAME="sizecomparator_backup_$(date +%Y%m%d_%H%M%S)"
        sudo cp -r /opt/sizecomparator/app "$BACKUP_DIR/$BACKUP_NAME"
        
        log "✓ Backup created: $BACKUP_DIR/$BACKUP_NAME"
    fi
}

# Stop existing services
stop_services() {
    log "Stopping existing services..."
    
    if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
        log "✓ Stopped existing container"
    fi
    
    if [ "$(docker-compose ps -q)" ]; then
        docker-compose down
        log "✓ Stopped docker-compose services"
    fi
}

# Build and deploy
build_and_deploy() {
    log "Building and deploying application..."
    
    # Build the Docker image
    docker build -t $DOCKER_IMAGE .
    
    # Deploy with docker-compose
    docker-compose up -d
    
    log "✓ Application deployed"
}

# Setup SSL with Let's Encrypt
setup_ssl() {
    log "Setting up SSL certificate..."
    
    if ! command -v certbot &> /dev/null; then
        warn "Certbot not installed. Installing..."
        sudo apt-get update
        sudo apt-get install -y certbot python3-certbot-nginx
    fi
    
    # Generate SSL certificate
    sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
    
    log "✓ SSL certificate setup completed"
}

# Setup nginx reverse proxy
setup_nginx() {
    log "Setting up Nginx reverse proxy..."
    
    cat > /tmp/nginx_sizecomparator.conf << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Proxy configuration
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
    
    # Static files with caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        proxy_pass http://127.0.0.1:8000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF
    
    sudo mv /tmp/nginx_sizecomparator.conf /etc/nginx/sites-available/sizecomparator
    sudo ln -sf /etc/nginx/sites-available/sizecomparator /etc/nginx/sites-enabled/
    
    # Test nginx configuration
    sudo nginx -t
    sudo systemctl reload nginx
    
    log "✓ Nginx configuration completed"
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Wait for application to start
    sleep 10
    
    # Check if application is responding
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "✓ Application is healthy"
    else
        error "Application health check failed"
    fi
    
    # Check if SSL is working
    if curl -f https://$DOMAIN/health > /dev/null 2>&1; then
        log "✓ SSL is working"
    else
        warn "SSL health check failed"
    fi
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create systemd service for monitoring
    cat > /tmp/sizecomparator-monitor.service << EOF
[Unit]
Description=SizeComparator Monitoring
After=docker.service

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=/usr/local/bin/docker-compose up prometheus grafana
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo mv /tmp/sizecomparator-monitor.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable sizecomparator-monitor.service
    
    log "✓ Monitoring setup completed"
}

# Setup log rotation
setup_log_rotation() {
    log "Setting up log rotation..."
    
    cat > /tmp/sizecomparator-logrotate << EOF
$LOG_DIR/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 $(whoami) $(whoami)
    postrotate
        /usr/bin/docker-compose restart sizecomparator
    endscript
}
EOF
    
    sudo mv /tmp/sizecomparator-logrotate /etc/logrotate.d/sizecomparator
    
    log "✓ Log rotation setup completed"
}

# Main deployment function
main() {
    log "Starting SizeComparator deployment..."
    
    check_dependencies
    setup_directories
    backup_deployment
    stop_services
    build_and_deploy
    
    # Optional components
    if [ "$1" = "--full" ]; then
        setup_nginx
        setup_ssl
        setup_monitoring
        setup_log_rotation
    fi
    
    health_check
    
    log "🎉 Deployment completed successfully!"
    log "Application is now running at:"
    log "  - HTTP: http://$DOMAIN"
    log "  - HTTPS: https://$DOMAIN"
    log "  - Health: https://$DOMAIN/health"
    log "  - API Docs: https://$DOMAIN/docs"
    
    if [ "$1" = "--full" ]; then
        log "  - Monitoring: http://$DOMAIN:3000 (Grafana)"
    fi
}

# Run main function
main "$@"