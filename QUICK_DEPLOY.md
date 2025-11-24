# Quick Start: Deploy to Production

## TL;DR - Fastest Path to Production

### Prerequisites (5 minutes)
```bash
# 1. Ensure you're logged into Azure
az login

# 2. Confirm you have the right subscription
az account show

# 3. Navigate to project
cd /home/sandeep.lingam/app-project/Audit-App
```

### Deploy (15-20 minutes)
```bash
# One command deploys everything!
cd infrastructure
./deploy.sh prod eastus

# This creates:
# ✅ All Azure resources
# ✅ Configuration file (.env.production)
# ✅ Outputs with connection strings
```

### Configure (5 minutes)
```bash
# Review the auto-generated config
cat ../.env.production

# Update if needed (SQL password, etc.)
nano ../.env.production
```

### Build & Deploy Backend (10 minutes)
```bash
# Get container registry name from deployment
ACR_NAME=$(cat deployment-outputs.json | jq -r .containerRegistryLoginServer.value | cut -d. -f1)

# Login to registry
az acr login --name $ACR_NAME

# Build and push
cd ../backend
docker build -t ${ACR_NAME}.azurecr.io/audit-app-backend:latest .
docker push ${ACR_NAME}.azurecr.io/audit-app-backend:latest

# Deploy to Container Apps
az containerapp create \
  --name auditapp-prod-backend \
  --resource-group auditapp-prod-rg \
  --environment $(cat ../infrastructure/deployment-outputs.json | jq -r .containerAppEnvName.value) \
  --image ${ACR_NAME}.azurecr.io/audit-app-backend:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 10 \
  --cpu 1.0 \
  --memory 2.0Gi
```

### Deploy Frontend (10 minutes)
```bash
# Get backend URL
BACKEND_URL=$(az containerapp show \
  --name auditapp-prod-backend \
  --resource-group auditapp-prod-rg \
  --query properties.configuration.ingress.fqdn -o tsv)

# Build frontend
cd ../frontend
npm install
VITE_API_URL=https://$BACKEND_URL npm run build

# Deploy
az staticwebapp create \
  --name auditapp-prod-frontend \
  --resource-group auditapp-prod-rg \
  --source ./dist \
  --location eastus
```

### Test (5 minutes)
```bash
# Get frontend URL
FRONTEND_URL=$(az staticwebapp show \
  --name auditapp-prod-frontend \
  --resource-group auditapp-prod-rg \
  --query defaultHostname -o tsv)

echo "🎉 Your app is live at: https://$FRONTEND_URL"

# Test backend health
curl https://$BACKEND_URL/health
```

---

## Estimated Total Time: 45-60 minutes

---

## What Gets Created

### Azure Resources (Auto-deployed by infrastructure/deploy.sh)

1. **Azure SQL Database**
   - Server: `auditapp-prod-sql-{uniqueid}`
   - Database: `auditapp-prod-db`
   - Tier: Standard S1 (20 DTU)

2. **Azure Storage Account**
   - Name: `auditappprodst{uniqueid}`
   - Containers: `audit-documents`
   - Queues: `document-processing`

3. **Azure AI Search**
   - Name: `auditapp-prod-search-{uniqueid}`
   - Tier: Standard (for production)
   - Ready for 500K+ document chunks

4. **Azure Cache for Redis**
   - Name: `auditapp-prod-redis-{uniqueid}`
   - Tier: Standard C1
   - SSL enabled

5. **Azure Key Vault**
   - Name: `auditapp-prod-kv-{uniqueid}`
   - For storing secrets securely

6. **Application Insights**
   - Name: `auditapp-prod-insights`
   - Connected to Log Analytics workspace
   - Monitoring enabled

7. **Container Registry**
   - Name: `auditappprodacr{uniqueid}`
   - For storing Docker images

8. **Container App Environment**
   - Name: `auditapp-prod-containerenv`
   - Ready for backend deployment

---

## Cost During Deployment

**First Month (with testing):**
- Infrastructure: ~$300-400
- Azure OpenAI: ~$50-100 (usage)
- **Total: ~$350-500**

**Ongoing Monthly:**
- ~$510-640/month (full production)
- Can reduce to ~$200/month for staging/basic tiers

---

## Alternative: Deploy to Staging First (Recommended)

```bash
# Use staging environment for testing
cd infrastructure
./deploy.sh staging eastus

# Costs ~$150-250/month
# Same process, lower tiers
# Test before production
```

---

## Rollback

If something goes wrong:

```bash
# Delete entire resource group
az group delete --name auditapp-prod-rg --yes --no-wait

# Your local app still works!
cd /home/sandeep.lingam/app-project/Audit-App
./start.sh
```

---

## Next Steps After Deployment

1. **Test with sample documents** (docs/PRODUCTION_CHECKLIST.md)
2. **Set up monitoring alerts** (docs/PRODUCTION_DEPLOYMENT.md)
3. **Configure backup policies**
4. **Add custom domain** (optional)
5. **Enable CI/CD** (.github/workflows/)
6. **Train users**
7. **Go live!** 🚀

---

## Support

- **Full Guide:** `docs/PRODUCTION_DEPLOYMENT.md`
- **Checklist:** `docs/PRODUCTION_CHECKLIST.md`
- **Changes:** `PRODUCTION_READY.md`
- **Issues:** Check backend.log and Application Insights

---

## Important Notes

- ⚠️ **Your local app still works** - No changes to dev workflow
- ✅ **Infrastructure script is idempotent** - Safe to re-run
- 💰 **Monitor costs** - Set up budget alerts in Azure
- 🔐 **Change default passwords** - Update SQL admin password
- 📊 **Review config** - Check .env.production before deploying code

---

**Ready? Let's deploy!** 🎯
