# Pluggable Architecture Guide

## System Overview

The Network Incident Investigator is now a **fully modular, pluggable platform** that can be deployed across different frontends, integrated with various LLM providers, and connected to multiple data sources.

```
┌──────────────────────────────────────────────────────────────────┐
│              PLUGGABLE ARCHITECTURE (With Governance)             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  FRONTEND LAYER (Pluggable)                               │  │
│  │  ├─ Streamlit (web UI)                                   │  │
│  │  ├─ Flask (REST API + web UI)                            │  │
│  │  ├─ CLI (command-line interface)                         │  │
│  │  ├─ React/Vue (JavaScript SPA)                           │  │
│  │  └─ Custom (implement IFrontend)                         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  REST API (Backend - Always Available)                    │  │
│  │  Data:      /api/data/*                                  │  │
│  │  Anomaly:   /api/anomaly/*                               │  │
│  │  GenAI:     /api/genai/*                                 │  │
│  │  Metrics:   /api/metrics, /api/metrics/* (NEW)          │  │
│  │  Health:    /api/health (NEW - detailed)                 │  │
│  │  Governance:/api/governance/* (NEW)                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  GOVERNANCE & MONITORING LAYER (NEW)                      │  │
│  │  ├─ Logging (structured traces)                          │  │
│  │  ├─ Evaluation (quality, drift, hallucination)           │  │
│  │  ├─ Observability (metrics, latency, costs)              │  │
│  │  ├─ Governance (RBAC, audit, PII scrubbing)             │  │
│  │  └─ Monitoring (health checks, failover)                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  SERVICES LAYER                                           │  │
│  │  ├─ Anomaly Detection (4 algorithms)                     │  │
│  │  ├─ GenAI Reasoning (pluggable providers)                │  │
│  │  └─ Context Building                                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  DATA SOURCE LAYER (Pluggable)                            │  │
│  │  ├─ CSV files                                            │  │
│  │  ├─ REST APIs (Backend APIs)                             │  │
│  │  ├─ SQL Databases (PostgreSQL, MySQL)                    │  │
│  │  ├─ Streaming (Kafka, Kinesis, Pub/Sub)                  │  │
│  │  ├─ Cloud Storage (S3, GCS, Azure)                       │  │
│  │  └─ Custom (implement DataSource)                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  GENAI PROVIDERS (Pluggable)                              │  │
│  │  ├─ Ollama (Local - Default)                             │  │
│  │  ├─ OpenAI (Cloud - Fallback)                            │  │
│  │  ├─ Google Vertex AI (Enterprise)                        │  │
│  │  ├─ Azure OpenAI (Enterprise)                            │  │
│  │  └─ Custom (implement LLMProvider)                       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Streamlit (Default)

```bash
# Install dependencies
pip install -r requirements.txt

# Run Streamlit frontend
streamlit run frontend/app.py

# Access at http://localhost:8501
```

### 2. Flask Frontend

```bash
# Run Flask frontend
python -m frontend.flask_frontend

# Access at http://localhost:5000

# API endpoints available:
# POST /api/data/upload
# GET  /api/data/preview
# POST /api/anomaly/detect
# GET  /api/anomaly/results
# POST /api/genai/explain
# GET  /api/summary
```

### 3. CLI Frontend

```bash
# Run CLI interface
python -c "from frontend.abstract_frontend import CLIFrontend, FrontendWorkflow; frontend = CLIFrontend(); workflow = FrontendWorkflow(frontend); workflow.run_workflow()"
```

### 4. REST API Only

```bash
# Run backend API (no frontend)
python -m backend.api

# Access at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

---

## Configuration

### Environment Variables

```bash
# GenAI Provider Configuration
export GENAI_PROVIDER=ollama_local  # or: openai, vertex_ai, azure_openai

# Ollama (Local)
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama2

# OpenAI (Cloud)
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-3.5-turbo

# Vertex AI (Google Cloud)
export GCP_PROJECT_ID=my-project
export VERTEX_AI_LOCATION=us-central1

# Azure OpenAI
export AZURE_OPENAI_ENDPOINT=https://...
export AZURE_OPENAI_KEY=...
export AZURE_OPENAI_DEPLOYMENT_ID=...

# Data Source
export DATA_SOURCE_TYPE=csv  # or: rest_api, database, streaming, cloud_storage
export DATA_SOURCE_PATH=/path/to/data.csv
```

### Configuration File (.env)

```bash
# Create .env file
cp .env.example .env

# Edit .env with your settings
GENAI_PROVIDER=ollama_local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral  # mistral is faster than llama2
```

---

## Deployment Scenarios

### Scenario 1: Local Development (Ollama + Streamlit)

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Pull model
ollama pull mistral

# Terminal 3: Run Streamlit
streamlit run frontend/app.py
```

**Pros:** No API keys, fast local processing, works offline
**Cons:** Depends on Ollama running, slower than cloud APIs

---

### Scenario 2: Cloud Analytics (OpenAI + Flask)

```bash
# Set API key
export OPENAI_API_KEY=sk-your-key

# Run Flask frontend
python -m frontend.flask_frontend

# Or use with backend API
python -m backend.api
```

**Pros:** Fast, reliable, production-grade
**Cons:** API costs, requires internet, data sent to cloud

---

### Scenario 3: Enterprise Deployment (Vertex AI + Custom Data)

```bash
# Configure Google Cloud
export GCP_PROJECT_ID=my-enterprise-project
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Connect to database
export DATA_SOURCE_TYPE=database
export DATABASE_URL=postgresql://user:pass@db.example.com/kpi_db
export DATABASE_QUERY="SELECT * FROM network_kpi WHERE timestamp > NOW() - INTERVAL '24 hours'"

# Run API
python -m backend.api
```

**Pros:** Secure, scalable, integrates with enterprise systems
**Cons:** More complex setup, requires cloud account

---

### Scenario 4: Hybrid Deployment (Multi-Frontend + Multiple Providers)

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Ollama for local processing
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  # Backend API (core service)
  backend:
    build:
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      GENAI_PROVIDER: ollama_local
      OLLAMA_BASE_URL: http://ollama:11434
    depends_on:
      - ollama

  # Streamlit frontend
  streamlit:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    ports:
      - "8501:8501"
    environment:
      BACKEND_URL: http://backend:8000
    depends_on:
      - backend

  # Flask frontend
  flask:
    build:
      context: .
      dockerfile: Dockerfile.flask
    ports:
      - "5000:5000"
    environment:
      BACKEND_URL: http://backend:8000
    depends_on:
      - backend

  # PostgreSQL database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: network_kpi
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - streamlit
      - flask
      - backend

volumes:
  ollama_data:
  postgres_data:
```

**Deploy with:** `docker-compose up -d`

---

## Provider Configuration Examples

### Example 1: Local Ollama (Default)

**Setup:**
```bash
# Install Ollama from https://ollama.ai
ollama serve
ollama pull mistral
```

**Configuration:**
```python
from services.genai_reasoning.provider_registry import LLMProviderRegistry

config = {
    "base_url": "http://localhost:11434",
    "model": "mistral"  # faster than llama2
}

provider = LLMProviderRegistry.create("ollama_local", config)
```

**Pros:** Free, offline, fast for small models
**Cons:** Requires local hardware, slower inference

---

### Example 2: OpenAI API

**Setup:**
```bash
# Get API key from https://platform.openai.com
export OPENAI_API_KEY=sk-...
```

**Configuration:**
```python
config = {
    "api_key": os.getenv("OPENAI_API_KEY"),
    "model": "gpt-4"
}

provider = LLMProviderRegistry.create("openai", config)
```

**Pros:** Best quality, GPT-4 available, reliable
**Cons:** Costs per API call, requires API key, data sent to OpenAI

---

### Example 3: Google Vertex AI

**Setup:**
```bash
# Install Google Cloud SDK
gcloud auth application-default login

# Set project
export GCP_PROJECT_ID=my-project
```

**Configuration:**
```python
config = {
    "project_id": os.getenv("GCP_PROJECT_ID"),
    "location": "us-central1"
}

provider = LLMProviderRegistry.create("vertex_ai", config)
```

**Pros:** Enterprise-grade, integrates with GCP ecosystem
**Cons:** Requires GCP account, pricing model complex

---

### Example 4: Azure OpenAI

**Setup:**
```bash
# Get credentials from Azure portal
export AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com/
export AZURE_OPENAI_KEY=...
export AZURE_OPENAI_DEPLOYMENT_ID=gpt-35-turbo
```

**Configuration:**
```python
config = {
    "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "api_key": os.getenv("AZURE_OPENAI_KEY"),
    "deployment_id": os.getenv("AZURE_OPENAI_DEPLOYMENT_ID")
}

provider = LLMProviderRegistry.create("azure_openai", config)
```

**Pros:** Enterprise support, data stays in Azure
**Cons:** Requires Azure subscription, setup complexity

---

## Data Source Examples

### Example 1: CSV Upload

```python
from backend.data_source_registry import DataSourceRegistry

# Create CSV source
source = DataSourceRegistry.create(
    "csv",
    filepath="/path/to/network_kpi.csv"
)

# Load data
df = source.load()
```

---

### Example 2: REST API (TELUS Backend)

```python
source = DataSourceRegistry.create(
    "rest_api",
    endpoint="https://api.telus.com/network-kpi",
    headers={"Authorization": f"Bearer {os.getenv('TELUS_API_TOKEN')}"},
    params={"start_time": "2026-06-20T00:00:00Z"}
)

df = source.load()
```

---

### Example 3: PostgreSQL Database

```python
source = DataSourceRegistry.create(
    "database",
    connection_string="postgresql://user:pass@localhost:5432/network_kpi",
    query="""
        SELECT timestamp, site_id, rsrp, rsrq, sinr, 
               throughput_mbps, latency_ms, dropped_call_rate
        FROM kpi_metrics
        WHERE timestamp > NOW() - INTERVAL '24 hours'
        ORDER BY timestamp DESC
    """
)

df = source.load()
```

---

### Example 4: Kafka Streaming

```python
source = DataSourceRegistry.create(
    "streaming",
    source_type="kafka",
    config={
        "bootstrap_servers": "kafka.example.com:9092",
        "topic": "network-kpi-events"
    }
)

# Load latest 100 messages
df = source.load(batch_size=100, timeout=30)
```

---

### Example 5: AWS S3

```python
source = DataSourceRegistry.create(
    "cloud_storage",
    storage_type="s3",
    config={
        "bucket": "telus-network-data",
        "key": "kpi/2026-06-20/metrics.csv"
    }
)

df = source.load()
```

---

## Custom Extensions

### Creating a Custom Frontend

```python
# frontend/custom_frontend.py
from frontend.abstract_frontend import IFrontend

class CustomFrontend(IFrontend):
    def upload_data(self):
        # Your implementation
        pass
    
    def get_detection_config(self):
        # Your implementation
        pass
    
    # ... implement other methods
```

### Creating a Custom LLM Provider

```python
# services/genai_reasoning/providers/custom_provider.py
from services.genai_reasoning.provider_registry import ILLMProvider

class CustomProvider(ILLMProvider):
    def explain_anomaly(self, context: dict) -> dict:
        # Your implementation
        pass
    
    def health_check(self) -> bool:
        # Your implementation
        pass
```

### Creating a Custom Data Source

```python
# backend/custom_source.py
from backend.data_source_registry import IDataSource

class CustomSource(IDataSource):
    def load(self, **kwargs):
        # Your implementation
        pass
    
    def validate(self) -> bool:
        # Your implementation
        pass
```

---

## Monitoring & Debugging

### Check Provider Status

```python
from services.genai_reasoning.provider_registry import LLMProviderRegistry

# List available providers
providers = LLMProviderRegistry.list_providers()

# Check provider config
config = LLMProviderRegistry.get_provider_config("openai")

# Validate configuration
is_valid, errors = LLMProviderRegistry.validate_config("openai", my_config)
```

### Check Data Source Status

```python
from backend.data_source_registry import DataSourceRegistry

# List available sources
sources = DataSourceRegistry.list_sources()

# Validate source
source = DataSourceRegistry.create("rest_api", endpoint="...")
is_valid = source.validate()

# Get schema
schema = source.get_schema()
```

---

## Performance Tips

### 1. Use Ollama for Speed

For real-time analysis with lower latency:
```bash
ollama pull neural-chat  # Faster than llama2
# or
ollama pull mistral     # Good balance
```

### 2. Use Cloud Providers for Accuracy

For higher quality explanations:
```bash
export GENAI_PROVIDER=openai
export OPENAI_MODEL=gpt-4  # Best quality
```

### 3. Cache Results

```python
# Store detection results to avoid re-running
import pickle

# Save results
with open("detection_results.pkl", "wb") as f:
    pickle.dump(result_df, f)

# Load results
with open("detection_results.pkl", "rb") as f:
    result_df = pickle.load(f)
```

---

## Troubleshooting

### Issue: "Provider not available"

**Solution:** Check provider health
```python
provider = LLMProviderRegistry.create("ollama_local", config)
if not provider.health_check():
    print("Provider is not running")
```

### Issue: "Connection refused to Ollama"

**Solution:** Start Ollama
```bash
ollama serve
# In another terminal
ollama pull llama2
```

### Issue: "OpenAI API rate limit"

**Solution:** Use fallback provider
```python
from services.genai_reasoning.provider_registry import LLMProviderFactory

factory = LLMProviderFactory(
    primary_provider="openai",
    fallback_provider="ollama_local"
)
```

### Issue: "Database connection failed"

**Solution:** Check connection string
```bash
# Test connection
psql postgresql://user:pass@localhost/db -c "SELECT 1"
```

---

## Best Practices

1. **Use environment variables** for credentials
2. **Test providers** before deployment
3. **Implement fallback providers** for reliability
4. **Monitor API costs** when using cloud services
5. **Log all operations** for debugging
6. **Validate configurations** on startup
7. **Use health checks** regularly
8. **Cache expensive operations** when possible
9. **Set timeouts** for external services
10. **Document custom extensions** clearly

---

## Governance & Monitoring Layer (NEW)

The platform now includes enterprise-grade governance and monitoring built into every layer.

### Architecture Integration

```
All Data Sources → Governance Layer → All Services
                   ├─ Structured Logging (with trace IDs)
                   ├─ Audit Logging (immutable trail)
                   ├─ Quality Evaluation (metrics, drift)
                   ├─ Observability (latency, costs)
                   ├─ Access Control (RBAC)
                   ├─ PII Scrubbing (automatic masking)
                   └─ Health Monitoring (service checks)
```

### Five Core Capabilities

1. **Centralized Logging**
   - Structured JSON logs with trace IDs
   - Request tracing across services
   - Performance timing (PerformanceTimer)
   - Multi-backend support (file, ELK-ready)

2. **Evaluation Layer**
   - Anomaly detection quality metrics (precision, recall, F1)
   - LLM hallucination detection
   - Data drift detection (PSI)
   - False positive analysis

3. **Observability**
   - Real-time platform metrics
   - Latency tracking (p50, p95, p99)
   - Token usage per provider
   - Cost estimation & tracking
   - Error rate distribution

4. **Governance**
   - Role-Based Access Control (RBAC) with 4 roles
   - Immutable audit trail (11 action types)
   - Automatic PII detection & masking
   - API key management & verification
   - Permission checking

5. **Health Monitoring**
   - Service health checks (4 services)
   - Automatic provider failover
   - Graceful degradation
   - Meta-monitoring

### Configuration Files

```yaml
# governance/access_policies.yaml
roles:
  viewer:
    permissions: [view_metrics]
  analyst:
    permissions: [view_metrics, run_detection, upload_data]
  admin:
    permissions: [all]

rate_limiting:
  analyst: 300 requests/minute
  admin: 1000 requests/minute
```

```yaml
# governance/audit_rules.yaml
audit_events:
  run_anomaly_detection:
    retention_days: 365
    log_details: [metrics, anomalies_detected]
  
alerts:
  unauthorized_access:
    severity: critical
    action: alert_admin
```

### API Endpoints

```
# Health & Observability
GET  /api/health                # Service health status
GET  /api/metrics               # Platform metrics
GET  /api/metrics/latency       # Latency stats
GET  /api/metrics/tokens        # Token usage & costs
GET  /api/metrics/errors        # Error statistics

# Governance
GET  /api/governance/users      # List users (admin)
GET  /api/governance/audit-logs # Audit trail (admin)

# Headers
X-User: alice@example.com       # User identity
X-Trace-ID: req_abc123          # Request tracing
```

### Usage Examples

```python
# Structured logging with tracing
from services.logging import get_logger, PerformanceTimer

logger = get_logger("my_service")
trace_id = "req_abc123"

with PerformanceTimer(logger, "operation", "module", trace_id) as timer:
    result = do_work()
    logger.info("Work completed", latency_ms=timer.elapsed_ms)

# Quality evaluation
from services.evaluation import AnomalyQualityEvaluator

evaluator = AnomalyQualityEvaluator()
metrics = evaluator.evaluate(y_true, y_pred)
print(f"Precision: {metrics.precision:.2%}, Recall: {metrics.recall:.2%}")

# Health monitoring
from services.monitoring import get_health_monitor

hm = get_health_monitor()
status = hm.check_all_services()
print(f"Overall: {status['overall_status']}")
```

---

## Summary

The Network Incident Investigator is **enterprise-grade, fully modular, and infinitely extensible**:

- **Multiple frontends**: Streamlit, Flask, CLI, React, or your custom implementation
- **Multiple LLM providers**: Ollama, OpenAI, Vertex AI, Azure, or your custom provider
- **Multiple data sources**: CSV, REST API, Database, Streaming, Cloud Storage, or your custom source
- **Governance & Monitoring**: Structured logging, RBAC, audit trails, health checks, failover
- **Scalable architecture**: Backend/Frontend separation enables independent scaling
- **Production-ready**: Compliance (GDPR, SOC2), security, observability, error handling

Choose your deployment based on your needs. The architecture supports everything from **local development** to **enterprise-scale deployments**.

For detailed governance guidance, see [GOVERNANCE_AND_MONITORING.md](GOVERNANCE_AND_MONITORING.md)
