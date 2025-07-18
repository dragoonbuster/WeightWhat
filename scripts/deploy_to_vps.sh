#!/bin/bash
# Deploy script for WeightWhat to DigitalOcean VPS
# Handles git pull, dependency updates, and counter setup

set -e

echo "Starting WeightWhat deployment..."

# Change to project directory
cd ~/WeightWhat || cd ~/projects/SizeComparator || { echo "Project directory not found!"; exit 1; }

# Pull latest changes from GitHub
echo "Pulling latest changes from GitHub..."
git pull origin main

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run counter setup
echo "Setting up counter storage..."
if [ -f "scripts/setup_counter_vps.sh" ]; then
    bash scripts/setup_counter_vps.sh
else
    echo "Counter setup script not found, skipping..."
fi

# Restart the service
echo "Restarting WeightWhat service..."
sudo systemctl restart weightwhat || {
    echo "Failed to restart service, trying supervisor..."
    sudo supervisorctl restart weightwhat || {
        echo "Manual restart required - service manager not found"
    }
}

# Check service status
echo ""
echo "Checking service status..."
sudo systemctl status weightwhat --no-pager || sudo supervisorctl status weightwhat

# Display current counter value
echo ""
echo "Current counter status:"
for path in "/var/lib/weightwhat/counter.json" "/opt/WeightWhat/data/counter.json" "$HOME/.weightwhat/counter.json"; do
    if [ -f "$path" ]; then
        echo "Counter at $path:"
        cat "$path" | jq . 2>/dev/null || cat "$path"
        break
    fi
done

echo ""
echo "Deployment complete!"
echo "Site should be available at: https://weightwhat.xyz"