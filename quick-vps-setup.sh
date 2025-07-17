#!/bin/bash
# Quick VPS setup script for Weight What
# Run this after SSHing into your fresh Ubuntu server

set -e

echo "Weight What Quick VPS Setup"
echo "=============================="

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install requirements
echo "Installing Python, Nginx, and Git..."
apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Clone repository
echo "Cloning repository..."
cd /opt
if [ -d "WeightWhat" ]; then
    echo "Repository already exists, pulling latest..."
    cd WeightWhat
    git pull
else
    git clone https://github.com/dragoonbuster/WeightWhat.git
    cd WeightWhat
fi

# Setup Python environment
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn python-dotenv openai gunicorn httpx anthropic

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    
    # Update for production
    sed -i 's/SIZECOMPARATOR_ENV=development/SIZECOMPARATOR_ENV=production/' .env
    sed -i 's/SIZECOMPARATOR_DEBUG=true/SIZECOMPARATOR_DEBUG=false/' .env
    sed -i 's|SIZECOMPARATOR_CORS_ORIGINS=.*|SIZECOMPARATOR_CORS_ORIGINS=https://weightwhat.xyz,https://www.weightwhat.xyz|' .env
    
    echo ""
    echo "IMPORTANT: Edit /opt/WeightWhat/.env to add your API key(s)!"
    echo "   You can use OpenAI, Anthropic, or X.AI - just add at least one."
    echo ""
fi

# Create systemd service
echo "Creating systemd service..."
cat > /etc/systemd/system/weightwhat.service << 'EOF'
[Unit]
Description=Weight What Application
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/opt/WeightWhat
Environment="PATH=/opt/WeightWhat/venv/bin"
ExecStart=/opt/WeightWhat/venv/bin/gunicorn src.api.unified_app:create_unified_app \
    --factory \
    --bind 127.0.0.1:8000 \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 30

Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
systemctl daemon-reload
systemctl enable weightwhat
systemctl start weightwhat

# Setup Nginx
echo "Configuring Nginx..."
cat > /etc/nginx/sites-available/weightwhat << 'EOF'
server {
    listen 80;
    server_name weightwhat.xyz www.weightwhat.xyz;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/weightwhat /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit /opt/WeightWhat/.env to add your OpenAI API key"
echo "2. Point weightwhat.xyz to this server's IP in Namecheap"
echo "3. Run: certbot --nginx -d weightwhat.xyz -d www.weightwhat.xyz"
echo ""
echo "Useful commands:"
echo "- Check status: systemctl status weightwhat"
echo "- View logs: journalctl -u weightwhat -f"
echo "- Restart: systemctl restart weightwhat"
echo ""

# Show current status
echo "Current status:"
systemctl status weightwhat --no-pager

# Test if it's working
echo ""
echo "Testing API..."
curl -s http://localhost:8000/health | python3 -m json.tool || echo "API not responding yet, check your .env file"