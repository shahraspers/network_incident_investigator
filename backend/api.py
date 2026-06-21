"""
Backend REST API for Network Incident Investigator.
FastAPI-based service with endpoints for data, anomaly detection, and GenAI reasoning.
Includes governance, monitoring, and observability features.
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import pandas as pd
import io
import logging
import uvicorn
from datetime import datetime

# Import services
from services.anomaly_detection.kpi_detector import (
    NetworkKPIAnomalyDetectionService
)
from services.genai_reasoning.llm_client import LLMClient
from services.genai_reasoning.context_builder import build_anomaly_context
from data.cell_site_kpi_generator import generate_synthetic_kpi_data
from backend.data_loader import load_data_from_csv

# Import governance and observability
from services.logging import get_logger, PerformanceTimer
from services.governance import get_access_controller, get_audit_logger, Permission, AuditAction
from services.observability import get_metrics_collector
from services.monitoring import get_health_monitor, get_failover_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize governance and observability
structured_logger = get_logger("nii_api")
access_controller = get_access_controller()
audit_logger = get_audit_logger()
metrics_collector = get_metrics_collector()
health_monitor = get_health_monitor()
failover_manager = get_failover_manager()

# Create FastAPI app
app = FastAPI(
    title="Network Incident Investigator API",
    description="GenAI-powered anomaly detection and root cause analysis",
    version="1.0.0"
)

# ============================================================================
# DATA MODELS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str


class AnomalyDetectionRequest(BaseModel):
    """Anomaly detection request"""
    metrics: List[str] = Field(..., description="List of metric columns to analyze")
    method: str = Field(default="zscore", description="Detection method: zscore, mad, isolation_forest, stl")
    threshold: float = Field(default=3.0, description="Anomaly threshold")
    window_size: int = Field(default=30, description="Window size for trend analysis")


class AnomalyDetectionResponse(BaseModel):
    """Anomaly detection response"""
    success: bool
    anomalies_found: int
    anomaly_rate: float
    detection_method: str
    timestamp: str
    message: str
    trace_id: Optional[str] = None


class AnomalyExplanationRequest(BaseModel):
    """Request for GenAI anomaly explanation"""
    site_id: str = Field(..., description="Site ID")
    metrics: Dict[str, float] = Field(..., description="Metric values")
    anomaly_scores: Optional[Dict[str, float]] = Field(None, description="Anomaly scores")
    provider: str = Field(default="ollama_local", description="LLM provider")


class AnomalyExplanationResponse(BaseModel):
    """GenAI explanation response"""
    success: bool
    summary: str
    likely_causes: List[str]
    recommended_actions: List[str]
    severity: str
    confidence: float
    timestamp: str


class SyntheticDataRequest(BaseModel):
    """Request for synthetic data generation"""
    num_sites: int = Field(default=3, ge=1, le=20, description="Number of sites")
    num_hours: int = Field(default=24, ge=1, le=168, description="Number of hours")
    interval_minutes: int = Field(default=5, description="Sampling interval in minutes")


# ============================================================================
# GLOBAL STATE
# ============================================================================

# Store uploaded/generated data
uploaded_data: Optional[pd.DataFrame] = None
anomaly_results: Optional[pd.DataFrame] = None

# Initialize services
anomaly_service = NetworkKPIAnomalyDetectionService()

# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint - basic"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@app.get("/api/health")
async def detailed_health_check():
    """Comprehensive health check with service status"""
    health = health_monitor.check_all_services()
    metrics_collector.record_request()
    return health


@app.get("/api/health")
async def detailed_health_check():
    """Comprehensive health check with service status"""
    health = health_monitor.check_all_services()
    metrics_collector.record_request()
    return health


@app.get("/api/info")
async def get_info():
    """Get API information"""
    return {
        "name": "Network Incident Investigator API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "data": "/api/data/*",
            "anomaly": "/api/anomaly/*",
            "genai": "/api/genai/*"
        }
    }


# ============================================================================
# DATA ENDPOINTS
# ============================================================================

@app.post("/api/data/upload")
async def upload_csv(
    file: UploadFile = File(...),
    x_user: str = Header(default="anonymous"),
    x_trace_id: Optional[str] = Header(None)
):
    """
    Upload CSV file with network metrics.
    
    Returns: Summary of uploaded data
    """
    trace_id = x_trace_id or "upload_{}".format(datetime.now().timestamp())
    metrics_collector.record_request()
    
    try:
        global uploaded_data
        
        # Read file
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Validate
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="Empty CSV file")
        
        uploaded_data = df
        
        # Log audit event
        audit_logger.log_data_upload(
            actor=x_user,
            file_name=file.filename,
            row_count=len(df)
        )
        
        structured_logger.info(
            f"Uploaded {len(df)} rows from {file.filename}",
            module="api.upload",
            trace_id=trace_id,
            file_name=file.filename,
            row_count=len(df)
        )
        
        return {
            "success": True,
            "filename": file.filename,
            "rows": len(df),
            "columns": list(df.columns),
            "sites": df["site_id"].nunique() if "site_id" in df.columns else 0,
            "timestamp": datetime.now().isoformat(),
            "trace_id": trace_id
        }
    
    except Exception as e:
        structured_logger.error(
            f"Upload error: {e}",
            module="api.upload",
            trace_id=trace_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/data/preview")
async def get_data_preview(limit: int = Query(20, ge=1, le=1000)):
    """Get preview of uploaded data"""
    global uploaded_data
    
    if uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    return {
        "success": True,
        "total_rows": len(uploaded_data),
        "total_columns": len(uploaded_data.columns),
        "columns": list(uploaded_data.columns),
        "data": uploaded_data.head(limit).to_dict(orient="records"),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/data/synthetic")
async def generate_synthetic_data(request: SyntheticDataRequest):
    """
    Generate synthetic cell site data.
    
    Returns: Generated data summary and download URL
    """
    try:
        global uploaded_data
        
        logger.info(f"Generating {request.num_sites} sites × {request.num_hours}h")
        
        df = generate_synthetic_kpi_data(
            num_sites=request.num_sites,
            num_hours=request.num_hours,
            interval_minutes=request.interval_minutes,
            save_files=False
        )
        
        uploaded_data = df
        
        return {
            "success": True,
            "rows": len(df),
            "sites": request.num_sites,
            "hours": request.num_hours,
            "columns": list(df.columns),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Data generation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ANOMALY DETECTION ENDPOINTS
# ============================================================================

@app.post("/api/anomaly/detect", response_model=AnomalyDetectionResponse)
async def detect_anomalies(
    request: AnomalyDetectionRequest,
    x_user: str = Header(default="anonymous"),
    x_trace_id: Optional[str] = Header(None)
):
    """
    Detect anomalies in uploaded data.
    
    Returns: Detection summary and results
    """
    global uploaded_data, anomaly_results
    trace_id = x_trace_id or "detect_{}".format(datetime.now().timestamp())
    metrics_collector.record_request()
    
    if uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    try:
        with PerformanceTimer(structured_logger, "anomaly_detection", "api.detect", trace_id) as timer:
            # Run detection
            result_df = anomaly_service.detect_anomalies(
                df=uploaded_data,
                metrics=request.metrics,
                method=request.method,
                config={"threshold": request.threshold, "window_size": request.window_size}
            )
        
        anomaly_results = result_df
        
        # Calculate statistics
        if "is_anomaly" in result_df.columns:
            anomalies_found = int(result_df["is_anomaly"].sum())
            anomaly_rate = float(anomalies_found / len(result_df) * 100)
        else:
            anomalies_found = 0
            anomaly_rate = 0.0
        
        # Record metrics
        metrics_collector.record_anomalies(anomalies_found)
        
        # Log audit event
        audit_logger.log_detection_run(
            actor=x_user,
            site_id="all",
            metrics_count=len(request.metrics),
            anomalies_detected=anomalies_found
        )
        
        return AnomalyDetectionResponse(
            success=True,
            anomalies_found=anomalies_found,
            anomaly_rate=anomaly_rate,
            detection_method=request.method,
            timestamp=datetime.now().isoformat(),
            message=f"Detected {anomalies_found} anomalies ({anomaly_rate:.1f}%)",
            trace_id=trace_id
        )
    
    except Exception as e:
        metrics_collector.record_error("api.detect", "DetectionError", str(e))
        structured_logger.error(
            f"Detection error: {e}",
            module="api.detect",
            trace_id=trace_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/anomaly/results")
async def get_anomaly_results(limit: int = Query(100, ge=1, le=10000)):
    """Get anomaly detection results"""
    global anomaly_results
    
    if anomaly_results is None:
        raise HTTPException(status_code=400, detail="No detection results available")
    
    try:
        anomalies = anomaly_results[anomaly_results["is_anomaly"]] if "is_anomaly" in anomaly_results.columns else anomaly_results
        
        return {
            "success": True,
            "total_anomalies": len(anomalies),
            "anomalies": anomalies.head(limit).to_dict(orient="records"),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Results retrieval error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# GENAI REASONING ENDPOINTS
# ============================================================================

@app.post("/api/genai/explain", response_model=AnomalyExplanationResponse)
async def explain_anomaly(request: AnomalyExplanationRequest):
    """
    Generate GenAI explanation for anomaly.
    
    Returns: Analysis with causes and recommendations
    """
    try:
        logger.info(f"Generating explanation for {request.site_id}")
        
        # Initialize LLM client
        genai_config = {}
        if request.provider == "ollama_local":
            genai_config = {
                "base_url": "http://localhost:11434",
                "model": "llama2"
            }
        elif request.provider == "openai":
            genai_config = {
                "api_key": "",  # Should come from config
                "model": "gpt-3.5-turbo"
            }
        
        client = LLMClient(provider=request.provider, config=genai_config)
        
        # Build context
        context = {
            "site_id": request.site_id,
            "timestamp": datetime.now().isoformat(),
            "anomalies": {
                metric: {
                    "is_anomaly": True,
                    "value": value,
                    "score": request.anomaly_scores.get(metric, 0.0) if request.anomaly_scores else 0.0
                }
                for metric, value in request.metrics.items()
            },
            "metrics": {
                metric: {
                    "value": value,
                    "min": 0,
                    "max": 100,
                    "avg": 50
                }
                for metric, value in request.metrics.items()
            }
        }
        
        # Get explanation
        explanation = client.explain_anomaly(context)
        
        return AnomalyExplanationResponse(
            success=True,
            summary=explanation.get("summary", "Analysis complete"),
            likely_causes=explanation.get("likely_causes", []),
            recommended_actions=explanation.get("recommended_actions", []),
            severity=explanation.get("severity", "Medium"),
            confidence=explanation.get("confidence", 0.7),
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"GenAI error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/genai/providers")
async def get_providers():
    """Get list of supported GenAI providers"""
    provider_status = failover_manager.get_provider_status()
    return {
        "providers": [
            "ollama_local",
            "openai",
            "vertex_ai",
            "azure_openai"
        ],
        "provider_status": provider_status,
        "default": "ollama_local"
    }


# ============================================================================
# OBSERVABILITY ENDPOINTS
# ============================================================================

@app.get("/api/metrics")
async def get_platform_metrics():
    """Get comprehensive platform metrics and performance data"""
    metrics_collector.record_request()
    return metrics_collector.get_platform_metrics()


@app.get("/api/metrics/latency")
async def get_latency_metrics(
    module: Optional[str] = Query(None),
    operation: Optional[str] = Query(None),
    minutes: int = Query(60, ge=1, le=1440)
):
    """Get latency metrics for specific module/operation"""
    return metrics_collector.get_latency_stats(
        module=module,
        operation=operation,
        minutes=minutes
    )


@app.get("/api/metrics/tokens")
async def get_token_metrics(minutes: int = Query(60, ge=1, le=1440)):
    """Get LLM token usage and cost metrics"""
    return metrics_collector.get_token_usage_stats(minutes=minutes)


@app.get("/api/metrics/errors")
async def get_error_metrics(minutes: int = Query(60, ge=1, le=1440)):
    """Get error statistics"""
    return metrics_collector.get_error_stats(minutes=minutes)


# ============================================================================
# GOVERNANCE ENDPOINTS
# ============================================================================

@app.get("/api/governance/users")
async def list_users(x_user: str = Header(default="anonymous")):
    """List all users (admin only)"""
    if not access_controller.check_permission(x_user, Permission.MANAGE_ACCESS):
        audit_logger.log_unauthorized_access(
            actor=x_user,
            resource_type="users",
            resource_id="list"
        )
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return {"users": access_controller.list_users()}


@app.get("/api/governance/audit-logs")
async def get_audit_logs(
    actor: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    x_user: str = Header(default="anonymous")
):
    """Get audit logs (admin only)"""
    if not access_controller.check_permission(x_user, Permission.VIEW_AUDIT_LOGS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return audit_logger.get_audit_trail(actor=actor, action=action, limit=limit)


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/api/metrics")
async def get_metrics_info():
    """Get information about available metrics"""
    metrics_info = {
        "rsrp": {
            "name": "Reference Signal Received Power",
            "unit": "dBm",
            "range": [-140, -50],
            "direction": "higher_is_better"
        },
        "rsrq": {
            "name": "Reference Signal Received Quality",
            "unit": "dB",
            "range": [-20, -5],
            "direction": "higher_is_better"
        },
        "sinr": {
            "name": "Signal-to-Interference Ratio",
            "unit": "dB",
            "range": [-10, 30],
            "direction": "higher_is_better"
        },
        "throughput_mbps": {
            "name": "Data Throughput",
            "unit": "Mbps",
            "range": [0.5, 500],
            "direction": "higher_is_better"
        },
        "latency_ms": {
            "name": "Round-trip Latency",
            "unit": "ms",
            "range": [5, 200],
            "direction": "lower_is_better"
        },
        "dropped_call_rate": {
            "name": "Dropped Call Rate",
            "unit": "%",
            "range": [0, 5],
            "direction": "lower_is_better"
        }
    }
    return metrics_info


@app.get("/api/detection-methods")
async def get_detection_methods():
    """Get available anomaly detection methods"""
    return {
        "methods": [
            {
                "name": "zscore",
                "description": "Z-Score based anomaly detection",
                "best_for": "General purpose, normal distributions"
            },
            {
                "name": "mad",
                "description": "Median Absolute Deviation",
                "best_for": "Robust to outliers"
            },
            {
                "name": "isolation_forest",
                "description": "Isolation Forest algorithm",
                "best_for": "High-dimensional data"
            },
            {
                "name": "stl",
                "description": "Seasonal and Trend decomposition",
                "best_for": "Time-series with seasonality"
            }
        ]
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    logger.info("Network Incident Investigator API starting...")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Network Incident Investigator API shutting down...")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
