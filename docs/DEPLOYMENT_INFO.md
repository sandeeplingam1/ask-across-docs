# Development vs Production Setup

## Current Setup: LOCAL DEVELOPMENT

The application is currently configured for **local development** on your machine. This means:

### What You Have Now:

**Backend Server:**
- Runs on: `http://localhost:8000`
- Type: Development server (uvicorn with --reload)
- Database: SQLite (local file at `./data/audit_app.db`)
- Vector Store: ChromaDB (local files at `./data/chromadb/`)
- File Storage: Local filesystem (`./data/uploads/`)

**Frontend Server:**
- Runs on: `http://localhost:5173`
- Type: Vite development server (hot reload enabled)
- API Proxy: Forwards requests to backend at localhost:8000

**Access:**
- Only accessible from YOUR computer
- NOT accessible from internet
- NOT accessible from other computers on your network
- Perfect for development and testing

---

## Development Server Features

### Advantages:
- Hot reload (code changes update automatically)
- Detailed error messages
- Easy debugging
- No deployment costs
- Fast iteration
- Can test offline

### Limitations:
- Only accessible locally
- Not suitable for team use
- Performance not optimized
- Data stored locally only
- No redundancy/backup

---

## How to Use

### Start the Application:

```bash
# From the Audit App root directory
./start.sh
```

This will:
1. Check prerequisites (virtual env, .env file, dependencies)
2. Start backend server on port 8000
3. Start frontend server on port 5173
4. Show logs from both servers

### Access the Application:

Open your browser to: **http://localhost:5173**

### Stop the Application:

```bash
./stop.sh
```

### View Logs:

While running:
```bash
tail -f backend.log     # Backend logs
tail -f frontend.log    # Frontend logs
```

---

## Cloud Deployment (Production)

If you want to make this accessible online, you would need to deploy to cloud:

### Option 1: Azure (Recommended for this app)

**Backend:**
- Deploy to: Azure Container Apps or Azure App Service
- Database: Azure SQL Database or Azure PostgreSQL
- Vector Store: Azure AI Search
- File Storage: Azure Blob Storage
- Cost: ~$50-200/month depending on usage

**Frontend:**
- Deploy to: Azure Static Web Apps
- Cost: Free tier available, ~$10/month for standard

**Total Setup Time:** 2-4 hours (with deployment automation)

### Option 2: Other Cloud Providers

- AWS: EC2 + S3 + RDS
- Google Cloud: Cloud Run + Cloud Storage + Cloud SQL
- Heroku: App + Postgres addon
- Vercel/Netlify: Frontend only, need separate backend

---

## Current Startup Process

When you run `./start.sh`:

```
1. Script checks prerequisites
   ├─ Backend virtual environment exists?
   ├─ .env file exists?
   ├─ Frontend dependencies installed?
   └─ Ports 8000 and 5173 available?

2. Start Backend
   ├─ Activate Python virtual environment
   ├─ Run: python -m uvicorn app.main:app --reload
   ├─ Backend initializes:
   │  ├─ Creates ./data/ directory
   │  ├─ Creates database tables
   │  ├─ Initializes ChromaDB
   │  └─ Starts listening on port 8000
   └─ Saves process ID to .backend.pid

3. Start Frontend
   ├─ Run: npm run dev
   ├─ Vite dev server starts
   ├─ Proxies API calls to localhost:8000
   └─ Saves process ID to .frontend.pid

4. Both servers running
   ├─ Backend: http://localhost:8000
   ├─ Frontend: http://localhost:5173
   └─ Logs: backend.log, frontend.log
```

---

## Recommendation

**For Now (Development/Testing):**
- Use the local setup with `./start.sh`
- Perfect for development and testing
- Zero cloud costs
- Full control over everything

**When Ready for Production:**
- Deploy to Azure for multi-user access
- Switch to cloud database and vector store
- Set up proper authentication
- Configure backups and monitoring

**Migration is Easy:**
- Change environment variables
- Deploy code (no code changes needed!)
- Vector store abstraction makes it seamless

---

## Summary

**What You're Running:** Local development servers on your machine

**Access:** http://localhost:5173 (your computer only)

**To Start:** `./start.sh`

**To Stop:** `./stop.sh`

**Cost:** $0 (runs on your computer)

**Next Step After Development:** Deploy to Azure for cloud access
