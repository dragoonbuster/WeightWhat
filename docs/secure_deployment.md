# Secure Deployment Guide

## API Keys Management

Weight What? uses a separated API keys system for enhanced security. This allows you to:
- Safely commit `.env` to version control
- Keep sensitive API keys in a separate file
- Deploy without exposing keys in your repository

## Setup Instructions

### 1. Local Development

```bash
# Run the setup script
./scripts/setup_env.sh

# This will:
# - Create .env from .env.example
# - Prompt for API keys and save to .env.keys
# - Configure your prompt profile preference
```

### 2. File Structure

After setup, you'll have:
```
.env              # Safe to commit - contains non-sensitive config
.env.keys         # NEVER commit - contains API keys
.env.example      # Template for .env
.env.keys.example # Template showing key format
```

### 3. API Keys File Format

`.env.keys` should contain:
```bash
# API Keys - DO NOT COMMIT THIS FILE!
SIZECOMPARATOR_OPENAI_API_KEY=sk-your-actual-key-here
SIZECOMPARATOR_ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
SIZECOMPARATOR_XAI_API_KEY=xai-your-actual-key-here
```

## Deployment Workflow

### Safe Local to GitHub to Server Flow

1. **Local Development**:
   ```bash
   # Your .env and code changes are safe to commit
   git add .env src/
   git commit -m "Update configuration"
   git push origin main
   ```

2. **On Server**:
   ```bash
   cd /opt/WeightWhat
   
   # Pull code changes (including .env)
   sudo git pull
   
   # API keys stay in server's .env.keys (not overwritten)
   # Restart service
   sudo systemctl restart weightwhat
   ```

### First-Time Server Setup

```bash
# 1. Clone repository
cd /opt
sudo git clone https://github.com/yourusername/SizeComparator WeightWhat
cd WeightWhat

# 2. Run setup script
sudo ./scripts/setup_env.sh
# Enter your production API keys when prompted

# 3. Verify keys file permissions
sudo chmod 600 .env.keys
sudo chown root:root .env.keys

# 4. Start service
sudo systemctl start weightwhat
```

## Security Best Practices

### 1. File Permissions
```bash
# API keys file should be readable only by owner
chmod 600 .env.keys

# On server, owned by service user
sudo chown www-data:www-data .env.keys  # or whatever user runs your service
```

### 2. Alternative Key Locations

The system checks these locations in order:
1. `./.env.keys` (current directory)
2. `/opt/WeightWhat/.env.keys` (production default)
3. `~/.weightwhat/.env.keys` (user home)
4. `/etc/weightwhat/.env.keys` (system-wide)

### 3. Environment Variables

You can also set keys directly as environment variables:
```bash
# In systemd service file
Environment="SIZECOMPARATOR_OPENAI_API_KEY=sk-..."
```

## Backup and Recovery

### Backup API Keys
```bash
# Create encrypted backup
sudo tar -czf - .env.keys | gpg -c > api_keys_backup.tar.gz.gpg

# Store backup securely (not in repo!)
```

### Restore API Keys
```bash
# Decrypt and restore
gpg -d api_keys_backup.tar.gz.gpg | sudo tar -xzf -
```

## Troubleshooting

### Keys Not Loading

1. Check file exists:
   ```bash
   ls -la .env.keys
   ```

2. Check permissions:
   ```bash
   # Should show -rw-------
   stat .env.keys
   ```

3. Check logs:
   ```bash
   sudo journalctl -u weightwhat | grep -i "env.keys"
   ```

### Missing Keys Error

If you see "No AI provider API keys configured":
1. Verify .env.keys exists and contains valid keys
2. Check file permissions
3. Restart the service

## CI/CD Integration

For automated deployments:

1. Store API keys in CI/CD secrets
2. Create .env.keys during deployment:
   ```yaml
   # Example GitHub Actions
   - name: Create API keys file
     run: |
       echo "SIZECOMPARATOR_OPENAI_API_KEY=${{ secrets.OPENAI_KEY }}" > .env.keys
       chmod 600 .env.keys
   ```

3. Deploy normally - .env from repo, .env.keys from secrets

## Summary

- **Always**: Keep .env.keys out of version control
- **Never**: Commit actual API keys
- **Do**: Use the setup script for easy configuration
- **Remember**: Different prompt profiles affect response style, not security