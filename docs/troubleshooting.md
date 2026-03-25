# Troubleshooting Guide

## Common Issues

### Ferry Data Not Loading
**Symptoms:** Empty ferry list, no positions in search

**Check:**
1. Environment variables set: `railway logs` should show OAuth token acquisition
2. API connectivity: Look for network error messages
3. Client credentials validity: Barentswatch credentials may be revoked

**Solutions:**
- Regenerate client credentials if invalid
- Verify Norwegian waters coordinate validation
- Check Railway environment variables

### Startup Errors
**Symptoms:** App crashes on startup, 500 errors

**Check:**
1. `railway logs` for Python errors
2. CSV file presence: `data/ferries.csv`
3. Import errors in ferry_api module

**Solutions:**
- Verify all dependencies in requirements.txt
- Check file paths are correct
- Restart deployment: `railway up --detach`

### API Rate Limiting
**Symptoms:** 429 status codes, throttling messages

**Check:**
- Barentswatch API limits (check documentation)
- Request frequency during startup

**Solutions:**
- Implement exponential backoff (future enhancement)
- Cache ferry positions (current: startup only)
- Contact Barentswatch for limit increases

## Monitoring

### Health Check Endpoints
- `/api/status` - Shows ferry count and system status (JSON response)

### Log Analysis
```bash
# View recent logs
railway logs

# Follow logs in real-time
railway logs --follow

# Filter for ferry-related logs
railway logs | grep -i ferry
```

### Performance Metrics
- Startup time: Ferry loading should complete within 30 seconds
- Memory usage: Monitor for memory leaks in long-running deployments
- API response times: Track Barentswatch API performance