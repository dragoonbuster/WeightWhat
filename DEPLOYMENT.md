# Deploying Weight, What?

A simple guide for deploying your weight comparison gag site.

## Option 1: Free Static Hosting (No AI)

The simplest option - just funny pre-written comparisons.

### GitHub Pages (Recommended)
```bash
1. Push to GitHub
2. Settings → Pages → Source: main branch, /frontend folder
3. Your site: https://username.github.io/WeightWhat/simple.html
```

### Netlify Drop
1. Go to [app.netlify.com/drop](https://app.netlify.com/drop)
2. Drag the `frontend` folder
3. Done!

### Custom Domain Setup
In Namecheap, add:
- **A Record:** @ → 75.2.60.5 (Netlify)
- **CNAME:** www → yoursite.netlify.app

## Option 2: Simple VPS with AI ($6/month)

Get real AI responses with your API keys kept secret.

### Quick Setup
```bash
# 1. Get a $6/month VPS (DigitalOcean, Vultr, Linode)
# 2. SSH in and run:
wget https://raw.githubusercontent.com/dragoonbuster/WeightWhat/main/quick-vps-setup.sh
chmod +x quick-vps-setup.sh
./quick-vps-setup.sh

# 3. Edit /opt/WeightWhat/.env and add your API key(s)
# 4. Point weightwhat.xyz to your server IP in Namecheap
# 5. Get SSL: certbot --nginx -d weightwhat.xyz -d www.weightwhat.xyz
```

### What You Get
- Real AI responses
- Your custom domain with SSL
- Handles plenty of traffic
- ~30 minute setup

## Which Should I Choose?

- **Just want it online fast?** → Static hosting (Option 1)
- **Want real AI responses?** → Simple VPS (Option 2)
- **Budget conscious?** → Static is free forever
- **Want the full experience?** → VPS for $6/month

## Management Commands (VPS only)

```bash
# Check status
systemctl status weightwhat

# View logs
journalctl -u weightwhat -f

# Update code
cd /opt/WeightWhat && git pull && systemctl restart weightwhat
```

That's it! No Docker, no complexity, just a fun site that works.