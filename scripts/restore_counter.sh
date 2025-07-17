#!/bin/bash
# Restore script for counter data
# Use after updates if counter was lost

BACKUP_DIR="/opt/WeightWhat/backups"

echo "Restoring counter data..."

# Find the latest backup
if [ -f "$BACKUP_DIR/counter_latest.json" ]; then
    BACKUP_FILE="$BACKUP_DIR/counter_latest.json"
elif [ -n "$(ls -A $BACKUP_DIR/counter_*.json 2>/dev/null)" ]; then
    BACKUP_FILE=$(ls -t $BACKUP_DIR/counter_*.json | head -1)
else
    echo "No backup files found in $BACKUP_DIR!"
    exit 1
fi

echo "Using backup file: $BACKUP_FILE"
COUNT=$(python3 -c "import json; print(json.load(open('$BACKUP_FILE'))['count'])" 2>/dev/null || echo "0")
echo "Counter value to restore: $COUNT"

# Restore to all locations
echo "Restoring to all locations..."

# 1. System location
if [ -w "/var/lib" ] || [ "$EUID" -eq 0 ]; then
    sudo mkdir -p /var/lib/weightwhat
    sudo cp "$BACKUP_FILE" "/var/lib/weightwhat/counter.json"
    sudo chmod 644 "/var/lib/weightwhat/counter.json"
    echo "✓ Restored to /var/lib/weightwhat/counter.json"
fi

# 2. Application directory
if [ -d "/opt/WeightWhat" ]; then
    sudo mkdir -p /opt/WeightWhat/data
    sudo cp "$BACKUP_FILE" "/opt/WeightWhat/data/counter.json"
    sudo chmod 644 "/opt/WeightWhat/data/counter.json"
    echo "✓ Restored to /opt/WeightWhat/data/counter.json"
fi

# 3. User home directory
mkdir -p "$HOME/.weightwhat"
cp "$BACKUP_FILE" "$HOME/.weightwhat/counter.json"
echo "✓ Restored to $HOME/.weightwhat/counter.json"

echo ""
echo "Counter restored successfully!"
echo "Restart the service to apply: sudo systemctl restart weightwhat"