"""
Unit tests for Network Incident Investigator
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.cell_site_kpi_generator import generate_synthetic_kpi_data, CellSiteKPIGenerator
from services.anomaly_detection.kpi_detector import (
    NetworkKPIAnomalyDetectionService,
    detect_anomalies,
    ZScoreDetector,
    MADDetector,
    AnomalyDetectionConfig
)
from services.genai_reasoning.context_builder import build_anomaly_context
from services.genai_reasoning.llm_client import LLMClient
from backend.data_loader import CSVDataSource, DataSourceFactory


class TestSyntheticDataGeneration:
    """Test synthetic data generation"""
    
    def test_generate_data_basic(self):
        """Test basic data generation"""
        df = generate_synthetic_kpi_data(
            num_sites=2,
            num_hours=6,
            save_files=False
        )
        
        assert len(df) > 0
        assert "site_id" in df.columns
        assert "timestamp" in df.columns
        assert "rsrp" in df.columns
        assert "throughput_mbps" in df.columns
    
    def test_generate_data_sites(self):
        """Test correct number of sites"""
        df = generate_synthetic_kpi_data(
            num_sites=5,
            num_hours=6,
            save_files=False
        )
        
        unique_sites = df["site_id"].nunique()
        assert unique_sites == 5
    
    def test_generate_data_columns(self):
        """Test all required columns exist"""
        df = generate_synthetic_kpi_data(num_sites=2, num_hours=6, save_files=False)
        
        required_cols = ["timestamp", "site_id", "rsrp", "rsrq", "sinr", 
                        "throughput_mbps", "latency_ms", "dropped_call_rate"]
        
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"
    
    def test_data_ranges(self):
        """Test data is within valid ranges"""
        df = generate_synthetic_kpi_data(num_sites=2, num_hours=6, save_files=False)
        
        # RSRP: -140 to -50 dBm
        assert df["rsrp"].min() >= -140
        assert df["rsrp"].max() <= -50
        
        # Throughput: 0.5 to 500 Mbps
        assert df["throughput_mbps"].min() >= 0.5
        assert df["throughput_mbps"].max() <= 500
        
        # Latency: 5 to 200 ms
        assert df["latency_ms"].min() >= 5
        assert df["latency_ms"].max() <= 200


class TestAnomalyDetection:
    """Test anomaly detection"""
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample data"""
        return generate_synthetic_kpi_data(
            num_sites=2,
            num_hours=12,
            save_files=False
        )
    
    def test_zscore_detector(self, sample_data):
        """Test Z-Score detector"""
        config = AnomalyDetectionConfig(
            metric_name="rsrp",
            method="zscore",
            threshold=3.0
        )
        
        detector = ZScoreDetector()
        data = sample_data["rsrp"].values
        scores, meta = detector.detect(data, config)
        
        assert len(scores) == len(data)
        assert "method" in meta
        assert meta["method"] == "zscore"
    
    def test_mad_detector(self, sample_data):
        """Test MAD detector"""
        config = AnomalyDetectionConfig(
            metric_name="throughput_mbps",
            method="mad",
            threshold=2.5
        )
        
        detector = MADDetector()
        data = sample_data["throughput_mbps"].values
        scores, meta = detector.detect(data, config)
        
        assert len(scores) == len(data)
        assert meta["method"] == "mad"
    
    def test_service_detect_anomalies(self, sample_data):
        """Test anomaly detection service"""
        service = NetworkKPIAnomalyDetectionService()
        
        result_df = service.detect_anomalies(
            df=sample_data,
            metrics=["rsrp", "throughput_mbps"],
            method="zscore"
        )
        
        assert "is_anomaly" in result_df.columns
        assert "is_anomaly_rsrp" in result_df.columns
        assert "anomaly_score_rsrp" in result_df.columns
        assert len(result_df) == len(sample_data)
    
    def test_detect_anomalies_function(self, sample_data):
        """Test convenience function"""
        result_df = detect_anomalies(
            df=sample_data,
            metrics=["rsrp", "latency_ms"],
            method="zscore",
            config={"threshold": 3.0}
        )
        
        assert "is_anomaly" in result_df.columns
        assert len(result_df) == len(sample_data)


class TestContextBuilder:
    """Test anomaly context building"""
    
    def test_build_context(self):
        """Test context building"""
        df = generate_synthetic_kpi_data(num_sites=1, num_hours=6, save_files=False)
        
        # Run anomaly detection to get results
        result_df = detect_anomalies(
            df=df,
            metrics=["rsrp", "throughput_mbps"],
            method="zscore"
        )
        
        # Get an anomalous row
        anomalies = result_df[result_df["is_anomaly"]]
        if len(anomalies) > 0:
            anomaly_row = anomalies.iloc[0]
            
            context = build_anomaly_context(
                df=result_df,
                anomaly_row=anomaly_row,
                metric_columns=["rsrp", "throughput_mbps"]
            )
            
            assert "site_id" in context
            assert "timestamp" in context
            assert "anomalies" in context
            assert "metrics" in context
            assert "history_summary" in context


class TestLLMClient:
    """Test LLM client"""
    
    def test_ollama_client_creation(self):
        """Test Ollama client creation"""
        client = LLMClient('ollama_local', {
            'base_url': 'http://localhost:11434',
            'model': 'llama2'
        })
        
        assert client is not None
        provider_info = client.get_provider_info()
        assert provider_info["provider"] == "ollama_local"
    
    def test_openai_client_creation(self):
        """Test OpenAI client creation (mock)"""
        client = LLMClient('openai', {
            'api_key': 'test-key',
            'model': 'gpt-3.5-turbo'
        })
        
        assert client is not None
        provider_info = client.get_provider_info()
        assert provider_info["provider"] == "openai"
    
    def test_explain_anomaly_with_fallback(self):
        """Test fallback when LLM unavailable"""
        client = LLMClient('ollama_local', {
            'base_url': 'http://invalid:11434',
            'model': 'llama2'
        })
        
        context = {
            "site_id": "CELL_001",
            "timestamp": "2026-06-20T12:00:00Z",
            "anomalies": {
                "rsrp": {"is_anomaly": True, "score": 0.9, "value": -130}
            },
            "metrics": {
                "rsrp": {"value": -130, "min": -140, "max": -50}
            }
        }
        
        # Should return fallback response
        result = client.explain_anomaly(context)
        
        assert "summary" in result
        assert "likely_causes" in result
        assert "recommended_actions" in result


class TestDataLoaders:
    """Test data loaders"""
    
    def test_csv_source_creation(self, tmp_path):
        """Test CSV data source"""
        # Create test CSV
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=10),
            "site_id": ["CELL_001"] * 10,
            "rsrp": np.random.uniform(-140, -50, 10)
        })
        
        csv_file = tmp_path / "test.csv"
        df.to_csv(csv_file, index=False)
        
        # Test loader
        source = CSVDataSource(filepath=str(csv_file))
        assert source.validate()
        
        loaded_df = source.load()
        assert len(loaded_df) == 10
        assert "rsrp" in loaded_df.columns
    
    def test_data_source_factory(self):
        """Test data source factory"""
        factory = DataSourceFactory()
        
        # Test creating CSV source
        source = factory.create('csv', {
            'filepath': './test.csv'
        })
        
        assert source is not None
        assert isinstance(source, CSVDataSource)


class TestIntegration:
    """Integration tests"""
    
    def test_full_pipeline(self):
        """Test complete pipeline: generate → detect → analyze"""
        
        # 1. Generate data
        df = generate_synthetic_kpi_data(
            num_sites=2,
            num_hours=12,
            save_files=False
        )
        print(f"✓ Generated {len(df)} rows of synthetic data")
        
        # 2. Detect anomalies
        result_df = detect_anomalies(
            df=df,
            metrics=["rsrp", "throughput_mbps", "latency_ms"],
            method="zscore"
        )
        
        anomaly_count = result_df["is_anomaly"].sum()
        print(f"✓ Detected {anomaly_count} anomalies")
        
        assert "is_anomaly" in result_df.columns
        assert anomaly_count > 0
        
        # 3. Build context for LLM
        if anomaly_count > 0:
            anomalies = result_df[result_df["is_anomaly"]]
            anomaly_row = anomalies.iloc[0]
            
            context = build_anomaly_context(
                df=result_df,
                anomaly_row=anomaly_row,
                metric_columns=["rsrp", "throughput_mbps", "latency_ms"]
            )
            
            assert "site_id" in context
            print(f"✓ Built context for {context['site_id']}")
            
            # 4. Explain anomaly (with fallback)
            client = LLMClient('ollama_local', {
                'base_url': 'http://localhost:11434',
                'model': 'llama2'
            })
            
            explanation = client.explain_anomaly(context)
            assert "summary" in explanation
            print(f"✓ Generated explanation with {explanation.get('severity')} severity")
        
        print("\n✅ Full pipeline test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
