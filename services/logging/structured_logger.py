"""
Centralized Structured Logging Module.
Provides structured JSON logging with multiple backends (file, ELK, cloud).
All logs include: timestamp, trace_id, module, level, and custom fields.
"""
import json
import logging
import logging.handlers
import time
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
import uuid
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogContext:
    """Structured log context"""
    timestamp: str
    trace_id: str
    module: str
    level: str
    message: str
    site_id: Optional[str] = None
    metric: Optional[str] = None
    action: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, removing None values"""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


class StructuredLogger:
    """Centralized structured logging with traceability"""
    
    def __init__(
        self,
        name: str,
        log_dir: str = "logs",
        log_file: str = "app.log",
        enable_file: bool = True,
        enable_console: bool = True
    ):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_file = log_file
        self.enable_file = enable_file
        self.enable_console = enable_console
        
        # Ensure log directory exists
        if self.enable_file:
            self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # JSON formatter
        formatter = logging.Formatter(
            '%(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        
        # File handler (JSON lines format)
        if self.enable_file:
            file_handler = logging.FileHandler(
                self.log_dir / self.log_file,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    @staticmethod
    def generate_trace_id() -> str:
        """Generate unique trace ID for request tracing"""
        return str(uuid.uuid4())[:8]
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        module: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log structured event"""
        trace_id = trace_id or self.generate_trace_id()
        
        log_context = LogContext(
            timestamp=datetime.utcnow().isoformat() + "Z",
            trace_id=trace_id,
            module=module,
            level=level.value,
            message=message,
            **kwargs
        )
        
        # Log as JSON
        log_dict = log_context.to_dict()
        self.logger.log(
            getattr(logging, level.value),
            json.dumps(log_dict)
        )
    
    def debug(
        self,
        message: str,
        module: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, module, trace_id, **kwargs)
    
    def info(
        self,
        message: str,
        module: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log info message"""
        self._log(LogLevel.INFO, message, module, trace_id, **kwargs)
    
    def warning(
        self,
        message: str,
        module: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log warning message"""
        self._log(LogLevel.WARNING, message, module, trace_id, **kwargs)
    
    def error(
        self,
        message: str,
        module: str,
        trace_id: Optional[str] = None,
        error: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log error message"""
        self._log(LogLevel.ERROR, message, module, trace_id, error=error, **kwargs)
    
    def critical(
        self,
        message: str,
        module: str,
        trace_id: Optional[str] = None,
        error: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, module, trace_id, error=error, **kwargs)


class PerformanceTimer:
    """Context manager for measuring operation latency"""
    
    def __init__(self, logger: StructuredLogger, operation_name: str, module: str, trace_id: Optional[str] = None):
        self.logger = logger
        self.operation_name = operation_name
        self.module = module
        self.trace_id = trace_id or StructuredLogger.generate_trace_id()
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        latency_ms = (time.time() - self.start_time) * 1000
        
        if exc_type:
            self.logger.error(
                f"Operation {self.operation_name} failed",
                module=self.module,
                trace_id=self.trace_id,
                latency_ms=latency_ms,
                error=str(exc_val)
            )
        else:
            self.logger.info(
                f"Operation {self.operation_name} completed",
                module=self.module,
                trace_id=self.trace_id,
                latency_ms=latency_ms,
                action=self.operation_name
            )


# Global logger instance
_global_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "network_incident_investigator") -> StructuredLogger:
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(name)
    return _global_logger


def initialize_logger(
    name: str = "network_incident_investigator",
    log_dir: str = "logs",
    log_file: str = "app.log",
    enable_file: bool = True,
    enable_console: bool = True
) -> StructuredLogger:
    """Initialize global logger with custom settings"""
    global _global_logger
    _global_logger = StructuredLogger(
        name,
        log_dir=log_dir,
        log_file=log_file,
        enable_file=enable_file,
        enable_console=enable_console
    )
    return _global_logger
