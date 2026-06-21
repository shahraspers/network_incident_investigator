# Implementation Guide - Using New Pluggable Systems

## Overview

This guide explains how to use the new pluggable architecture components:

1. **Frontend Abstraction** (`frontend/abstract_frontend.py`)
2. **Data Source Registry** (`backend/data_source_registry.py`)
3. **LLM Provider Registry** (`services/genai_reasoning/provider_registry.py`)
4. **Flask Frontend Example** (`frontend/flask_frontend.py`)

---

## 1. Using the Frontend Abstraction

### Quick Start

```python
from frontend.abstract_frontend import CLIFrontend, FrontendWorkflow

# Create a CLI frontend
frontend = CLIFrontend()

# Create workflow
workflow = FrontendWorkflow(frontend, backend_url="http://localhost:8000")

# Run the complete workflow
success = workflow.run_workflow()
```

### Creating a Custom Frontend

```python
from frontend.abstract_frontend import IFrontend, DetectionConfig, GenAIConfig
from typing import Optional, Dict, List

class MyCustomFrontend(IFrontend):
    """Your custom frontend implementation"""
    
    def upload_data(self) -> Optional[Dict]:
        """Load data from your source"""
        # Must return: {"success": bool, "data": DataFrame or None, "error": str}
        pass
    
    def get_detection_config(self) -> DetectionConfig:
        """Get anomaly detection configuration"""
        return DetectionConfig(
            metrics=["rsrp", "throughput_mbps"],
            method="zscore",
            threshold=3.0
        )
    
    def get_genai_config(self) -> GenAIConfig:
        """Get GenAI provider configuration"""
        return GenAIConfig(
            provider="ollama_local",
            model="mistral"
        )
    
    def display_detection_results(self, results: Dict) -> None:
        """Display detection results"""
        print(f"Found {results['anomalies_found']} anomalies")
    
    def select_anomaly(self, anomaly_rows: List[Dict]) -> Optional[Dict]:
        """Let user select an anomaly"""
        return anomaly_rows[0] if anomaly_rows else None
    
    def display_genai_explanation(self, explanation: Dict) -> None:
        """Display GenAI explanation"""
        print(f"Summary: {explanation['summary']}")
    
    def display_executive_summary(self, summary: Dict) -> None:
        """Display summary"""
        print(f"Total anomalies: {summary['total_anomalies']}")
    
    def run(self) -> None:
        """Run the frontend"""
        workflow = FrontendWorkflow(self)
        workflow.run_workflow()
```

### Using with Backend API

```python
# Option 1: Run standalone (calls backend API)
frontend = MyCustomFrontend()
workflow = FrontendWorkflow(
    frontend, 
    backend_url="http://my-backend.example.com:8000"
)
workflow.run_workflow()

# Option 2: Integrate with your app
workflow = FrontendWorkflow(frontend)

# Step-by-step control
workflow.step1_load_data()
workflow.step2_configure()
workflow.step3_detect()
workflow.step4_explain()
workflow.step5_summarize()
```

---

## 2. Using the Data Source Registry

### Register Data Sources

```python
from backend.data_source_registry import DataSourceRegistry

# List available sources
available = DataSourceRegistry.list_sources()
# Output: ['csv', 'rest_api', 'database', 'streaming', 'cloud_storage']

# Get configuration template
template = DataSourceRegistry.get_source_config("rest_api")
print(template)
# Output: {'endpoint': '...', 'headers': {...}, 'params': {...}}
```

### Use Built-in Sources

```python
# CSV
csv_source = DataSourceRegistry.create(
    "csv",
    filepath="data.csv"
)
df = csv_source.load()

# REST API
api_source = DataSourceRegistry.create(
    "rest_api",
    endpoint="https://api.example.com/kpi",
    headers={"Authorization": "Bearer token"},
    params={"start_time": "2026-06-01"}
)
df = api_source.load()

# Database
db_source = DataSourceRegistry.create(
    "database",
    connection_string="postgresql://user:pass@localhost/db",
    query="SELECT * FROM kpi_metrics WHERE timestamp > NOW() - INTERVAL '24 hours'"
)
df = db_source.load()

# Streaming (Kafka)
stream_source = DataSourceRegistry.create(
    "streaming",
    source_type="kafka",
    config={
        "bootstrap_servers": "localhost:9092",
        "topic": "kpi-events"
    }
)
df = stream_source.load(batch_size=100)

# Cloud Storage (S3)
cloud_source = DataSourceRegistry.create(
    "cloud_storage",
    storage_type="s3",
    config={
        "bucket": "my-bucket",
        "key": "data/kpi.csv"
    }
)
df = cloud_source.load()
```

### Validate Data Source

```python
source = DataSourceRegistry.create("rest_api", endpoint="https://api.example.com")

# Check if accessible
if source.validate():
    print("✓ Source is accessible")
    
    # Get schema
    schema = source.get_schema()
    print(f"Columns: {schema['columns']}")
else:
    print("✗ Source is not accessible")
```

### Create Custom Data Source

```python
from backend.data_source_registry import IDataSource, DataSourceRegistry
import pandas as pd

class MongoDBDataSource(IDataSource):
    """MongoDB data source"""
    
    def __init__(self, uri: str, db: str, collection: str, query: dict = None):
        self.uri = uri
        self.db = db
        self.collection = collection
        self.query = query or {}
    
    def load(self, **kwargs) -> pd.DataFrame:
        from pymongo import MongoClient
        
        client = MongoClient(self.uri)
        db = client[self.db]
        coll = db[self.collection]
        
        # Query with merge of kwargs
        query = {**self.query, **kwargs}
        data = list(coll.find(query))
        
        df = pd.DataFrame(data)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        return df
    
    def validate(self) -> bool:
        try:
            from pymongo import MongoClient
            client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ismaster')
            return True
        except:
            return False
    
    def get_schema(self) -> dict:
        df = self.load()
        return {"columns": df.columns.tolist(), "dtypes": df.dtypes.astype(str).to_dict()}

# Register the source
DataSourceRegistry.register("mongodb", MongoDBDataSource)

# Use it
source = DataSourceRegistry.create(
    "mongodb",
    uri="mongodb://localhost:27017",
    db="network_kpi",
    collection="metrics"
)

df = source.load()
```

---

## 3. Using the LLM Provider Registry

### Get Available Providers

```python
from services.genai_reasoning.provider_registry import (
    LLMProviderRegistry,
    ProviderConfigBuilder,
    LLMProviderFactory
)

# List providers
providers = LLMProviderRegistry.list_providers()

# Get provider template
template = LLMProviderRegistry.get_provider_config("openai")
print(template)
# Output: {description, required_config, default_config, env_vars}
```

### Create Providers

```python
# Method 1: Direct creation with config
config = {
    "base_url": "http://localhost:11434",
    "model": "mistral"
}
provider = LLMProviderRegistry.create("ollama_local", config)

# Method 2: Auto-configure from environment
config = LLMProviderRegistry.auto_configure("openai")
# Loads OPENAI_API_KEY from environment

# Method 3: Builder pattern
config = ProviderConfigBuilder("vertex_ai") \
    .with_env_vars() \
    .with_defaults() \
    .with_custom(location="europe-west1") \
    .build()

provider = LLMProviderRegistry.create("vertex_ai", config)
```

### Validate Configuration

```python
config = {
    "api_key": "sk-...",
    "model": "gpt-4"
}

is_valid, errors = LLMProviderRegistry.validate_config("openai", config)

if not is_valid:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
```

### Use Provider with Fallback

```python
# Create factory with primary + fallback
factory = LLMProviderFactory(
    primary_provider="openai",
    fallback_provider="ollama_local",
    primary_config={
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "gpt-4"
    },
    fallback_config={
        "base_url": "http://localhost:11434",
        "model": "mistral"
    }
)

# Get available provider (tries primary, falls back to secondary)
provider = factory.get_provider()

# Use provider
if provider:
    explanation = provider.explain_anomaly(context)
else:
    print("No providers available")
```

### Implement Custom Provider

```python
from services.genai_reasoning.provider_registry import ILLMProvider, LLMProviderRegistry

class LLamaProvider(ILLMProvider):
    """Meta's Llama inference server"""
    
    def __init__(self, config: dict):
        self.endpoint = config.get("endpoint")
        self.model = config.get("model", "llama-2-7b")
    
    def explain_anomaly(self, context: dict) -> dict:
        import requests
        
        prompt = self._build_prompt(context)
        
        response = requests.post(
            f"{self.endpoint}/generate",
            json={"prompt": prompt, "model": self.model}
        )
        
        return self._parse_response(response.json())
    
    def health_check(self) -> bool:
        import requests
        try:
            resp = requests.get(f"{self.endpoint}/health", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def get_config_schema(self) -> dict:
        return {
            "endpoint": {"type": "string", "required": True},
            "model": {"type": "string", "default": "llama-2-7b"}
        }
    
    def _build_prompt(self, context: dict) -> str:
        return f"Analyze anomaly: {context}"
    
    def _parse_response(self, response: dict) -> dict:
        return {
            "summary": response.get("text", ""),
            "likely_causes": [],
            "recommended_actions": [],
            "severity": "Medium",
            "confidence": 0.7
        }

# Register provider
LLMProviderRegistry.register("llama", LLamaProvider)

# Add to templates
LLMProviderRegistry.PROVIDER_TEMPLATES["llama"] = {
    "description": "Meta Llama inference server",
    "required_config": ["endpoint"],
    "default_config": {"model": "llama-2-7b"}
}

# Use provider
provider = LLMProviderRegistry.create("llama", {
    "endpoint": "http://llama-server.example.com"
})
```

---

## 4. Using Flask Frontend

### Basic Setup

```python
from flask import Flask
from frontend.flask_frontend import FlaskFrontend

# Create Flask app
app = Flask(__name__)

# Initialize frontend
frontend = FlaskFrontend(app)

# Run
if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

### Using Existing Flask App

```python
from flask import Flask
from frontend.flask_frontend import FlaskFrontend

# Your existing Flask app
app = Flask(__name__)

# Add routes from frontend
frontend = FlaskFrontend(app)

# Your custom routes
@app.route("/custom")
def custom():
    return {"message": "Hello from custom route"}

# Run app
app.run()
```

### API Endpoints

```bash
# Upload data
curl -X POST http://localhost:5000/api/data/upload \
  -F "file=@data.csv"

# Generate sample data
curl -X POST http://localhost:5000/api/data/sample \
  -H "Content-Type: application/json" \
  -d '{"num_sites": 5, "num_hours": 24}'

# Get data preview
curl http://localhost:5000/api/data/preview?limit=10

# Run detection
curl -X POST http://localhost:5000/api/anomaly/detect \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": ["rsrp", "throughput_mbps"],
    "method": "zscore",
    "threshold": 3.0
  }'

# Get results
curl http://localhost:5000/api/anomaly/results?limit=50

# Explain anomaly
curl -X POST http://localhost:5000/api/genai/explain \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_idx": 0,
    "provider": "ollama_local",
    "genai_config": {
      "base_url": "http://localhost:11434",
      "model": "mistral"
    }
  }'

# Get summary
curl http://localhost:5000/api/summary

# Download results
curl http://localhost:5000/api/results/download > anomalies.csv
```

---

## 5. Complete Example Workflow

```python
import os
from backend.data_source_registry import DataSourceRegistry
from services.anomaly_detection.kpi_detector import detect_anomalies
from services.genai_reasoning.provider_registry import LLMProviderFactory
from services.genai_reasoning.context_builder import build_anomaly_context

# Step 1: Load data from REST API
data_source = DataSourceRegistry.create(
    "rest_api",
    endpoint="https://api.telus.com/network-kpi",
    headers={"Authorization": f"Bearer {os.getenv('API_TOKEN')}"},
    params={"hours": 24}
)

print("Loading data...")
df = data_source.load()
print(f"Loaded {len(df)} rows")

# Step 2: Detect anomalies
print("\nDetecting anomalies...")
result_df = detect_anomalies(
    df=df,
    metrics=["rsrp", "throughput_mbps", "latency_ms"],
    method="zscore",
    config={"threshold": 3.0}
)

anomalies = result_df[result_df["is_anomaly"]]
print(f"Found {len(anomalies)} anomalies ({len(anomalies)/len(result_df)*100:.1f}%)")

# Step 3: Analyze with GenAI
print("\nAnalyzing with GenAI...")
factory = LLMProviderFactory(
    primary_provider="openai",
    fallback_provider="ollama_local",
    primary_config={"api_key": os.getenv("OPENAI_API_KEY")},
    fallback_config={"base_url": "http://localhost:11434"}
)

# Get first anomaly
if len(anomalies) > 0:
    anomaly = anomalies.iloc[0]
    
    context = build_anomaly_context(
        df=result_df,
        anomaly_row=anomaly,
        metric_columns=["rsrp", "throughput_mbps", "latency_ms"]
    )
    
    explanation = factory.explain_anomaly(context)
    
    print(f"\nSummary: {explanation['summary']}")
    print(f"Severity: {explanation['severity']}")
    print(f"Confidence: {explanation['confidence']:.0%}")
    print("\nCauses:")
    for i, cause in enumerate(explanation['likely_causes'], 1):
        print(f"  {i}. {cause}")
    print("\nActions:")
    for i, action in enumerate(explanation['recommended_actions'], 1):
        print(f"  {i}. {action}")
```

---

## 6. Configuration Management

### Load Configuration

```python
import os
from dotenv import load_dotenv
from services.genai_reasoning.provider_registry import LLMProviderRegistry

# Load from .env file
load_dotenv()

# Auto-configure provider from environment
provider_type = os.getenv("GENAI_PROVIDER", "ollama_local")
config = LLMProviderRegistry.auto_configure(provider_type)

# Validate
is_valid, errors = LLMProviderRegistry.validate_config(provider_type, config)

if not is_valid:
    print("Configuration invalid:")
    for error in errors:
        print(f"  - {error}")
else:
    provider = LLMProviderRegistry.create(provider_type, config)
    print(f"Using provider: {provider_type}")
```

---

## Summary

The new pluggable architecture provides:

1. **Frontend Abstraction** - Support any UI (Streamlit, Flask, CLI, etc.)
2. **Data Source Registry** - Connect to any data source (CSV, APIs, DBs, etc.)
3. **LLM Provider Registry** - Use any LLM provider (Ollama, OpenAI, Vertex, Azure, etc.)
4. **Flask Frontend** - Ready-to-use REST frontend example

All components are **fully extensible** through implementation of abstract interfaces and registry-based registration.

See `ARCHITECTURE_EXTENSIBILITY.md` and `PLUGGABLE_ARCHITECTURE.md` for detailed documentation.
