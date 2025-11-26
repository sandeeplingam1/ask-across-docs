# Bug Report - Azure Deployment Issues

## Status: Backend is RUNNING but has issues

**Backend URL:** https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io  
**Frontend URL:** https://blue-island-0b509160f.3.azurestaticapps.net  
**Health Status:** DEGRADED (database unhealthy)

---

## Issues Found

### 1. ❌ CRITICAL: Database Health Check Error
**Location:** `backend/app/main.py` line 83  
**Error:** `Textual SQL expression 'SELECT 1' should be explicitly declared as text('SELECT 1')`  
**Impact:** Health check failing, container may be restarted  
**Fix:** Use SQLAlchemy's `text()` function

```python
# Current (WRONG):
session.execute("SELECT 1")

# Should be:
from sqlalchemy import text
session.execute(text("SELECT 1"))
```

---

### 2. ⚠️ Database Session Type Mismatch
**Location:** `backend/app/db_session.py`  
**Issue:** Using sync SQLAlchemy but many routes expect async  
**Impact:** Routes may fail with async/sync errors  
**Details:**
- Changed to sync for pyodbc compatibility
- But routes still have `async def` and `AsyncSession`
- Will cause runtime errors

**Fix:** Need to update routes to use sync sessions OR use async with different driver

---

###3. ⚠️ Missing Azure OpenAI API Key
**Location:** `backend/app/config.py` line 20  
**Issue:** `azure_openai_api_key` is Optional but code likely expects it  
**Impact:** Embeddings and chat will fail  
**Check:** Is API key set in Container App environment variables?

---

### 4. ⚠️ AZURE_OPENAI_API_KEY Environment Variable
**Location:** Container App configuration  
**Issue:** API key might not be passed as secret/env variable  
**Impact:** Cannot call Azure OpenAI  
**Check:** Bicep sets these env variables:
- AZURE_OPENAI_ENDPOINT ✅
- AZURE_OPENAI_API_VERSION ✅  
- AZURE_OPENAI_EMBEDDING_DEPLOYMENT ✅
- AZURE_OPENAI_CHAT_DEPLOYMENT ✅
- AZURE_OPENAI_API_KEY ??? (NOT IN BICEP!)

---

### 5. ⚠️ Hardcoded Azure OpenAI Endpoint
**Location:** `infrastructure/main.bicep` line 323  
**Issue:** Hardcoded to `cog-obghpsbi63abq.openai.azure.com`  
**Impact:** May work if that's your resource, but not portable  
**Recommendation:** Should be a parameter

---

### 6. ⚠️ Frontend API URL Configuration
**Location:** Static Web App  
**Issue:** Static Web Apps don't automatically inject build-time env vars  
**Impact:** Frontend may call wrong API URL  
**Check:** Is VITE_API_URL properly configured in Static Web App settings?

---

### 7. ⚠️ CORS Configuration
**Location:** `backend/app/config.py` lines 78-81  
**Issue:** Hardcoded frontend URL doesn't match actual Static Web App URL  
**Current:** `auditapp-frontend.graydune-dadabae1.eastus.azurecontainerapps.io`  
**Actual:** `blue-island-0b509160f.3.azurestaticapps.net`  
**Impact:** Frontend requests will be blocked by CORS  
**Priority:** HIGH

---

### 8. ⚠️ Database Connection String Format
**Location:** `infrastructure/main.bicep` line 287  
**Issue:** Using `mssql+pyodbc://` with URL-encoded password  
**Concern:** Complex password encoding may have issues  
**Current:** `P%40ssw0rd123%21` (P@ssw0rd123!)  
**Recommendation:** Use simpler password or test thoroughly

---

### 9. ❌ Async/Sync Mismatch in Routes
**Location:** All route files  
**Issue:** Routes are `async def` but using sync database sessions  
**Impact:** Will cause errors at runtime  
**Examples:**
- `backend/app/routes/engagements.py` - uses `AsyncSession`
- `backend/app/routes/documents.py` - uses `AsyncSession`  
- But `db_session.py` provides sync `Session`

---

### 10. ⚠️ Background Processing Not Configured
**Location:** `background_tasks.py`  
**Issue:** Code exists but no worker/Celery configured  
**Impact:** Document processing may not complete  
**Note:** Celery/Redis configured but not deployed as separate worker

---

## Priority Fixes

### IMMEDIATE (Deploy won't work without these):

1. **Fix health check SQL** - Causes container restarts
2. **Add AZURE_OPENAI_API_KEY to Bicep** - AI won't work
3. **Fix CORS** - Frontend can't call backend

### HIGH (App will error):

4. **Fix async/sync session mismatch** - Routes will crash
5. **Configure Static Web App env vars** - Frontend calls wrong API

### MEDIUM (Should fix for production):

6. **Remove hardcoded Azure OpenAI endpoint** - Make it portable
7. **Deploy Celery worker** - Background processing won't work
8. **Test database password encoding** - May cause connection errors

---

## Quick Fixes to Deploy Now

Here are the exact changes needed to make it work:

### File 1: `backend/app/main.py`
```python
# Line 68-100, replace health_check function:
@app.get("/health")
def health_check():
    """Health check endpoint for Container Apps"""
    from app.db_session import get_session
    from sqlalchemy import text  # ADD THIS IMPORT
    
    health_status = {
        "status": "healthy",
        "version": "1.1.0",
        "environment": settings.environment,
        "vector_db": settings.vector_db_type,
        "services": {}
    }
    
    # Check database connectivity
    try:
        for session in get_session():
            session.execute(text("SELECT 1"))  # FIX: Add text()
            health_status["services"]["database"] = "healthy"
            break
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
    
    # Rest same...
```

### File 2: `infrastructure/main.bicep`
```bicep
# Line 322-336, add AZURE_OPENAI_API_KEY:
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: 'https://cog-obghpsbi63abq.openai.azure.com/'
            }
            {
              name: 'AZURE_OPENAI_API_KEY'  # ADD THIS
              secretRef: 'azure-openai-api-key'  # ADD THIS
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: '2024-02-15-preview'
            }

# Also add to secrets section (around line 280):
        {
          name: 'azure-openai-api-key'
          value: 'YOUR-AZURE-OPENAI-KEY-HERE'  # REPLACE WITH REAL KEY
        }
```

### File 3: `backend/app/config.py`
```python
# Line 76-82, fix CORS:
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        origins = [origin.strip() for origin in self.backend_cors_origins.split(",")]
        # Add production frontend URL if in staging/production
        if not self.is_development:
            origins.extend([
                "https://blue-island-0b509160f.3.azurestaticapps.net",  # FIX: Use actual URL
                "https://*.azurestaticapps.net"  # Allow all Static Web Apps
            ])
        return origins
```

---

## Testing Commands

After fixes, test:

```bash
# 1. Test health check
curl https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io/health

# 2. Test API root
curl https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io/

# 3. Test CORS (from browser console on frontend):
fetch('https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io/api/engagements')
  .then(r => r.json())
  .then(console.log)
```

---

## Estimated Impact

**If fixed:**
- Backend health: Healthy ✅
- Frontend can call API ✅  
- Can create engagements ✅
- Can upload documents (but processing may fail without worker) ⚠️
- Can ask questions ✅

**Still needs work:**
- Background document processing (need Celery worker)
- Production secrets management (use Key Vault)
- Monitoring/alerts setup
