# Resource Reuse Analysis for Audit App Staging

## Executive Summary

**Recommendation: Reuse 5 resources, Create 3 new ones**

- ✅ **Can Reuse**: Azure OpenAI, AI Search, Storage Account, Key Vault, Container Registry
- ❌ **Must Create New**: SQL Database, Redis Cache, Container App Environment

**Estimated Staging Cost with Reuse**: ~$50-75/month (vs $150-250/month if creating all new)

---

## Detailed Analysis of rg-saga-dev Resources

### 1. ✅ **Azure OpenAI** - `cog-obghpsbi63abq`

**Status**: ✅ **REUSE - Already Using**

| Property | Value |
|----------|-------|
| Location | North Central US |
| Tier | S0 (Standard) |
| Endpoint | https://cog-obghpsbi63abq.openai.azure.com/ |
| Deployments | gpt-4.1-mini, text-embedding-3-large |

**Analysis**:
- ✅ Already configured in your `.env` file
- ✅ Pay-per-use model (no fixed cost)
- ✅ Sufficient capacity for multiple apps
- ✅ Using Azure AD auth (no API key conflicts)

**Decision**: **REUSE** - No changes needed, already working

**Cost Impact**: $0 additional (usage-based billing)

---

### 2. ✅ **Azure AI Search** - `gptkb-obghpsbi63abq`

**Status**: ✅ **CAN REUSE - Recommended for Staging**

| Property | Value |
|----------|-------|
| Location | North Central US |
| Tier | Basic |
| Replicas | 1 |
| Partitions | 1 |
| Indexes | 0 (Empty - no data) |

**Analysis**:
- ✅ Currently empty - no existing data
- ✅ Supports multiple isolated indexes
- ✅ Audit app would create: `audit-documents` index
- ✅ Saga app could use: `saga-index` (separate)
- ⚠️ Basic tier = shared resources (might be slower under heavy load)
- ✅ Perfect for staging/testing

**Decision**: **REUSE for Staging** - Create separate index name

**Cost Impact**: $0 (already paying ~$75/month)

**Implementation**:
```bash
# Use existing AI Search
AZURE_SEARCH_ENDPOINT=https://gptkb-obghpsbi63abq.search.windows.net
AZURE_SEARCH_INDEX_NAME=audit-staging-documents  # Different name
```

---

### 3. ✅ **Storage Account** - `stobghpsbi63abq`

**Status**: ✅ **CAN REUSE - Recommended**

| Property | Value |
|----------|-------|
| Location | North Central US |
| Tier | Standard LRS |
| Access Tier | Hot |
| Existing Containers | azure-webjobs-hosts, azure-webjobs-secrets, content, engagements, tokens |

**Analysis**:
- ✅ Has existing containers for saga app
- ✅ Can create new container: `audit-staging-documents`
- ✅ Complete isolation between containers
- ✅ Standard LRS sufficient for staging
- ✅ Cost scales with usage

**Decision**: **REUSE** - Create separate container

**Cost Impact**: ~$5-10/month additional (storage usage only)

**Implementation**:
```bash
# Create new container in existing storage
az storage container create \
  --name audit-staging-documents \
  --account-name stobghpsbi63abq
```

---

### 4. ❌ **PostgreSQL Database** - `saga-db-74765`

**Status**: ❌ **DO NOT REUSE - Create New**

| Property | Value |
|----------|-------|
| Location | North Central US |
| Tier | Burstable |
| Version | PostgreSQL 14 |
| Storage | 32 GB |
| Databases | azure_maintenance, postgres, azure_sys, saga_production |

**Analysis**:
- ❌ Already has `saga_production` database in use
- ⚠️ Could create new database `audit_staging` on same server
- ❌ **Risk**: Shared resources could cause performance issues
- ❌ **Risk**: Schema conflicts, connection pool sharing
- ❌ **Risk**: Backup/restore affects both apps
- ✅ **Better**: Create dedicated SQL Database for Audit App

**Decision**: **CREATE NEW Azure SQL Database**

**Reason**: 
- Audit App uses SQL Server (not PostgreSQL) in Bicep template
- Different database engine (PostgreSQL vs SQL Server)
- Avoid cross-app dependencies

**Cost Impact**: ~$5/month (Azure SQL Basic tier for staging)

---

### 5. ❌ **Redis Cache** - Not Present

**Status**: ❌ **MUST CREATE NEW**

**Analysis**:
- ❌ No Redis in rg-saga-dev
- ✅ Need Redis for Celery background tasks
- ✅ Need Redis for caching

**Decision**: **CREATE NEW**

**Cost Impact**: ~$16/month (Basic C0 tier for staging)

---

### 6. ✅ **Key Vault** - `saga-kv`

**Status**: ✅ **CAN REUSE - Recommended**

| Property | Value |
|----------|-------|
| Location | North Central US |
| Tier | Standard |

**Analysis**:
- ✅ Can store secrets with prefixes: `audit-staging-*`
- ✅ RBAC-based access control (isolated permissions)
- ✅ No additional cost (pay per operation)
- ✅ Centralized secret management

**Decision**: **REUSE** - Use secret naming convention

**Cost Impact**: $0 (minimal operations)

**Implementation**:
```bash
# Store secrets with audit-staging prefix
az keyvault secret set --vault-name saga-kv \
  --name audit-staging-sql-password \
  --value "YourPassword"
```

---

### 7. ✅ **Container Registry** - `sagaapiregistry`

**Status**: ✅ **CAN REUSE - Recommended**

| Property | Value |
|----------|-------|
| Location | North Central US |
| Tier | Basic |
| Login Server | sagaapiregistry.azurecr.io |
| Existing Images | saga/api-saga-dev, saga-api, saga-api-container |

**Analysis**:
- ✅ Can store images with different names: `audit-app-backend`, `audit-app-frontend`
- ✅ Complete isolation between image repositories
- ✅ Basic tier supports multiple images
- ✅ Already has admin enabled

**Decision**: **REUSE** - Push images with audit-app prefix

**Cost Impact**: $0 (already paying ~$5/month)

**Implementation**:
```bash
# Build and push to existing registry
docker build -t sagaapiregistry.azurecr.io/audit-app-backend:staging .
docker push sagaapiregistry.azurecr.io/audit-app-backend:staging
```

---

### 8. ❌ **Container App Environment** - `saga-container-env`

**Status**: ⚠️ **COULD REUSE, BUT BETTER TO CREATE NEW**

| Property | Value |
|----------|-------|
| Location | North Central US |

**Analysis**:
- ⚠️ Could deploy audit app containers to same environment
- ❌ Shared networking and monitoring
- ❌ Harder to isolate logs and metrics
- ❌ Both apps restart if environment restarts
- ✅ Better: Create separate environment for staging

**Decision**: **CREATE NEW** - Better isolation

**Cost Impact**: $0 (Container App Environment is free, only pay for apps)

---

## Summary Table

| Resource | Type | Action | Cost Savings | Risk |
|----------|------|--------|--------------|------|
| Azure OpenAI | AI Service | ✅ Reuse | N/A (usage-based) | None - already using |
| AI Search | Vector DB | ✅ Reuse | $75/month | Low - separate indexes |
| Storage Account | Blob Storage | ✅ Reuse | ~$20/month | None - separate containers |
| PostgreSQL DB | Database | ❌ Create New SQL | $0 | N/A - different engine |
| Redis Cache | Cache | ❌ Create New | $0 | N/A - doesn't exist |
| Key Vault | Secrets | ✅ Reuse | ~$5/month | None - RBAC isolated |
| Container Registry | Images | ✅ Reuse | ~$5/month | None - separate repos |
| Container Env | Hosting | ❌ Create New | $0 | N/A - better isolation |
| Log Analytics | Monitoring | ✅ Could Share | ~$10/month | Low |

**Total Savings**: ~$100-115/month for staging

---

## Recommended Staging Architecture

### Resources in `rg-saga-dev` (Reused):
```
rg-saga-dev/
├── cog-obghpsbi63abq (Azure OpenAI)          ← Reuse
├── gptkb-obghpsbi63abq (AI Search)           ← Reuse (new index)
├── stobghpsbi63abq (Storage)                 ← Reuse (new container)
├── saga-kv (Key Vault)                       ← Reuse (prefixed secrets)
└── sagaapiregistry (Container Registry)      ← Reuse (new images)
```

### Resources in `auditapp-staging-rg` (New):
```
auditapp-staging-rg/
├── auditapp-staging-sql (Azure SQL)          ← Create New
├── auditapp-staging-redis (Redis Cache)      ← Create New
├── auditapp-staging-containerenv (Container Apps Env) ← Create New
└── auditapp-staging-insights (App Insights)  ← Create New
```

---

## Implementation Plan

### Step 1: Modify Bicep Template
Add parameters to make resources optional:
```bicep
@description('Use existing AI Search instead of creating new')
param useExistingAISearch bool = false

@description('Existing AI Search service name')
param existingAISearchName string = ''

@description('Existing AI Search resource group')
param existingAISearchRG string = ''
```

### Step 2: Deploy Staging with Reuse
```bash
cd infrastructure
./deploy.sh staging eastus \
  --use-existing-ai-search true \
  --existing-ai-search-name gptkb-obghpsbi63abq \
  --existing-ai-search-rg rg-saga-dev \
  --use-existing-storage true \
  --existing-storage-name stobghpsbi63abq \
  --existing-storage-rg rg-saga-dev \
  --use-existing-keyvault true \
  --existing-keyvault-name saga-kv \
  --use-existing-acr true \
  --existing-acr-name sagaapiregistry
```

### Step 3: Manual Setup for Reused Resources
```bash
# Create blob container
az storage container create \
  --name audit-staging-documents \
  --account-name stobghpsbi63abq

# Create queue
az storage queue create \
  --name audit-staging-processing \
  --account-name stobghpsbi63abq

# No AI Search setup needed - app will create index automatically
```

---

## Cost Comparison

### Option A: Reuse Everything Possible (Recommended)
| Resource | Monthly Cost |
|----------|--------------|
| Azure SQL Basic | $5 |
| Redis Basic C0 | $16 |
| Container Apps (2 instances) | $25 |
| App Insights | $5 |
| Storage (incremental) | $5 |
| **Total** | **~$56/month** |

### Option B: Create All New Resources
| Resource | Monthly Cost |
|----------|--------------|
| Azure SQL Basic | $5 |
| AI Search Basic | $75 |
| Redis Basic C0 | $16 |
| Storage Account | $25 |
| Container Registry | $5 |
| Key Vault | $5 |
| Container Apps | $25 |
| App Insights | $5 |
| **Total** | **~$161/month** |

**Savings with Reuse**: ~$105/month (65% cost reduction)

---

## Security Considerations

### ✅ Safe to Reuse:
1. **Azure OpenAI** - Using Azure AD auth (no key sharing)
2. **AI Search** - Separate indexes (complete data isolation)
3. **Storage Account** - Separate containers (no cross-access)
4. **Key Vault** - RBAC permissions (can restrict by app)
5. **Container Registry** - Separate repositories (no conflicts)

### ⚠️ Considerations:
1. **Shared Cost Billing** - All resources bill to same subscription
2. **Performance** - Basic AI Search tier is shared (monitor performance)
3. **Quotas** - Shared storage account quotas (unlikely to hit limits)

---

## Next Steps

1. **Review this analysis** - Confirm reuse strategy
2. **Modify Bicep template** - Add optional resource parameters
3. **Update deploy.sh script** - Accept resource reuse flags
4. **Deploy staging** - Test with reused resources
5. **Monitor costs** - Validate cost savings
6. **Plan production** - Use all new resources for prod

---

## Questions to Answer

1. ✅ Is saga app using AI Search? **No - it's empty**
2. ✅ Can we share Storage Account? **Yes - separate containers**
3. ✅ Should we use existing PostgreSQL? **No - different engine (need SQL Server)**
4. ✅ Is Container Registry shared? **Yes - safe with separate image names**

**Ready to proceed?** I can modify the Bicep template to support resource reuse.
