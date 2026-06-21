## 📋 Flexible Architecture Overview

This system is **completely frontend-agnostic** and **provider-agnostic**:

```
┌─────────────────────────────────────┐
│  Multiple Frontend Options          │
├─────────────────────────────────────┤
│ • Streamlit (current)               │
│ • React.js / Vue.js                 │
│ • Mobile (React Native / Flutter)   │
│ • Custom (any platform)             │
└────────────┬────────────────────────┘
             │ HTTP REST API
             ↓
┌─────────────────────────────────────┐
│  FastAPI Backend (Scalable)         │
├─────────────────────────────────────┤
│ • Stateless services                │
│ • Runs on Kubernetes                │
│ • Multi-instance support            │
└────────────┬────────────────────────┘
```

---

# 🚀 Getting Started - Network Incident Investigator

**5-minute setup guide**

---

## Installation

### 1. Prerequisites
- Python 3.8+
- pip
- (Optional) Ollama for local LLM

### 2. Setup Environment

```bash
# Clone/navigate to project
cd telus_rec_interview_2606

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
```

### 3. Run the Application

**Option A: Web UI (Recommended for Demo)**
```bash
streamlit run frontend/app.py
# Opens at http://localhost:8501
```

**Option B: REST API**
```bash
# Start with uvicorn (recommended)
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload

# OR alternatively:
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload

# Available at http://localhost:8000
# API Docs: http://localhost:8000/docs
# OpenAPI Schema: http://localhost:8000/openapi.json
```

**Option C: Quick Start Script** (if available)
```bash
python quickstart.py setup      # Install & setup
python quickstart.py frontend   # Run UI (Streamlit on 8501)
python quickstart.py backend    # Run API (Uvicorn on 8000)
python quickstart.py demo       # Quick demo
```

---

## First Steps

### 1. Generate Sample Data

In the Streamlit UI:
1. Go to "📈 Sample Data" tab
2. Adjust settings (sites, hours)
3. Click "Generate Sample Data"
4. Download CSV

### 2. Upload & Analyze

In the Streamlit UI:
1. Go to "📊 Data Upload" tab
2. Upload CSV or click "Generate 3 Sites × 24 Hours"
3. Go to "🔎 Anomaly Detection" tab
4. Select metrics
5. Click "Run Detection"

### 3. Get AI Insights

In the Streamlit UI:
1. Go to "🧠 GenAI Analysis" tab
2. Select an anomaly from the list
3. Click "Analyze with GenAI"
4. Review summary, causes, and recommendations

---

## Using the REST API

### Upload Data
```bash
curl -X POST http://localhost:8000/api/data/upload \
  -F "file=@data.csv"
```

### Generate Synthetic Data
```bash
curl -X POST http://localhost:8000/api/data/synthetic \
  -H "Content-Type: application/json" \
  -d '{"num_sites": 3, "num_hours": 24}'
```

### Detect Anomalies
```bash
curl -X POST http://localhost:8000/api/anomaly/detect \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": ["rsrp", "throughput_mbps"],
    "method": "zscore",
    "threshold": 3.0
  }'
```

### Get Anomaly Results
```bash
curl http://localhost:8000/api/anomaly/results
```

---

## Python API

### Generate Data
```python
from data.cell_site_kpi_generator import generate_synthetic_kpi_data

df = generate_synthetic_kpi_data(
    num_sites=5,
    num_hours=48
)
```

### Detect Anomalies
```python
from services.anomaly_detection.kpi_detector import detect_anomalies

result_df = detect_anomalies(
    df=df,
    metrics=['rsrp', 'throughput_mbps', 'latency_ms'],
    method='zscore'
)
```

### Get GenAI Analysis
```python
from services.genai_reasoning.llm_client import LLMClient
from services.genai_reasoning.context_builder import build_anomaly_context

# Create client
client = LLMClient('ollama_local', {
    'base_url': 'http://localhost:11434',
    'model': 'llama2'
})

# Build context
context = build_anomaly_context(df, anomaly_row)

# Get explanation
explanation = client.explain_anomaly(context)
print(explanation['summary'])
print(explanation['likely_causes'])
print(explanation['recommended_actions'])
```

---

## Configuration

### Using Ollama (Local)
```bash
# Install Ollama: https://ollama.ai
# Run Ollama:
ollama serve
# In another terminal, pull a model:
ollama pull llama2
```

Edit `.env`:
```
GENAI_PROVIDER=ollama_local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### Using OpenAI (Cloud)
Edit `.env`:
```
GENAI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo
```

### Using Azure OpenAI (Enterprise)
Edit `.env`:
```
GENAI_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_DEPLOYMENT_ID=deployment-name
```

### Using Google Vertex AI
Edit `.env`:
```
GENAI_PROVIDER=vertex_ai
GCP_PROJECT_ID=your-project
GCP_LOCATION=us-central1
```

### Adding Custom LLM Providers

The system supports **pluggable LLM providers**. To add a new provider:

1. **Create provider class** in `services/genai_reasoning/llm_client.py`:

```python
class CustomLLMProvider(BaseLLMProvider):
    def __init__(self, config: Dict):
        self.endpoint = config['endpoint']
    
    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.endpoint}/health")
            return response.status_code == 200
        except:
            return False
    
    def explain_anomaly(self, context: Dict) -> Dict:
        response = requests.post(
            f"{self.endpoint}/analyze",
            json={'context': context}
        )
        return response.json()
```

2. **Register in LLMClient**: Update `_initialize_provider()` method
3. **Use via environment**:
   ```
   GENAI_PROVIDER=custom
   CUSTOM_ENDPOINT=https://your-api.com
   ```

---

## 🎨 Frontend Alternatives (Not Just Streamlit)

The backend **REST API** (`backend/api.py`) is completely independent, so you can use ANY frontend:

### Option 1: Streamlit (Current)
```bash
streamlit run frontend/app.py
```

### Option 2: React.js Frontend

```bash
# Create React app
npx create-react-app nii-frontend
cd nii-frontend

# Install dependencies
npm install axios plotly.js

# Create API client (src/api.js)
import axios from 'axios';
const API = axios.create({ baseURL: 'http://localhost:8000' });
export const detectAnomalies = (metrics, method) =>
  API.post('/api/anomaly/detect', {metrics, method});

# npm start (runs on port 3000)
```

### Option 3: Vue.js Frontend

```bash
npm create vue@latest nii-frontend
cd nii-frontend
npm install

# Create composable (src/composables/useAPI.js)
import axios from 'axios'
const API = axios.create({ baseURL: 'http://localhost:8000' })
export function useDetection() {
  return { runDetection: (metrics) => API.post('/api/anomaly/detect', {metrics}) }
}
```

### Option 4: Mobile App (React Native)

```javascript
// API wrapper for React Native
export const API_BASE = 'http://backend:8000';

export async function detectAnomalies(metrics) {
  const response = await fetch(`${API_BASE}/api/anomaly/detect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({metrics, method: 'zscore'})
  });
  return response.json();
}
```

### Option 5: Desktop App (Python + PyQt)

```python
import requests
from PyQt5.QtWidgets import QMainWindow

class NIIApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = requests.Session()
    
    def run_detection(self):
        response = self.api.post(
            'http://localhost:8000/api/anomaly/detect',
            json={'metrics': ['rsrp'], 'method': 'zscore'}
        )
        return response.json()
```

### Option 6: Any Custom Frontend (JavaScript, C#, Java, etc.)

All you need is HTTP + JSON support:

```bash
# JavaScript (Node.js/Express)
const response = await fetch('http://localhost:8000/api/anomaly/detect', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({metrics: ['rsrp'], method: 'zscore'})
});

# Python (requests)
import requests
requests.post('http://localhost:8000/api/anomaly/detect', 
  json={'metrics': ['rsrp'], 'method': 'zscore'})

# Java (HttpClient)
HttpClient client = HttpClient.newHttpClient();
HttpRequest request = HttpRequest.newBuilder()
  .uri(new URI("http://localhost:8000/api/anomaly/detect"))
  .POST(BodyPublishers.ofString("{...}"))
  .build();

# C# (HttpClient)
using (HttpClient client = new HttpClient()) {
  var response = await client.PostAsync(
    "http://localhost:8000/api/anomaly/detect",
    new StringContent("{...}", Encoding.UTF8, "application/json"));
}
```

---

## 📊 Data Source Integration

The system supports **pluggable data sources**:

### Source 1: CSV Files (Default)
```bash
# Upload via UI or API
curl -X POST -F "file=@data.csv" http://localhost:8000/api/data/upload
```

### Source 2: Backend API
Implement `BackendAPIDataSource` in `backend/data_loader.py`:
```python
source = DataSourceFactory.create('api', {
    'endpoint': 'https://api.telus.com/kpi',
    'auth_token': 'xxx'
})
df = source.load()
```

### Source 3: Database (PostgreSQL, MySQL)
```python
source = DataSourceFactory.create('database', {
    'connection_string': 'postgresql://user:pass@host:5432/kpi',
    'query': 'SELECT * FROM cell_metrics'
})
df = source.load()
```

### Source 4: Kafka Streaming
```python
source = DataSourceFactory.create('kafka', {
    'bootstrap_servers': 'kafka:9092',
    'topic': 'network-kpi'
})
df = source.load()  # Collects batch
```

---

## ⚙️ Configuration

---

## Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop
docker-compose down
```

Access:
- Frontend: http://localhost:8501
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Supported Detection Methods

| Method | Best For | Threshold |
|--------|----------|-----------|
| zscore | General purpose | 3.0 (default) |
| mad | Outlier robust | 2.5 |
| isolation_forest | High dimensions | 0.1 (contamination) |
| stl | Seasonal data | 3.0 |

---

## Supported Metrics

- **rsrp**: Reference Signal Received Power (dBm)
- **rsrq**: Reference Signal Received Quality (dB)
- **sinr**: Signal-to-Interference Ratio (dB)
- **throughput_mbps**: Data Throughput (Mbps)
- **latency_ms**: Round-trip Latency (ms)
- **dropped_call_rate**: Dropped Call Rate (%)

---

## Troubleshooting

### Port Already in Use
```bash
# Streamlit default: 8501
streamlit run frontend/app.py --server.port 8502

# FastAPI default: 8000
python -m backend.api --port 8001
```

### Ollama Connection Failed
- Check if Ollama is running: `ollama serve`
- Verify endpoint in `.env`: `OLLAMA_BASE_URL=http://localhost:11434`
- Test connection: `curl http://localhost:11434/api/tags`

### Slow LLM Response
- Using local Ollama? It's slower than cloud providers
- Try smaller model: `ollama pull neural-chat` (faster than llama2)
- Or use OpenAI for faster responses

### CSV Parse Error
- Check format: Must have columns: `timestamp, site_id, rsrp, rsrq, sinr, throughput_mbps, latency_ms, dropped_call_rate`
- Ensure timestamp is ISO format: `2026-06-20T12:00:00Z`
- Try sample data generator first

---

## Testing

Run tests:
```bash
pytest tests/ -v
```

Run demo:
```bash
python quickstart.py demo
```

---

## Governance & Monitoring (NEW)

The platform now includes enterprise-grade governance features:

**IMPORTANT**: Make sure the backend API is running first:
```bash
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```

Then in another terminal, you can test governance endpoints:

### Check Platform Health

```bash
# Detailed health status
curl http://localhost:8000/api/health

# Platform metrics
curl http://localhost:8000/api/metrics

# Latency stats
curl http://localhost:8000/api/metrics/latency?module=anomaly_detector

# Token usage & costs
curl http://localhost:8000/api/metrics/tokens

# Error statistics
curl http://localhost:8000/api/metrics/errors
```

### Access Control

The platform supports Role-Based Access Control (RBAC):

```python
from services.governance import get_access_controller, Role

ac = get_access_controller()

# Create users with roles
analyst = ac.create_user("alice@example.com", Role.ANALYST)
admin = ac.create_user("bob@example.com", Role.ADMIN)

# Check permissions
if ac.check_permission("alice@example.com", "run_detection"):
    # Alice can run detection
    pass
```

### Audit Logging

All sensitive actions are automatically logged:

```bash
# Query audit logs
curl "http://localhost:8000/api/governance/audit-logs?actor=alice@example.com"

# Returns: all actions by alice with timestamps, status, details
```

### Request Tracing

All requests support tracing via headers:

```bash
curl -X POST http://localhost:8000/api/anomaly/detect \
  -H "X-User: alice@example.com" \
  -H "X-Trace-ID: req_abc123" \
  -H "Content-Type: application/json" \
  -d '{"metrics": ["rsrp"]}'
```

For detailed governance guidance, see [GOVERNANCE_AND_MONITORING.md](GOVERNANCE_AND_MONITORING.md)

---

## Next Steps

1. ✅ Explore sample data
2. ✅ Try different detection methods
3. ✅ Compare GenAI providers
4. ✅ Upload your own CSV
5. ✅ Review API documentation
6. ✅ Check Docker deployment

---

## Documentation

- **README.md** - Full project documentation
- **GOVERNANCE_AND_MONITORING.md** - Enterprise governance guide (NEW)
- **PLUGGABLE_ARCHITECTURE.md** - System architecture & extensibility
- **ARCHITECTURE_EXTENSIBILITY.md** - How to extend each component
- **PROJECT_SUMMARY.md** - Project overview
- **MANIFEST.md** - File structure
- **Code comments** - Implementation details

---

## Need Help?

1. Check README.md for detailed guide
2. Run demo: `python quickstart.py demo`
3. View API docs: http://localhost:8000/docs
4. Review test examples: `tests/test_services.py`

---

**Let's get started! 🚀**
