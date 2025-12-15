# Quick Setup Guide: Worker Secrets Configuration

## Current Status
✅ API Container: Deployed and working (no background processor)  
✅ Worker Container: Created but needs secrets to function  
⏳ Secrets: Need to be added to worker  

## Why Secrets Are Needed
The worker needs access to:
1. **Database** - To find queued documents
2. **Blob Storage** - To download uploaded files
3. **AI Search** - To index processed documents

## Setup Instructions (Choose One Method)

### Method 1: Azure Portal (Recommended - Easiest)

1. **Open Azure Portal**: https://portal.azure.com
2. **Get Secrets from Backend**:
   - Navigate to: Resource Groups > auditapp-staging-rg > auditapp-staging-backend
   - Click "Secrets" in the left menu
   - You'll see these secrets (values are hidden):
     - `database-url`
     - `storage-connection-string`
     - `azure-search-api-key`

3. **Option A - If you created the backend**, you know these values
4. **Option B - Contact your Azure admin** to get these values from Key Vault: `kv-auditapp-wgjuafflp2`

5. **Add Secrets to Worker**:
   - Navigate to: Resource Groups > auditapp-staging-rg > auditapp-staging-worker
   - Click "Secrets" in the left menu
   - Click "+ Add" three times to add:
     ```
     Name: database-url
     Value: <SQL connection string from backend>
     
     Name: storage-connection-string
     Value: <Blob storage connection string from backend>
     
     Name: azure-search-api-key
     Value: <AI Search admin key from backend>
     ```

6. **Update Environment Variables**:
   - Still in worker container, click "Containers" in left menu
   - Click "Edit and deploy"
   - Scroll to "Environment variables"
   - Add these THREE variables:
     ```
     Name: DATABASE_URL
     Type: Reference a secret
     Value: database-url
     
     Name: AZURE_STORAGE_CONNECTION_STRING
     Type: Reference a secret
     Value: storage-connection-string
     
     Name: AZURE_SEARCH_API_KEY
     Type: Reference a secret
     Value: azure-search-api-key
     ```
   - Click "Create" to deploy new revision

7. **Verify Worker Started**:
   ```bash
   az containerapp logs show --name auditapp-staging-worker -g auditapp-staging-rg --follow
   ```
   You should see:
   ```
   [WORKER] Document Worker Starting...
   [WORKER] Database initialized
   [WORKER] Worker ready - waiting for documents...
   ```

### Method 2: Azure CLI (If you have Key Vault access)

```bash
# Get your Azure admin to grant you this role:
az role assignment create \
  --assignee your-email@company.com \
  --role "Key Vault Secrets Officer" \
  --scope "/subscriptions/.../resourceGroups/auditapp-staging-rg/providers/Microsoft.KeyVault/vaults/kv-auditapp-wgjuafflp2"

# Then run:
DB_URL=$(az keyvault secret show --vault-name kv-auditapp-wgjuafflp2 --name database-url --query value -o tsv)
STORAGE=$(az keyvault secret show --vault-name kv-auditapp-wgjuafflp2 --name storage-connection-string --query value -o tsv)
SEARCH=$(az keyvault secret show --vault-name kv-auditapp-wgjuafflp2 --name azure-search-api-key --query value -o tsv)

# Add secrets to worker
az containerapp secret set \
  --name auditapp-staging-worker \
  --resource-group auditapp-staging-rg \
  --secrets \
    database-url="$DB_URL" \
    storage-connection-string="$STORAGE" \
    azure-search-api-key="$SEARCH"

# Update worker to use secrets
az containerapp update \
  --name auditapp-staging-worker \
  --resource-group auditapp-staging-rg \
  --set-env-vars \
    DATABASE_URL=secretref:database-url \
    AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection-string \
    AZURE_SEARCH_API_KEY=secretref:azure-search-api-key
```

## Testing After Setup

### 1. Check Worker Logs
```bash
az containerapp logs show --name auditapp-staging-worker -g auditapp-staging-rg --follow
```

Expected output:
```
[2025-12-15T22:XX:XX] [WORKER] INFO - 🚀 Document Worker Starting...
[2025-12-15T22:XX:XX] [WORKER] INFO - Database initialized
[2025-12-15T22:XX:XX] [WORKER] INFO - No stuck documents found
[2025-12-15T22:XX:XX] [WORKER] INFO - 📋 Worker ready - waiting for documents...
```

### 2. Upload a Test Document
1. Go to your frontend: https://blue-island-0b509160f.3.azurestaticapps.net
2. Upload a document
3. Watch worker logs - you should see:
   ```
   [WORKER] INFO - Processing 1 queued document(s)
   [WORKER] INFO - Starting document abc-123: test.pdf
   [WORKER] INFO - Created 15 chunks for test.pdf
   [WORKER] INFO - ✅ Completed test.pdf - 15 chunks indexed
   ```

### 3. Verify Document Status
```bash
# Get documents for your engagement
curl "https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io/api/engagements/{engagement-id}/documents" | jq '.[] | {filename, status}'
```

Expected progression:
- After upload: `status: "queued"`
- During processing: `status: "processing"`
- After completion: `status: "completed"`

## Troubleshooting

### Worker Not Starting
**Symptom**: Worker logs show connection errors  
**Solution**: Check that all 3 secrets are added correctly

### Documents Stay "Queued"
**Symptom**: Status doesn't change from "queued"  
**Possible Causes**:
1. Worker not running - check replica count:
   ```bash
   az containerapp replica list --name auditapp-staging-worker -g auditapp-staging-rg
   ```
2. Database connection issue - check worker logs for errors
3. Worker doesn't have secrets - add them using Method 1 or 2 above

### Worker Crashes
**Symptom**: Replica keeps restarting  
**Solution**: Check logs for error message:
```bash
az containerapp logs show --name auditapp-staging-worker -g auditapp-staging-rg --tail 100
```

Common issues:
- Invalid connection string format
- Network access denied to SQL/Storage/Search
- Missing Python dependencies (shouldn't happen, but rebuild if needed)

## Architecture Benefits

### Before (In-Process Background Processor)
- ❌ API response time: 2+ minutes or timeout
- ❌ UI freezes waiting for responses
- ❌ Document processing blocks API requests
- ❌ One bad document crashes entire API
- ❌ Cannot scale API and processing separately

### After (Separate Worker Process)
- ✅ API response time: <200ms
- ✅ UI loads instantly
- ✅ Document processing completely isolated
- ✅ Worker failures don't affect API
- ✅ Can scale API (1-3 replicas) and worker (1 replica) independently
- ✅ Enterprise-grade architecture

## Monitoring Commands

```bash
# Check API status
curl https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io/health

# Check API response time
time curl -s https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io/api/engagements

# Watch worker processing
az containerapp logs show --name auditapp-staging-worker -g auditapp-staging-rg --follow

# Check document counts by status
curl "https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io/api/engagements/{id}/documents" | jq 'group_by(.status) | map({status: .[0].status, count: length})'
```

## Cost Impact
- API: 1 CPU, 2Gi memory @ 1-3 replicas = ~$30/month
- Worker: 0.5 CPU, 1Gi memory @ 1 replica = ~$15/month
- **Total additional cost**: ~$15/month
- **Value**: 100% uptime, professional architecture, instant UI

## Next Steps
1. Follow Method 1 or Method 2 above to add secrets
2. Verify worker starts successfully
3. Upload a test document
4. Confirm document processes to "completed" status
5. Test Q&A on the completed document

## Support
If you encounter issues:
1. Check worker logs first
2. Verify all secrets are configured
3. Ensure worker replica is "Running"
4. Check database connectivity
5. Review WORKER_ARCHITECTURE.md for detailed info
