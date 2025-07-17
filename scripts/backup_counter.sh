#!/bin/bash
# Backup script for counter data
# Run this before major updates

BACKUP_DIR="/opt/WeightWhat/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Backing up counter data..."

# Create backup directory
sudo mkdir -p "$BACKUP_DIR"

# Find and backup all counter files
LOCATIONS=(
    "/var/lib/weightwhat/counter.json"
    "/opt/WeightWhat/data/counter.json"
    "$HOME/.weightwhat/counter.json"
    "/tmp/sizecomparator_counter.json"
)

FOUND=0
for loc in "${LOCATIONS[@]}"; do
    if [ -f "$loc" ]; then
        echo "Backing up $loc..."
        sudo cp "$loc" "$BACKUP_DIR/counter_${TIMESTAMP}_$(basename $(dirname $loc)).json"
        FOUND=1
        
        # Also create a latest backup
        sudo cp "$loc" "$BACKUP_DIR/counter_latest.json"
        
        # Display the counter value
        COUNT=$(python3 -c "import json; print(json.load(open('$loc'))['count'])" 2>/dev/null || echo "unknown")
        echo "  Counter value: $COUNT"
    fi
done

if [ $FOUND -eq 0 ]; then
    echo "No counter files found!"
else
    echo "Backup complete. Files saved to $BACKUP_DIR"
    ls -la "$BACKUP_DIR"/counter_*.json
fi