#!/bin/bash
# Setup script for persistent counter storage
# This script ensures counter persists across updates

echo "Setting up persistent counter storage..."

# Function to find existing counter value
find_existing_counter() {
    local locations=(
        "/var/lib/weightwhat/counter.json"
        "/opt/WeightWhat/data/counter.json"
        "$HOME/.weightwhat/counter.json"
        "/tmp/sizecomparator_counter.json"
    )
    
    for loc in "${locations[@]}"; do
        if [ -f "$loc" ]; then
            echo "Found existing counter at: $loc"
            COUNT=$(python3 -c "import json; print(json.load(open('$loc'))['count'])" 2>/dev/null || echo "0")
            if [ "$COUNT" != "0" ]; then
                echo "Existing counter value: $COUNT"
                return 0
            fi
        fi
    done
    
    echo "No existing counter found"
    COUNT="0"
    return 1
}

# Find any existing counter
find_existing_counter
EXISTING_COUNT="$COUNT"

# Create multiple storage locations to ensure persistence
echo "Creating storage directories..."

# 1. System location (if we have permissions)
if [ -w "/var/lib" ] || [ "$EUID" -eq 0 ]; then
    sudo mkdir -p /var/lib/weightwhat
    sudo chmod 755 /var/lib/weightwhat
    
    if [ ! -f "/var/lib/weightwhat/counter.json" ] || [ "$EXISTING_COUNT" != "0" ]; then
        echo "{\"count\": $EXISTING_COUNT, \"updated_at\": $(date +%s)}" | sudo tee "/var/lib/weightwhat/counter.json" > /dev/null
        sudo chmod 644 "/var/lib/weightwhat/counter.json"
    fi
fi

# 2. Application data directory
if [ -d "/opt/WeightWhat" ]; then
    sudo mkdir -p /opt/WeightWhat/data
    sudo chmod 755 /opt/WeightWhat/data
    
    if [ ! -f "/opt/WeightWhat/data/counter.json" ] || [ "$EXISTING_COUNT" != "0" ]; then
        echo "{\"count\": $EXISTING_COUNT, \"updated_at\": $(date +%s)}" | sudo tee "/opt/WeightWhat/data/counter.json" > /dev/null
        sudo chmod 644 "/opt/WeightWhat/data/counter.json"
    fi
fi

# 3. User home directory (always writable)
mkdir -p "$HOME/.weightwhat"
if [ ! -f "$HOME/.weightwhat/counter.json" ] || [ "$EXISTING_COUNT" != "0" ]; then
    echo "{\"count\": $EXISTING_COUNT, \"updated_at\": $(date +%s)}" > "$HOME/.weightwhat/counter.json"
fi

echo "Counter setup complete!"
echo "Counter will be stored in the first writable location from:"
echo "  1. /var/lib/weightwhat/counter.json"
echo "  2. /opt/WeightWhat/data/counter.json"
echo "  3. ~/.weightwhat/counter.json"
echo "  4. /tmp/sizecomparator_counter.json (fallback)"
echo ""
echo "Current counter value: $EXISTING_COUNT"