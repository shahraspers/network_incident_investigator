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
python -m backend.api
# Available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

**Option C: Quick Start Script**
```bash
python quickstart.py setup      # Install & setup
python quickstart.py frontend   # Run UI
python quickstart.py backend    # Run API
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

### Using OpenAI
Edit `.env`:
```
GENAI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo
```

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

## Next Steps

1. ✅ Explore sample data
2. ✅ Try different detection methods
3. ✅ Compare GenAI providers
4. ✅ Upload your own CSV
5. ✅ Review API documentation
6. ✅ Check Docker deployment

---

## Documentation

- **README.md** - Full documentation
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
