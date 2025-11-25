# Audit App - Deployment Information

## Version 1.1.0 - Staging Environment

### 🌐 Application URLs

**Frontend (User Interface)**
```
https://auditapp-frontend.graydune-dadabae1.eastus.azurecontainerapps.io
```

**Backend API**
```
https://auditapp-backend.graydune-dadabae1.eastus.azurecontainerapps.io
```

**API Documentation**
```
https://auditapp-backend.graydune-dadabae1.eastus.azurecontainerapps.io/docs
```

**Health Check**
```
https://auditapp-backend.graydune-dadabae1.eastus.azurecontainerapps.io/health
```

---

## 📦 Deployment Architecture

### Azure Resources (auditapp-staging-rg)

- **Container Apps Environment**: `auditapp-staging-containerenv`
- **Container Registry**: `auditappstagingacrwgjuafflp2o4o.azurecr.io`
- **Azure SQL Database**: `auditapp-staging-sql-wgjuafflp2o4o`
- **Redis Cache**: `auditapp-staging-redis-wgjuafflp2o4o`
- **Log Analytics**: `auditapp-staging-logs-wgjuafflp2o4o`
- **Application Insights**: Connected for monitoring

### Reused Resources (rg-saga-dev)

- **Azure OpenAI**: `cog-obghpsbi63abq` (gpt-4.1-mini, text-embedding-3-large)
- **Azure AI Search**: `gptkb-obghpsbi63abq` (audit-staging-documents index)
- **Azure Storage**: `stobghpsbi63abq` (audit-staging-documents container)

---

## 🚀 Deployment Process

### Automatic Deployment Script

```bash
cd infrastructure
./deploy-apps.sh staging
```

This script:
1. Builds Docker images for backend (Python/FastAPI) and frontend (React/Vite)
2. Pushes images to Azure Container Registry
3. Creates/updates Container Apps with environment variables
4. Configures health checks and auto-scaling

### Manual Deployment

#### Backend Container App
```bash
az containerapp update \
  --name auditapp-backend \
  --resource-group auditapp-staging-rg \
  --image auditappstagingacrwgjuafflp2o4o.azurecr.io/auditapp-backend:latest
```

#### Frontend Container App
```bash
az containerapp update \
  --name auditapp-frontend \
  --resource-group auditapp-staging-rg \
  --image auditappstagingacrwgjuafflp2o4o.azurecr.io/auditapp-frontend:latest
```

---

## 📊 Monitoring & Logs

### View Application Logs

**Backend logs (real-time)**
```bash
az containerapp logs tail \
  --name auditapp-backend \
  --resource-group auditapp-staging-rg \
  --follow
```

**Frontend logs (real-time)**
```bash
az containerapp logs tail \
  --name auditapp-frontend \
  --resource-group auditapp-staging-rg \
  --follow
```

### Application Insights
- Connection String configured in environment variables
- View metrics, traces, and logs in Azure Portal
- Application Insights resource: `auditapp-staging-insights-wgjuafflp2o4o`

### Container App Metrics
```bash
az containerapp show \
  --name auditapp-backend \
  --resource-group auditapp-staging-rg \
  --query "properties.{status:runningStatus,replicas:template.scale}" -o table
```

---

## 🔧 Configuration

### Environment Variables

All environment variables are loaded from `.env.production`:

**Backend**
- `ENVIRONMENT=staging`
- `DATABASE_URL` - Azure SQL connection string (pyodbc format)
- `AZURE_OPENAI_ENDPOINT` - OpenAI endpoint URL
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` - text-embedding-3-large
- `AZURE_OPENAI_CHAT_DEPLOYMENT` - gpt-4.1-mini
- `AZURE_SEARCH_ENDPOINT` - AI Search endpoint
- `AZURE_SEARCH_INDEX_NAME` - audit-staging-documents
- `AZURE_STORAGE_CONNECTION_STRING` - Blob storage connection
- `REDIS_URL` - Redis cache connection
- `VECTOR_DB_TYPE=azure_search`

**Frontend**
- `VITE_API_URL` - Backend API URL (set during build)

### Update Environment Variables

After updating `.env.production`, redeploy:
```bash
cd infrastructure
./deploy-apps.sh staging
```

---

## 🔄 Scaling Configuration

### Backend Container App
- **Min Replicas**: 1
- **Max Replicas**: 3
- **CPU**: 1.0 cores
- **Memory**: 2Gi
- **Target Port**: 8000

### Frontend Container App
- **Min Replicas**: 1
- **Max Replicas**: 3
- **CPU**: 0.5 cores
- **Memory**: 1Gi
- **Target Port**: 80

### Manual Scaling
```bash
az containerapp update \
  --name auditapp-backend \
  --resource-group auditapp-staging-rg \
  --min-replicas 2 \
  --max-replicas 5
```

---

## 🛡️ Security

### CORS Configuration
Backend is configured to accept requests from:
- Frontend production URL: `https://auditapp-frontend.graydune-dadabae1.eastus.azurecontainerapps.io`
- Any `*.azurecontainerapps.io` domain (staging pattern)
- Localhost (for development)

### Database Security
- Azure SQL with firewall rules
- TLS/SSL enforced connections
- Connection timeout: 30 seconds

### Container Registry
- Admin access enabled for deployments
- Credentials stored as Container App secrets

---

## 📝 Version History

### v1.1.0 (2025-11-25)
**Features**
- ✅ Production-ready health checks with service validation
- ✅ Improved CORS handling for cloud deployment
- ✅ Azure AD authentication support (Managed Identity ready)
- ✅ Enhanced startup logging with environment details
- ✅ 30-second API timeout for cloud reliability
- ✅ Fixed DATABASE_URL format for SQLAlchemy + pyodbc
- ✅ Document viewer with Mammoth.js for DOCX rendering
- ✅ Text highlighting for cited passages
- ✅ Similarity threshold filtering (0.5) for Q&A accuracy
- ✅ Confidence scoring (High ≥75%, Medium ≥60%)

### v1.0.0 (2025-11-24)
**Initial Release**
- Basic RAG functionality
- Document upload and processing
- Question answering with sources
- Engagement management
- ChromaDB/Azure AI Search support

---

## 🔗 Quick Links

- **GitHub Repository**: https://github.com/sandeeplingam1/Audit-App
- **Azure Portal**: https://portal.azure.com
- **Resource Group**: auditapp-staging-rg (East US)

---

## 🆘 Troubleshooting

### Container not starting
```bash
# Check container logs
az containerapp logs tail --name auditapp-backend -g auditapp-staging-rg

# Check revision status
az containerapp revision list --name auditapp-backend -g auditapp-staging-rg -o table
```

### Database connection issues
1. Verify Azure SQL firewall rules allow Container App IPs
2. Check DATABASE_URL format in `.env.production`
3. Ensure ODBC Driver 18 is installed in container (it is in Dockerfile)

### Frontend not loading
1. Check if VITE_API_URL is correctly set in frontend build
2. Verify CORS settings in backend include frontend URL
3. Check nginx configuration in `frontend/nginx.conf`

### Health check failing
```bash
# Test health endpoint directly
curl https://auditapp-backend.graydune-dadabae1.eastus.azurecontainerapps.io/health

# Check detailed health status
az containerapp show --name auditapp-backend -g auditapp-staging-rg \
  --query "properties.{health:latestRevisionFqdn,status:runningStatus}"
```

---

## 📞 Support

For issues or questions:
1. Check Application Insights for errors and traces
2. Review container logs for detailed error messages
3. Verify all environment variables are correctly set
4. Ensure Azure services (SQL, Redis, Storage) are running

---

**Last Updated**: 2025-11-25  
**Deployed By**: sandeep.lingam@sbscyber.com  
**Environment**: Staging (Azure Container Apps)
