# Setup Guide

Complete installation and configuration instructions for the Audit App.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Azure Prerequisites](#azure-prerequisites)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [First Run](#first-run)
6. [Verification](#verification)

---

## System Requirements

### Operating System
- macOS (current environment)
- Linux (untested but should work)
- Windows (requires WSL or Git Bash for shell scripts)

### Required Software

| Software | Minimum Version | How to Check | Installation |
|----------|----------------|--------------|--------------|
| Python | 3.11+ | `python3 --version` | `brew install python` |
| Node.js | 18+ | `node --version` | `brew install node` |
| npm | 9+ | `npm --version` | Included with Node.js |
| Homebrew | Any | `brew --version` | See homebrew.sh |

### Hardware Requirements
- 4GB RAM minimum (8GB recommended)
- 2GB free disk space
- Internet connection (for Azure OpenAI API calls)

---

## Azure Prerequisites

### Required Azure Resources

You need an **Azure OpenAI Service** resource with two model deployments.

### Step 1: Create Azure OpenAI Resource

1. Log in to Azure Portal (portal.azure.com)
2. Click "Create a resource"
3. Search for "Azure OpenAI"
4. Click "Create"
5. Fill in details:
   - Subscription: Your subscription
   - Resource group: Create new or use existing
   - Region: Choose nearest region (e.g., East US)
   - Name: Choose a unique name
   - Pricing tier: Standard S0
6. Click "Review + create" then "Create"
7. Wait for deployment (1-2 minutes)

### Step 2: Deploy Models

After resource creation:

1. Go to your Azure OpenAI resource
2. Click "Model deployments" in left menu
3. Click "Create new deployment"

**Embedding Model:**
- Model: `text-embedding-ada-002`
- Deployment name: `text-embedding-ada-002` (or your choice)
- Keep other defaults
- Click "Create"

**Chat Model:**
- Model: `gpt-4` (or `gpt-35-turbo` if gpt-4 not available)
- Deployment name: `gpt-4` (or your choice)
- Keep other defaults
- Click "Create"

### Step 3: Get Credentials

1. In your Azure OpenAI resource, click "Keys and Endpoint"
2. Copy:
   - Endpoint URL (e.g., https://your-resource.openai.azure.com/)
   - KEY 1 (or KEY 2)
3. Save these for configuration step

**Important Notes:**
- Do NOT share your API keys
- Keys provide full access to your resource
- Regenerate keys if compromised

---

## Installation Steps

### Step 1: Verify Prerequisites

```bash
# Check Python version
python3 --version
# Expected: Python 3.11.x or higher

# Check Node.js version
node --version
# Expected: v18.x.x or higher

# Check npm version
npm --version
# Expected: 9.x.x or higher
```

If any command fails, install the missing software:

```bash
# Install Python
brew install python

# Install Node.js (includes npm)
brew install node
```

### Step 2: Navigate to Project

```bash
cd "/Users/sandeeplingam/VibeCoding/Audit App"
```

### Step 3: Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Create environment configuration file
cp .env.example .env
```

**Expected Output:**
- venv/ directory created
- Packages installed (should take 1-2 minutes)
- .env file created

### Step 4: Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Install Node.js dependencies
npm install
```

**Expected Output:**
- node_modules/ directory created
- ~174 packages installed (should take 30-60 seconds)

### Step 5: Return to Project Root

```bash
cd ..
```

---

## Configuration

### Edit Environment File

Open `backend/.env` in your text editor and update the following values:

```bash
# Option 1: Use nano editor
nano backend/.env

# Option 2: Use VS Code
code backend/.env

# Option 3: Use any text editor
open -a TextEdit backend/.env
```

### Required Configuration

Replace the placeholder values with your Azure OpenAI credentials:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE-NAME.openai.azure.com/
AZURE_OPENAI_API_KEY=YOUR-API-KEY-HERE
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4
```

**Where to find these values:**
- `ENDPOINT`: Azure Portal → Your OpenAI Resource → Keys and Endpoint
- `API_KEY`: Azure Portal → Your OpenAI Resource → Keys and Endpoint
- `EMBEDDING_DEPLOYMENT`: Name you gave when deploying text-embedding-ada-002
- `CHAT_DEPLOYMENT`: Name you gave when deploying gpt-4

### Optional Configuration

The following have sensible defaults but can be customized:

```env
# Vector Database (default: chromadb)
VECTOR_DB_TYPE=chromadb

# Document Processing
MAX_UPLOAD_SIZE_MB=100
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Database (default: SQLite)
DATABASE_URL=sqlite+aiosqlite:///./data/audit_app.db
```

### Save and Close

Save the file (Ctrl+O in nano, Cmd+S in editors) and exit.

---

## First Run

### Start the Application

From the project root directory:

```bash
./start.sh
```

### What Happens

The startup script will:

1. **Check Prerequisites**
   - Verify backend/venv exists
   - Verify backend/.env exists
   - Verify frontend/node_modules exists
   - Check ports 8000 and 5173 are available

2. **Start Backend Server**
   - Activate Python virtual environment
   - Run FastAPI application
   - Create ./data directory
   - Create database file (audit_app.db)
   - Create ChromaDB directory
   - Initialize database tables
   - Start listening on port 8000

3. **Start Frontend Server**
   - Run Vite development server
   - Start listening on port 5173
   - Proxy API requests to backend

4. **Display Information**
   - Frontend URL: http://localhost:5173
   - Backend URL: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Log file locations

### Expected Console Output

```
==========================================
Audit App - Starting Development Servers
==========================================

Checking ports...
Ports 8000 and 5173 are available

Starting Backend Server...
Location: http://localhost:8000
API Docs: http://localhost:8000/docs

Backend PID: 12345
Waiting for backend to initialize...
Backend is running and healthy!

Starting Frontend Server...
Location: http://localhost:5173

Frontend PID: 12346

==========================================
Servers Started Successfully!
==========================================

Access the application:
  Frontend: http://localhost:5173
  Backend:  http://localhost:8000
  API Docs: http://localhost:8000/docs
```

### Access the Application

Open your web browser and navigate to:
```
http://localhost:5173
```

---

## Verification

### 1. Check Backend Health

Open a new terminal and run:

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status":"healthy"}
```

### 2. Check API Documentation

Visit in browser:
```
http://localhost:8000/docs
```

You should see the Swagger UI with all API endpoints.

### 3. Check Frontend

Visit in browser:
```
http://localhost:5173
```

You should see the Audit App homepage with "New Engagement" button.

### 4. Test Basic Functionality

**Create Engagement:**
1. Click "New Engagement" button
2. Enter name: "Test Engagement"
3. Click "Create"
4. Verify engagement appears in list

**Check Database:**
```bash
# From project root
sqlite3 data/audit_app.db "SELECT * FROM engagements;"
```

You should see your test engagement.

### 5. View Logs

If something isn't working, check the logs:

```bash
# Backend logs
tail -f backend.log

# Frontend logs
tail -f frontend.log
```

---

## Stopping the Application

To stop both servers:

```bash
./stop.sh
```

This will:
1. Stop the backend server
2. Stop the frontend server
3. Clean up process ID files
4. Kill any remaining processes on ports 8000 and 5173

---

## Next Steps

After successful setup:

1. **Upload Documents:** Add PDF or DOCX files to test document processing
2. **Ask Questions:** Try the Q&A functionality
3. **Review History:** Check the history tab to see saved Q&As
4. **Read Documentation:** Review README.md for detailed features
5. **Explore API:** Use http://localhost:8000/docs to test API endpoints

---

## Troubleshooting

### "Port already in use"

If port 8000 or 5173 is in use:

```bash
# Find process using port 8000
lsof -ti:8000

# Kill process
kill -9 $(lsof -ti:8000)

# Same for port 5173
kill -9 $(lsof -ti:5173)
```

### "Virtual environment not found"

```bash
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### "npm: command not found"

```bash
brew install node
cd frontend
npm install
```

### Database Initialization Fails

```bash
rm -rf data/
# Restart application (will recreate database)
./start.sh
```

### Azure OpenAI Authentication Error

- Verify endpoint URL is correct (should end with .openai.azure.com/)
- Verify API key is correct (check for extra spaces)
- Verify deployment names match exactly
- Check deployments exist in Azure Portal

---

## Support

If you encounter issues not covered here:

1. Check the logs in backend.log and frontend.log
2. Review API documentation at http://localhost:8000/docs
3. Verify all prerequisites are installed
4. Ensure Azure OpenAI deployments are active

---

## Summary

**Setup Checklist:**
- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] Backend virtual environment created
- [ ] Backend dependencies installed
- [ ] Frontend dependencies installed
- [ ] .env file configured with Azure credentials
- [ ] Application starts successfully
- [ ] Can access http://localhost:5173
- [ ] Can create engagement
- [ ] Can upload document
- [ ] Can ask question

Once all items are checked, your setup is complete!
