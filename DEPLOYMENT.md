# 🚀 Deployment Process for AuditApp

## Overview
- **Frontend**: Auto-deploys via GitHub Actions on push to `main`
- **Backend**: Auto-deploys via GitHub Actions on push to `main`

---

## ✅ Consistent Deployment Workflow

### **Frontend Deployment**

**Method**: GitHub Actions (Automatic)

**Trigger**: Any change to `frontend/**` files on `main` branch

**Steps**:
1. Make changes to frontend code
2. Commit and push to `main`:
   ```bash
   cd /home/sandeep.lingam/app-project/Audit-App
   git add frontend/
   git commit -m "feat: your change description"
   git push
   ```
3. GitHub Actions automatically:
   - Builds the frontend (`npm run build`)
   - Deploys to Azure Static Web Apps
   - Live at: https://blue-island-0b509160f.3.azurestaticapps.net

**Manual Trigger** (if needed):
```bash
# Force deployment by touching a file in frontend/
echo "# Build $(date +%s)" >> frontend/.buildtrigger
git add frontend/.buildtrigger
git commit -m "trigger: force frontend deployment"
git push
```

**Verification**:
```bash
# Check deployment status (wait 2-3 minutes)
curl -I https://blue-island-0b509160f.3.azurestaticapps.net
```

---

### **Backend Deployment**

**Method**: GitHub Actions → Azure Container Apps (Automatic)

**Trigger**: Any change to `backend/**` files on `main` branch

**Steps**:
1. Make changes to backend code
2. Commit and push to `main`:
   ```bash
   cd /home/sandeep.lingam/app-project/Audit-App
   git add backend/
   git commit -m "feat: your change description"
   git push
   ```
3. GitHub Actions automatically:
   - Builds Docker image in Azure Container Registry
   - Deploys new revision to Container Apps
   - Live at: https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io

**Manual Trigger** (if needed):
```bash
# Force deployment by touching a file in backend/
echo "# Build $(date +%s)" >> backend/.buildtrigger
git add backend/.buildtrigger
git commit -m "trigger: force backend deployment"
git push
```

**Verification**:
```bash
# Check backend health (wait 3-5 minutes for container restart)
curl https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io/health
```

---

## ⚠️ NEVER DO THESE

❌ **DON'T** use `az acr build` manually
❌ **DON'T** use `az containerapp update` manually  
❌ **DON'T** use `swa deploy` manually
❌ **DON'T** deploy from local machine (except for testing)

**Always use Git + GitHub Actions** for production deployments.

---

## 🔧 Troubleshooting

### Frontend not updating?
1. Check GitHub Actions: https://github.com/sandeeplingam1/Audit-App/actions
2. Hard refresh browser: `Ctrl + Shift + R`
3. Clear cache

### Backend not updating?
1. Check GitHub Actions: https://github.com/sandeeplingam1/Audit-App/actions
2. Check Container Apps revision:
   ```bash
   az containerapp revision list --name auditapp-staging-backend --resource-group auditapp-staging-rg -o table
   ```
3. Check logs:
   ```bash
   az containerapp logs show --name auditapp-staging-backend --resource-group auditapp-staging-rg --tail 50
   ```

### CORS Issues?
- Frontend and backend must both be deployed
- Wait 2-3 minutes after deployment for DNS propagation
- Hard refresh browser

---

## 📝 Deployment Checklist

Before pushing changes:
- [ ] Test locally (frontend on localhost:5173, backend on localhost:8000)
- [ ] Commit with clear message
- [ ] Push to `main` branch
- [ ] Wait 3-5 minutes
- [ ] Verify deployment at URLs above
- [ ] Test in production environment
