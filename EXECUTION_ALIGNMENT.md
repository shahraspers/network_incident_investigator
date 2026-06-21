# 🎯 Execution & Port Alignment Guide

**Status**: ✅ Updated - All documentation and execution instructions aligned with latest changes

---

## 🔑 Critical: Environment Activation

**⚠️ IMPORTANT: Each terminal must activate the virtual environment FIRST**

Before running ANY command, activate the environment in your terminal:

```bash
# Windows (PowerShell)
venv\Scripts\activate

# Windows (Command Prompt)
venv\Scripts\activate.bat

# macOS/Linux
source venv/bin/activate
```

You should see `(venv)` prefix in your terminal prompt after activation.

---

## Port Configuration Summary

| Component | Default Port | Service Type | Status |
|-----------|--------------|--------------|--------|
| **Frontend (Streamlit)** | 8501 | Web UI | ✅ Active |
| **Backend API (FastAPI)** | 8000 | REST API | ✅ Active |
| **Ollama (LLM)** | 11434 | Local Model Server | 🟡 Optional |

---

## 🚀 Complete Startup Procedure

### Step 1: Open 3 Terminals (Windows PowerShell or macOS Terminal)

### Terminal 1: Backend API (FastAPI)

```bash
# Step 1: Activate environment
venv\Scripts\activate

# Step 2: Start FastAPI server
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```

**Output should show:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Verify API is working:**
- Open browser to: `http://localhost:8000/docs` (Swagger UI)
- Or: `http://localhost:8000/api/health` (health check)

---

### Terminal 2: Frontend UI (Streamlit)

```bash
# Step 1: Activate environment
venv\Scripts\activate

# Step 2: Start Streamlit UI
streamlit run frontend/app.py
```

**Output should show:**
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

**Verify UI is working:**
- Browser should auto-open to: `http://localhost:8501`
- Or open manually to same URL

---

### Terminal 3 (Optional): Ollama for Local LLM

```bash
# Only needed if you want local GenAI provider
# NOTE: Ollama must be installed separately on your system

# Step 1: Activate environment (optional, not required for ollama)
venv\Scripts\activate

# Step 2: Start Ollama
ollama serve
```

**Output should show:**
```
Listening on [::1]:11434 (and port 11434 on the default interface)
```

**Verify Ollama is working:**
- Run in another terminal: `curl http://localhost:11434/api/tags`
- Should return JSON with available models

---

## Recent Updates & Fixes

### UI Improvements
✅ **Simplified Sidebar**: Removed problematic health check display
✅ **Better Error Handling**: GenAI analysis gracefully handles provider failures
✅ **LLM Metrics**: Now tracked even if provider unavailable

### API Improvements
✅ **Metrics Recording**: LLM calls counted regardless of success/failure
✅ **Timezone Fix**: Metrics datetime comparisons now work correctly
✅ **Graceful Degradation**: All endpoints return valid JSON responses

### Monitoring & Governance
✅ **Platform Metrics**: Tracks total requests, LLM calls, errors, latency
✅ **Token Usage**: Estimates and records LLM token consumption
✅ **Audit Logging**: All operations logged with trace IDs

---

## Uvicorn Execution Details

### Standard Command Breakdown

```bash
uvicorn backend.api:app                    # Module and app object
  --host 0.0.0.0                           # Listen on all network interfaces
  --port 8000                              # Port number
  --reload                                 # Auto-reload on file changes (dev only)
```

### For Production Deployment

```bash
# Multiple workers (disable reload)
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --workers 4

# With SSL/HTTPS
uvicorn backend.api:app --host 0.0.0.0 --port 8000 \
  --ssl-keyfile=./key.pem --ssl-certfile=./cert.pem

# Behind reverse proxy
uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

### 1. Backend API (Port 8000) - Provides Governance

These governance endpoints are served by FastAPI:
- `/api/health` - Health status
- `/api/metrics` - Platform metrics
- `/api/metrics/latency` - Latency stats
- `/api/metrics/tokens` - Token usage & costs
- `/api/metrics/errors` - Error statistics
- `/api/governance/users` - User management
- `/api/governance/audit-logs` - Audit trail

### 2. Frontend UI (Port 8501) - Consumes API

The Streamlit frontend can:
- Display governance dashboards (when API is running)
- Show audit logs via API calls
- Monitor health status
- Track metrics in real-time

### 3. Proper Startup Order

```bash
# Step 1: Start Backend (port 8000) - MUST be first
Terminal 1> uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload

# Wait 2-3 seconds for API to initialize...

# Step 2: Start Frontend (port 8501)
Terminal 2> streamlit run frontend/app.py

# Step 3: Verify Everything Works
curl http://localhost:8000/api/health        # Check API
curl http://localhost:8000/api/metrics       # Check metrics
# Then open http://localhost:8501 in browser
```

---

## Testing Governance via Curl

### Verify API is Running (Port 8000)
```bash
# Simple health check
curl http://localhost:8000/health

# Detailed health with governance status
curl http://localhost:8000/api/health

# Platform metrics
curl http://localhost:8000/api/metrics

# User management (requires X-User header)
curl -H "X-User: admin@example.com" \
  http://localhost:8000/api/governance/users

# Audit logs
curl http://localhost:8000/api/governance/audit-logs
```

### Upload Data via API (Port 8000)
```bash
curl -X POST http://localhost:8000/api/data/upload \
  -F "file=@sample_data.csv" \
  -H "X-User: analyst@example.com"
```

### Run Anomaly Detection (Port 8000)
```bash
curl -X POST http://localhost:8000/api/anomaly/detect \
  -H "Content-Type: application/json" \
  -H "X-User: analyst@example.com" \
  -H "X-Trace-ID: req_abc123" \
  -d '{
    "metrics": ["rsrp", "throughput_mbps"],
    "method": "zscore",
    "threshold": 3.0
  }'
```

---

## Port Already in Use? (Troubleshooting)

### Streamlit Port (8501) in Use
```bash
# Use different port
streamlit run frontend/app.py --server.port 8502
```

### FastAPI Port (8000) in Use
```bash
# Use different port
uvicorn backend.api:app --host 0.0.0.0 --port 9000 --reload

# Then update .env or config to point to new port
```

### Find What's Using a Port
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :8000
kill -9 <PID>
```

---

## Environment Variables (.env)

The `.env` file controls port and connection settings:

```bash
# Backend API
API_HOST=0.0.0.0
API_PORT=8000

# Frontend (Streamlit uses CLI args, not .env)
# Set via: streamlit run app.py --server.port 8501

# LLM Provider Configuration
GENAI_PROVIDER=ollama_local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Optional: Alternative providers
# GENAI_PROVIDER=openai
# OPENAI_API_KEY=sk-...

# Governance
GOVERNANCE_ENABLED=true
AUDIT_LOG_FILE=logs/audit.jsonl
```

---

## Documentation Alignment

### ✅ Updated Files

| File | Port Info | Uvicorn Command |
|------|-----------|-----------------|
| **README.md** | ✅ Correct (8000, 8501) | ✅ `uvicorn backend.api:app ...` |
| **GETTING_STARTED.md** | ✅ Correct (8000, 8501) | ✅ `uvicorn backend.api:app ...` |
| **backend/api.py** | ✅ Correct (main block) | ✅ `uvicorn.run()` with port 8000 |
| **GOVERNANCE_AND_MONITORING.md** | ✅ References port 8000 | ✅ Assumes API running |

### Previous Issues Fixed

❌ **Issue 1**: `python -m backend.api` not clear about uvicorn  
✅ **Fix**: Changed to explicit `uvicorn backend.api:app --host 0.0.0.0 --port 8000`

❌ **Issue 2**: Governance docs assumed API was running without explaining how  
✅ **Fix**: Added prerequisite: "Make sure backend API is running first"

❌ **Issue 3**: No unified "run both" instruction  
✅ **Fix**: Added "Option 3: Run Both Simultaneously" with clear port assignment

---

## Docker/Compose Alternative

If using Docker:

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    command: uvicorn backend.api:app --host 0.0.0.0 --port 8000
    environment:
      - GENAI_PROVIDER=ollama_local
      - OLLAMA_BASE_URL=http://ollama:11434
    
  frontend:
    image: streamlit:latest
    ports:
      - "8501:8501"
    command: streamlit run frontend/app.py --server.address 0.0.0.0
    depends_on:
      - backend
    
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
```

Start all with:
```bash
docker-compose up -d
```

Access:
- Frontend: http://localhost:8501
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Ollama: http://localhost:11434

---

## Summary: All Systems Running

When everything is properly configured:

```
┌─────────────────────────────────┐
│ Streamlit UI                    │
│ http://localhost:8501           │  ← Port 8501 (Browser)
└─────────────┬───────────────────┘
              │ HTTP Requests
              ↓
┌─────────────────────────────────┐
│ FastAPI Backend                 │
│ http://localhost:8000           │  ← Port 8000 (API Server)
│ - Anomaly Detection             │
│ - GenAI Reasoning               │
│ - Governance & Monitoring       │
│ - Metrics & Health              │
└─────────────┬───────────────────┘
              │ HTTP Requests
              ↓
┌─────────────────────────────────┐
│ Ollama LLM Server               │
│ http://localhost:11434          │  ← Port 11434 (Optional)
└─────────────────────────────────┘
```

✅ **All ports are now consistent and documented**
