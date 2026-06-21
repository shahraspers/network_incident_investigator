"""
Pluggable GenAI reasoning layer.
Supports: Ollama (local), OpenAI (cloud), Vertex AI (Google Cloud).
"""
import requests
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from enum import Enum


class GenAIProvider(str, Enum):
    """Supported GenAI providers"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    VERTEX = "vertex"


class GenAIReasoner(ABC):
    """Abstract base class for GenAI reasoning"""
    
    @abstractmethod
    def reason(self, context: str, query: str) -> str:
        """
        Generate reasoning based on context and query.
        
        Args:
            context: Context information (anomaly data, metrics, etc.)
            query: User query or reasoning task
        
        Returns:
            Reasoning result from GenAI model
        """
        pass
    
    @abstractmethod
    def classify_incident(self, incident_data: Dict) -> Dict:
        """
        Classify a network incident.
        
        Args:
            incident_data: Incident information
        
        Returns:
            Classification results with severity, type, recommendations
        """
        pass


class OllamaReasoner(GenAIReasoner):
    """Local Ollama-based reasoning"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["response"]
        except requests.exceptions.ConnectionError:
            return f"[Ollama unavailable at {self.base_url}] Simulated response based on context"
        except Exception as e:
            return f"[Error calling Ollama: {str(e)}] Proceeding with fallback reasoning"
    
    def reason(self, context: str, query: str) -> str:
        """Generate reasoning"""
        prompt = f"""
You are a network incident investigation expert. Analyze the provided context and answer the query.

Context (anomaly and metric data):
{context}

Query:
{query}

Provide a detailed analysis with:
1. Key observations
2. Potential root causes
3. Recommended actions

Answer:
"""
        return self._call_ollama(prompt)
    
    def classify_incident(self, incident_data: Dict) -> Dict:
        """Classify incident severity and type"""
        context = json.dumps(incident_data, indent=2)
        prompt = f"""
Analyze the following network incident data and provide a classification:

Incident Data:
{context}

Classify the incident with:
1. Severity (Low/Medium/High/Critical)
2. Incident Type (e.g., Traffic Surge, Memory Leak, Latency Spike, Packet Loss)
3. Affected Components
4. Immediate Recommendations (3-5 actions)

Provide response in JSON format.
"""
        
        result_text = self._call_ollama(prompt)
        
        # Try to parse JSON response
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            return {
                "severity": "Medium",
                "incident_type": "Anomaly Detected",
                "affected_components": ["network_metrics"],
                "recommendations": [
                    "Review detailed metrics",
                    "Check for ongoing events",
                    "Validate anomaly detection",
                    "Alert operations team if critical"
                ],
                "raw_response": result_text
            }


class OpenAIReasoner(GenAIReasoner):
    """OpenAI-based reasoning"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = "https://api.openai.com/v1"
    
    def _call_openai(self, messages: List[Dict]) -> str:
        """Call OpenAI API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                },
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.ConnectionError:
            return "[OpenAI API unavailable] Simulated response based on context"
        except Exception as e:
            return f"[Error calling OpenAI: {str(e)}]"
    
    def reason(self, context: str, query: str) -> str:
        """Generate reasoning"""
        messages = [
            {
                "role": "system",
                "content": "You are a network incident investigation expert. Analyze the provided context and provide detailed analysis."
            },
            {
                "role": "user",
                "content": f"""Analyze the following anomaly and metric data:

Context:
{context}

Query:
{query}

Provide detailed analysis with key observations, potential root causes, and recommendations."""
            }
        ]
        return self._call_openai(messages)
    
    def classify_incident(self, incident_data: Dict) -> Dict:
        """Classify incident"""
        context = json.dumps(incident_data, indent=2)
        messages = [
            {
                "role": "system",
                "content": "You are a network operations expert. Classify incidents with severity, type, and recommendations."
            },
            {
                "role": "user",
                "content": f"""Classify this network incident:

{context}

Provide JSON response with: severity, incident_type, affected_components, recommendations."""
            }
        ]
        
        result_text = self._call_openai(messages)
        
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            return {
                "severity": "Medium",
                "incident_type": "Anomaly Detected",
                "affected_components": ["network_metrics"],
                "recommendations": ["Review metrics", "Alert team"],
                "raw_response": result_text
            }


class VertexAIReasoner(GenAIReasoner):
    """Vertex AI (Google Cloud) based reasoning"""
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model: str = "text-bison",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        self.project_id = project_id
        self.location = location
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Note: In production, use google-cloud-aiplatform library
        # For POC, this provides the interface
    
    def reason(self, context: str, query: str) -> str:
        """Generate reasoning"""
        # In production: from vertexai.language_models import TextGenerationModel
        # This is a placeholder for the POC
        prompt = f"""Analyze network incident:

Context:
{context}

Query:
{query}"""
        return f"[Vertex AI integration - placeholder] Analyzed context with {len(context)} chars"
    
    def classify_incident(self, incident_data: Dict) -> Dict:
        """Classify incident"""
        return {
            "severity": "Medium",
            "incident_type": "Anomaly Detected",
            "affected_components": ["network_metrics"],
            "recommendations": ["Review metrics", "Contact team"],
            "provider": "vertex_ai"
        }


class GenAIReasoningService:
    """Factory and service for GenAI reasoning"""
    
    def __init__(
        self,
        provider: str = "ollama",
        **kwargs
    ):
        """
        Initialize GenAI reasoning service.
        
        Args:
            provider: One of 'ollama', 'openai', 'vertex'
            **kwargs: Provider-specific configuration
        """
        self.provider = provider
        self.reasoner = self._create_reasoner(provider, kwargs)
    
    def _create_reasoner(self, provider: str, config: Dict) -> GenAIReasoner:
        """Create the appropriate reasoner"""
        if provider == GenAIProvider.OLLAMA:
            return OllamaReasoner(
                base_url=config.get("base_url", "http://localhost:11434"),
                model=config.get("model", "llama2"),
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 1000)
            )
        elif provider == GenAIProvider.OPENAI:
            return OpenAIReasoner(
                api_key=config.get("api_key", ""),
                model=config.get("model", "gpt-3.5-turbo"),
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 1000)
            )
        elif provider == GenAIProvider.VERTEX:
            return VertexAIReasoner(
                project_id=config.get("project_id", ""),
                location=config.get("location", "us-central1"),
                model=config.get("model", "text-bison"),
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 1000)
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def analyze_anomaly(
        self,
        anomaly_data: Dict,
        metrics_data: Dict
    ) -> str:
        """
        Analyze detected anomaly.
        
        Args:
            anomaly_data: Anomaly detection results
            metrics_data: Metric values and statistics
        
        Returns:
            Analysis reasoning
        """
        context = f"""
Anomaly Detection Results:
{json.dumps(anomaly_data, indent=2)}

Metric Statistics:
{json.dumps(metrics_data, indent=2)}
"""
        
        query = "What are the likely causes of these anomalies and what actions should be taken?"
        
        return self.reasoner.reason(context, query)
    
    def investigate_incident(
        self,
        incident_data: Dict
    ) -> Dict:
        """
        Investigate a network incident.
        
        Args:
            incident_data: Incident information (anomalies, metrics, etc.)
        
        Returns:
            Incident classification and recommendations
        """
        return self.reasoner.classify_incident(incident_data)
    
    def get_provider_info(self) -> Dict:
        """Get information about current provider"""
        return {
            "provider": self.provider,
            "reasoner_type": self.reasoner.__class__.__name__
        }


if __name__ == "__main__":
    # Example usage
    
    # Create service with Ollama (default)
    service = GenAIReasoningService(provider="ollama")
    
    # Sample anomaly data
    sample_data = {
        "cpu_utilization": {"anomaly_score": 0.85, "value": 95},
        "memory_utilization": {"anomaly_score": 0.72, "value": 88},
        "packet_loss_rate": {"anomaly_score": 0.45, "value": 2.3}
    }
    
    # Investigate incident
    result = service.investigate_incident(sample_data)
    print("Incident Investigation Result:")
    print(json.dumps(result, indent=2))
