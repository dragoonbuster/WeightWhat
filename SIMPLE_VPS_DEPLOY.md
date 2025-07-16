# Simple VPS Deployment for weightwhat.xyz

## Step 1: Get a VPS (5 minutes)

### DigitalOcean (Recommended)
1. Sign up at [digitalocean.com](https://digitalocean.com) (get $200 free credit)
2. Create a Droplet:
   - Choose Ubuntu 22.04
   - Basic Plan → Regular → $6/month (1GB RAM is plenty)
   - Choose nearest datacenter
   - Add your SSH key (or use password)
   - Create

### Alternative: Vultr, Linode, or Hetzner
All work the same, prices similar.

## Step 2: Quick Server Setup (10 minutes)

SSH into your server:
```bash
ssh root@your-server-ip
```

Run this setup script:
```bash
# Update system
apt update && apt upgrade -y

# Install Python and Git
apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Clone your repo
cd /opt
git clone https://github.com/yourusername/SizeComparator.git
cd SizeComparator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install fastapi uvicorn python-dotenv openai gunicorn

# Create .env file
cat > .env << 'EOF'
SIZECOMPARATOR_ENV=production
SIZECOMPARATOR_OPENAI_API_KEY=sk-your-key-here
SIZECOMPARATOR_SERVICE_MODE=basic
SIZECOMPARATOR_SECRET_KEY=your-random-secret-key-here
EOF

# Edit .env to add your real API key
nano .env
```

## Step 3: Simple Systemd Service (5 minutes)

Create service file:
```bash
cat > /etc/systemd/system/weightwhat.service << 'EOF'
[Unit]
Description=Weight What App
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/opt/SizeComparator
Environment="PATH=/opt/SizeComparator/venv/bin"
ExecStart=/opt/SizeComparator/venv/bin/gunicorn src.api.unified_app:create_unified_app --factory --bind 127.0.0.1:8000 --workers 2

[Install]
WantedBy=multi-user.target
EOF

# Start service
systemctl enable weightwhat
systemctl start weightwhat
```

## Step 4: Nginx Setup (5 minutes)

```bash
# Create Nginx config
cat > /etc/nginx/sites-available/weightwhat << 'EOF'
server {
    server_name weightwhat.xyz www.weightwhat.xyz;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/weightwhat /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

## Step 5: Point Domain to Server (5 minutes)

In Namecheap:
1. Domain List → Manage weightwhat.xyz
2. Advanced DNS
3. Add:
   - **A Record:** Host: `@`, Value: `your-server-ip`
   - **A Record:** Host: `www`, Value: `your-server-ip`

## Step 6: SSL Certificate (2 minutes)

```bash
# Get free SSL cert
certbot --nginx -d weightwhat.xyz -d www.weightwhat.xyz
```

## Done! 🎉

Your site is now live at https://weightwhat.xyz with:
- ✅ Real AI responses (using your OpenAI key)
- ✅ Your custom domain
- ✅ SSL certificate
- ✅ Costs just $6/month

## Super Simple Management

```bash
# View logs
journalctl -u weightwhat -f

# Restart app
systemctl restart weightwhat

# Update code
cd /opt/SizeComparator
git pull
systemctl restart weightwhat

# Check if it's running
systemctl status weightwhat
```

## Cost Breakdown
- VPS: $6/month
- Domain: ~$10/year (you already have)
- SSL: Free
- **Total: ~$7/month**

## Why This Works Well
- Simple enough to set up in 30 minutes
- Reliable (will run for months without touching)
- Your API keys stay secret on your server
- Real AI responses
- Can handle plenty of traffic for a gag site

## If Something Goes Wrong

```bash
# Check logs
journalctl -u weightwhat -n 50

# Test locally
curl http://localhost:8000/health

# Restart everything
systemctl restart weightwhat nginx
```

That's it! No Docker needed, just Python and Nginx.