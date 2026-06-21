# Architecture Guide - Extensibility & Pluggable Design

## Overview

The Network Incident Investigator is built with a fully **pluggable and scalable architecture**. This guide explains how to extend the system with:
- New frontend implementations (beyond Streamlit)
- Additional LLM providers (beyond Ollama/OpenAI)
- Custom data sources (beyond CSV)
- Custom anomaly detection algorithms
- Custom business logic

---

## 1. Frontend Extensibility

### Current Architecture

The system now includes a **frontend abstraction layer** (`frontend/abstract_frontend.py`) that defines the interface all frontends must implement.

### Supported Frontend Types

1. **Streamlit** (current) - Interactive web UI
2. **CLI** (included) - Command-line interface
3. **FastAPI** - REST-based frontend
4. **React/Vue** - JavaScript frontends
5. **Desktop Apps** - Electron, PyQt, etc.
6. **Mobile** - React Native, Flutter

### How to Add a New Frontend

#### Step 1: Implement IFrontend Interface

Create a new file in `frontend/` directory (e.g., `frontend/flask_frontend.py`):

```python
from frontend.abstract_frontend import IFrontend, DetectionConfig, GenAIConfig
from typing import Dict, List, Optional

class FlaskFrontend(IFrontend):
    """Flask-based web frontend"""
    
    def __init__(self, app):
        self.app = app
    
    def upload_data(self) -> Optional[Dict]:
        """Handle file upload route"""
        from flask import request
        import pandas as pd
        
        if 'file' not in request.files:
            return {"success": False, "error": "No file uploaded"}
        
        file = request.files['file']
        try:
            df = pd.read_csv(file)
            return {"success": True, "data": df}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_detection_config(self) -> DetectionConfig:
        """Get config from POST request"""
        from flask import request
        
        data = request.get_json()
        return DetectionConfig(
            metrics=data.get("metrics", []),
            method=data.get("method", "zscore"),
            threshold=float(data.get("threshold", 3.0))
        )
    
    def get_genai_config(self) -> GenAIConfig:
        """Get GenAI config from POST request"""
        from flask import request
        
        data = request.get_json()
        return GenAIConfig(
            provider=data.get("provider", "ollama_local"),
            model=data.get("model", "llama2")
        )
    
    def display_detection_results(self, results: Dict) -> None:
        """Return results as JSON"""
        pass  # Flask will return directly
    
    def select_anomaly(self, anomaly_rows: List[Dict]) -> Optional[Dict]:
        """Get selected anomaly from request parameter"""
        from flask import request
        
        idx = request.args.get("anomaly_idx", 0, type=int)
        return anomaly_rows[idx] if idx < len(anomaly_rows) else None
    
    def display_genai_explanation(self, explanation: Dict) -> None:
        """Return explanation as JSON"""
        pass
    
    def display_executive_summary(self, summary: Dict) -> None:
        """Return summary as JSON"""
        pass
    
    def run(self) -> None:
        """Run Flask app"""
        self.app.run(debug=True)
```

#### Step 2: Use in Application

```python
from flask import Flask
from frontend.flask_frontend import FlaskFrontend
from frontend.abstract_frontend import FrontendWorkflow

app = Flask(__name__)
frontend = FlaskFrontend(app)
workflow = FrontendWorkflow(frontend, backend_url="http://localhost:8000")

@app.route("/api/analyze", methods=["POST"])
def analyze():
    return workflow.run_workflow()
```

#### Step 3: Register Frontend

In `config/__init__.py`:

```python
AVAILABLE_FRONTENDS = {
    "streamlit": "frontend.app.StreamlitFrontend",
    "cli": "frontend.abstract_frontend.CLIFrontend",
    "flask": "frontend.flask_frontend.FlaskFrontend",
}
```

---

## 2. LLM Provider Extensibility

### Current Architecture

The system includes a **provider registry** (`services/genai_reasoning/provider_registry.py`) that manages all LLM providers with a factory pattern.

### Built-in Providers

- ✅ **Ollama Local** - Local LLM inference (llama2, mistral, neural-chat)
- ✅ **OpenAI** - Cloud API (gpt-3.5-turbo, gpt-4)
- 🔄 **Vertex AI** - Google Cloud generative AI
- 🔄 **Azure OpenAI** - Microsoft cloud AI
- 🔧 **Custom** - Any provider you implement

### How to Add a New LLM Provider

#### Step 1: Implement ILLMProvider

Create new provider class (e.g., `services/genai_reasoning/providers/anthropic_provider.py`):

```python
from services.genai_reasoning.provider_registry import ILLMProvider
import anthropic

class AnthropicProvider(ILLMProvider):
    """Claude AI provider via Anthropic API"""
    
    def __init__(self, config: dict):
        self.config = config
        self.api_key = config.get("api_key")
        self.model = config.get("model", "claude-3-sonnet-20240229")
    
    def explain_anomaly(self, anomaly_context: dict) -> dict:
        """Generate explanation using Claude"""
        client = anthropic.Anthropic(api_key=self.api_key)
        
        # Build prompt
        prompt = self._build_prompt(anomaly_context)
        
        # Call Claude API
        message = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Parse response
        response_text = message.content[0].text
        return self._parse_response(response_text)
    
    def health_check(self) -> bool:
        """Check if Anthropic API is accessible"""
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            # Send minimal request
            response = client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            return response is not None
        except Exception:
            return False
    
    def get_config_schema(self) -> dict:
        """Return configuration schema"""
        return {
            "api_key": {
                "type": "string",
                "description": "Anthropic API key",
                "required": True,
                "secret": True
            },
            "model": {
                "type": "string",
                "description": "Claude model to use",
                "default": "claude-3-sonnet-20240229",
                "options": [
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307"
                ]
            }
        }
    
    def _build_prompt(self, context: dict) -> str:
        """Build prompt from anomaly context"""
        return f"""
        Analyze this network anomaly and provide root cause analysis:
        
        Site: {context.get('site_id')}
        Time: {context.get('timestamp')}
        Anomalies: {context.get('anomalies')}
        
        Provide:
        1. Summary (2-3 sentences)
        2. Likely causes (ranked list)
        3. Recommended actions (actionable steps)
        4. Severity (Low/Medium/High/Critical)
        """
    
    def _parse_response(self, text: str) -> dict:
        """Parse Claude response into structured format"""
        # Implement parsing logic
        return {
            "summary": "...",
            "likely_causes": ["..."],
            "recommended_actions": ["..."],
            "severity": "Medium",
            "confidence": 0.8
        }
```

#### Step 2: Register Provider

```python
from services.genai_reasoning.provider_registry import LLMProviderRegistry
from services.genai_reasoning.providers.anthropic_provider import AnthropicProvider

# Register in config or startup
LLMProviderRegistry.register("anthropic", AnthropicProvider)

# Add to templates
LLMProviderRegistry.PROVIDER_TEMPLATES["anthropic"] = {
    "description": "Anthropic Claude AI",
    "required_config": ["api_key"],
    "default_config": {"model": "claude-3-sonnet-20240229"},
    "env_vars": {"api_key": "ANTHROPIC_API_KEY"}
}
```

#### Step 3: Use Provider

```python
from services.genai_reasoning.provider_registry import LLMProviderRegistry

# Create provider
config = {
    "api_key": os.getenv("ANTHROPIC_API_KEY"),
    "model": "claude-3-opus-20240229"
}

provider = LLMProviderRegistry.create("anthropic", config)

# Validate before use
is_valid, errors = LLMProviderRegistry.validate_config("anthropic", config)
if is_valid:
    explanation = provider.explain_anomaly(context)
```

---

## 3. Data Source Extensibility

### Current Architecture

Data sources are managed via **DataSourceRegistry** (`backend/data_source_registry.py`) with support for:
- CSV files
- REST APIs
- SQL Databases
- Streaming (Kafka, Kinesis, Pub/Sub)
- Cloud Storage (S3, GCS, Azure)

### How to Add a Custom Data Source

#### Step 1: Implement IDataSource

```python
from backend.data_source_registry import IDataSource
import pandas as pd

class CustomDataSource(IDataSource):
    """Custom data source implementation"""
    
    def __init__(self, custom_param: str):
        self.custom_param = custom_param
    
    def load(self, **kwargs) -> pd.DataFrame:
        """
        Load data and return DataFrame with required columns:
        - timestamp: datetime
        - site_id: str/int
        - [metric columns]: float
        """
        # Implement your data loading logic
        data = self._fetch_data(**kwargs)
        df = pd.DataFrame(data)
        
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        return df
    
    def validate(self) -> bool:
        """Check if source is accessible"""
        try:
            self.load()
            return True
        except Exception:
            return False
    
    def get_schema(self) -> dict:
        """Return data schema"""
        df = self.load()
        return {
            "columns": df.columns.tolist(),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "rows": len(df)
        }
    
    def _fetch_data(self, **kwargs) -> list:
        """Implement actual data fetching"""
        # Your implementation here
        pass
```

#### Step 2: Register Data Source

```python
from backend.data_source_registry import DataSourceRegistry
from your_module import CustomDataSource

# Register
DataSourceRegistry.register("custom_source", CustomDataSource)

# Use
source = DataSourceRegistry.create(
    "custom_source",
    custom_param="value"
)

df = source.load()
```

---

## 4. Anomaly Detection Algorithm Extensibility

### How to Add a Custom Detection Algorithm

```python
from services.anomaly_detection.kpi_detector import AnomalyDetector
import numpy as np

class CustomDetector(AnomalyDetector):
    """Custom anomaly detection algorithm"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.custom_param = config.get("custom_param", 0.5)
    
    def detect(self, series: np.ndarray) -> dict:
        """
        Detect anomalies in time series.
        
        Returns:
            {
                "is_anomaly": bool,
                "score": float (0-1),
                "threshold": float
            }
        """
        # Implement custom detection logic
        anomaly_scores = self._compute_scores(series)
        threshold = self.config.get("threshold", 0.5)
        
        return {
            "is_anomaly": np.max(anomaly_scores) > threshold,
            "scores": anomaly_scores,
            "threshold": threshold
        }
    
    def _compute_scores(self, series: np.ndarray) -> np.ndarray:
        """Your custom scoring logic"""
        # Implementation
        pass
```

### Register Custom Detector

```python
from services.anomaly_detection.kpi_detector import NetworkKPIAnomalyDetectionService

# Register in service initialization
service = NetworkKPIAnomalyDetectionService()
service.register_detector("custom_detector", CustomDetector)

# Use in detection
result = service.detect_anomalies(
    df=df,
    metrics=["rsrp", "throughput_mbps"],
    method="custom_detector"
)
```

---

## 5. Architecture Patterns

### Plugin Architecture

```
System Core
├── Frontend Layer (Pluggable)
│   ├── IFrontend interface
│   ├── Streamlit implementation
│   ├── CLI implementation
│   ├── Flask implementation
│   └── [Your custom implementation]
│
├── Backend API (REST)
│   └── Agnostic to frontend
│
├── Data Layer (Pluggable)
│   ├── IDataSource interface
│   ├── CSV source
│   ├── REST API source
│   ├── Database source
│   └── [Your custom source]
│
├── Detection Layer (Pluggable)
│   ├── AnomalyDetector base
│   ├── Z-Score
│   ├── MAD
│   ├── Isolation Forest
│   └── [Your custom detector]
│
└── GenAI Layer (Pluggable)
    ├── ILLMProvider interface
    ├── Ollama provider
    ├── OpenAI provider
    ├── Vertex AI provider
    ├── Azure OpenAI provider
    └── [Your custom provider]
```

### Dependency Flow

```
Frontend → REST API → Services → Data Sources
   ↓           ↓          ↓
[UI Logic]  [Routing]  [Business Logic]
   
Services → Anomaly Detection → Data
Services → GenAI Providers → LLM API
Services → Context Builder → Data Analysis
```

---

## 6. Configuration Hierarchy

### Priority Order (Highest to Lowest)

1. **Environment Variables** - `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, etc.
2. **Command-line Arguments** - `--provider ollama_local`
3. **Configuration Files** - `.env`, `config.yaml`
4. **Application Defaults** - Hardcoded in code

### Example Configuration

```yaml
# config.yaml
frontend:
  type: streamlit
  port: 8501

backend:
  type: fastapi
  port: 8000
  host: 0.0.0.0

data_source:
  type: rest_api
  endpoint: https://api.telus.com/network-kpi
  headers:
    Authorization: "Bearer {{TELUS_API_TOKEN}}"

genai:
  primary_provider: ollama_local
  fallback_provider: openai
  
  providers:
    ollama_local:
      base_url: http://localhost:11434
      model: llama2
    
    openai:
      model: gpt-3.5-turbo
      # api_key from env: OPENAI_API_KEY

detection:
  methods:
    - zscore
    - isolation_forest
  
  defaults:
    method: zscore
    threshold: 3.0
```

---

## 7. Testing Custom Extensions

### Unit Tests

```python
import pytest
from frontend.flask_frontend import FlaskFrontend
from services.genai_reasoning.providers.anthropic_provider import AnthropicProvider

class TestCustomFrontend:
    def test_upload_data(self):
        frontend = FlaskFrontend(app)
        result = frontend.upload_data()
        assert result["success"] is True

class TestCustomProvider:
    def test_health_check(self):
        config = {"api_key": "test-key"}
        provider = AnthropicProvider(config)
        # Mock API call
        assert provider.health_check() is True
    
    def test_explain_anomaly(self):
        provider = AnthropicProvider(config)
        result = provider.explain_anomaly(context)
        assert "summary" in result
        assert "likely_causes" in result
```

### Integration Tests

```python
def test_full_workflow_with_custom_frontend():
    """Test complete workflow with custom frontend"""
    frontend = FlaskFrontend(app)
    workflow = FrontendWorkflow(frontend)
    
    assert workflow.step1_load_data() is True
    assert workflow.step2_configure() is True
    assert workflow.step3_detect() is True
    assert workflow.step4_explain() is True
    assert workflow.step5_summarize() is True
```

---

## 8. Deployment Patterns

### Multi-Frontend Deployment

```
┌─────────────────────────────────────┐
│   Nginx Load Balancer               │
└─────────────────────────────────────┘
    ↓           ↓           ↓
┌────────┐ ┌────────┐ ┌────────┐
│Streamlit│ │Flask   │ │React   │
│:8501   │ │:5000   │ │:3000   │
└────────┘ └────────┘ └────────┘
    ↓           ↓           ↓
┌─────────────────────────────────────┐
│   FastAPI Backend (Port 8000)       │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│   Data Source (REST/DB/Streaming)   │
└─────────────────────────────────────┘
```

### Containerized Deployment

```dockerfile
# Dockerfile.custom-frontend
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run custom frontend
CMD ["python", "-m", "frontend.custom_frontend"]
```

---

## 9. Examples

### Example 1: Local Ollama + Flask Frontend

```python
# main.py
from flask import Flask
from frontend.flask_frontend import FlaskFrontend
from services.genai_reasoning.provider_registry import LLMProviderRegistry

app = Flask(__name__)
frontend = FlaskFrontend(app)

# Register Ollama provider
config = {
    "base_url": "http://localhost:11434",
    "model": "llama2"
}

provider = LLMProviderRegistry.create("ollama_local", config)

if __name__ == "__main__":
    app.run(port=5000)
```

### Example 2: Azure OpenAI + CLI Frontend

```python
# cli_app.py
from frontend.abstract_frontend import CLIFrontend, FrontendWorkflow
from services.genai_reasoning.provider_registry import ProviderConfigBuilder

# Build Azure config from env
config = ProviderConfigBuilder("azure_openai") \
    .with_env_vars() \
    .with_defaults() \
    .build()

# Create CLI frontend
frontend = CLIFrontend()
workflow = FrontendWorkflow(frontend)

# Run workflow
workflow.run_workflow()
```

### Example 3: Custom Data Source + Vertex AI

```python
from backend.data_source_registry import DataSourceRegistry
from services.genai_reasoning.provider_registry import LLMProviderRegistry

# Register custom data source
DataSourceRegistry.register("telus_backend", TELUSBackendSource)

# Load data
source = DataSourceRegistry.create(
    "telus_backend",
    endpoint="https://api.telus.com/kpi"
)
df = source.load()

# Analyze with Vertex AI
provider = LLMProviderRegistry.create("vertex_ai", {
    "project_id": "my-gcp-project"
})

result = provider.explain_anomaly(context)
```

---

## 10. Best Practices

1. **Always implement interfaces** - Use ABC for contracts
2. **Provide health checks** - Enable graceful degradation
3. **Log extensively** - Use standard Python logging
4. **Handle errors gracefully** - Return sensible defaults
5. **Document configuration** - Make it clear what's needed
6. **Write tests** - Unit tests for components
7. **Use registry patterns** - Enable runtime registration
8. **Avoid tight coupling** - Depend on abstractions
9. **Version APIs** - Plan for backward compatibility
10. **Monitor resources** - Track usage patterns

---

## Summary

The Network Incident Investigator is built with **separation of concerns** and **plugin architecture**:

- **Frontend**: Implement `IFrontend` for any UI platform
- **LLM Providers**: Implement `ILLMProvider` for any AI service
- **Data Sources**: Implement `IDataSource` for any data repository
- **Detection**: Extend `AnomalyDetector` for custom algorithms
- **Configuration**: Use registry patterns for pluggable components

This architecture enables **true scalability and flexibility** for enterprise deployments.
