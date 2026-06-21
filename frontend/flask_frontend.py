"""
Flask-based frontend for Network Incident Investigator.
Example of implementing IFrontend with Flask framework.
"""
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import io
import logging
from typing import Optional, Dict, List

from frontend.abstract_frontend import IFrontend, DetectionConfig, GenAIConfig, FrontendWorkflow
from services.anomaly_detection.kpi_detector import detect_anomalies
from services.genai_reasoning.llm_client import LLMClient
from services.genai_reasoning.context_builder import build_anomaly_context
from data.cell_site_kpi_generator import generate_synthetic_kpi_data

logger = logging.getLogger(__name__)


class FlaskFrontend(IFrontend):
    """Flask-based REST frontend for Network Incident Investigator"""
    
    def __init__(self, app: Flask = None):
        """Initialize Flask frontend"""
        self.app = app or Flask(__name__)
        self.current_data: Optional[pd.DataFrame] = None
        self.current_results: Optional[pd.DataFrame] = None
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route("/api/health", methods=["GET"])
        def health():
            return jsonify({"status": "healthy", "version": "1.0.0"})
        
        @self.app.route("/api/data/upload", methods=["POST"])
        def upload_data():
            """Upload CSV file"""
            try:
                if "file" not in request.files:
                    return jsonify({"success": False, "error": "No file uploaded"}), 400
                
                file = request.files["file"]
                if file.filename == "":
                    return jsonify({"success": False, "error": "No file selected"}), 400
                
                df = pd.read_csv(file)
                self.current_data = df
                
                return jsonify({
                    "success": True,
                    "rows": len(df),
                    "columns": df.columns.tolist(),
                    "sites": df["site_id"].nunique() if "site_id" in df.columns else 0
                })
            
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 400
        
        @self.app.route("/api/data/sample", methods=["POST"])
        def generate_sample_data():
            """Generate synthetic sample data"""
            try:
                data = request.get_json()
                num_sites = data.get("num_sites", 3)
                num_hours = data.get("num_hours", 24)
                
                df = generate_synthetic_kpi_data(
                    num_sites=num_sites,
                    num_hours=num_hours,
                    save_files=False
                )
                
                self.current_data = df
                
                return jsonify({
                    "success": True,
                    "rows": len(df),
                    "columns": df.columns.tolist()
                })
            
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 400
        
        @self.app.route("/api/data/preview", methods=["GET"])
        def preview_data():
            """Get data preview"""
            if self.current_data is None:
                return jsonify({"success": False, "error": "No data loaded"}), 400
            
            limit = request.args.get("limit", 10, type=int)
            return jsonify({
                "success": True,
                "data": self.current_data.head(limit).to_dict(orient="records"),
                "total_rows": len(self.current_data)
            })
        
        @self.app.route("/api/anomaly/detect", methods=["POST"])
        def detect():
            """Run anomaly detection"""
            try:
                if self.current_data is None:
                    return jsonify({"success": False, "error": "No data loaded"}), 400
                
                data = request.get_json()
                metrics = data.get("metrics", [])
                method = data.get("method", "zscore")
                threshold = float(data.get("threshold", 3.0))
                
                result_df = detect_anomalies(
                    df=self.current_data,
                    metrics=metrics,
                    method=method,
                    config={"threshold": threshold}
                )
                
                self.current_results = result_df
                
                anomaly_count = result_df["is_anomaly"].sum() if "is_anomaly" in result_df.columns else 0
                
                return jsonify({
                    "success": True,
                    "anomalies_found": int(anomaly_count),
                    "anomaly_rate": float(anomaly_count / len(result_df) * 100),
                    "detection_method": method
                })
            
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 400
        
        @self.app.route("/api/anomaly/results", methods=["GET"])
        def get_results():
            """Get anomaly detection results"""
            if self.current_results is None:
                return jsonify({"success": False, "error": "No detection results"}), 400
            
            limit = request.args.get("limit", 50, type=int)
            
            anomaly_rows = self.current_results[
                self.current_results["is_anomaly"] 
                if "is_anomaly" in self.current_results.columns 
                else []
            ]
            
            return jsonify({
                "success": True,
                "total_anomalies": len(anomaly_rows),
                "anomalies": anomaly_rows.head(limit).to_dict(orient="records")
            })
        
        @self.app.route("/api/genai/explain", methods=["POST"])
        def explain():
            """Get GenAI explanation for anomaly"""
            try:
                if self.current_results is None:
                    return jsonify({"success": False, "error": "No detection results"}), 400
                
                data = request.get_json()
                anomaly_idx = data.get("anomaly_idx", 0)
                provider = data.get("provider", "ollama_local")
                
                # Get anomalies
                anomalies = self.current_results[
                    self.current_results["is_anomaly"] 
                    if "is_anomaly" in self.current_results.columns 
                    else []
                ]
                
                if anomaly_idx >= len(anomalies):
                    return jsonify({"success": False, "error": "Invalid anomaly index"}), 400
                
                selected_anomaly = anomalies.iloc[anomaly_idx]
                
                # Initialize LLM client
                genai_config = data.get("genai_config", {})
                client = LLMClient(provider=provider, config=genai_config)
                
                # Build context
                metric_columns = [
                    col for col in self.current_results.columns 
                    if col not in ["timestamp", "site_id", "is_anomaly"]
                ]
                
                context = build_anomaly_context(
                    df=self.current_results,
                    anomaly_row=selected_anomaly,
                    metric_columns=metric_columns
                )
                
                # Get explanation
                explanation = client.explain_anomaly(context)
                
                return jsonify({
                    "success": True,
                    "explanation": explanation
                })
            
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 400
        
        @self.app.route("/api/summary", methods=["GET"])
        def executive_summary():
            """Get executive summary"""
            if self.current_results is None:
                return jsonify({"success": False, "error": "No detection results"}), 400
            
            anomaly_count = self.current_results["is_anomaly"].sum() if "is_anomaly" in self.current_results.columns else 0
            
            affected_sites = self.current_results[
                self.current_results["is_anomaly"]
            ]["site_id"].nunique() if "is_anomaly" in self.current_results.columns else 0
            
            return jsonify({
                "success": True,
                "summary": {
                    "total_anomalies": int(anomaly_count),
                    "anomaly_rate": float(anomaly_count / len(self.current_results) * 100),
                    "affected_sites": int(affected_sites),
                    "total_rows": len(self.current_results)
                }
            })
        
        @self.app.route("/api/results/download", methods=["GET"])
        def download_results():
            """Download results as CSV"""
            if self.current_results is None:
                return jsonify({"success": False, "error": "No results to download"}), 400
            
            # Filter anomalies only
            anomalies = self.current_results[self.current_results["is_anomaly"]]
            
            # Convert to CSV
            csv_buffer = io.StringIO()
            anomalies.to_csv(csv_buffer, index=False)
            
            # Return as download
            csv_buffer.seek(0)
            return send_file(
                io.BytesIO(csv_buffer.getvalue().encode()),
                mimetype="text/csv",
                as_attachment=True,
                download_name="anomalies.csv"
            )
    
    # ========================================================================
    # IFrontend Implementation Methods
    # ========================================================================
    
    def upload_data(self) -> Optional[Dict]:
        """Upload data (handled by Flask route)"""
        # This is called by FrontendWorkflow when running standalone
        # In Flask app, this is handled by POST /api/data/upload
        pass
    
    def get_detection_config(self) -> DetectionConfig:
        """Get detection config from request"""
        data = request.get_json() if request.is_json else {}
        return DetectionConfig(
            metrics=data.get("metrics", []),
            method=data.get("method", "zscore"),
            threshold=float(data.get("threshold", 3.0))
        )
    
    def get_genai_config(self) -> GenAIConfig:
        """Get GenAI config from request"""
        data = request.get_json() if request.is_json else {}
        return GenAIConfig(
            provider=data.get("provider", "ollama_local"),
            model=data.get("model", "llama2")
        )
    
    def display_detection_results(self, results: Dict) -> None:
        """Results are returned as JSON"""
        pass
    
    def select_anomaly(self, anomaly_rows: List[Dict]) -> Optional[Dict]:
        """Get selected anomaly index from request"""
        idx = request.args.get("anomaly_idx", 0, type=int)
        return anomaly_rows[idx] if idx < len(anomaly_rows) else None
    
    def display_genai_explanation(self, explanation: Dict) -> None:
        """Explanation returned as JSON"""
        pass
    
    def display_executive_summary(self, summary: Dict) -> None:
        """Summary returned as JSON"""
        pass
    
    def run(self):
        """Run Flask app"""
        self.app.run(debug=True, port=5000, host="0.0.0.0")


# ============================================================================
# Application Factory
# ============================================================================

def create_app() -> Flask:
    """Create Flask application"""
    app = Flask(__name__)
    frontend = FlaskFrontend(app)
    return app


# ============================================================================
# Run Application
# ============================================================================

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
