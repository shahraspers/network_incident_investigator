# 🔍 Network Incident Investigator

**GenAI-Powered Anomaly Detection & Root Cause Analysis Platform**

A modular, scalable system for detecting network anomalies and providing AI-driven insights into root causes and remediation actions. Built as a POC with architecture designed to scale across TELUS network operations.

---

## 📋 Overview

### Key Features

✅ **Synthetic Network KPI Generation**
- Realistic LTE/5G metrics (RSRP, RSRQ, SINR, throughput, latency, call drops)
- Injected anomalies with correlated multi-metric failures
- Multiple site simulation

✅ **Reusable Anomaly Detection Service**
- Multiple algorithms: Z-Score, MAD, Isolation Forest, STL
- Per-metric and per-site configuration
- Flexible threshold configuration
- Anomaly scoring and classification

✅ **Pluggable GenAI Reasoning Layer**
- Provider-agnostic LLM client
- Support for: Ollama (local), OpenAI, Vertex AI, Azure OpenAI
- Rich anomaly context building
- Automatic root cause inference and recommendations

✅ **Streamlit Web UI**
- CSV upload & real-time analysis
- Interactive anomaly visualization
- GenAI-powered explanations
- Sample data generation

✅ **REST API Backend**
- FastAPI-based service
- Data upload & management
- Anomaly detection endpoints
- GenAI explanation service
- Metrics & observability endpoints
- Governance & access control endpoints

✅ **Enterprise Governance & Monitoring**
- Centralized logging with trace IDs
- Quality evaluation (precision, recall, hallucinations)
- Real-time observability metrics
- Role-Based Access Control (RBAC) 
- Immutable audit trails
- PII detection & masking
- Service health checks with failover

---

## 🏗️ Architecture

### Directory Structure

```
telus_rec_interview_2606/
├── frontend/
│   └── app.py                 # Streamlit web UI
├── backend/
│   ├── api.py                 # FastAPI REST API (with governance)
│   └── data_loader.py         # Pluggable data sources
├── services/
│   ├── anomaly_detection/
│   │   ├── kpi_detector.py   # Anomaly detection service
│   │   └── detector.py        # Detection algorithms
│   ├── genai_reasoning/
│   │   ├── llm_client.py      # LLM provider client
│   │   ├── reasoner.py        # GenAI reasoning
│   │   └── context_builder.py # Context building
│   ├── logging/               # Structured logging
│   │   └── structured_logger.py
│   ├── evaluation/            # Quality & drift metrics
│   │   ├── anomaly_metrics.py
│   │   ├── llm_quality.py
│   │   └── drift_detection.py
│   ├── observability/         # Platform metrics
│   │   └── metrics_collector.py
│   ├── governance/            # RBAC, audit, security
│   │   ├── access_control.py
│   │   ├── audit_logger.py
│   │   └── pii_scrubbing.py
│   └── monitoring/            # Health & failover
│       └── health_monitor.py
├── governance/                # Configuration
│   ├── access_policies.yaml
│   └── audit_rules.yaml
├── data/
│   ├── cell_site_kpi_generator.py
│   └── synthetic_kpi_generator.py
├── logs/
│   ├── app.log                # Structured logs
│   └── audit.jsonl            # Audit trail
├── requirements.txt
├── .env.example
├── GOVERNANCE_AND_MONITORING.md
├── GOVERNANCE_IMPLEMENTATION_SUMMARY.md
└── README.md
```

### Data Flow

```
CSV/Backend/Stream
     │
     ├─→ Data Loader (pluggable)
     │
     ├─→ Anomaly Detection Service
     │   ├── Per-metric configuration
     │   ├── Multiple algorithms
     │   └── Per-site analysis
     │
     ├─→ Anomaly Context Builder
     │   ├── Historical analysis
     │   ├── Correlation detection
     │   └── Incident indicators
     │
     ├─→ GenAI Reasoning Layer
     │   ├── Provider abstraction
     │   ├── Multi-provider support
     │   └── Structured output
     │
     └─→ UI/API (Results)
```

### Complete System Architecture

```
DATA SOURCES: CSV | Synthetic | Backend API | Streaming
              ↓
         BACKEND API (FastAPI)
         + Governance Integration
         + Structured Logging  
         + Metrics Collection
              ↓
    ┌─────────┴──────────┐
    ↓                    ↓
ANOMALY DETECTION    GOVERNANCE & MONITORING
├─ Detectors         ├─ RBAC
├─ Quality Metrics   ├─ Audit Logging
├─ Drift Detection   ├─ PII Scrubbing
└─ LLM Analysis      ├─ Health Checks
    ↓                └─ Failover
GenAI REASONING
├─ Ollama (local)
├─ OpenAI (cloud)
├─ Vertex AI
└─ Azure OpenAI
    ↓
STREAMLIT UI + REST API
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip
- Optional: Ollama for local LLM (or OpenAI/Vertex AI API key)

### Installation

1. **Clone/Setup the project**
```bash
cd telus_rec_interview_2606
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

### Running the System

#### ⚠️ IMPORTANT: Activate Virtual Environment First

Before running ANY command, activate the virtual environment in your terminal:

**Windows (PowerShell):**
```bash
venv\Scripts\activate
```

**Windows (Command Prompt):**
```bash
venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

You should see `(venv)` prefix in your terminal after activation.

---

#### Option 1: Streamlit UI (Recommended for Demo)

In a terminal with `(venv)` activated:
```bash
streamlit run frontend/app.py
```
- Opens at `http://localhost:8501`
- Features: Upload CSV, real-time anomaly detection, GenAI analysis
- ✅ Simplified sidebar (no connection errors)
- ✅ Graceful error handling for GenAI failures

#### Option 2: Backend API

In a terminal with `(venv)` activated:
```bash
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```
- Runs at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- ✅ All metrics endpoints functional
- ✅ LLM metrics tracked (even with provider failures)

#### Option 3: Run Both Simultaneously (Recommended)

**Terminal 1 (Backend API on port 8000)** - Activate venv, then:
```bash
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 (Frontend UI on port 8501)** - Activate venv, then:
```bash
streamlit run frontend/app.py
```

**Terminal 3 (Optional - Ollama for local LLM):**
```bash
ollama serve
```
- Runs on port 11434
- Only needed if using local GenAI provider

---

## � Governance & Monitoring

The platform includes **enterprise-grade governance and monitoring capabilities**:

### Five Core Capabilities

1. **Centralized Logging** - Structured JSON logs with trace IDs for request correlation
2. **Evaluation Layer** - Quality metrics (precision, recall), drift detection, hallucination analysis
3. **Observability** - Real-time platform metrics (latency, costs, errors, LLM usage)
4. **Governance** - RBAC, immutable audit trails, PII scrubbing
5. **Health Monitoring** - Service health checks, automatic provider failover

### Recent Improvements (Latest Session)

✅ **LLM Metrics Now Always Tracked** - Token usage recorded even when provider unavailable  
✅ **Graceful Degradation** - GenAI failures don't crash API, return fallback responses  
✅ **Timezone-Safe Metrics** - Fixed datetime comparison bug in metrics collection  
✅ **Simplified UI** - Removed problematic health check from sidebar  
✅ **Better Error Handling** - All endpoints return valid JSON responses  

### Platform Metrics Dashboard

The UI displays real-time platform metrics in the Executive Summary section:

| Metric | Source | Updated |
|--------|--------|---------|
| Total Requests | API counter | Every request |
| LLM Calls | GenAI endpoint | Every call (incl. failures) |
| LLM Token Usage | Token recorder | Per GenAI request |
| Estimated Cost | Token pricing | Per LLM call |
| Total Errors | Error recorder | On failures |
| Latency Stats | PerformanceTimer | Per operation |

### API Endpoints for Observability

```
GET  /api/metrics                   # Full platform metrics dashboard
GET  /api/metrics/latency           # Latency percentiles (p50, p95, p99)
GET  /api/metrics/tokens            # Token usage by model & cost
GET  /api/metrics/errors            # Error stats by type/module
GET  /api/health                    # Service health check
GET  /api/genai/providers           # LLM provider status
GET  /api/governance/audit-logs     # Audit trail query
```

### New API Endpoints

```
Observability:
GET  /api/health                    # Service health status
GET  /api/metrics                   # Platform metrics
GET  /api/metrics/latency           # Latency stats (p50, p95, p99)
GET  /api/metrics/tokens            # Token usage & costs
GET  /api/metrics/errors            # Error statistics

Governance:
GET  /api/governance/users          # List users (admin only)
GET  /api/governance/audit-logs     # Query audit trail
```

### Usage Examples

```python
# Structured logging with tracing
from services.logging import get_logger
logger = get_logger("my_service")
logger.info("Event occurred", trace_id="abc123", module="detector")

# Quality evaluation
from services.evaluation import AnomalyQualityEvaluator
evaluator = AnomalyQualityEvaluator()
metrics = evaluator.evaluate(y_true, y_pred)
print(f"Precision: {metrics.precision:.2%}, Recall: {metrics.recall:.2%}")

# Check platform health
from services.monitoring import get_health_monitor
hm = get_health_monitor()
status = hm.check_all_services()
print(f"Overall: {status['overall_status']}")
```

For detailed documentation, see [GOVERNANCE_AND_MONITORING.md](GOVERNANCE_AND_MONITORING.md)

---

## �📊 Data Format

### Expected CSV Columns

| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime | 5-minute intervals (ISO format) |
| site_id | string | Cell site identifier (e.g., CELL_001) |
| rsrp | float | Reference Signal Received Power (dBm) |
| rsrq | float | Reference Signal Received Quality (dB) |
| sinr | float | Signal-to-Interference Ratio (dB) |
| throughput_mbps | float | Data throughput (Mbps) |
| latency_ms | float | Round-trip latency (ms) |
| dropped_call_rate | float | Call drop percentage (%) |

### Sample Data Generation

```python
from data.cell_site_kpi_generator import generate_synthetic_kpi_data

# Generate data: 5 sites × 48 hours with 5-min intervals
df = generate_synthetic_kpi_data(
    num_sites=5,
    num_hours=48,
    interval_minutes=5
)
```

---

## 🔎 Anomaly Detection

### Supported Methods

| Method | Best For | Parameters |
|--------|----------|------------|
| **zscore** | General purpose, normal distributions | `threshold` (default: 3.0) |
| **mad** | Robust to outliers | `threshold` (default: 2.5) |
| **isolation_forest** | High-dimensional data | `contamination` (default: 0.1) |
| **stl** | Seasonal time-series | `seasonal_period`, `threshold` |

### Configuration

```python
from services.anomaly_detection.kpi_detector import detect_anomalies

# Detect anomalies with custom config
result_df = detect_anomalies(
    df=df,
    metrics=['rsrp', 'throughput_mbps', 'latency_ms'],
    method='zscore',
    config={'threshold': 3.0}
)
```

---

## 🧠 GenAI Reasoning

### Supported Providers

#### 1. **Ollama (Local)** - Recommended for POC
```python
from services.genai_reasoning.llm_client import LLMClient

client = LLMClient('ollama_local', {
    'base_url': 'http://localhost:11434',
    'model': 'llama2'
})

explanation = client.explain_anomaly(context)
```

**Setup Ollama:**
```bash
# Download and run Ollama
# Visit: https://ollama.ai
ollama pull llama2
ollama serve
```

#### 2. **OpenAI**
```python
client = LLMClient('openai', {
    'api_key': 'sk-...',
    'model': 'gpt-3.5-turbo'
})
```

#### 3. **Vertex AI (Google Cloud)**
```python
client = LLMClient('vertex_ai', {
    'project_id': 'your-gcp-project',
    'model': 'text-bison@001'
})
```

#### 4. **Azure OpenAI**
```python
client = LLMClient('azure_openai', {
    'endpoint': 'https://your-resource.openai.azure.com/',
    'api_key': 'your-key',
    'deployment_id': 'your-deployment'
})
```

### Explanation Output

```json
{
  "summary": "RSRP signal strength degradation detected",
  "likely_causes": [
    "Antenna obstruction or misalignment",
    "Increased path loss from weather",
    "RF interference from nearby sources"
  ],
  "recommended_actions": [
    "Inspect antenna alignment and integrity",
    "Check weather conditions and forecast",
    "Scan RF environment for interference sources"
  ],
  "severity": "High",
  "confidence": 0.92
}
```

---

## 🔌 Data Sources (Pluggable)

### CSV Files

```python
from backend.data_loader import load_data_from_csv

df = load_data_from_csv(
    filepath='data/cell_metrics.csv',
    timestamp_col='timestamp',
    parse_dates=True
)
```

### Backend API

```python
from backend.data_loader import load_data_from_backend

config = {
    'endpoint': 'https://api.telus.com/metrics',
    'site_id': 'CELL_001',
    'start_time': '2026-06-20T00:00:00Z',
    'auth_token': 'bearer_token'
}
df = load_data_from_backend(config)
```

### Streaming Sources (Placeholder)

```python
from backend.data_loader import load_data_from_stream

config = {
    'type': 'kafka',
    'brokers': ['localhost:9092'],
    'topic': 'network_metrics'
}
df = load_data_from_stream(config)  # Stub - implement as needed
```

---

## 🧪 Testing

### Run Tests

```bash
pytest tests/ -v
pytest tests/ --cov=services --cov=backend
```

### Example: Testing Anomaly Detection

```python
from services.anomaly_detection.kpi_detector import NetworkKPIAnomalyDetectionService
from data.cell_site_kpi_generator import generate_synthetic_kpi_data

# Generate test data
df = generate_synthetic_kpi_data(num_sites=2, num_hours=12, save_files=False)

# Configure service
service = NetworkKPIAnomalyDetectionService()
service.configure_metric('rsrp', method='zscore', threshold=2.5)
service.configure_metric('throughput_mbps', method='mad', threshold=3.0)

# Run detection
result_df = service.detect_anomalies(
    df=df,
    metrics=['rsrp', 'throughput_mbps']
)

# Verify
assert 'is_anomaly' in result_df.columns
assert 'anomaly_score_rsrp' in result_df.columns
```

---

## 📡 REST API Endpoints

### Data Management

```
POST   /api/data/upload           # Upload CSV file
GET    /api/data/preview          # Preview uploaded data
POST   /api/data/synthetic        # Generate synthetic data
```

### Anomaly Detection

```
POST   /api/anomaly/detect        # Run anomaly detection
GET    /api/anomaly/results       # Get detection results
```

### GenAI Reasoning

```
POST   /api/genai/explain         # Generate explanation for anomaly
GET    /api/genai/providers       # List supported LLM providers
```

### Information

```
GET    /health                    # Health check
GET    /api/info                  # API information
GET    /api/metrics               # Metrics schema
GET    /api/detection-methods     # Available detection algorithms
```

### API Documentation

- **Interactive Docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 📝 Configuration

### Environment Variables

Create `.env` file (copy from `.env.example`):

```bash
# GenAI Provider
GENAI_PROVIDER=ollama_local              # ollama_local, openai, vertex_ai, azure_openai

# Ollama (if using local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# OpenAI (if using OpenAI)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo

# Anomaly Detection
DEFAULT_DETECTION_METHOD=zscore
DEFAULT_ANOMALY_THRESHOLD=3.0
DEFAULT_WINDOW_SIZE=30

# Logging
LOG_LEVEL=INFO
```

### Programmatic Configuration

```python
from config import get_config, validate_config

config = get_config()
is_valid, errors = validate_config(config)

if not is_valid:
    print("Configuration errors:", errors)
```

---

## 🎯 Use Cases

### 1. **Network Operations Center (NOC)**
- Real-time anomaly monitoring
- Automated root cause identification
- Rapid incident response

### 2. **Predictive Maintenance**
- Identify degrading metrics early
- Plan maintenance proactively
- Reduce unplanned outages

### 3. **Performance Optimization**
- Identify capacity bottlenecks
- Detect interference patterns
- Optimize network resources

### 4. **Compliance & SLA Monitoring**
- Track KPI adherence
- Document incidents
- Generate reports

---

## 🔮 Future Enhancements

- [ ] **Integration with TELUS backend systems**
  - Real-time data streaming
  - Historical data lake queries
  - Incident ticket creation

- [ ] **Advanced ML Models**
  - Regression-based forecasting
  - LSTM for sequence prediction
  - Clustering for pattern discovery

- [ ] **Enhanced Visualization**
  - Time-series charts
  - Correlation matrices
  - Incident heatmaps

- [ ] **Multi-tenant Support**
  - Organization isolation
  - Role-based access
  - Custom branding

- [ ] **CI/CD Pipeline**
  - Automated testing
  - Model versioning
  - A/B testing framework

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 📞 Support

For questions or issues:
- Check [Architecture Documentation](./docs/ARCHITECTURE.md)
- Review [API Examples](./docs/API_EXAMPLES.md)
- Open an issue on GitHub

---

## 🏆 Key Technologies

- **Data Science:** Pandas, NumPy, Scikit-learn, Statsmodels
- **Web:** Streamlit, FastAPI, Uvicorn
- **GenAI:** Ollama, OpenAI, Vertex AI, Azure OpenAI
- **DevOps:** Docker (ready), Environment management

---

**Built for TELUS Network Operations**
*GenAI-Powered Incident Investigation - POC to Production*
