# Environment Variables

## Required Variables

### BARENTSWATCH_CLIENT_ID
**Purpose:** Client ID for Barentswatch OAuth2 client credentials flow

### BARENTSWATCH_CLIENT_SECRET
**Purpose:** Client secret for Barentswatch OAuth2 client credentials flow

**How to obtain:**
1. Register at https://www.barentswatch.no/
2. Create API application with client credentials
3. Copy Client ID and Client Secret
4. Set both in Railway environment

**Railway setup:**
```bash
railway variables set BARENTSWATCH_CLIENT_ID="your-client-id"
railway variables set BARENTSWATCH_CLIENT_SECRET="your-client-secret"
```

**Local development:**
Add to `.env` file:
```
BARENTSWATCH_CLIENT_ID=your-client-id
BARENTSWATCH_CLIENT_SECRET=your-client-secret
```