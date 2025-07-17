#!/bin/bash
# Setup script for persistent counter storage

# Create directory for persistent data if it doesn't exist
if [ ! -d "/var/lib/weightwhat" ]; then
    echo "Creating /var/lib/weightwhat directory..."
    sudo mkdir -p /var/lib/weightwhat
    sudo chown root:root /var/lib/weightwhat
    sudo chmod 755 /var/lib/weightwhat
fi

# Initialize counter file if it doesn't exist
COUNTER_FILE="/var/lib/weightwhat/counter.json"
if [ ! -f "$COUNTER_FILE" ]; then
    echo "Creating counter file..."
    echo '{"count": 0, "updated_at": 0}' | sudo tee "$COUNTER_FILE" > /dev/null
    sudo chown root:root "$COUNTER_FILE"
    sudo chmod 644 "$COUNTER_FILE"
else
    echo "Counter file already exists at $COUNTER_FILE"
    sudo cat "$COUNTER_FILE"
fi

echo "Counter setup complete!"