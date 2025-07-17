# Counter Persistence Guide

The Weight What application maintains a global counter of all weight comparisons made. This guide explains how the counter persists across server updates and restarts.

## How It Works

The counter uses a multi-location fallback system to ensure persistence:

1. **Primary**: `/var/lib/weightwhat/counter.json` (system location)
2. **Secondary**: `/opt/WeightWhat/data/counter.json` (application data)
3. **Tertiary**: `~/.weightwhat/counter.json` (user home)
4. **Fallback**: `/tmp/sizecomparator_counter.json` (temporary)

The application automatically:
- Finds the first writable location
- Migrates data from old locations
- Maintains backups during writes

## Initial Setup

After deploying the application:

```bash
cd /opt/WeightWhat
sudo ./scripts/setup_counter.sh
```

This script will:
- Create necessary directories
- Set proper permissions
- Migrate any existing counter data

## Before Updates

Always backup the counter before major updates:

```bash
sudo ./scripts/backup_counter.sh
```

This creates timestamped backups in `/opt/WeightWhat/backups/`

## After Updates

If the counter is lost after an update:

```bash
sudo ./scripts/restore_counter.sh
sudo systemctl restart weightwhat
```

## Manual Verification

Check current counter value:

```bash
# Via API
curl http://localhost/api/counter

# Via filesystem
for f in /var/lib/weightwhat/counter.json /opt/WeightWhat/data/counter.json ~/.weightwhat/counter.json; do
    [ -f "$f" ] && echo "$f: $(cat $f)"
done
```

## Troubleshooting

### Counter resets to 0
1. Check file permissions: `ls -la /var/lib/weightwhat/counter.json`
2. Check service logs: `sudo journalctl -u weightwhat | grep -i counter`
3. Run setup script: `sudo ./scripts/setup_counter.sh`

### Counter not incrementing
1. Check API endpoint: `curl http://localhost/api/counter`
2. Check write permissions on counter file
3. Verify service is running: `sudo systemctl status weightwhat`

### Migration from old location
The application automatically migrates counters from old locations on startup. Check logs for migration messages.

## Best Practices

1. **Regular Backups**: Run backup script weekly or before updates
2. **Monitor Logs**: Check for counter-related warnings in service logs
3. **Test After Updates**: Always verify counter works after deployments
4. **Keep Multiple Copies**: The multi-location system ensures redundancy

## Technical Details

- Counter is stored as JSON: `{"count": 12345, "updated_at": 1234567890}`
- File permissions: 644 (readable by all, writable by owner)
- Atomic writes prevent corruption
- Automatic migration preserves historical data