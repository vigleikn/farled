#!/bin/bash
# Railway Deployment Script for Ferry Integration

echo "🚀 Deploying Ferry Sea Route Calculator to Railway"
echo "=================================================="

echo ""
echo "📋 Prerequisites Check:"
echo "1. ✅ Railway CLI installed"
echo "2. 🔐 Barentswatch API credentials needed"
echo "   - Get them at: https://www.barentswatch.no/"
echo "   - You need CLIENT_ID and CLIENT_SECRET"

echo ""
echo "🔧 Deployment Steps:"
echo ""

echo "STEP 1: Login to Railway"
echo "railway login"
echo ""

echo "STEP 2: Initialize project"
echo "railway init"
echo ""

echo "STEP 3: Set environment variables (replace with your actual credentials)"
echo "railway variables set BARENTSWATCH_CLIENT_ID=\"your-client-id-here\""
echo "railway variables set BARENTSWATCH_CLIENT_SECRET=\"your-client-secret-here\""
echo ""

echo "STEP 4: Deploy application"
echo "railway up"
echo ""

echo "STEP 5: Check deployment"
echo "railway status"
echo "railway logs"
echo ""

echo "🎯 After deployment:"
echo "- Your app will be available at the Railway URL"
echo "- Check logs for ferry data loading"
echo "- Test /api/ferries endpoint"
echo "- Monitor /api/status for ferry count"
echo ""

echo "🔍 Troubleshooting:"
echo "- Check docs/troubleshooting.md for common issues"
echo "- Verify Barentswatch credentials are valid"
echo "- Monitor Railway logs for startup errors"