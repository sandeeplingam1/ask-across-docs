# Issues Found & How to Fix

## 🔍 Diagnostic Results Summary

Based on your diagnostic output, here are the **exact issues**:

### ❌ **Issue 1: Duplicate Backend Container App**
**Found:**
- `auditapp-backend` (old/wrong name)
- `auditapp-staging-backend` (correct one)

**Problem:** You have TWO backend apps running. The old one is orphaned.

**Fix:** Delete `auditapp-backend`

---

### ❌ **Issue 2: Redis Cache Still Deployed**
**Found:** `auditapp-staging-redis-wgjuafflp2o4o`

**Problem:** Costs **$75/month** but NOT used in your code (we removed it)

**Fix:** Delete it and save $75/month

---

### ❌ **Issue 3: Key Vault Still Deployed**
**Found:** `kv-auditapp-wgjuafflp2`

**Problem:** Costs **$1/month** but NOT used (secrets are in Container App directly)

**Fix:** Delete it and save $1/month

---

### ❌ **Issue 4: Static Web App NOT Connected to GitHub**
**Found:**
```json
{
  "RepositoryUrl": null,
  "Branch": null,
  "BuildLocation": null,
  "DefaultHostname": null
}
```

**Problem:** 
- Static Web App exists but has NO code deployed
- Not connected to your GitHub repository
- Frontend won't load

**This is the MAIN issue you mentioned!**

**Fix:** Connect to GitHub manually or via CLI

---

### ❌ **Issue 5: Old Frontend Docker Image**
**Found:** `auditapp-frontend` image in Container Registry

**Problem:** 
- You switched from Container App to Static Web App for frontend
- Old Docker image still there (wastes space)

**Fix:** Delete the old image

---

## 🚀 **AUTOMATED FIX - Run This:**

I created a script that fixes EVERYTHING automatically!

```bash
cd infrastructure
./fix-azure-setup.sh
```

**What it does:**
1. ✅ Deletes duplicate backend (`auditapp-backend`)
2. ✅ Deletes Redis ($75/month saved)
3. ✅ Deletes Key Vault ($1/month saved)
4. ✅ Deletes old frontend Docker image
5. ⚠️ **Guides you to connect Static Web App to GitHub**
6. ✅ Sets correct backend URL in frontend config

**Total savings: $76/month** 💰

---

## 📝 **Manual Steps Required**

### For Static Web App GitHub Connection:

**Option A: Azure Portal (Easiest)**

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to: `auditapp-staging-rg` → `auditapp-staging-frontend`
3. Click **"Deployment"** in left menu
4. Click **"GitHub"** button
5. Authorize Azure to access your GitHub
6. Select:
   - **Organization:** `sandeeplingam1`
   - **Repository:** `Audit-App`
   - **Branch:** `main`
7. Build configuration:
   - **App location:** `/frontend`
   - **Api location:** _(leave empty)_
   - **Output location:** `dist`
8. Click **"Save"**

GitHub Actions will auto-deploy your frontend in 5-10 minutes!

---

**Option B: Via GitHub Token (Advanced)**

```bash
# Get GitHub token from: https://github.com/settings/tokens
# Permissions needed: repo, workflow

az staticwebapp update \
  --name auditapp-staging-frontend \
  --resource-group auditapp-staging-rg \
  --source https://github.com/sandeeplingam1/Audit-App \
  --branch main \
  --app-location '/frontend' \
  --output-location 'dist' \
  --token YOUR_GITHUB_TOKEN_HERE
```

---

## ✅ **After Running fix-azure-setup.sh**

### Your Final Setup Will Be:

**Resources (10 total):**
1. ✅ SQL Server + Database
2. ✅ Container Registry (with backend image only)
3. ✅ Container Apps Environment
4. ✅ Backend Container App (`auditapp-staging-backend`)
5. ✅ Static Web App (`auditapp-staging-frontend`)
6. ✅ Application Insights + Log Analytics
7. ✅ Reusing existing: AI Search, Blob Storage (from `rg-saga-dev`)

**Removed:**
- ❌ Duplicate backend app
- ❌ Redis Cache
- ❌ Key Vault
- ❌ Old frontend Docker image

**URLs:**
- **Backend:** `https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io`
- **Frontend:** `https://[assigned-by-azure].azurestaticapps.net` (after GitHub connection)

---

## 🔥 **Quick Commands Reference**

### Test Backend:
```bash
curl https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io/health
```

Should return:
```json
{"status":"healthy","version":"1.1.0",...}
```

### Check Frontend Deployment Status:
```bash
az staticwebapp show \
  --name auditapp-staging-frontend \
  --resource-group auditapp-staging-rg \
  --query "{Status:properties.provisioningState, Hostname:defaultHostname, Repo:properties.repositoryUrl}"
```

### View GitHub Actions Deployment:
After connecting GitHub, go to:
```
https://github.com/sandeeplingam1/Audit-App/actions
```

You'll see the deployment workflow running!

---

## 🎯 Summary

**Problems:**
1. Duplicate backend app ❌
2. Redis + Key Vault costing $76/month ❌
3. Static Web App not connected to GitHub ❌ **(MAIN ISSUE)**
4. Old Docker image ❌

**Solution:**
```bash
./infrastructure/fix-azure-setup.sh
```
Then connect Static Web App to GitHub via Azure Portal.

**Result:**
- Clean infrastructure ✅
- $76/month saved ✅
- Frontend auto-deploys from GitHub ✅
- Everything working ✅

**Run the script and you're good to go!** 🚀
