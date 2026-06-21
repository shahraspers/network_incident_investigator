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

---

## 🏗️ Architecture

### Directory Structure

```
telus_rec_interview_2606/
├── frontend/
│   └── app.py                 # Streamlit web UI
├── backend/
│   ├── api.py                 # FastAPI REST API
│   └── data_loader.py         # Pluggable data source loaders
├── services/
│   ├── anomaly_detection/
│   │   ├── kpi_detector.py   # Main anomaly detection service
│   │   └── detector.py        # Alternative detectors
│   └── genai_reasoning/
│       ├── llm_client.py      # Provider-agnostic LLM client
│       ├── reasoner.py        # Legacy reasoner module
│       └── context_builder.py # Anomaly context building
├── data/
│   ├── cell_site_kpi_generator.py   # Synthetic data generator
│   └── synthetic_kpi_generator.py   # Legacy generator
├── config/
│   ├── __init__.py            # Configuration management
│   └── settings.py            # Legacy settings
├── tests/
│   └── test_services.py       # Unit tests
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
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

### Component Interactions

```
Frontend (Streamlit)
    ↓
Backend API (FastAPI)
    ↓
Data Loader → Anomaly Detector → Context Builder → LLM Client
    ↓
Database/Export
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

#### Option 1: Streamlit UI (Recommended for Demo)

```bash
streamlit run frontend/app.py
```
- Opens at `http://localhost:8501`
- Features: Upload CSV, real-time anomaly detection, GenAI analysis

#### Option 2: Backend API

```bash
python -m backend.api
```
- Starts at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

#### Option 3: Run Both

Terminal 1:
```bash
python -m backend.api
```

Terminal 2:
```bash
streamlit run frontend/app.py
```

---

## 📊 Data Format

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
