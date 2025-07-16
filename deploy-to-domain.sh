#!/bin/bash
# Quick deploy to weightwhat.xyz using Netlify

echo "🚀 Deploying Weight, What? to weightwhat.xyz"
echo "==========================================="

# Check if netlify CLI is installed
if ! command -v netlify &> /dev/null; then
    echo "Installing Netlify CLI..."
    npm install -g netlify-cli
fi

# Deploy to Netlify
echo "Deploying to Netlify..."
cd frontend
netlify deploy --prod --dir . --site weightwhat

echo ""
echo "✅ Deployed to Netlify!"
echo ""
echo "Now set up your domain:"
echo "1. Go to Netlify dashboard"
echo "2. Add custom domain: weightwhat.xyz"
echo "3. In Namecheap, add these DNS records:"
echo "   Type: A      Name: @     Value: 75.2.60.5"
echo "   Type: CNAME  Name: www   Value: [your-site].netlify.app"
echo ""
echo "Your site will be live at https://weightwhat.xyz in ~10 minutes!"