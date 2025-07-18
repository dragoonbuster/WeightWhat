#!/bin/bash
# Setup counter storage for WeightWhat on VPS
# This script ensures proper directories and permissions for counter persistence

set -e

echo "Setting up counter storage for WeightWhat..."

# Create primary storage directory with proper permissions
if [ -w "/var/lib" ]; then
    echo "Creating /var/lib/weightwhat directory..."
    sudo mkdir -p /var/lib/weightwhat
    sudo chown $(whoami):$(whoami) /var/lib/weightwhat
    sudo chmod 755 /var/lib/weightwhat
    echo "Primary storage directory created: /var/lib/weightwhat"
else
    echo "Cannot write to /var/lib, skipping..."
fi

# Create secondary storage directory
if [ -w "/opt" ]; then
    echo "Creating /opt/WeightWhat/data directory..."
    sudo mkdir -p /opt/WeightWhat/data
    sudo chown $(whoami):$(whoami) /opt/WeightWhat/data
    sudo chmod 755 /opt/WeightWhat/data
    echo "Secondary storage directory created: /opt/WeightWhat/data"
else
    echo "Cannot write to /opt, skipping..."
fi

# Ensure user home directory fallback exists
echo "Creating user home directory fallback..."
mkdir -p ~/.weightwhat
chmod 755 ~/.weightwhat

# Migrate existing counter if it exists in old location
if [ -f "/tmp/sizecomparator_counter.json" ]; then
    echo "Found existing counter in /tmp, migrating..."
    
    # Try to copy to primary location first
    if [ -w "/var/lib/weightwhat" ]; then
        cp /tmp/sizecomparator_counter.json /var/lib/weightwhat/counter.json
        echo "Counter migrated to /var/lib/weightwhat/counter.json"
    elif [ -w "/opt/WeightWhat/data" ]; then
        cp /tmp/sizecomparator_counter.json /opt/WeightWhat/data/counter.json
        echo "Counter migrated to /opt/WeightWhat/data/counter.json"
    else
        cp /tmp/sizecomparator_counter.json ~/.weightwhat/counter.json
        echo "Counter migrated to ~/.weightwhat/counter.json"
    fi
fi

# Check if counter exists in any location
echo ""
echo "Checking for existing counter files..."
for path in "/var/lib/weightwhat/counter.json" "/opt/WeightWhat/data/counter.json" "$HOME/.weightwhat/counter.json" "/tmp/sizecomparator_counter.json"; do
    if [ -f "$path" ]; then
        echo "Found counter at: $path"
        cat "$path" | jq . 2>/dev/null || cat "$path"
    fi
done

echo ""
echo "Setup complete! The counter service will use the first available location."