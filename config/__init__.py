"""
Core configuration and initialization module.
Centralizes settings for all components.
"""
from dataclasses import dataclass
from typing import Optional, Dict
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class AppConfig:
    """Application configuration"""
    
    # App settings
    APP_NAME: str = "Network Incident Investigator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server settings
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    BACKEND_WORKERS: int = int(os.getenv("BACKEND_WORKERS", "4"))
    
    # Data settings
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    EXPORTS_DIR: str = os.getenv("EXPORTS_DIR", "./exports")
    
    # Anomaly detection defaults
    DEFAULT_DETECTION_METHOD: str = os.getenv("DEFAULT_DETECTION_METHOD", "zscore")
    DEFAULT_ANOMALY_THRESHOLD: float = float(os.getenv("DEFAULT_ANOMALY_THRESHOLD", "3.0"))
    DEFAULT_WINDOW_SIZE: int = int(os.getenv("DEFAULT_WINDOW_SIZE", "30"))
    
    # GenAI settings
    GENAI_PROVIDER: str = os.getenv("GENAI_PROVIDER", "ollama_local")
    GENAI_TEMPERATURE: float = float(os.getenv("GENAI_TEMPERATURE", "0.7"))
    GENAI_MAX_TOKENS: int = int(os.getenv("GENAI_MAX_TOKENS", "1000"))
    
    # Ollama settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")
    
    # OpenAI settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # Vertex AI settings
    VERTEX_PROJECT_ID: str = os.getenv("VERTEX_PROJECT_ID", "")
    VERTEX_LOCATION: str = os.getenv("VERTEX_LOCATION", "us-central1")
    
    # Azure OpenAI settings
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_KEY: str = os.getenv("AZURE_OPENAI_KEY", "")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def get_config() -> AppConfig:
    """Get application configuration"""
    return AppConfig()


def validate_config(config: AppConfig) -> tuple[bool, list[str]]:
    """
    Validate configuration.
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check genai provider configuration
    if config.GENAI_PROVIDER == "ollama_local":
        if not config.OLLAMA_BASE_URL:
            errors.append("Ollama Base URL not configured")
    
    elif config.GENAI_PROVIDER == "openai":
        if not config.OPENAI_API_KEY:
            errors.append("OpenAI API key not configured")
    
    elif config.GENAI_PROVIDER == "vertex_ai":
        if not config.VERTEX_PROJECT_ID:
            errors.append("Vertex AI project ID not configured")
    
    elif config.GENAI_PROVIDER == "azure_openai":
        if not all([config.AZURE_OPENAI_ENDPOINT, config.AZURE_OPENAI_KEY]):
            errors.append("Azure OpenAI credentials not fully configured")
    
    return len(errors) == 0, errors


if __name__ == "__main__":
    config = get_config()
    is_valid, errors = validate_config(config)
    
    print(f"Configuration Valid: {is_valid}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    
    print("\nConfiguration Summary:")
    print(f"  Provider: {config.GENAI_PROVIDER}")
    print(f"  Detection Method: {config.DEFAULT_DETECTION_METHOD}")
    print(f"  Threshold: {config.DEFAULT_ANOMALY_THRESHOLD}")
