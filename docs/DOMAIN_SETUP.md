# Domain Setup Guide for weightwhat.xyz

Quick reference for setting up the weightwhat.xyz domain with your SizeComparator deployment.

## DNS Configuration

### Required DNS Records

Configure these DNS records in your domain registrar's control panel:

| Type  | Name | Value            | TTL | Priority |
|-------|------|------------------|-----|----------|
| A     | @    | YOUR_SERVER_IP   | 300 | -        |
| A     | www  | YOUR_SERVER_IP   | 300 | -        |
| CNAME | api  | weightwhat.xyz   | 300 | -        |

### Optional DNS Records

| Type | Name | Value                          | TTL | Priority |
|------|------|--------------------------------|-----|----------|
| MX   | @    | mail.weightwhat.xyz           | 300 | 10       |
| TXT  | @    | "v=spf1 include:_spf.google.com ~all" | 300 | -  |

## Common Domain Registrars

### 1. Namecheap
1. Login to Namecheap account
2. Go to "Domain List" → "Manage"
3. Click "Advanced DNS" tab
4. Add the records above
5. Wait 5-30 minutes for propagation

### 2. GoDaddy
1. Login to GoDaddy account
2. Go to "My Products" → "DNS"
3. Click "Manage DNS" for weightwhat.xyz
4. Add the records above
5. Wait 5-30 minutes for propagation

### 3. Cloudflare
1. Login to Cloudflare account
2. Add weightwhat.xyz domain
3. Update nameservers at your registrar
4. Add the records above
5. Enable proxy (orange cloud) for web traffic

### 4. AWS Route 53
1. Create hosted zone for weightwhat.xyz
2. Add the records above
3. Update nameservers at your registrar
4. Enable health checks

## SSL Certificate Setup

### Automatic with Let's Encrypt
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d weightwhat.xyz -d www.weightwhat.xyz

# Test auto-renewal
sudo certbot renew --dry-run
```

### Manual Certificate
If you prefer a manual certificate:
```bash
# Generate certificate request
sudo certbot certonly --manual -d weightwhat.xyz -d www.weightwhat.xyz
```

## Verification Steps

### 1. DNS Propagation
```bash
# Check DNS resolution
dig weightwhat.xyz
dig www.weightwhat.xyz

# Check from different locations
https://dnschecker.org/
```

### 2. SSL Certificate
```bash
# Check certificate
openssl s_client -connect weightwhat.xyz:443

# Online SSL checker
https://www.ssllabs.com/ssltest/analyze.html?d=weightwhat.xyz
```

### 3. Application Response
```bash
# Test HTTP redirect
curl -I http://weightwhat.xyz

# Test HTTPS
curl -I https://weightwhat.xyz

# Test API
curl -X POST https://weightwhat.xyz/api/compare \
  -H "Content-Type: application/json" \
  -d '{"weight_input": "5 kg"}'
```

## Subdomain Configuration

### API Subdomain (Optional)
If you want `api.weightwhat.xyz`:

```nginx
server {
    listen 443 ssl http2;
    server_name api.weightwhat.xyz;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/weightwhat.xyz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/weightwhat.xyz/privkey.pem;
    
    # API only
    location / {
        proxy_pass http://127.0.0.1:8000/api;
        # ... proxy configuration
    }
}
```

### Monitoring Subdomain (Optional)
If you want `monitor.weightwhat.xyz`:

```nginx
server {
    listen 443 ssl http2;
    server_name monitor.weightwhat.xyz;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/weightwhat.xyz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/weightwhat.xyz/privkey.pem;
    
    # Grafana
    location / {
        proxy_pass http://127.0.0.1:3000;
        # ... proxy configuration
    }
}
```

## Troubleshooting

### Common Issues

1. **DNS not propagating**
   - Wait up to 48 hours for full propagation
   - Check TTL values (lower = faster updates)
   - Use different DNS checker tools

2. **SSL certificate errors**
   - Ensure DNS points to server before getting certificate
   - Check that port 80 is accessible
   - Verify domain ownership

3. **Site not accessible**
   - Check firewall settings
   - Verify nginx configuration
   - Check application logs

### DNS Troubleshooting Commands

```bash
# Check current DNS
nslookup weightwhat.xyz

# Trace DNS resolution
dig +trace weightwhat.xyz

# Check specific DNS server
dig @8.8.8.8 weightwhat.xyz

# Check all record types
dig weightwhat.xyz ANY
```

## Domain Email Setup (Optional)

If you want email for your domain:

### 1. Google Workspace
1. Sign up for Google Workspace
2. Add MX records:
   ```
   MX @ ASPMX.L.GOOGLE.COM (Priority: 1)
   MX @ ALT1.ASPMX.L.GOOGLE.COM (Priority: 5)
   MX @ ALT2.ASPMX.L.GOOGLE.COM (Priority: 5)
   ```

### 2. Simple Email Forwarding
Many registrars offer email forwarding:
1. Enable email forwarding in registrar panel
2. Forward admin@weightwhat.xyz to your personal email
3. Use for cost alerts and notifications

## CDN Setup (Optional)

For better performance, consider using a CDN:

### Cloudflare CDN
1. Add domain to Cloudflare
2. Enable proxy for web traffic
3. Configure caching rules
4. Enable security features

### AWS CloudFront
1. Create CloudFront distribution
2. Point to your server
3. Configure SSL certificate
4. Update DNS to point to CloudFront

## Monitoring Domain Health

### Domain Monitoring Tools
- **UptimeRobot**: Free uptime monitoring
- **Pingdom**: Comprehensive monitoring
- **StatusCake**: Performance monitoring

### DNS Monitoring
```bash
# Add to crontab for regular checks
*/5 * * * * dig weightwhat.xyz | grep -q "YOUR_SERVER_IP" || echo "DNS issue detected"
```

## Security Considerations

### Domain Security
- Enable domain lock at registrar
- Use strong registrar account password
- Enable two-factor authentication
- Consider domain privacy protection

### DNS Security
- Use DNSSEC if supported
- Monitor for unauthorized changes
- Use reputable DNS providers

## Quick Setup Script

```bash
#!/bin/bash
# Quick domain verification script

DOMAIN="weightwhat.xyz"
SERVER_IP="YOUR_SERVER_IP"

echo "Checking DNS resolution for $DOMAIN..."
RESOLVED_IP=$(dig +short $DOMAIN)

if [ "$RESOLVED_IP" = "$SERVER_IP" ]; then
    echo "✓ DNS resolution correct"
else
    echo "✗ DNS resolution incorrect. Got: $RESOLVED_IP, Expected: $SERVER_IP"
fi

echo "Checking SSL certificate..."
if curl -I https://$DOMAIN 2>/dev/null | grep -q "200 OK"; then
    echo "✓ SSL certificate working"
else
    echo "✗ SSL certificate issue"
fi

echo "Checking application health..."
if curl -f https://$DOMAIN/health >/dev/null 2>&1; then
    echo "✓ Application healthy"
else
    echo "✗ Application health check failed"
fi
```

---

**Domain setup complete!** Your weightwhat.xyz domain should now be properly configured and ready for production use.