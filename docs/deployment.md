# Deployment Guide

## Railway Platform Setup

### Prerequisites
- Railway CLI installed (`npm install -g @railway/cli`)
- Barentswatch API credentials (see environment-variables.md)

### Initial Deployment
1. Connect Railway to your repository
2. Set environment variables (see environment-variables.md)
3. Deploy: `railway up`

### Environment Configuration
- Python 3.9+ runtime
- Automatic dependency installation from requirements.txt
- PORT variable auto-configured by Railway

### Health Checks
- App startup logs should show ferry data loading
- Status endpoint: `/status` shows ferry count
- Logs accessible via Railway dashboard