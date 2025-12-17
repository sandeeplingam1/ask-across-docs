#!/bin/bash
# Setup GitHub Actions with Managed Identity for Backend Deployment

set -e

echo "=== GitHub Actions Backend Deployment Setup ==="
echo ""

# Variables
REPO_OWNER="sandeeplingam1"
REPO_NAME="Audit-App"
APP_NAME="github-actions-auditapp-backend"
RESOURCE_GROUP="auditapp-staging-rg"

echo "Repository: $REPO_OWNER/$REPO_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo ""

# Step 1: Get subscription and tenant IDs
echo "Step 1: Getting Azure subscription and tenant IDs..."
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "✅ Subscription ID: $SUBSCRIPTION_ID"
echo "✅ Tenant ID: $TENANT_ID"
echo ""

# Step 2: Create App Registration
echo "Step 2: Creating App Registration..."
APP_ID=$(az ad app create \
  --display-name "$APP_NAME" \
  --query appId -o tsv 2>/dev/null || \
  az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv)

echo "✅ App ID (Client ID): $APP_ID"
echo ""

# Step 3: Create Service Principal
echo "Step 3: Creating Service Principal..."
SP_ID=$(az ad sp create --id $APP_ID --query id -o tsv 2>/dev/null || \
  az ad sp list --filter "appId eq '$APP_ID'" --query "[0].id" -o tsv)

echo "✅ Service Principal ID: $SP_ID"
echo ""

# Step 4: Assign Contributor role to resource group
echo "Step 4: Assigning Contributor role..."
az role assignment create \
  --role "Contributor" \
  --assignee $APP_ID \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
  2>/dev/null || echo "Role already assigned"

echo "✅ Contributor role assigned to resource group"
echo ""

# Step 5: Assign ACR Push role
echo "Step 5: Assigning ACR Push role..."
ACR_ID=$(az acr show \
  --name auditappstagingacrwgjuafflp2o4o \
  --resource-group $RESOURCE_GROUP \
  --query id -o tsv)

az role assignment create \
  --role "AcrPush" \
  --assignee $APP_ID \
  --scope $ACR_ID \
  2>/dev/null || echo "ACR Push role already assigned"

echo "✅ AcrPush role assigned"
echo ""

# Step 6: Create federated credential for GitHub Actions
echo "Step 6: Creating federated credential for GitHub Actions..."
CREDENTIAL_NAME="github-actions-main"

# Delete existing credential if it exists
az ad app federated-credential delete \
  --id $APP_ID \
  --federated-credential-id $CREDENTIAL_NAME \
  2>/dev/null || true

# Create new federated credential
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "'$CREDENTIAL_NAME'",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'$REPO_OWNER'/'$REPO_NAME':ref:refs/heads/main",
    "description": "GitHub Actions for main branch",
    "audiences": ["api://AzureADTokenExchange"]
  }'

echo "✅ Federated credential created for main branch"
echo ""

# Summary
echo "========================================"
echo "✅ SETUP COMPLETE!"
echo "========================================"
echo ""
echo "Add these secrets to GitHub repository:"
echo "Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "Secret Name: AZURE_CLIENT_ID"
echo "Value: $APP_ID"
echo ""
echo "Secret Name: AZURE_TENANT_ID"
echo "Value: $TENANT_ID"
echo ""
echo "Secret Name: AZURE_SUBSCRIPTION_ID"
echo "Value: $SUBSCRIPTION_ID"
echo ""
echo "GitHub URL: https://github.com/$REPO_OWNER/$REPO_NAME/settings/secrets/actions"
echo ""
echo "After adding secrets:"
echo "1. Rename .github/workflows/deploy-backend-v2.yml to deploy-backend.yml"
echo "2. Delete or rename old deploy-backend.yml"
echo "3. Push changes to trigger deployment"
