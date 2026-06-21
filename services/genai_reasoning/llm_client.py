"""
Provider-agnostic LLM client for anomaly explanation and reasoning.
Supports: Ollama (local), OpenAI, Vertex AI, Azure OpenAI.
"""
import requests
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OLLAMA_LOCAL = "ollama_local"
    OPENAI = "openai"
    VERTEX_AI = "vertex_ai"
    AZURE_OPENAI = "azure_openai"


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def explain_anomaly(self, anomaly_context: Dict) -> Dict:
        """
        Generate explanation for detected anomalies.
        
        Args:
            anomaly_context: Dict with anomaly data, metrics, thresholds, etc.
        
        Returns:
            {
                "summary": str,
                "likely_causes": list[str],
                "recommended_actions": list[str],
                "severity": str,  # "Low", "Medium", "High", "Critical"
                "confidence": float  # 0.0-1.0
            }
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if provider is available"""
        pass


class OllamaLocalProvider(BaseLLMProvider):
    """Local Ollama LLM provider"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: int = 60
    ):
        """
        Initialize Ollama local provider.
        
        Args:
            base_url: Ollama server base URL
            model: Model name (llama2, mistral, neural-chat, etc.)
            temperature: Sampling temperature (0.0-1.0)
            top_p: Top-p sampling parameter
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.timeout = timeout
    
    def health_check(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
    
    def _call_ollama(self, prompt: str) -> str:
        """Make a request to Ollama API"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "stream": False,
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()["response"]
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None
    
    def explain_anomaly(self, anomaly_context: Dict) -> Dict:
        """Generate anomaly explanation using Ollama"""
        
        # Build context string
        metrics_info = json.dumps(anomaly_context.get("metrics", {}), indent=2)
        anomaly_info = json.dumps(anomaly_context.get("anomalies", {}), indent=2)
        site_id = anomaly_context.get("site_id", "Unknown")
        timestamp = anomaly_context.get("timestamp", "Unknown")
        
        prompt = f"""You are a network operations expert analyzing cell site performance anomalies.

INCIDENT CONTEXT:
- Site ID: {site_id}
- Timestamp: {timestamp}

DETECTED ANOMALIES:
{anomaly_info}

CURRENT METRICS:
{metrics_info}

Please provide a concise analysis in the following JSON format:
{{
  "summary": "1-2 sentence summary of the issue",
  "likely_causes": ["cause1", "cause2", "cause3"],
  "recommended_actions": ["action1", "action2", "action3"],
  "severity": "Low|Medium|High|Critical",
  "confidence": 0.85
}}

Respond with ONLY valid JSON, no additional text."""

        response_text = self._call_ollama(prompt)
        
        if not response_text:
            # Return fallback response if Ollama unavailable
            return self._fallback_response(anomaly_context)
        
        # Try to parse JSON from response
        try:
            # Extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text
            
            result = json.loads(json_str)
            return self._validate_response(result)
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"Failed to parse Ollama response: {e}")
            return self._fallback_response(anomaly_context)
    
    def _fallback_response(self, anomaly_context: Dict) -> Dict:
        """Generate fallback response when LLM is unavailable"""
        anomalies = anomaly_context.get("anomalies", {})
        
        causes = []
        actions = []
        severity = "Medium"
        
        # Simple heuristic-based fallback
        if "rsrp" in anomalies and anomalies["rsrp"]["is_anomaly"]:
            causes.append("Signal strength degradation (RSRP drop)")
            actions.append("Check antenna alignment and obstruction")
            severity = "High"
        
        if "sinr" in anomalies and anomalies["sinr"]["is_anomaly"]:
            causes.append("Signal-to-noise ratio degradation")
            actions.append("Investigate interference sources")
        
        if "throughput_mbps" in anomalies and anomalies["throughput_mbps"]["is_anomaly"]:
            causes.append("Capacity issue or congestion")
            actions.append("Check backhaul and traffic load")
            if severity == "Medium":
                severity = "High"
        
        if "latency_ms" in anomalies and anomalies["latency_ms"]["is_anomaly"]:
            causes.append("Network latency increase")
            actions.append("Check transport network and core connectivity")
        
        if "dropped_call_rate" in anomalies and anomalies["dropped_call_rate"]["is_anomaly"]:
            causes.append("Elevated call drop rate")
            actions.append("Review radio conditions and availability")
            severity = "Critical"
        
        if not causes:
            causes = ["Unknown anomaly pattern detected"]
            actions = ["Collect additional metrics and logs"]
        
        actions.append("Escalate to operations team if issue persists")
        
        return {
            "summary": f"{len(anomalies)} metric anomalies detected",
            "likely_causes": causes[:3],
            "recommended_actions": actions[:3],
            "severity": severity,
            "confidence": 0.6
        }
    
    def _validate_response(self, response: Dict) -> Dict:
        """Validate and normalize LLM response"""
        # Ensure all required fields exist
        return {
            "summary": str(response.get("summary", "")),
            "likely_causes": response.get("likely_causes", [])[:5],
            "recommended_actions": response.get("recommended_actions", [])[:5],
            "severity": response.get("severity", "Medium"),
            "confidence": float(response.get("confidence", 0.7))
        }


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        timeout: int = 30
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.base_url = "https://api.openai.com/v1"
    
    def health_check(self) -> bool:
        """Check if OpenAI API is available"""
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(
                f"{self.base_url}/models/gpt-3.5-turbo",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False
    
    def explain_anomaly(self, anomaly_context: Dict) -> Dict:
        """Generate anomaly explanation using OpenAI"""
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            return self._fallback_response(anomaly_context)
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            user_message = self._build_prompt(anomaly_context)
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a network operations expert. Respond with valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ],
                    "temperature": self.temperature,
                    "max_tokens": 500
                },
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            # Parse JSON response
            result = json.loads(content)
            return self._validate_response(result)
        
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return self._fallback_response(anomaly_context)
    
    def _build_prompt(self, anomaly_context: Dict) -> str:
        """Build prompt for OpenAI"""
        metrics_info = json.dumps(anomaly_context.get("metrics", {}), indent=2)
        anomaly_info = json.dumps(anomaly_context.get("anomalies", {}), indent=2)
        
        return f"""Analyze this cell site anomaly and provide JSON response:

Site ID: {anomaly_context.get("site_id", "Unknown")}
Timestamp: {anomaly_context.get("timestamp", "Unknown")}

Anomalies:
{anomaly_info}

Metrics:
{metrics_info}

Return JSON:
{{
  "summary": "1-2 sentence summary",
  "likely_causes": ["cause1", "cause2", "cause3"],
  "recommended_actions": ["action1", "action2", "action3"],
  "severity": "Low|Medium|High|Critical",
  "confidence": 0.85
}}"""
    
    def _fallback_response(self, anomaly_context: Dict) -> Dict:
        """Fallback response"""
        return {
            "summary": "Analysis unavailable - using fallback",
            "likely_causes": ["Refer to metrics for root cause"],
            "recommended_actions": ["Review detailed metrics", "Contact support"],
            "severity": "Medium",
            "confidence": 0.5
        }
    
    def _validate_response(self, response: Dict) -> Dict:
        """Validate response"""
        return {
            "summary": str(response.get("summary", "")),
            "likely_causes": response.get("likely_causes", [])[:5],
            "recommended_actions": response.get("recommended_actions", [])[:5],
            "severity": response.get("severity", "Medium"),
            "confidence": float(response.get("confidence", 0.7))
        }


class VertexAIProvider(BaseLLMProvider):
    """Vertex AI (Google Cloud) LLM provider - Stub"""
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model: str = "text-bison@001",
        temperature: float = 0.7
    ):
        self.project_id = project_id
        self.location = location
        self.model = model
        self.temperature = temperature
    
    def health_check(self) -> bool:
        """Check if Vertex AI is available - stub"""
        logger.info("Vertex AI health check - stub implementation")
        return bool(self.project_id)
    
    def explain_anomaly(self, anomaly_context: Dict) -> Dict:
        """Stub implementation for Vertex AI"""
        logger.info("Vertex AI explain_anomaly - using stub implementation")
        return {
            "summary": f"Anomalies detected at {anomaly_context.get('site_id')}",
            "likely_causes": ["Refer to detailed metrics for analysis"],
            "recommended_actions": ["Integrate Vertex AI for full analysis"],
            "severity": "Medium",
            "confidence": 0.5,
            "note": "Vertex AI integration - stub"
        }


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI LLM provider - Stub"""
    
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment_id: str,
        temperature: float = 0.7
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment_id = deployment_id
        self.temperature = temperature
    
    def health_check(self) -> bool:
        """Check if Azure OpenAI is available - stub"""
        logger.info("Azure OpenAI health check - stub implementation")
        return bool(self.endpoint and self.api_key)
    
    def explain_anomaly(self, anomaly_context: Dict) -> Dict:
        """Stub implementation for Azure OpenAI"""
        logger.info("Azure OpenAI explain_anomaly - using stub implementation")
        return {
            "summary": f"Incident analysis for {anomaly_context.get('site_id')}",
            "likely_causes": ["Refer to detailed metrics"],
            "recommended_actions": ["Integrate Azure OpenAI for full analysis"],
            "severity": "Medium",
            "confidence": 0.5,
            "note": "Azure OpenAI integration - stub"
        }


class LLMClient:
    """
    Provider-agnostic LLM client for anomaly explanation.
    Main entry point for GenAI reasoning layer.
    """
    
    def __init__(self, provider: str, config: Dict):
        """
        Initialize LLM client.
        
        Args:
            provider: One of 'ollama_local', 'openai', 'vertex_ai', 'azure_openai'
            config: Provider-specific configuration dict
        
        Examples:
            Ollama:
            >>> client = LLMClient('ollama_local', {
            ...     'base_url': 'http://localhost:11434',
            ...     'model': 'llama2'
            ... })
            
            OpenAI:
            >>> client = LLMClient('openai', {
            ...     'api_key': 'sk-...',
            ...     'model': 'gpt-3.5-turbo'
            ... })
        """
        self.provider = provider
        self.config = config
        self.llm = self._initialize_provider(provider, config)
        
        # Check health on initialization
        is_healthy = self.llm.health_check()
        logger.info(f"LLM Client initialized with {provider} - Health: {is_healthy}")
    
    def _initialize_provider(self, provider: str, config: Dict) -> BaseLLMProvider:
        """Initialize the appropriate LLM provider"""
        
        if provider == LLMProvider.OLLAMA_LOCAL:
            return OllamaLocalProvider(
                base_url=config.get("base_url", "http://localhost:11434"),
                model=config.get("model", "llama2"),
                temperature=config.get("temperature", 0.7),
                top_p=config.get("top_p", 0.9),
                timeout=config.get("timeout", 60)
            )
        
        elif provider == LLMProvider.OPENAI:
            return OpenAIProvider(
                api_key=config.get("api_key", ""),
                model=config.get("model", "gpt-3.5-turbo"),
                temperature=config.get("temperature", 0.7),
                timeout=config.get("timeout", 30)
            )
        
        elif provider == LLMProvider.VERTEX_AI:
            return VertexAIProvider(
                project_id=config.get("project_id", ""),
                location=config.get("location", "us-central1"),
                model=config.get("model", "text-bison@001"),
                temperature=config.get("temperature", 0.7)
            )
        
        elif provider == LLMProvider.AZURE_OPENAI:
            return AzureOpenAIProvider(
                endpoint=config.get("endpoint", ""),
                api_key=config.get("api_key", ""),
                deployment_id=config.get("deployment_id", ""),
                temperature=config.get("temperature", 0.7)
            )
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def explain_anomaly(self, anomaly_context: Dict) -> Dict:
        """
        Generate explanation for detected anomalies.
        
        Args:
            anomaly_context: Dict with structure:
            {
                "site_id": str,
                "timestamp": str,
                "anomalies": {metric_name: {is_anomaly, score, value, threshold}},
                "metrics": {metric_name: {value, min, max, avg}}
            }
        
        Returns:
            {
                "summary": str,
                "likely_causes": list[str],
                "recommended_actions": list[str],
                "severity": str,
                "confidence": float
            }
        """
        return self.llm.explain_anomaly(anomaly_context)
    
    def is_available(self) -> bool:
        """Check if LLM provider is available"""
        return self.llm.health_check()
    
    def get_provider_info(self) -> Dict:
        """Get information about current provider"""
        return {
            "provider": self.provider,
            "provider_class": self.llm.__class__.__name__,
            "is_available": self.is_available()
        }


if __name__ == "__main__":
    # Example usage
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Example with Ollama
    client = LLMClient("ollama_local", {
        "base_url": "http://localhost:11434",
        "model": "llama2"
    })
    
    sample_context = {
        "site_id": "CELL_001",
        "timestamp": "2026-06-20T14:30:00Z",
        "anomalies": {
            "rsrp": {"is_anomaly": True, "score": 0.92, "value": -130},
            "sinr": {"is_anomaly": True, "score": 0.85, "value": 2},
            "throughput_mbps": {"is_anomaly": True, "score": 0.78, "value": 45}
        },
        "metrics": {
            "rsrp": {"value": -130, "min": -140, "max": -50, "avg": -95},
            "sinr": {"value": 2, "min": -10, "max": 30, "avg": 15}
        }
    }
    
    result = client.explain_anomaly(sample_context)
    print(json.dumps(result, indent=2))
