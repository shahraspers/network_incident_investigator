"""
Frontend abstraction layer for Network Incident Investigator.
Enables pluggable frontends: Streamlit, Flask/FastAPI, React, CLI, etc.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json


@dataclass
class DetectionConfig:
    """Configuration for anomaly detection"""
    metrics: List[str]
    method: str  # "zscore", "mad", "isolation_forest", "stl"
    threshold: float = 3.0
    window_size: int = 30


@dataclass
class GenAIConfig:
    """Configuration for GenAI reasoning"""
    provider: str  # "ollama_local", "openai", "vertex_ai", "azure_openai"
    model: str
    params: Dict[str, Any] = None


@dataclass
class DataSource:
    """Data source definition"""
    type: str  # "csv", "backend_api", "streaming", "database"
    config: Dict[str, Any]


class IFrontend(ABC):
    """
    Abstract interface for frontend implementations.
    All frontends (Streamlit, Flask, React, CLI) must implement this.
    """
    
    @abstractmethod
    def upload_data(self) -> Optional[Dict]:
        """
        Upload or load data.
        
        Returns:
            {
                "success": bool,
                "data": DataFrame or None,
                "error": str or None
            }
        """
        pass
    
    @abstractmethod
    def get_detection_config(self) -> DetectionConfig:
        """
        Get anomaly detection configuration from user.
        
        Returns:
            DetectionConfig with selected metrics, method, threshold
        """
        pass
    
    @abstractmethod
    def get_genai_config(self) -> GenAIConfig:
        """
        Get GenAI provider configuration from user.
        
        Returns:
            GenAIConfig with provider selection and settings
        """
        pass
    
    @abstractmethod
    def display_detection_results(self, results: Dict) -> None:
        """
        Display anomaly detection results.
        
        Args:
            results: {
                "anomalies_found": int,
                "anomaly_rate": float,
                "detection_method": str,
                "anomaly_rows": DataFrame,
                "plots": Optional[Dict]  # Platform-specific plot data
            }
        """
        pass
    
    @abstractmethod
    def select_anomaly(self, anomaly_rows: List[Dict]) -> Optional[Dict]:
        """
        Let user select an anomaly to explain.
        
        Args:
            anomaly_rows: List of anomalous records
        
        Returns:
            Selected anomaly row or None
        """
        pass
    
    @abstractmethod
    def display_genai_explanation(self, explanation: Dict) -> None:
        """
        Display GenAI explanation.
        
        Args:
            explanation: {
                "summary": str,
                "likely_causes": list[str],
                "recommended_actions": list[str],
                "severity": str,
                "confidence": float
            }
        """
        pass
    
    @abstractmethod
    def display_executive_summary(self, summary: Dict) -> None:
        """
        Display executive summary.
        
        Args:
            summary: {
                "total_anomalies": int,
                "anomaly_rate": float,
                "affected_sites": int,
                "severity_distribution": Dict,
                "metric_impact": Dict
            }
        """
        pass
    
    @abstractmethod
    def run(self) -> None:
        """Run the frontend application"""
        pass


class FrontendWorkflow:
    """
    Generic workflow orchestrator for any frontend implementation.
    Coordinates: Data → Config → Detection → Explanation → Summary
    """
    
    def __init__(self, frontend: IFrontend, backend_url: str = "http://localhost:8000"):
        """
        Initialize workflow.
        
        Args:
            frontend: IFrontend implementation (Streamlit, Flask, React, CLI, etc.)
            backend_url: Backend API URL
        """
        self.frontend = frontend
        self.backend_url = backend_url
        self.data = None
        self.detection_config = None
        self.genai_config = None
        self.detection_results = None
    
    def step1_load_data(self) -> bool:
        """Step 1: Load data"""
        result = self.frontend.upload_data()
        if result and result.get("success"):
            self.data = result.get("data")
            return True
        return False
    
    def step2_configure(self) -> bool:
        """Step 2: Get configuration"""
        self.detection_config = self.frontend.get_detection_config()
        self.genai_config = self.frontend.get_genai_config()
        return self.detection_config is not None and self.genai_config is not None
    
    def step3_detect(self) -> bool:
        """Step 3: Run anomaly detection"""
        import requests
        
        if self.data is None or self.detection_config is None:
            return False
        
        try:
            # Call backend API
            response = requests.post(
                f"{self.backend_url}/api/anomaly/detect",
                json={
                    "metrics": self.detection_config.metrics,
                    "method": self.detection_config.method,
                    "threshold": self.detection_config.threshold,
                    "window_size": self.detection_config.window_size
                }
            )
            
            if response.status_code == 200:
                self.detection_results = response.json()
                self.frontend.display_detection_results(self.detection_results)
                return True
        except Exception as e:
            print(f"Detection error: {e}")
        
        return False
    
    def step4_explain(self) -> bool:
        """Step 4: Get GenAI explanation"""
        if self.detection_results is None:
            return False
        
        # Let user select anomaly
        anomaly_rows = self.detection_results.get("anomaly_rows", [])
        selected = self.frontend.select_anomaly(anomaly_rows)
        
        if selected:
            import requests
            
            try:
                response = requests.post(
                    f"{self.backend_url}/api/genai/explain",
                    json={
                        "site_id": selected.get("site_id"),
                        "metrics": {k: v for k, v in selected.items() if k not in ["timestamp", "site_id"]},
                        "provider": self.genai_config.provider
                    }
                )
                
                if response.status_code == 200:
                    explanation = response.json()
                    self.frontend.display_genai_explanation(explanation)
                    return True
            except Exception as e:
                print(f"Explanation error: {e}")
        
        return False
    
    def step5_summarize(self) -> bool:
        """Step 5: Display executive summary"""
        if self.detection_results is None:
            return False
        
        summary = {
            "total_anomalies": self.detection_results.get("anomalies_found", 0),
            "anomaly_rate": self.detection_results.get("anomaly_rate", 0),
            "affected_sites": len(set(row.get("site_id") for row in self.detection_results.get("anomaly_rows", []))),
            "severity_distribution": {},
            "metric_impact": {}
        }
        
        self.frontend.display_executive_summary(summary)
        return True
    
    def run_workflow(self) -> bool:
        """Execute complete workflow"""
        steps = [
            ("Loading data", self.step1_load_data),
            ("Configuring", self.step2_configure),
            ("Detecting anomalies", self.step3_detect),
            ("Explaining anomalies", self.step4_explain),
            ("Generating summary", self.step5_summarize),
        ]
        
        for step_name, step_func in steps:
            print(f"\n→ {step_name}...")
            if not step_func():
                print(f"✗ Failed at: {step_name}")
                return False
            print(f"✓ {step_name}")
        
        return True


# ============================================================================
# REFERENCE FRONTEND IMPLEMENTATIONS
# ============================================================================

class StreamlitFrontend(IFrontend):
    """Streamlit frontend implementation (example)"""
    
    def upload_data(self) -> Optional[Dict]:
        """Upload data via Streamlit UI"""
        import streamlit as st
        
        uploaded_file = st.file_uploader("Upload CSV", type="csv")
        if uploaded_file:
            try:
                import pandas as pd
                df = pd.read_csv(uploaded_file)
                return {"success": True, "data": df}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "data": None}
    
    def get_detection_config(self) -> DetectionConfig:
        """Get config from Streamlit UI"""
        import streamlit as st
        
        metrics = st.multiselect("Select metrics", ["rsrp", "throughput_mbps", "latency_ms"])
        method = st.selectbox("Detection method", ["zscore", "mad", "isolation_forest", "stl"])
        threshold = st.slider("Threshold", 1.0, 5.0, 3.0)
        
        return DetectionConfig(metrics=metrics, method=method, threshold=threshold)
    
    def get_genai_config(self) -> GenAIConfig:
        """Get config from Streamlit UI"""
        import streamlit as st
        
        provider = st.selectbox("LLM Provider", ["ollama_local", "openai", "vertex_ai", "azure_openai"])
        
        return GenAIConfig(provider=provider, model="default")
    
    def display_detection_results(self, results: Dict) -> None:
        """Display results in Streamlit"""
        import streamlit as st
        
        st.metric("Anomalies Found", results.get("anomalies_found", 0))
        st.metric("Anomaly Rate", f"{results.get('anomaly_rate', 0):.1f}%")
    
    def select_anomaly(self, anomaly_rows: List[Dict]) -> Optional[Dict]:
        """Select anomaly in Streamlit"""
        import streamlit as st
        
        idx = st.selectbox("Select anomaly", range(len(anomaly_rows)))
        return anomaly_rows[idx] if idx is not None else None
    
    def display_genai_explanation(self, explanation: Dict) -> None:
        """Display explanation in Streamlit"""
        import streamlit as st
        
        st.write(f"**Summary:** {explanation.get('summary')}")
        st.write(f"**Severity:** {explanation.get('severity')}")
    
    def display_executive_summary(self, summary: Dict) -> None:
        """Display summary in Streamlit"""
        import streamlit as st
        
        st.metric("Total Anomalies", summary.get("total_anomalies", 0))
        st.metric("Anomaly Rate", f"{summary.get('anomaly_rate', 0):.1f}%")
    
    def run(self) -> None:
        """Run Streamlit frontend"""
        workflow = FrontendWorkflow(self)
        workflow.run_workflow()


class CLIFrontend(IFrontend):
    """Command-line frontend implementation (example)"""
    
    def upload_data(self) -> Optional[Dict]:
        """Upload data via CLI"""
        import pandas as pd
        
        filepath = input("Enter CSV file path: ")
        try:
            df = pd.read_csv(filepath)
            print(f"✓ Loaded {len(df)} rows")
            return {"success": True, "data": df}
        except Exception as e:
            print(f"✗ Error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_detection_config(self) -> DetectionConfig:
        """Get config from CLI prompts"""
        metrics = input("Enter metrics (comma-separated): ").split(",")
        method = input("Detection method (zscore/mad/isolation_forest/stl) [zscore]: ") or "zscore"
        threshold = float(input("Threshold [3.0]: ") or "3.0")
        
        return DetectionConfig(metrics=metrics, method=method, threshold=threshold)
    
    def get_genai_config(self) -> GenAIConfig:
        """Get config from CLI prompts"""
        provider = input("LLM Provider (ollama_local/openai/vertex_ai/azure_openai) [ollama_local]: ") or "ollama_local"
        
        return GenAIConfig(provider=provider, model="default")
    
    def display_detection_results(self, results: Dict) -> None:
        """Display results in CLI"""
        print("\n📊 Detection Results:")
        print(f"  Anomalies Found: {results.get('anomalies_found', 0)}")
        print(f"  Anomaly Rate: {results.get('anomaly_rate', 0):.1f}%")
    
    def select_anomaly(self, anomaly_rows: List[Dict]) -> Optional[Dict]:
        """Select anomaly in CLI"""
        for i, row in enumerate(anomaly_rows[:5]):
            print(f"{i}. {row.get('timestamp')} @ Site {row.get('site_id')}")
        
        idx = int(input("Select anomaly number: "))
        return anomaly_rows[idx] if idx < len(anomaly_rows) else None
    
    def display_genai_explanation(self, explanation: Dict) -> None:
        """Display explanation in CLI"""
        print("\n🧠 GenAI Analysis:")
        print(f"Summary: {explanation.get('summary')}")
        print(f"Severity: {explanation.get('severity')}")
        print(f"Causes: {', '.join(explanation.get('likely_causes', []))}")
    
    def display_executive_summary(self, summary: Dict) -> None:
        """Display summary in CLI"""
        print("\n📈 Executive Summary:")
        print(f"Total Anomalies: {summary.get('total_anomalies', 0)}")
        print(f"Anomaly Rate: {summary.get('anomaly_rate', 0):.1f}%")
    
    def run(self) -> None:
        """Run CLI frontend"""
        workflow = FrontendWorkflow(self)
        workflow.run_workflow()
