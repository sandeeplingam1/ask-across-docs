#!/bin/bash
# Verify GitHub Actions Backend Deployment Setup

echo "=== GitHub Actions Backend Deployment Verification ==="
echo ""

# Check if workflow files exist
echo "1. Checking workflow files..."
if [ -f ".github/workflows/deploy-backend-v2.yml" ]; then
    echo "   ✅ New workflow exists: deploy-backend-v2.yml"
else
    echo "   ❌ Missing: deploy-backend-v2.yml"
fi

if [ -f ".github/workflows/deploy-backend.yml" ]; then
    echo "   ⚠️  Old workflow still active: deploy-backend.yml"
    echo "      (This will fail until you switch to v2)"
else
    echo "   ✅ Old workflow removed/renamed"
fi
echo ""

# Check if setup script exists
echo "2. Checking setup script..."
if [ -x "scripts/setup-github-actions-backend.sh" ]; then
    echo "   ✅ Setup script exists and is executable"
else
    echo "   ❌ Setup script missing or not executable"
    echo "      Run: chmod +x scripts/setup-github-actions-backend.sh"
fi
echo ""

# Check Azure CLI
echo "3. Checking Azure CLI..."
if command -v az &> /dev/null; then
    ACCOUNT=$(az account show --query name -o tsv 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "   ✅ Azure CLI authenticated"
        echo "      Account: $ACCOUNT"
    else
        echo "   ❌ Azure CLI not authenticated"
        echo "      Run: az login"
    fi
else
    echo "   ❌ Azure CLI not installed"
fi
echo ""

# Check GitHub repository
echo "4. Checking GitHub repository..."
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if [[ $REMOTE_URL == *"sandeeplingam1/Audit-App"* ]]; then
    echo "   ✅ Correct repository: $REMOTE_URL"
else
    echo "   ⚠️  Repository: $REMOTE_URL"
fi
echo ""

# Summary
echo "=========================================="
echo "NEXT STEPS:"
echo "=========================================="
echo ""

if [ ! -x "scripts/setup-github-actions-backend.sh" ]; then
    echo "1. Make setup script executable:"
    echo "   chmod +x scripts/setup-github-actions-backend.sh"
    echo ""
fi

echo "2. Run setup script (needs Azure CLI authenticated):"
echo "   ./scripts/setup-github-actions-backend.sh"
echo ""
echo "3. Add 3 secrets to GitHub:"
echo "   https://github.com/sandeeplingam1/Audit-App/settings/secrets/actions"
echo ""
echo "4. Activate new workflow:"
echo "   mv .github/workflows/deploy-backend.yml .github/workflows/deploy-backend-old.yml"
echo "   mv .github/workflows/deploy-backend-v2.yml .github/workflows/deploy-backend.yml"
echo "   git add -A && git commit -m 'Enable Managed Identity workflow'"
echo "   git push"
echo ""
echo "5. Test by making a change to backend/ and pushing"
