# Azure Deployment Troubleshooting Guide

## What You Need to Share

To help you fix your Azure setup, I need these outputs:

### 1. Run the Diagnostic Script

```bash
cd infrastructure
./diagnose-azure.sh > azure-current-state.txt
cat azure-current-state.txt
```

This will show me:
- ✅ What resources are actually deployed
- ⚠️ Any orphaned/failed resources
- 🌐 Static Web App configuration
- 🐳 Container Apps status
- 📦 What images are in your Container Registry

### 2. If Script Doesn't Work, Run These Commands:

```bash
# List all resources
az resource list --resource-group auditapp-staging-rg --output table

# Check Container Apps
az containerapp list --resource-group auditapp-staging-rg --output table

# Check Static Web Apps  
az staticwebapp list --resource-group auditapp-staging-rg --output table

# Check recent deployments
az deployment group list --resource-group auditapp-staging-rg --output table
```

---

## Common Deployment Issues & Fixes

### Issue 1: Frontend in Container App (Old Setup)

**What happened:**
- You deployed frontend as a Container App
- Then deleted it
- Created a Static Web App instead

**What to check:**
```bash
# Should show NO frontend container app
az containerapp list --resource-group auditapp-staging-rg --query "[?contains(name, 'frontend')]"

# Should show ONE static web app
az staticwebapp list --resource-group auditapp-staging-rg
```

**Fix if frontend Container App still exists:**
```bash
az containerapp delete --name auditapp-staging-frontend --resource-group auditapp-staging-rg --yes
```

---

### Issue 2: Static Web App Not Configured

**What to check:**
```bash
az staticwebapp show --name auditapp-staging-frontend --resource-group auditapp-staging-rg \
  --query "{DefaultHostname:properties.defaultHostname, Repo:properties.repositoryUrl, Branch:properties.branch}"
```

**Should show:**
- `repositoryUrl`: `https://github.com/sandeeplingam1/Audit-App`
- `branch`: `main`
- `defaultHostname`: `something.azurestaticapps.net`

**If repo is NOT connected:**

**Option A: Connect via GitHub (Recommended)**
1. Go to Azure Portal
2. Navigate to your Static Web App
3. Click "Deployment" → "GitHub"
4. Authorize and select your repo
5. Set build configuration:
   - App location: `/frontend`
   - Output location: `dist`

**Option B: Deploy manually**
```bash
cd frontend
npm install
npm run build

# Get deployment token
TOKEN=$(az staticwebapp secrets list --name auditapp-staging-frontend --resource-group auditapp-staging-rg --query "properties.apiKey" -o tsv)

# Deploy using SWA CLI
npx @azure/static-web-apps-cli deploy ./dist --deployment-token $TOKEN
```

---

### Issue 3: Frontend Calling Wrong Backend URL

**Check current config:**
```bash
az staticwebapp appsettings list --name auditapp-staging-frontend --resource-group auditapp-staging-rg
```

**Should have:**
```json
{
  "VITE_API_URL": "https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io"
}
```

**If missing or wrong:**
```bash
# Get backend URL
BACKEND_URL=$(az containerapp show --name auditapp-staging-backend --resource-group auditapp-staging-rg --query "properties.configuration.ingress.fqdn" -o tsv)

# Set frontend env var
az staticwebapp appsettings set \
  --name auditapp-staging-frontend \
  --resource-group auditapp-staging-rg \
  --setting-names VITE_API_URL=https://$BACKEND_URL
```

---

### Issue 4: Backend Not Running

**Check backend status:**
```bash
az containerapp show --name auditapp-staging-backend --resource-group auditapp-staging-rg \
  --query "{Status:properties.provisioningState, Replicas:properties.runningStatus, URL:properties.configuration.ingress.fqdn}"
```

**Test backend:**
```bash
BACKEND_URL=$(az containerapp show --name auditapp-staging-backend --resource-group auditapp-staging-rg --query "properties.configuration.ingress.fqdn" -o tsv)

curl https://$BACKEND_URL/health
```

**Should return:**
```json
{"status":"healthy","version":"1.1.0",...}
```

**If backend is down:**
```bash
# Check logs
az containerapp logs show --name auditapp-staging-backend --resource-group auditapp-staging-rg --tail 100

# Restart
az containerapp revision restart --name auditapp-staging-backend --resource-group auditapp-staging-rg
```

---

### Issue 5: Duplicate or Old Resources

**Check for duplicates:**
```bash
# Should show ONLY ONE backend
az containerapp list --resource-group auditapp-staging-rg --query "[].name"

# Should show ONLY ONE static web app
az staticwebapp list --resource-group auditapp-staging-rg --query "[].name"
```

**Clean up old resources:**
```bash
# Delete old/unused Container App
az containerapp delete --name OLD_NAME --resource-group auditapp-staging-rg --yes

# Delete old/unused Static Web App
az staticwebapp delete --name OLD_NAME --resource-group auditapp-staging-rg --yes
```

---

### Issue 6: Redis/Key Vault Still Deployed

**Check:**
```bash
az redis list --resource-group auditapp-staging-rg
az keyvault list --resource-group auditapp-staging-rg
```

**Delete if found (saves $76/month):**
```bash
# Delete Redis
az redis delete --name auditapp-staging-redis-XXX --resource-group auditapp-staging-rg --yes

# Delete Key Vault
az keyvault delete --name kv-auditapp-XXX --resource-group auditapp-staging-rg
az keyvault purge --name kv-auditapp-XXX  # Permanent delete
```

---

## Complete Fresh Deployment

If things are really messed up, here's how to start clean:

### Option 1: Clean Resource Group
```bash
# Delete EVERYTHING in resource group
az group delete --name auditapp-staging-rg --yes

# Wait for deletion
az group wait --name auditapp-staging-rg --deleted

# Create fresh resource group
az group create --name auditapp-prod-rg --location eastus

# Deploy clean infrastructure
cd infrastructure
az deployment group create \
  --resource-group auditapp-prod-rg \
  --template-file main.bicep \
  --parameters environment=prod \
  --parameters sqlAdminPassword='YourPassword' \
  --parameters azureOpenAIResourceName='cog-obghpsbi63abq' \
  --parameters azureOpenAIResourceGroup='rg-saga-dev' \
  --parameters useExistingAISearch=true \
  --parameters existingAISearchName='gptkb-obghpsbi63abq' \
  --parameters existingAISearchRG='rg-saga-dev' \
  --parameters useExistingStorage=true \
  --parameters existingStorageAccountName='stobghpsbi63abq' \
  --parameters existingStorageAccountRG='rg-saga-dev'
```

### Option 2: Fix Current Setup
```bash
# Update existing deployment with clean Bicep
cd infrastructure
az deployment group create \
  --resource-group auditapp-staging-rg \
  --template-file main.bicep \
  --mode Complete \
  --parameters environment=staging \
  --parameters sqlAdminPassword='P@ssw0rd123!' \
  --parameters azureOpenAIResourceName='cog-obghpsbi63abq' \
  --parameters azureOpenAIResourceGroup='rg-saga-dev' \
  --parameters useExistingAISearch=true \
  --parameters existingAISearchName='gptkb-obghpsbi63abq' \
  --parameters existingAISearchRG='rg-saga-dev' \
  --parameters useExistingStorage=true \
  --parameters existingStorageAccountName='stobghpsbi63abq' \
  --parameters existingStorageAccountRG='rg-saga-dev'
```

---

## What I Need From You

Please run the diagnostic script and share:

1. **Full output** of `./diagnose-azure.sh`
2. **Any error messages** you're seeing
3. **What's not working** (e.g., frontend not loading, backend errors)

Then I can give you exact commands to fix it! 🛠️
