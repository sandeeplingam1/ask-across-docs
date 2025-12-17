# Backend GitHub Actions Deployment Fix

## Problem Analysis
The backend deployment workflow fails while frontend deployment works because:

1. **Backend workflow requires 3 secrets** (complex setup):
   - `ACR_USERNAME` - Azure Container Registry username
   - `ACR_PASSWORD` - Azure Container Registry password  
   - `AZURE_CREDENTIALS` - Azure service principal credentials (JSON)

2. **Frontend workflow requires 1 secret** (simple):
   - `AZURE_STATIC_WEB_APPS_API_TOKEN` - Static Web App deployment token

## Root Cause
Missing or incorrect GitHub Secrets for backend deployment:
- ACR credentials not configured
- Azure service principal not set up
- Or secrets expired/invalid

## Solution Options

### Option 1: Use Managed Identity (RECOMMENDED - No Secrets!)
Replace the complex authentication with Managed Identity + Federated Credentials:

```yaml
# backend/.github/workflows/deploy-backend.yml
- name: Azure Login
  uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

- name: Build and push to ACR
  run: |
    az acr build \
      --registry auditappstagingacrwgjuafflp2o4o \
      --image auditapp-backend:${{ github.sha }} \
      --image auditapp-backend:latest \
      --file backend/Dockerfile \
      backend/
```

**Advantages:**
- No passwords to manage
- More secure (Federated credentials)
- Same approach we use manually (az acr build)
- Only needs 3 non-sensitive IDs

### Option 2: Fix Existing Workflow (Current Approach)
Get and set the missing secrets in GitHub:

```bash
# 1. Get ACR credentials
az acr credential show --name auditappstagingacrwgjuafflp2o4o --resource-group auditapp-staging-rg

# 2. Create service principal
az ad sp create-for-rbac \
  --name "github-actions-auditapp" \
  --role contributor \
  --scopes /subscriptions/SUBSCRIPTION_ID/resourceGroups/auditapp-staging-rg \
  --sdk-auth

# 3. Add secrets to GitHub:
# Settings → Secrets → Actions → New repository secret
# - ACR_USERNAME: <from step 1>
# - ACR_PASSWORD: <from step 1>  
# - AZURE_CREDENTIALS: <from step 2, entire JSON>
```

## Current Workaround
Manual deployment using Azure CLI (what we've been doing):
```bash
az acr build --registry auditappstagingacrwgjuafflp2o4o --image auditapp-backend:latest --file Dockerfile .
az containerapp update --name auditapp-staging-backend --resource-group auditapp-staging-rg --image ...
```

## Recommended Action
**Switch to Option 1 (Managed Identity)** because:
- Aligns with our manual deployment approach
- No secret management headaches
- More secure
- Simpler workflow
- Already using Managed Identity for Service Bus and Azure OpenAI

## Files That Need Changes
1. `.github/workflows/deploy-backend.yml` - Update to use Managed Identity
2. GitHub Secrets - Add only 3 IDs (client-id, tenant-id, subscription-id)
3. Azure - Configure federated credentials for GitHub Actions

## Next Steps
1. Get Azure subscription and tenant IDs
2. Create App Registration with federated credential for GitHub
3. Update workflow file
4. Test deployment
