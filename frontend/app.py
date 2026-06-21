"""
Streamlit UI for Network Incident Investigator.
Linear 5-section workflow for data analysis and GenAI-powered root cause investigation.
"""
import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import logging

# Set page config
st.set_page_config(
    page_title="🔍 Network Incident Investigator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.anomaly_detection.kpi_detector import (
    NetworkKPIAnomalyDetectionService,
    detect_anomalies
)
from services.genai_reasoning.llm_client import LLMClient
from services.genai_reasoning.context_builder import build_anomaly_context
from data.cell_site_kpi_generator import generate_synthetic_kpi_data
from backend.data_loader import load_data_from_csv


# ============================================================================
# PAGE TITLE & DESCRIPTION
# ============================================================================

st.title("🔍 Network Incident Investigator")
st.markdown(
    "GenAI-powered anomaly detection and root cause analysis for network KPI metrics"
)

st.markdown("---")

st.markdown("---")


# ============================================================================
# SECTION 1: DATA SOURCE
# ============================================================================

st.header("📊 Section 1: Data Source")

col1, col2 = st.columns([2, 3])

with col1:
    data_source = st.radio(
        "Select data input mode:",
        options=["Upload CSV", "Use Backend Sample Data"],
        horizontal=False,
        help="Choose between uploading your own CSV or using a backend sample dataset"
    )

df = None

with col2:
    if data_source == "Upload CSV":
        st.subheader("CSV Upload")
        uploaded_file = st.file_uploader(
            "Choose a CSV file with network metrics",
            type="csv",
            help="CSV should have columns: timestamp, site_id, rsrp, rsrq, sinr, throughput_mbps, latency_ms, dropped_call_rate"
        )
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.session_state.df = df
                st.success(f"✅ Loaded {len(df)} rows")
            except Exception as e:
                st.error(f"❌ Error loading file: {e}")
    
    else:  # Backend Sample Data
        st.subheader("Backend Sample Datasets")
        sample_option = st.selectbox(
            "Select dataset:",
            options=[
                "3 Sites × 24 Hours",
                "5 Sites × 48 Hours",
                "10 Sites × 72 Hours",
                "Custom"
            ]
        )
        
        if sample_option == "Custom":
            num_sites = st.slider("Number of sites", 1, 10, 3)
            num_hours = st.slider("Number of hours", 1, 72, 24)
        else:
            config = {
                "3 Sites × 24 Hours": (3, 24),
                "5 Sites × 48 Hours": (5, 48),
                "10 Sites × 72 Hours": (10, 72),
            }
            num_sites, num_hours = config.get(sample_option, (3, 24))
        
        if st.button("📥 Load Sample Data", key="load_sample"):
            with st.spinner(f"Generating {num_sites} sites × {num_hours} hours..."):
                try:
                    df = generate_synthetic_kpi_data(
                        num_sites=num_sites,
                        num_hours=num_hours,
                        save_files=False
                    )
                    st.session_state.df = df
                    st.success(f"✅ Generated {len(df)} rows")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# Load from session state if available
if df is None and "df" in st.session_state:
    df = st.session_state.df

# Display data preview if loaded
if df is not None:
    with st.expander("📋 Data Preview", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", len(df))
        with col2:
            st.metric("Total Columns", len(df.columns))
        with col3:
            if "site_id" in df.columns:
                st.metric("Unique Sites", df["site_id"].nunique())
        
        st.dataframe(df.head(10), use_container_width=True)

st.markdown("---")


# ============================================================================
# SECTION 2: CONFIGURATION
# ============================================================================

st.header("⚙️ Section 2: Configuration")

if df is not None:
    col1, col2, col3 = st.columns(3)
    
    # Identify numeric columns for metrics
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    exclude_cols = ["timestamp"]
    metric_cols = [col for col in numeric_cols if col not in exclude_cols]
    
    with col1:
        st.subheader("Metrics")
        selected_metrics = st.multiselect(
            "Select metrics to analyze:",
            options=metric_cols,
            default=metric_cols[:3] if len(metric_cols) >= 3 else metric_cols,
            help="Choose which KPI metrics to include in anomaly detection"
        )
    
    with col2:
        st.subheader("Detection Settings")
        detection_method = st.selectbox(
            "Detection Method:",
            options=["zscore", "mad", "isolation_forest", "stl"],
            help="Algorithm for anomaly detection"
        )
        
        anomaly_threshold = st.slider(
            "Threshold:",
            min_value=1.0,
            max_value=5.0,
            value=3.0,
            step=0.5,
            help="Higher = stricter (fewer anomalies detected)"
        )
    
    with col3:
        st.subheader("GenAI Provider")
        provider = st.selectbox(
            "LLM Provider:",
            options=["ollama_local", "openai", "vertex_ai", "azure_openai"],
            help="Provider for root cause analysis"
        )
        
        genai_config = {}
        
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
    st.warning("⚠️ Please load data first in Section 1")

st.markdown("---")


# ============================================================================
# SECTION 3: RUN DETECTION
# ============================================================================

st.header("🚀 Section 3: Run Anomaly Detection")

if df is not None and selected_metrics:
    
    if st.button("🔍 Run Detection", key="run_detection", use_container_width=True):
        with st.spinner("Running anomaly detection..."):
            try:
                # Run anomaly detection
                result_df = detect_anomalies(
                    df=df,
                    metrics=selected_metrics,
                    method=detection_method,
                    config={"threshold": anomaly_threshold}
                )
                
                st.session_state.result_df = result_df
                st.session_state.selected_metrics = selected_metrics
                st.success("✅ Anomaly detection completed")
                
            except Exception as e:
                st.error(f"❌ Error: {e}")
                logger.exception("Anomaly detection error")
    
    # Display detection results
    if "result_df" in st.session_state:
        result_df = st.session_state.result_df
        
        # Summary metrics
        st.subheader("📊 Detection Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Count anomalies
        is_anomaly_col = "is_anomaly" if "is_anomaly" in result_df.columns else None
        anomaly_count = result_df["is_anomaly"].sum() if is_anomaly_col else 0
        
        with col1:
            st.metric("Total Anomalies", int(anomaly_count))
        
        with col2:
            anomaly_rate = (anomaly_count / len(result_df) * 100) if len(result_df) > 0 else 0
            st.metric("Anomaly Rate", f"{anomaly_rate:.1f}%")
        
        with col3:
            st.metric("Detection Method", detection_method.upper())
        
        with col4:
            st.metric("Rows Analyzed", len(result_df))
        
        # KPI Plots with Anomalies
        st.subheader("📈 KPI Plots with Anomalies Highlighted")
        
        if "timestamp" in result_df.columns and "site_id" in result_df.columns:
            # Get unique sites
            unique_sites = result_df["site_id"].unique()
            
            # Create plots for each metric
            for metric in selected_metrics:
                if metric in result_df.columns:
                    fig = go.Figure()
                    
                    # Plot for each site
                    for site in unique_sites:
                        site_data = result_df[result_df["site_id"] == site].copy()
                        
                        # Normal points
                        normal_mask = ~site_data["is_anomaly"] if "is_anomaly" in site_data.columns else [True] * len(site_data)
                        fig.add_trace(go.Scatter(
                            x=site_data[normal_mask]["timestamp"],
                            y=site_data[normal_mask][metric],
                            mode="lines+markers",
                            name=f"Site {site} (Normal)",
                            line=dict(width=2)
                        ))
                        
                        # Anomaly points
                        if "is_anomaly" in site_data.columns:
                            anomaly_mask = site_data["is_anomaly"]
                            if anomaly_mask.any():
                                fig.add_trace(go.Scatter(
                                    x=site_data[anomaly_mask]["timestamp"],
                                    y=site_data[anomaly_mask][metric],
                                    mode="markers",
                                    name=f"Site {site} (Anomaly)",
                                    marker=dict(size=10, color="red", symbol="x")
                                ))
                    
                    fig.update_layout(
                        title=f"{metric.upper()} Over Time",
                        xaxis_title="Timestamp",
                        yaxis_title=metric,
                        hovermode="x unified",
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
        
        # Anomalies table
        st.subheader("📋 Anomalous Events Table")
        
        if "is_anomaly" in result_df.columns:
            anomaly_rows = result_df[result_df["is_anomaly"]].copy()
            
            if len(anomaly_rows) > 0:
                # Select columns to display
                display_cols = ["timestamp", "site_id"] + selected_metrics + [
                    col for col in result_df.columns if "is_anomaly" in col or "anomaly_score" in col
                ]
                display_cols = [col for col in display_cols if col in result_df.columns]
                
                st.dataframe(
                    anomaly_rows[display_cols].head(50),
                    use_container_width=True
                )
                
                # Download anomalies
                csv = anomaly_rows.to_csv(index=False)
                st.download_button(
                    "📥 Download Anomalies CSV",
                    csv,
                    file_name=f"anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("✅ No anomalies detected")
        else:
            st.info("Run detection to see anomalies")

else:
    st.warning("⚠️ Please load data and select metrics in Sections 1-2")

st.markdown("---")


# ============================================================================
# SECTION 4: GENAI EXPLANATION
# ============================================================================

st.header("🧠 Section 4: GenAI Explanation")

if "result_df" in st.session_state:
    result_df = st.session_state.result_df
    selected_metrics = st.session_state.get("selected_metrics", [])
    
    # Filter anomalies
    anomalies = result_df[result_df["is_anomaly"]] if "is_anomaly" in result_df.columns else pd.DataFrame()
    
    if len(anomalies) == 0:
        st.info("ℹ️ No anomalies detected. Run detection first in Section 3.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Select anomaly to explain
            anomaly_idx = st.selectbox(
                "Select an anomaly to explain:",
                options=range(len(anomalies)),
                format_func=lambda i: f"Row {i}: {anomalies.iloc[i].get('timestamp', 'N/A')} @ Site {anomalies.iloc[i].get('site_id', 'N/A')}"
            )
            
            selected_anomaly = anomalies.iloc[anomaly_idx]
        
        with col2:
            explain_button = st.button("🔍 Analyze with GenAI", key="analyze_genai", use_container_width=True)
        
        if explain_button:
            with st.spinner("Generating GenAI analysis..."):
                try:
                    # Initialize LLM client
                    client = LLMClient(provider=provider, config=genai_config)
                    
                    # Build context
                    context = build_anomaly_context(
                        df=result_df,
                        anomaly_row=selected_anomaly,
                        metric_columns=selected_metrics
                    )
                    
                    # Get LLM explanation
                    explanation = client.explain_anomaly(context)
                    
                    st.session_state.explanation = explanation
                    st.success("✅ Analysis complete")
                    
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    logger.exception("GenAI analysis error")
        
        # Display explanation
        if "explanation" in st.session_state:
            explanation = st.session_state.explanation
            
            # Anomaly details
            st.subheader("📍 Anomaly Details")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Site ID", selected_anomaly.get("site_id", "N/A"))
            
            with col2:
                st.write(f"**Timestamp:** {selected_anomaly.get('timestamp', 'N/A')}")
            
            with col3:
                severity = explanation.get("severity", "Unknown")
                severity_emoji = {
                    "Low": "🟢", "Medium": "🟡",
                    "High": "🔴", "Critical": "⛔"
                }.get(severity, "❓")
                st.metric("Severity", f"{severity_emoji} {severity}")
            
            with col4:
                confidence = explanation.get("confidence", 0)
                st.metric("Confidence", f"{confidence:.0%}")
            
            st.divider()
            
            # Summary
            st.subheader("📋 Summary")
            st.write(explanation.get("summary", "No summary available"))
            
            # Likely causes
            st.subheader("🎯 Likely Causes (Ranked)")
            causes = explanation.get("likely_causes", [])
            if causes:
                for i, cause in enumerate(causes, 1):
                    st.write(f"**{i}.** {cause}")
            else:
                st.write("No causes identified")
            
            # Recommended actions
            st.subheader("✅ Recommended Actions")
            actions = explanation.get("recommended_actions", [])
            if actions:
                for i, action in enumerate(actions, 1):
                    st.write(f"**{i}.** {action}")
            else:
                st.write("No actions recommended")
            
            # Raw context
            with st.expander("📊 Raw Analysis Context", expanded=False):
                st.json(context)

else:
    st.info("ℹ️ Run anomaly detection in Section 3 first")

st.markdown("---")


# ============================================================================
# SECTION 5: EXECUTIVE SUMMARY
# ============================================================================

st.header("📈 Section 5: Executive Summary")

if "result_df" in st.session_state:
    result_df = st.session_state.result_df
    
    # Key metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_anomalies = result_df["is_anomaly"].sum() if "is_anomaly" in result_df.columns else 0
        st.metric("Total Anomalies Detected", int(total_anomalies))
    
    with col2:
        anomaly_rate = (total_anomalies / len(result_df) * 100) if len(result_df) > 0 else 0
        st.metric("Overall Anomaly Rate", f"{anomaly_rate:.1f}%")
    
    with col3:
        if "site_id" in result_df.columns:
            affected_sites = result_df[result_df["is_anomaly"]]["site_id"].nunique() if total_anomalies > 0 else 0
            st.metric("Affected Sites", int(affected_sites))
    
    st.divider()
    
    # Severity distribution
    if "explanation" in st.session_state and len(st.session_state.explanation) > 0:
        st.subheader("⚠️ Severity Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Count severity levels from explanations (if multiple)
            severity_counts = {
                "🟢 Low": 0,
                "🟡 Medium": 0,
                "🔴 High": 0,
                "⛔ Critical": 0
            }
            
            # For demonstration, show the current explanation
            if "severity" in st.session_state.explanation:
                severity = st.session_state.explanation["severity"]
                st.write(f"Current Anomaly Severity: **{severity}**")
            
            # Show severity breakdown
            st.write("""
            **Severity Levels:**
            - 🟢 **Low**: Minor metric deviation, normal operation
            - 🟡 **Medium**: Notable anomaly, monitor closely
            - 🔴 **High**: Significant issue, investigate
            - ⛔ **Critical**: Service impact, immediate action
            """)
        
        with col2:
            # Anomalies by site
            if "site_id" in result_df.columns and "is_anomaly" in result_df.columns:
                st.subheader("📍 Anomalies by Site")
                
                anomalies_by_site = result_df[result_df["is_anomaly"]].groupby("site_id").size()
                
                if len(anomalies_by_site) > 0:
                    fig_bar = go.Figure(data=[
                        go.Bar(x=anomalies_by_site.index.astype(str), y=anomalies_by_site.values)
                    ])
                    fig_bar.update_layout(
                        title="Anomaly Count by Site",
                        xaxis_title="Site ID",
                        yaxis_title="Anomaly Count",
                        height=300
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.divider()
    
    # Metric impact analysis
    st.subheader("📊 Affected Metrics")
    
    if selected_metrics:
        metric_anomalies = {}
        
        for metric in selected_metrics:
            if f"is_anomaly_{metric}" in result_df.columns:
                count = result_df[f"is_anomaly_{metric}"].sum()
                metric_anomalies[metric] = int(count)
            elif "is_anomaly" in result_df.columns:
                # Fallback: count if metric has extreme values
                count = result_df["is_anomaly"].sum()
                metric_anomalies[metric] = int(count)
        
        # Display metric impact
        metric_data = pd.DataFrame(
            list(metric_anomalies.items()),
            columns=["Metric", "Anomaly Count"]
        ).sort_values("Anomaly Count", ascending=False)
        
        st.dataframe(metric_data, use_container_width=True, hide_index=True)
        
        # Pie chart
        if len(metric_data) > 0 and metric_data["Anomaly Count"].sum() > 0:
            fig_pie = go.Figure(data=[
                go.Pie(labels=metric_data["Metric"], values=metric_data["Anomaly Count"])
            ])
            fig_pie.update_layout(
                title="Anomaly Distribution by Metric",
                height=400
            )
            st.plotly_chart(fig_pie, use_container_width=True)

else:
    st.info("ℹ️ Run anomaly detection to see executive summary")

st.markdown("---")
            if st.button("🔍 Analyze with GenAI", key="analyze_genai"):
                with st.spinner("Generating analysis..."):
                    try:
                        # Initialize LLM client
                        client = LLMClient(provider=provider, config=genai_config)
                        
                        # Build context
                        context = build_anomaly_context(
                            df=result_df,
                            anomaly_row=selected_anomaly,
                            metric_columns=selected_metrics
                        )
                        
                        # Get LLM explanation
                        explanation = client.explain_anomaly(context)
                        
                        st.session_state.explanation = explanation
                        st.success("✅ Analysis complete")
                        
                    except Exception as e:
                        st.error(f"Error: {e}")
                        logger.exception("GenAI analysis error")
            
            # Display explanation
            if "explanation" in st.session_state:
                explanation = st.session_state.explanation
                
                st.subheader("Anomaly Details")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Site ID:** {selected_anomaly.get('site_id', 'N/A')}")
                    st.write(f"**Timestamp:** {selected_anomaly.get('timestamp', 'N/A')}")
                with col2:
                    if "severity" in explanation:
                        severity_color = {
                            "Low": "🟢", "Medium": "🟡",
                            "High": "🔴", "Critical": "⛔"
                        }.get(explanation["severity"], "❓")
                        st.write(f"**Severity:** {severity_color} {explanation['severity']}")
                    if "confidence" in explanation:
                        st.write(f"**Confidence:** {explanation['confidence']:.1%}")
                
                st.divider()
                
                st.subheader("📋 Summary")
                st.write(explanation.get("summary", "N/A"))
                
                st.subheader("🎯 Likely Causes")
                for i, cause in enumerate(explanation.get("likely_causes", []), 1):
                    st.write(f"{i}. {cause}")
                
                st.subheader("✅ Recommended Actions")
                for i, action in enumerate(explanation.get("recommended_actions", []), 1):
                    st.write(f"{i}. {action}")
                
                # Show raw context (expandable)
                with st.expander("📊 Raw Context Data"):
                    st.json(context)

# ============================================================================
# TAB 4: SAMPLE DATA GENERATION
# ============================================================================

with tab4:
    st.header("📈 Generate Sample Data")
    
    st.markdown("""
    Generate synthetic cell site KPI data with injected anomalies.
    Perfect for testing and demonstration.
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        num_sites = st.slider("Number of Sites", 1, 10, 3)
    
    with col2:
        num_hours = st.slider("Number of Hours", 1, 72, 24)
    
    with col3:
        interval_minutes = st.selectbox("Interval (minutes)", [5, 10, 15, 30])
    
    if st.button("📊 Generate Sample Data", key="gen_sample_data"):
        with st.spinner("Generating data..."):
            try:
                df = generate_synthetic_kpi_data(
                    num_sites=num_sites,
                    num_hours=num_hours,
                    interval_minutes=interval_minutes,
                    save_files=False
                )
                
                st.session_state.df = df
                st.success(f"✅ Generated {len(df)} rows")
                
                # Show preview
                st.subheader("Data Preview")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Show statistics
                st.subheader("Metrics Summary")
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                
                # Download
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download Sample Data",
                    csv,
                    file_name=f"sample_data_{num_sites}sites_{num_hours}h.csv",
                    mime="text/csv"
                )
                
            except Exception as e:
# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
### 📊 Network Incident Investigator

**Workflow:**
1. 📊 **Load Data** — Upload CSV or use backend sample data
2. ⚙️ **Configure** — Select metrics, detection method, and GenAI provider
3. 🚀 **Detect** — Run anomaly detection with plots and table
4. 🧠 **Analyze** — Get GenAI explanations for selected anomalies
5. 📈 **Summarize** — View executive summary and severity distribution

**Key Features:**
- 🔧 Reusable anomaly detection service (4 algorithms)
- 🧠 Pluggable GenAI reasoning layer (Ollama, OpenAI, Vertex AI, Azure)
- 📊 CSV upload with real-time analysis
- 📈 Interactive plots and data visualization
- 🎯 Clear backend/frontend separation
- ⚡ Scalable architecture

**Documentation:** See README.md for detailed guidance
""")
