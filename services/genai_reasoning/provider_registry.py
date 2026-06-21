"""
Enhanced LLM provider registry and configuration system.
Supports: Ollama (local), OpenAI, Vertex AI, Azure OpenAI + custom providers.
"""
from typing import Dict, Optional, Any, Type
from abc import ABC, abstractmethod
import os
import logging

logger = logging.getLogger(__name__)


class ILLMProvider(ABC):
    """Abstract interface for LLM providers"""
    
    @abstractmethod
    def explain_anomaly(self, anomaly_context: Dict) -> Dict:
        """Generate explanation for anomaly"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if provider is available"""
        pass
    
    @abstractmethod
    def get_config_schema(self) -> Dict:
        """Get configuration schema"""
        pass


class ProviderConfig:
    """Provider configuration"""
    
    def __init__(self, provider_type: str, config: Dict):
        self.provider_type = provider_type
        self.config = config
    
    def validate(self) -> bool:
        """Validate configuration"""
        required = self.get_required_fields()
        return all(key in self.config for key in required)
    
    def get_required_fields(self) -> list:
        """Get required configuration fields"""
        schemas = {
            "ollama_local": ["base_url", "model"],
            "openai": ["api_key", "model"],
            "vertex_ai": ["project_id", "location"],
            "azure_openai": ["endpoint", "api_key", "deployment_id"],
        }
        return schemas.get(self.provider_type, [])


class LLMProviderRegistry:
    """Registry for LLM providers with factory pattern"""
    
    _providers: Dict[str, Type[ILLMProvider]] = {}
    _default_provider = "ollama_local"
    
    # Built-in provider templates
    PROVIDER_TEMPLATES = {
        "ollama_local": {
            "description": "Local Ollama LLM server",
            "required_config": ["base_url", "model"],
            "default_config": {
                "base_url": "http://localhost:11434",
                "model": "llama2"
            }
        },
        "openai": {
            "description": "OpenAI API (gpt-3.5-turbo, gpt-4)",
            "required_config": ["api_key", "model"],
            "default_config": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7
            },
            "env_vars": {"api_key": "OPENAI_API_KEY"}
        },
        "vertex_ai": {
            "description": "Google Vertex AI LLMs",
            "required_config": ["project_id", "location"],
            "default_config": {
                "location": "us-central1",
                "model": "text-bison"
            },
            "env_vars": {"project_id": "GCP_PROJECT_ID"}
        },
        "azure_openai": {
            "description": "Azure OpenAI Service",
            "required_config": ["endpoint", "api_key", "deployment_id"],
            "default_config": {
                "api_version": "2023-05-15"
            },
            "env_vars": {
                "endpoint": "AZURE_OPENAI_ENDPOINT",
                "api_key": "AZURE_OPENAI_KEY"
            }
        }
    }
    
    @classmethod
    def register(cls, name: str, provider_class: Type[ILLMProvider]) -> None:
        """
        Register a custom LLM provider.
        
        Args:
            name: Provider name
            provider_class: Class implementing ILLMProvider
        """
        if not issubclass(provider_class, ILLMProvider):
            raise TypeError(f"{provider_class} must implement ILLMProvider")
        
        cls._providers[name] = provider_class
        logger.info(f"Registered LLM provider: {name}")
    
    @classmethod
    def create(cls, provider_type: str, config: Optional[Dict] = None) -> ILLMProvider:
        """
        Create LLM provider instance.
        
        Args:
            provider_type: Provider type (ollama_local, openai, vertex_ai, azure_openai, or custom)
            config: Provider-specific configuration
        
        Returns:
            ILLMProvider implementation
        
        Raises:
            ValueError: If provider not found or invalid configuration
        """
        if provider_type not in cls._providers:
            # Try to load from built-in providers if available
            if provider_type in cls.PROVIDER_TEMPLATES:
                logger.warning(f"Provider '{provider_type}' not registered, using fallback")
            else:
                raise ValueError(
                    f"Unknown provider: {provider_type}. "
                    f"Available: {cls.list_providers()}"
                )
        
        provider_class = cls._providers.get(provider_type)
        if provider_class:
            return provider_class(config or {})
        else:
            raise ValueError(f"Provider '{provider_type}' not implemented")
    
    @classmethod
    def list_providers(cls) -> list:
        """List available providers"""
        return list(cls._providers.keys())
    
    @classmethod
    def get_provider_config(cls, provider_type: str) -> Dict:
        """
        Get provider configuration template.
        
        Args:
            provider_type: Provider type
        
        Returns:
            Configuration template
        """
        return cls.PROVIDER_TEMPLATES.get(provider_type, {})
    
    @classmethod
    def auto_configure(cls, provider_type: str) -> Dict:
        """
        Auto-configure provider from environment variables.
        
        Args:
            provider_type: Provider type
        
        Returns:
            Configuration from environment
        """
        template = cls.PROVIDER_TEMPLATES.get(provider_type, {})
        config = template.get("default_config", {}).copy()
        
        # Load from environment variables
        env_vars = template.get("env_vars", {})
        for key, env_var in env_vars.items():
            env_value = os.getenv(env_var)
            if env_value:
                config[key] = env_value
        
        return config
    
    @classmethod
    def validate_config(cls, provider_type: str, config: Dict) -> tuple:
        """
        Validate provider configuration.
        
        Args:
            provider_type: Provider type
            config: Configuration to validate
        
        Returns:
            (is_valid: bool, errors: list[str])
        """
        template = cls.PROVIDER_TEMPLATES.get(provider_type, {})
        required = template.get("required_config", [])
        
        errors = []
        for field in required:
            if field not in config or not config[field]:
                errors.append(f"Missing required field: {field}")
        
        return len(errors) == 0, errors


class LLMProviderFactory:
    """Unified LLM provider factory with fallback and error handling"""
    
    def __init__(self, primary_provider: str = "ollama_local", 
                 fallback_provider: str = "openai",
                 primary_config: Optional[Dict] = None,
                 fallback_config: Optional[Dict] = None):
        """
        Initialize factory with primary and fallback providers.
        
        Args:
            primary_provider: Primary LLM provider
            fallback_provider: Fallback provider if primary unavailable
            primary_config: Primary provider configuration
            fallback_config: Fallback provider configuration
        """
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.primary_config = primary_config or {}
        self.fallback_config = fallback_config or {}
        
        self.current_provider = None
        self.current_config = None
    
    def get_provider(self) -> Optional[ILLMProvider]:
        """
        Get available provider with fallback.
        
        Returns:
            ILLMProvider or None if all unavailable
        """
        # Try primary provider
        try:
            config = self.primary_config or \
                    LLMProviderRegistry.auto_configure(self.primary_provider)
            
            is_valid, errors = LLMProviderRegistry.validate_config(
                self.primary_provider, config
            )
            
            if not is_valid:
                logger.warning(f"Primary provider config invalid: {errors}")
            else:
                provider = LLMProviderRegistry.create(self.primary_provider, config)
                if provider.health_check():
                    self.current_provider = self.primary_provider
                    self.current_config = config
                    logger.info(f"Using primary provider: {self.primary_provider}")
                    return provider
                else:
                    logger.warning(f"Primary provider health check failed: {self.primary_provider}")
        
        except Exception as e:
            logger.warning(f"Primary provider unavailable: {e}")
        
        # Try fallback provider
        if self.fallback_provider:
            try:
                config = self.fallback_config or \
                        LLMProviderRegistry.auto_configure(self.fallback_provider)
                
                provider = LLMProviderRegistry.create(self.fallback_provider, config)
                if provider.health_check():
                    self.current_provider = self.fallback_provider
                    self.current_config = config
                    logger.info(f"Using fallback provider: {self.fallback_provider}")
                    return provider
            
            except Exception as e:
                logger.warning(f"Fallback provider unavailable: {e}")
        
        logger.error("No LLM providers available")
        return None
    
    def explain_anomaly(self, context: Dict) -> Dict:
        """
        Explain anomaly using available provider.
        
        Args:
            context: Anomaly context
        
        Returns:
            Explanation or heuristic response
        """
        provider = self.get_provider()
        
        if provider:
            try:
                return provider.explain_anomaly(context)
            except Exception as e:
                logger.error(f"Provider error: {e}")
        
        # Fallback: return heuristic explanation
        return self._generate_heuristic_explanation(context)
    
    @staticmethod
    def _generate_heuristic_explanation(context: Dict) -> Dict:
        """Generate heuristic explanation when no provider available"""
        anomalies = context.get("anomalies", {})
        
        # Determine severity based on anomaly count and scores
        anomaly_count = len([v for v in anomalies.values() if v.get("is_anomaly")])
        max_score = max([v.get("score", 0) for v in anomalies.values()], default=0)
        
        if anomaly_count > 3 or max_score > 4:
            severity = "High"
        elif anomaly_count > 1 or max_score > 2:
            severity = "Medium"
        else:
            severity = "Low"
        
        causes = []
        if any("rsrp" in k and anomalies[k].get("is_anomaly") for k in anomalies):
            causes.append("Signal strength degradation detected")
        if any("throughput" in k and anomalies[k].get("is_anomaly") for k in anomalies):
            causes.append("Network throughput reduction")
        if any("latency" in k and anomalies[k].get("is_anomaly") for k in anomalies):
            causes.append("Increased network latency")
        
        actions = [
            "Monitor site metrics closely",
            "Check for ongoing maintenance or incidents",
            "Review recent configuration changes",
            "Contact network operations team"
        ]
        
        return {
            "summary": f"Anomaly detected at site {context.get('site_id', 'N/A')}: "
                      f"{anomaly_count} metrics affected",
            "likely_causes": causes or ["Unknown cause - review metrics"],
            "recommended_actions": actions,
            "severity": severity,
            "confidence": 0.5 + (min(anomaly_count, 3) * 0.15)  # 0.5-0.95
        }


# ============================================================================
# PROVIDER CONFIGURATION UTILITIES
# ============================================================================

class ProviderConfigBuilder:
    """Builder for provider configurations"""
    
    def __init__(self, provider_type: str):
        self.provider_type = provider_type
        self.config = {}
    
    def with_env_vars(self) -> "ProviderConfigBuilder":
        """Load configuration from environment variables"""
        template = LLMProviderRegistry.PROVIDER_TEMPLATES.get(self.provider_type, {})
        env_vars = template.get("env_vars", {})
        
        for key, env_var in env_vars.items():
            value = os.getenv(env_var)
            if value:
                self.config[key] = value
        
        return self
    
    def with_defaults(self) -> "ProviderConfigBuilder":
        """Load default configuration"""
        template = LLMProviderRegistry.PROVIDER_TEMPLATES.get(self.provider_type, {})
        defaults = template.get("default_config", {})
        
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value
        
        return self
    
    def with_custom(self, **kwargs) -> "ProviderConfigBuilder":
        """Add custom configuration"""
        self.config.update(kwargs)
        return self
    
    def build(self) -> Dict:
        """Build final configuration"""
        return self.config


# Example usage in documentation:
"""
# Using registry
registry = LLMProviderRegistry()
provider = registry.create("ollama_local", {
    "base_url": "http://localhost:11434",
    "model": "llama2"
})

# Using factory with fallback
factory = LLMProviderFactory(
    primary_provider="ollama_local",
    fallback_provider="openai",
    primary_config={"base_url": "http://localhost:11434", "model": "llama2"},
    fallback_config={"api_key": os.getenv("OPENAI_API_KEY")}
)
explanation = factory.explain_anomaly(context)

# Using builder pattern
config = ProviderConfigBuilder("openai") \
    .with_env_vars() \
    .with_defaults() \
    .build()
"""
