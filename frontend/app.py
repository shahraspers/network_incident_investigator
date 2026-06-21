"""
Streamlit UI for Network Incident Investigator.
5-section linear workflow: Data -> Config -> Detection -> Analysis -> Summary
Frontend is independent via REST API - can be replaced with React/Vue/Mobile.

This UI consumes REST API endpoints from the FastAPI backend (port 8000).
All data operations go through HTTP API, enabling:
- Governance & audit logging
- Metrics collection & observability
- Multi-user access control
- Provider-agnostic architecture
"""
import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import logging
import requests
import uuid

# Set page config
st.set_page_config(
    page_title="Network Incident Investigator",
    page_icon="magnifying_glass",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# API CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"
API_TIMEOUT = 60  # seconds

# Generate trace ID for request tracking
def get_trace_id():
    """Generate unique trace ID for request correlation"""
    if "trace_id" not in st.session_state:
        st.session_state.trace_id = f"ui_{uuid.uuid4().hex[:12]}"
    return st.session_state.trace_id

# Get current user (can be enhanced with authentication)
def get_current_user():
    """Get current user for audit logging"""
    return st.session_state.get("user_email", "anonymous")


# ============================================================================
# PAGE TITLE & SIDEBAR
# ============================================================================

st.title("Network Incident Investigator")
st.markdown("GenAI-powered anomaly detection and root cause analysis for network KPI metrics")

# Sidebar: API Status & Configuration
with st.sidebar:
    st.header("Configuration")
    
    # API Status Check
    try:
        health = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
        if health.status_code == 200:
            st.success("✅ API Connected (port 8000)")
        else:
            st.error("❌ API Error")
    except Exception as e:
        st.error(f"❌ API Offline: {str(e)[:50]}")
    
    # User email for audit logging
    st.text_input(
        "User Email (for audit logging):",
        value=st.session_state.get("user_email", "analyst@example.com"),
        key="user_email"
    )
    
    # Trace ID
    st.text(f"Trace ID: {get_trace_id()[:16]}...")

st.markdown("---")


# ============================================================================
# SECTION 1: DATA SOURCE
# ============================================================================

st.header("Section 1: Data Source")

col1, col2 = st.columns([2, 3])

with col1:
    data_source = st.radio(
        "Select data input mode:",
        options=["Upload CSV", "Use Backend Sample Data"],
        horizontal=False
    )

df = None

with col2:
    if data_source == "Upload CSV":
        st.subheader("CSV Upload")
        uploaded_file = st.file_uploader(
            "Choose a CSV file with network metrics",
            type="csv"
        )
        
        if uploaded_file:
            try:
                # Upload via REST API
                trace_id = get_trace_id()
                files = {"file": (uploaded_file.name, uploaded_file)}
                headers = {
                    "X-User": get_current_user(),
                    "X-Trace-ID": trace_id
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/api/data/upload",
                    files=files,
                    headers=headers,
                    timeout=API_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.df = None  # Clear local cache
                    st.session_state.api_data_loaded = True
                    st.success(f"✅ Uploaded {result['rows']} rows via API")
                    st.info(f"Trace ID: {trace_id}")
                else:
                    st.error(f"Upload failed: {response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    else:  # Backend Sample Data
        st.subheader("Backend Sample Datasets")
        sample_option = st.selectbox(
            "Select dataset:",
            options=[
                "3 Sites - 24 Hours",
                "5 Sites - 48 Hours",
                "10 Sites - 72 Hours",
                "Custom"
            ]
        )
        
        if sample_option == "Custom":
            num_sites = st.slider("Number of sites", 1, 10, 3)
            num_hours = st.slider("Number of hours", 1, 72, 24)
        else:
            config = {
                "3 Sites - 24 Hours": (3, 24),
                "5 Sites - 48 Hours": (5, 48),
                "10 Sites - 72 Hours": (10, 72),
            }
            num_sites, num_hours = config.get(sample_option, (3, 24))
        
        if st.button("Load Sample Data", key="load_sample"):
            with st.spinner(f"Generating {num_sites} sites x {num_hours} hours..."):
                try:
                    trace_id = get_trace_id()
                    headers = {
                        "X-User": get_current_user(),
                        "X-Trace-ID": trace_id
                    }
                    
                    # Call API to generate synthetic data
                    response = requests.post(
                        f"{API_BASE_URL}/api/data/synthetic",
                        json={
                            "num_sites": num_sites,
                            "num_hours": num_hours,
                            "interval_minutes": 5
                        },
                        headers=headers,
                        timeout=API_TIMEOUT
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.api_data_loaded = True
                        st.session_state.data_summary = result
                        st.success(f"✅ Generated {result['rows']} rows")
                        st.info(f"Trace ID: {trace_id}")
                    else:
                        st.error(f"Generation failed: {response.json().get('detail', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Display data loaded indicator
if st.session_state.get("api_data_loaded"):
    st.success("✅ Data loaded via API")
    if "data_summary" in st.session_state:
        summary = st.session_state.data_summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", summary.get("rows", "?"))
        with col2:
            st.metric("Sites", summary.get("sites", "?"))
        with col3:
            st.metric("Hours", summary.get("hours", "?"))

st.markdown("---")


# ============================================================================
# SECTION 2: CONFIGURATION
# ============================================================================

st.header("Section 2: Configuration")

selected_metrics = []
detection_method = "zscore"
anomaly_threshold = 3.0
provider = "ollama_local"
genai_config = {}

if st.session_state.get("api_data_loaded"):
    # Fetch available metrics from API
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/data/preview",
            params={"limit": 1},
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            preview = response.json()
            available_columns = preview.get("columns", [])
            metric_cols = [col for col in available_columns if col not in ["timestamp", "site_id"]]
        else:
            metric_cols = ["rsrp", "rsrq", "sinr", "throughput_mbps", "latency_ms", "dropped_call_rate"]
    except:
        metric_cols = ["rsrp", "rsrq", "sinr", "throughput_mbps", "latency_ms", "dropped_call_rate"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Metrics")
        selected_metrics = st.multiselect(
            "Select metrics to analyze:",
            options=metric_cols,
            default=metric_cols[:3] if len(metric_cols) >= 3 else metric_cols
        )
    
    with col2:
        st.subheader("Detection Settings")
        detection_method = st.selectbox(
            "Detection Method:",
            options=["zscore", "mad", "isolation_forest", "stl"],
            help="zscore: general purpose, mad: robust to outliers, isolation_forest: high-dimensional, stl: time-series"
        )
        
        anomaly_threshold = st.slider(
            "Threshold:",
            min_value=1.0,
            max_value=5.0,
            value=3.0,
            step=0.5,
            help="Higher = more conservative (fewer anomalies)"
        )
    
    with col3:
        st.subheader("GenAI Provider")
        provider = st.selectbox(
            "LLM Provider:",
            options=["ollama_local", "openai", "vertex_ai", "azure_openai"]
        )
        
        if provider == "ollama_local":
            genai_config = {
                "base_url": st.text_input("Ollama URL", "http://localhost:11434"),
                "model": st.selectbox("Model", ["llama2", "mistral", "neural-chat"]),
            }
        elif provider == "openai":
            genai_config = {
                "api_key": st.text_input("OpenAI API Key", type="password"),
                "model": st.selectbox("Model", ["gpt-3.5-turbo", "gpt-4"]),
            }
        elif provider == "vertex_ai":
            genai_config = {
                "project_id": st.text_input("GCP Project ID"),
            }
        elif provider == "azure_openai":
            genai_config = {
                "endpoint": st.text_input("Azure Endpoint"),
                "api_key": st.text_input("API Key", type="password"),
                "deployment_id": st.text_input("Deployment ID"),
            }

else:
    st.warning("Please load data first in Section 1")

st.markdown("---")


# ============================================================================
# SECTION 3: RUN DETECTION
# ============================================================================

st.header("Section 3: Run Anomaly Detection")

if st.session_state.get("api_data_loaded") and selected_metrics:
    
    if st.button("Run Detection", key="run_detection", use_container_width=True):
        with st.spinner("Running anomaly detection via API..."):
            try:
                trace_id = get_trace_id()
                headers = {
                    "X-User": get_current_user(),
                    "X-Trace-ID": trace_id
                }
                
                # Call API to run detection
                response = requests.post(
                    f"{API_BASE_URL}/api/anomaly/detect",
                    json={
                        "metrics": selected_metrics,
                        "method": detection_method,
                        "threshold": anomaly_threshold,
                        "window_size": 30
                    },
                    headers=headers,
                    timeout=API_TIMEOUT
                )
                
                if response.status_code == 200:
                    detection_result = response.json()
                    st.session_state.detection_result = detection_result
                    st.session_state.selected_metrics = selected_metrics
                    st.session_state.provider = provider
                    st.session_state.genai_config = genai_config
                    st.session_state.detection_method = detection_method
                    st.success(f"✅ Detection completed")
                    st.info(f"Trace ID: {trace_id}")
                else:
                    st.error(f"Detection failed: {response.json().get('detail', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
                logger.exception("Anomaly detection error")
    
    # Display detection results
    if "detection_result" in st.session_state:
        result = st.session_state.detection_result
        
        st.subheader("Detection Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        anomaly_count = result.get("anomalies_found", 0)
        
        with col1:
            st.metric("Total Anomalies", int(anomaly_count))
        
        with col2:
            anomaly_rate = result.get("anomaly_rate", 0.0)
            st.metric("Anomaly Rate", f"{anomaly_rate:.1f}%")
        
        with col3:
            st.metric("Detection Method", result.get("detection_method", "?").upper())
        
        with col4:
            st.metric("Message", result.get("message", "Detection complete"))
        
        # Fetch detailed anomaly results from API
        st.subheader("Anomalous Events (from API)")
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/anomaly/results",
                params={"limit": 100},
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                api_results = response.json()
                total_anomalies = api_results.get("total_anomalies", 0)
                anomalies = api_results.get("anomalies", [])
                
                if total_anomalies > 0:
                    # Display anomalies table
                    anomaly_df = pd.DataFrame(anomalies)
                    st.dataframe(
                        anomaly_df.head(50),
                        use_container_width=True
                    )
                    
                    # Download button
                    csv = anomaly_df.to_csv(index=False)
                    st.download_button(
                        "Download Anomalies CSV",
                        csv,
                        file_name=f"anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No anomalies detected")
            else:
                st.warning("Could not fetch detailed results from API")
                
        except Exception as e:
            st.warning(f"Could not fetch detailed results: {str(e)}")

else:
    st.warning("Please load data and select metrics in Sections 1-2")

st.markdown("---")


# ============================================================================
# SECTION 4: GENAI EXPLANATION
# ============================================================================

st.header("Section 4: GenAI Explanation")

if "detection_result" in st.session_state:
    
    # Fetch anomalies from API for selection
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/anomaly/results",
            params={"limit": 1000},
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            api_results = response.json()
            anomalies = api_results.get("anomalies", [])
            
            if len(anomalies) == 0:
                st.info("No anomalies detected. Run detection first in Section 3.")
            else:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    anomaly_idx = st.selectbox(
                        "Select an anomaly to explain:",
                        options=range(len(anomalies)),
                        format_func=lambda i: f"Row {i}: {anomalies[i].get('timestamp', 'N/A')} @ Site {anomalies[i].get('site_id', 'N/A')}"
                    )
                    
                    selected_anomaly = anomalies[anomaly_idx]
                
                with col2:
                    explain_button = st.button("Analyze with GenAI", key="analyze_genai", use_container_width=True)
                
                if explain_button:
                    with st.spinner("Generating GenAI analysis via API..."):
                        try:
                            trace_id = get_trace_id()
                            headers = {
                                "X-User": get_current_user(),
                                "X-Trace-ID": trace_id
                            }
                            
                            # Extract metric values from anomaly
                            selected_metrics = st.session_state.get("selected_metrics", [])
                            metrics_dict = {
                                metric: float(selected_anomaly.get(metric, 0))
                                for metric in selected_metrics
                                if metric in selected_anomaly
                            }
                            
                            # Call API to explain anomaly
                            response = requests.post(
                                f"{API_BASE_URL}/api/genai/explain",
                                json={
                                    "site_id": str(selected_anomaly.get("site_id", "unknown")),
                                    "metrics": metrics_dict,
                                    "provider": st.session_state.get("provider", "ollama_local")
                                },
                                headers=headers,
                                timeout=API_TIMEOUT
                            )
                            
                            if response.status_code == 200:
                                explanation = response.json()
                                st.session_state.explanation = explanation
                                st.session_state.selected_anomaly = selected_anomaly
                                st.success("✅ Analysis complete")
                                st.info(f"Trace ID: {trace_id}")
                            else:
                                st.error(f"Analysis failed: {response.json().get('detail', 'Unknown error')}")
                                
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            logger.exception("GenAI analysis error")
                
                # Display explanation
                if "explanation" in st.session_state:
                    explanation = st.session_state.explanation
                    selected_anomaly = st.session_state.get("selected_anomaly", {})
                    
                    st.subheader("Anomaly Details")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Site ID", selected_anomaly.get("site_id", "N/A"))
                    
                    with col2:
                        st.write(f"**Timestamp:** {selected_anomaly.get('timestamp', 'N/A')}")
                    
                    with col3:
                        severity = explanation.get("severity", "Unknown")
                        st.metric("Severity", severity)
                    
                    with col4:
                        confidence = explanation.get("confidence", 0)
                        st.metric("Confidence", f"{confidence:.0%}")
                    
                    st.divider()
                    
                    st.subheader("Summary")
                    st.write(explanation.get("summary", "No summary available"))
                    
                    st.subheader("Likely Causes (Ranked)")
                    causes = explanation.get("likely_causes", [])
                    if causes:
                        for i, cause in enumerate(causes, 1):
                            st.write(f"**{i}.** {cause}")
                    else:
                        st.write("No causes identified")
                    
                    st.subheader("Recommended Actions")
                    actions = explanation.get("recommended_actions", [])
                    if actions:
                        for i, action in enumerate(actions, 1):
                            st.write(f"**{i}.** {action}")
                    else:
                        st.write("No actions recommended")
        else:
            st.error("Could not fetch anomalies from API")
            
    except Exception as e:
        st.error(f"Error fetching anomalies: {str(e)}")

else:
    st.info("Run anomaly detection in Section 3 first")

st.markdown("---")


# ============================================================================
# SECTION 5: EXECUTIVE SUMMARY
# ============================================================================

st.header("Section 5: Executive Summary")

if "detection_result" in st.session_state:
    result = st.session_state.detection_result
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_anomalies = result.get("anomalies_found", 0)
        st.metric("Total Anomalies Detected", int(total_anomalies))
    
    with col2:
        anomaly_rate = result.get("anomaly_rate", 0.0)
        st.metric("Overall Anomaly Rate", f"{anomaly_rate:.1f}%")
    
    with col3:
        if "explanation" in st.session_state:
            severity = st.session_state.explanation.get("severity", "Unknown")
            st.metric("Current Anomaly Severity", severity)
    
    st.divider()
    
    # Severity distribution
    if "explanation" in st.session_state:
        st.subheader("Severity Assessment")
        
        col1, col2 = st.columns(2)
        
        with col1:
            explanation = st.session_state.explanation
            severity = explanation.get("severity", "Unknown")
            confidence = explanation.get("confidence", 0)
            
            st.write(f"**Severity Level:** {severity}")
            st.write(f"**Confidence:** {confidence:.0%}")
            
            st.write("""
            **Severity Scale:**
            - Low: Minor metric deviation
            - Medium: Notable anomaly, monitor
            - High: Significant issue, investigate
            - Critical: Service impact, immediate action
            """)
        
        with col2:
            # Try to fetch anomaly distribution from API
            try:
                response = requests.get(
                    f"{API_BASE_URL}/api/metrics",
                    timeout=API_TIMEOUT
                )
                
                if response.status_code == 200:
                    metrics = response.json()
                    st.metric("Detection Method", result.get("detection_method", "?").upper())
                    st.metric("Anomalies Found", result.get("anomalies_found", 0))
            except:
                pass
    
    st.divider()
    
    st.subheader("Platform Metrics & Governance")
    
    try:
        # Fetch platform metrics from API
        response = requests.get(
            f"{API_BASE_URL}/api/metrics",
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            metrics = response.json()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Requests", metrics.get("total_requests", 0))
            
            with col2:
                st.metric("LLM Calls", metrics.get("total_llm_calls", 0))
            
            with col3:
                st.metric("Total Errors", metrics.get("total_errors", 0))
            
            with col4:
                st.metric("Latency Measurements", metrics.get("total_latency_measurements", 0))
            
            # Token usage
            token_stats = metrics.get("token_usage_stats", {})
            if token_stats:
                st.write(f"**LLM Token Usage:** {token_stats.get('total_tokens', 0)} tokens")
                st.write(f"**Estimated Cost:** ${token_stats.get('total_cost_usd', 0):.4f}")
    except Exception as e:
        st.warning(f"Could not fetch metrics: {str(e)}")

else:
    st.info("Run anomaly detection to see executive summary")


# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
### ✅ Network Incident Investigator - REST API Edition

**Architecture:**
- ✅ Frontend communicates via REST API (not direct Python calls)
- ✅ All operations tracked with governance & audit logs
- ✅ Metrics collected in real-time for observability
- ✅ User actions recorded with trace IDs for debugging
- ✅ Multi-provider support (Ollama, OpenAI, Azure, Vertex AI)

**5-Section Workflow:**
1. **Data Source:** Upload CSV or generate synthetic data via API
2. **Configuration:** Choose metrics, detection method, LLM provider
3. **Detection:** Run anomaly detection with metrics recorded to platform
4. **Explanation:** Get AI-powered root cause analysis (traced)
5. **Summary:** View executive metrics and governance data

**Governance Features (via API):**
- Audit logging: All actions logged to `/api/governance/audit-logs`
- Access control: Role-based permissions via `/api/governance/users`
- Metrics: Real-time observability via `/api/metrics`
- Health: Service status via `/api/health`
- Tracing: Request correlation via X-Trace-ID header

**Scalable & Frontend-Agnostic:**
- FastAPI backend decoupled from UI
- Can replace Streamlit with React, Vue, Mobile, or custom frontend
- Docker & Kubernetes ready
- Multi-instance deployment supported

**Documentation:** See [EXECUTION_ALIGNMENT.md](EXECUTION_ALIGNMENT.md), [GETTING_STARTED.md](GETTING_STARTED.md), [GOVERNANCE_AND_MONITORING.md](GOVERNANCE_AND_MONITORING.md)
""")
