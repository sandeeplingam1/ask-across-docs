# Production Deployment Guide

Complete guide for deploying the Audit App to Azure production environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Cost Estimates](#cost-estimates)
4. [Deployment Steps](#deployment-steps)
5. [Post-Deployment](#post-deployment)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- Azure CLI (v2.50+)
- Docker Desktop
- Node.js 20+
- Python 3.12+
- Git

### Azure Requirements
- Active Azure subscription
- Azure OpenAI access (already approved)
- Permissions to create resources
- Estimated budget: $300-700/month

### Secrets Needed
- SQL Database admin password
- Application secret key
- SSL certificates (optional for custom domains)

---

## Architecture Overview

### Production Architecture

```
Internet
    │
    ├─→ Azure Static Web Apps (Frontend)
    │   └─→ React SPA + CDN
    │
    └─→ Azure Container Apps (Backend)
        ├─→ FastAPI Application (4 instances)
        ├─→ Background Workers (2 instances)
        │
        ├─→ Azure OpenAI
        │   ├─→ text-embedding-3-large
        │   └─→ gpt-4.1-mini
        │
        ├─→ Azure AI Search (Vector DB)
        │   └─→ ~100K-500K chunks
        │
        ├─→ Azure SQL Database
        │   └─→ Metadata + History
        │
        ├─→ Azure Blob Storage
        │   └─→ Document Files
        │
        ├─→ Azure Storage Queue
        │   └─→ Background Processing
        │
        ├─→ Azure Cache for Redis
        │   └─→ Session + Cache
        │
        └─→ Application Insights
            └─→ Monitoring + Logs
```

### Key Improvements Over Local Setup

1. **Async Document Processing**
   - Upload returns immediately
   - Processing happens in background
   - Real-time progress updates
   - Can handle 300+ documents in parallel

2. **Scalability**
   - Auto-scaling backend (2-20 instances)
   - Azure AI Search for fast vector queries
   - Distributed processing with queues
   - Handles concurrent users

3. **Reliability**
   - High availability (99.9% SLA)
   - Automatic backups
   - Disaster recovery
   - Health monitoring

4. **Security**
   - Azure AD authentication
   - Managed identities
   - Encrypted at rest and in transit
   - Key Vault for secrets

---

## Cost Estimates

### Production Environment (~300-400 docs/engagement)

| Service | Tier | Monthly Cost | Notes |
|---------|------|--------------|-------|
| Azure Container Apps | 2-4 instances | $100-200 | Auto-scaling backend |
| Azure AI Search | Standard | $250 | 500K chunks capacity |
| Azure SQL Database | Standard S1 | $30 | 20 DTU, 250GB |
| Azure Blob Storage | Hot tier | $20 | ~100GB documents |
| Azure Cache for Redis | Standard C1 | $75 | 1GB cache |
| Azure Static Web Apps | Standard | $10 | Frontend hosting |
| Application Insights | Pay-as-you-go | $20-50 | Monitoring |
| Storage Queue | Pay-as-you-go | $5 | Message processing |
| **Total** | | **$510-640/mo** | |

**Notes:**
- Azure OpenAI costs separate (~$50-200/mo usage-based)
- Can reduce to ~$200/mo for dev/staging environments
- Free tier available for testing (limited features)

---

## Deployment Steps

### Step 1: Deploy Azure Infrastructure

```bash
cd infrastructure

# Make deploy script executable
chmod +x deploy.sh

# Deploy (takes 10-15 minutes)
./deploy.sh prod eastus

# This creates:
# - Resource group: auditapp-prod-rg
# - All Azure resources
# - Outputs saved to deployment-outputs.json
```

### Step 2: Configure Environment Variables

The deployment script creates `.env.production` file. Review and update:

```bash
# Edit production config
nano ../.env.production

# Required updates:
# 1. Verify Azure OpenAI endpoint (using existing cog-obghpsbi63abq)
# 2. Update SQL admin password (if changed)
# 3. Add any custom domain configurations
```

### Step 3: Deploy Backend to Container Apps

```bash
# Login to Azure Container Registry
ACR_NAME=$(az deployment group show \
  --name auditapp-deployment-* \
  --resource-group auditapp-prod-rg \
  --query properties.outputs.containerRegistryName.value -o tsv)

az acr login --name $ACR_NAME

# Build and push Docker image
cd ../backend
docker build -t ${ACR_NAME}.azurecr.io/audit-app-backend:latest .
docker push ${ACR_NAME}.azurecr.io/audit-app-backend:latest

# Deploy to Container Apps
az containerapp create \
  --name auditapp-prod-backend \
  --resource-group auditapp-prod-rg \
  --environment $(az deployment group show \
    --name auditapp-deployment-* \
    --resource-group auditapp-prod-rg \
    --query properties.outputs.containerAppEnvName.value -o tsv) \
  --image ${ACR_NAME}.azurecr.io/audit-app-backend:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 10 \
  --cpu 1.0 \
  --memory 2.0Gi \
  --env-vars-file ../.env.production
```

### Step 4: Run Database Migrations

```bash
# Install alembic if not already
pip install alembic

# Initialize alembic (if first time)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial production schema"

# Apply to production database
alembic upgrade head
```

### Step 5: Deploy Frontend

```bash
cd ../frontend

# Build production bundle
npm run build

# Deploy to Azure Static Web Apps
az staticwebapp create \
  --name auditapp-prod-frontend \
  --resource-group auditapp-prod-rg \
  --source ./dist \
  --location eastus \
  --branch main \
  --app-location "/" \
  --output-location "dist"
```

### Step 6: Configure CI/CD (Optional)

```bash
# Set up GitHub Actions secrets:
# 1. Go to GitHub repo → Settings → Secrets
# 2. Add the following secrets:
#    - AZURE_CREDENTIALS
#    - ACR_USERNAME
#    - ACR_PASSWORD
#    - AZURE_STATIC_WEB_APPS_API_TOKEN
#    - PRODUCTION_API_URL

# Workflows will auto-deploy on push to main branch
```

---

## Post-Deployment

### 1. Verify Health

```bash
# Check backend health
BACKEND_URL=$(az containerapp show \
  --name auditapp-prod-backend \
  --resource-group auditapp-prod-rg \
  --query properties.configuration.ingress.fqdn -o tsv)

curl https://$BACKEND_URL/health

# Expected: {"status":"healthy"}
```

### 2. Test Document Upload

```bash
# Create test engagement
curl -X POST https://$BACKEND_URL/api/engagements \
  -H "Content-Type: application/json" \
  -d '{"name":"Production Test","description":"Testing deployment"}'

# Upload test document
curl -X POST https://$BACKEND_URL/api/engagements/{engagement_id}/documents \
  -F "files=@test-document.pdf"
```

### 3. Monitor Processing

```bash
# Check document status
curl https://$BACKEND_URL/api/engagements/{engagement_id}/documents

# Watch Application Insights for telemetry
az monitor app-insights query \
  --app $(az deployment group show \
    --name auditapp-deployment-* \
    --resource-group auditapp-prod-rg \
    --query properties.outputs.appInsightsName.value -o tsv) \
  --analytics-query "traces | where message contains 'document' | take 50"
```

### 4. Load Testing (Recommended)

```bash
# Install locust
pip install locust

# Run load test (simulate 100 users uploading documents)
locust -f tests/load_test.py --host https://$BACKEND_URL
```

---

## Monitoring

### Application Insights Dashboards

1. **Performance Monitoring**
   - Request duration
   - Dependency calls (Azure OpenAI, SQL, etc.)
   - Exception rates

2. **Usage Analytics**
   - Active users
   - Documents processed
   - Questions asked
   - Success/failure rates

3. **Custom Metrics**
   - Document processing time
   - Vector search latency
   - Embedding generation time
   - Cache hit rates

### Alerts (Recommended)

```bash
# Create alert for high error rate
az monitor metrics alert create \
  --name high-error-rate \
  --resource-group auditapp-prod-rg \
  --scopes $(az containerapp show \
    --name auditapp-prod-backend \
    --resource-group auditapp-prod-rg \
    --query id -o tsv) \
  --condition "avg requests/failed > 5" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email admin@company.com

# Create alert for high response time
az monitor metrics alert create \
  --name high-response-time \
  --resource-group auditapp-prod-rg \
  --condition "avg requests/duration > 3000" \
  --window-size 5m
```

---

## Troubleshooting

### Common Issues

#### 1. Document Processing Fails

**Symptoms:** Documents stuck in "processing" status

**Solution:**
```bash
# Check container logs
az containerapp logs show \
  --name auditapp-prod-backend \
  --resource-group auditapp-prod-rg \
  --follow

# Check queue messages
az storage queue list \
  --account-name $(az storage account list \
    --resource-group auditapp-prod-rg \
    --query [0].name -o tsv)
```

#### 2. Slow Vector Search

**Symptoms:** Q&A responses take > 5 seconds

**Solution:**
```bash
# Check Azure AI Search performance
az search service show \
  --name $(az search service list \
    --resource-group auditapp-prod-rg \
    --query [0].name -o tsv) \
  --resource-group auditapp-prod-rg

# Consider upgrading search tier
az search service update \
  --name your-search-service \
  --resource-group auditapp-prod-rg \
  --partition-count 2 \
  --replica-count 2
```

#### 3. Out of Memory Errors

**Symptoms:** Container restarts frequently

**Solution:**
```bash
# Increase container memory
az containerapp update \
  --name auditapp-prod-backend \
  --resource-group auditapp-prod-rg \
  --memory 4.0Gi \
  --cpu 2.0
```

#### 4. Database Connection Issues

**Symptoms:** 500 errors, "connection refused"

**Solution:**
```bash
# Check firewall rules
az sql server firewall-rule list \
  --server $(az sql server list \
    --resource-group auditapp-prod-rg \
    --query [0].name -o tsv) \
  --resource-group auditapp-prod-rg

# Add Container Apps IP range
az sql server firewall-rule create \
  --name AllowContainerApps \
  --server your-sql-server \
  --resource-group auditapp-prod-rg \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 255.255.255.255
```

---

## Security Best Practices

### 1. Use Managed Identities
- Enable for Container Apps
- Remove API keys from config
- Use Azure AD authentication everywhere

### 2. Enable Private Endpoints
- Azure SQL
- Azure Storage
- Azure AI Search
- Restricts to virtual network only

### 3. Implement Rate Limiting
```python
# Add to main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

### 4. Regular Security Scans
```bash
# Scan Docker images
docker scan ${ACR_NAME}.azurecr.io/audit-app-backend:latest

# Check for vulnerable dependencies
pip-audit
npm audit
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Check Application Insights for errors
- Monitor processing queue depth
- Review failed document uploads

**Weekly:**
- Review cost analysis
- Check resource utilization
- Update dependencies if needed

**Monthly:**
- Database maintenance (index optimization)
- Review and rotate secrets
- Backup validation
- Performance tuning

---

## Rollback Procedure

If deployment fails:

```bash
# Rollback backend
az containerapp revision copy \
  --name auditapp-prod-backend \
  --resource-group auditapp-prod-rg \
  --from-revision previous-revision-name

# Rollback frontend
git revert HEAD
git push origin main
```

---

## Support Contacts

- Azure Support: portal.azure.com → Help + Support
- Application Insights: Real-time diagnostics
- Emergency: Check runbook in `/docs/runbook.md`

---

## Next Steps After Deployment

1. ✅ Test with 50-100 documents
2. ✅ Load test with simulated users
3. ✅ Set up monitoring alerts
4. ✅ Configure backup policies
5. ✅ Document admin procedures
6. ✅ Train users on the system
7. ✅ Plan disaster recovery
8. ✅ Schedule regular maintenance

---

**Estimated Deployment Time:** 2-3 hours (first time)

**Recommended Team:** 1 DevOps engineer, 1 Developer

**Support Level:** 24/7 monitoring recommended for production
