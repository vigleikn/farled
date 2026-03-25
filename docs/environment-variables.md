# Environment Variables

## Required Variables

### BARENTSWATCH_CLIENT_ID
**Purpose:** OAuth2 client ID for Barentswatch AIS API access

**How to obtain:**
1. Register at https://www.barentswatch.no/
2. Create API application
3. Note the client ID from your application settings

**Railway setup:**
```bash
railway variables set BARENTSWATCH_CLIENT_ID="your-client-id-here"
```

**Local development:**
Add to `.env` file:
```
BARENTSWATCH_CLIENT_ID=your-client-id-here
```

### BARENTSWATCH_CLIENT_SECRET
**Purpose:** OAuth2 client secret for Barentswatch AIS API access

**How to obtain:**
1. Register at https://www.barentswatch.no/
2. Create API application
3. Note the client secret from your application settings

**Railway setup:**
```bash
railway variables set BARENTSWATCH_CLIENT_SECRET="your-client-secret-here"
```

**Local development:**
Add to `.env` file:
```
BARENTSWATCH_CLIENT_SECRET=your-client-secret-here
```

## Optional Variables

### FERRY_REFRESH_TIMEOUT
- Default: 30 seconds
- Purpose: API request timeout
- Example: `FERRY_REFRESH_TIMEOUT=45`

### DEBUG
- Default: False in production
- Purpose: Enable debug logging
- Example: `DEBUG=True`