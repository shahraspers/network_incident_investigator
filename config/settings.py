"""
Configuration settings for the Network Incident Investigator system.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class GenAIConfig:
    """GenAI provider configuration"""
    # Ollama configuration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
    
    # OpenAI configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # Vertex AI configuration
    VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID", "")
    VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
    VERTEX_MODEL = os.getenv("VERTEX_MODEL", "text-bison")
    
    # Provider selection
    PROVIDER = os.getenv("GENAI_PROVIDER", "ollama")  # ollama, openai, vertex
    
    # Temperature and token limits
    TEMPERATURE = float(os.getenv("GENAI_TEMPERATURE", "0.7"))
    MAX_TOKENS = int(os.getenv("GENAI_MAX_TOKENS", "1000"))


class AnomalyDetectionConfig:
    """Anomaly detection configuration"""
    ALGORITHM = os.getenv("ANOMALY_ALGORITHM", "isolation_forest")  # isolation_forest, zscore, mad
    CONTAMINATION = float(os.getenv("ANOMALY_CONTAMINATION", "0.1"))
    THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "3.0"))
    WINDOW_SIZE = int(os.getenv("ANOMALY_WINDOW_SIZE", "30"))


class DataConfig:
    """Data generation and storage configuration"""
    # Time series parameters
    NUM_METRICS = int(os.getenv("NUM_METRICS", "5"))
    TIME_STEPS = int(os.getenv("TIME_STEPS", "1000"))
    SAMPLING_INTERVAL = int(os.getenv("SAMPLING_INTERVAL", "60"))  # seconds
    
    # Anomaly injection
    ANOMALY_PROBABILITY = float(os.getenv("ANOMALY_PROBABILITY", "0.05"))
    ANOMALY_MAGNITUDE = float(os.getenv("ANOMALY_MAGNITUDE", "3.0"))
    
    # Data storage
    DATA_DIR = os.getenv("DATA_DIR", "./data")
    CSV_EXPORT_DIR = os.getenv("CSV_EXPORT_DIR", "./exports")


class BackendConfig:
    """Backend API configuration"""
    HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
    PORT = int(os.getenv("BACKEND_PORT", "8000"))
    WORKERS = int(os.getenv("BACKEND_WORKERS", "4"))
    RELOAD = os.getenv("BACKEND_RELOAD", "False").lower() == "true"


class FrontendConfig:
    """Streamlit frontend configuration"""
    PAGE_TITLE = "Network Incident Investigator"
    PAGE_ICON = "🔍"
    LAYOUT = "wide"
    THEME = "light"  # light or dark


class DatabaseConfig:
    """Database configuration (placeholder for future use)"""
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./incidents.db")
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true"


def get_config() -> Config:
    """Get the configuration object"""
    return Config()


def get_genai_config() -> GenAIConfig:
    """Get GenAI configuration"""
    return GenAIConfig()


def get_anomaly_config() -> AnomalyDetectionConfig:
    """Get anomaly detection configuration"""
    return AnomalyDetectionConfig()


def get_data_config() -> DataConfig:
    """Get data configuration"""
    return DataConfig()
