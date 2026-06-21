"""
Synthetic network KPI time-series data generator.
Generates realistic network metrics with injected anomalies.
Supports both generic KPIs and cell site specific metrics (RSRP, RSRQ, SINR, etc.).
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path


class NetworkKPIGenerator:
    """Generate synthetic network KPI metrics"""
    
    METRICS = {
        "cpu_utilization": {"min": 10, "max": 90, "trend": 0.01},
        "memory_utilization": {"min": 20, "max": 85, "trend": 0.005},
        "packet_loss_rate": {"min": 0, "max": 5, "trend": -0.001},
        "latency_ms": {"min": 10, "max": 100, "trend": 0.002},
        "bandwidth_utilization": {"min": 5, "max": 80, "trend": 0.015},
    }
    
    # Cell site specific metrics (LTE/5G KPIs)
    CELL_SITE_METRICS = {
        "rsrp": {"min": -140, "max": -50, "trend": 0.0, "unit": "dBm", "type": "signal_strength"},
        "rsrq": {"min": -20, "max": -5, "trend": 0.0, "unit": "dB", "type": "signal_quality"},
        "sinr": {"min": -10, "max": 30, "trend": 0.0, "unit": "dB", "type": "signal_quality"},
        "throughput_mbps": {"min": 0.5, "max": 500, "trend": 0.01, "unit": "Mbps", "type": "performance"},
        "latency_ms": {"min": 5, "max": 200, "trend": 0.005, "unit": "ms", "type": "performance"},
        "dropped_call_rate": {"min": 0, "max": 5, "trend": -0.001, "unit": "%", "type": "quality"},
    }
    
    def __init__(
        self,
        num_metrics: int = 5,
        time_steps: int = 1000,
        sampling_interval: int = 60,
        anomaly_probability: float = 0.05,
        anomaly_magnitude: float = 3.0,
        seed: int = 42
    ):
        """
        Initialize the KPI generator.
        
        Args:
            num_metrics: Number of metrics to generate
            time_steps: Number of time steps
            sampling_interval: Time between samples in seconds
            anomaly_probability: Probability of anomaly in each time step
            anomaly_magnitude: Magnitude of anomalies (in stdev)
            seed: Random seed for reproducibility
        """
        self.num_metrics = num_metrics
        self.time_steps = time_steps
        self.sampling_interval = sampling_interval
        self.anomaly_probability = anomaly_probability
        self.anomaly_magnitude = anomaly_magnitude
        np.random.seed(seed)
        
        # Select metrics
        self.selected_metrics = list(self.METRICS.keys())[:num_metrics]
    
    def generate_timeseries(self) -> Tuple[pd.DataFrame, Dict]:
        """
        Generate synthetic KPI time-series data.
        
        Returns:
            Tuple of (DataFrame with metrics, dict with anomaly info)
        """
        # Generate timestamps
        now = datetime.now()
        timestamps = [now - timedelta(seconds=i * self.sampling_interval) 
                     for i in range(self.time_steps - 1, -1, -1)]
        
        # Initialize data dictionary
        data = {"timestamp": timestamps}
        anomaly_info = {}
        
        # Generate each metric
        for metric_name in self.selected_metrics:
            config = self.METRICS[metric_name]
            
            # Generate base time-series with trend
            metric_data = self._generate_metric(
                config["min"],
                config["max"],
                config["trend"]
            )
            
            # Inject anomalies
            anomalies = self._inject_anomalies(metric_data)
            data[metric_name] = metric_data
            anomaly_info[metric_name] = anomalies
        
        df = pd.DataFrame(data)
        return df, anomaly_info
    
    def _generate_metric(
        self,
        min_val: float,
        max_val: float,
        trend: float
    ) -> np.ndarray:
        """Generate a single metric time-series with trend and noise"""
        # Start from middle of range
        start_val = (min_val + max_val) / 2
        
        # Generate random walk with trend
        changes = np.random.normal(trend, 0.5, self.time_steps)
        values = np.cumsum(changes) + start_val
        
        # Add noise
        values += np.random.normal(0, (max_val - min_val) * 0.05, self.time_steps)
        
        # Clip to valid range
        values = np.clip(values, min_val, max_val)
        
        return values
    
    def _inject_anomalies(self, metric_data: np.ndarray) -> List[int]:
        """Inject anomalies into metric data and return anomaly indices"""
        anomalies = []
        
        for i in range(self.time_steps):
            if np.random.random() < self.anomaly_probability:
                # Calculate deviation
                std_dev = np.std(metric_data)
                deviation = np.random.choice([-1, 1]) * self.anomaly_magnitude * std_dev
                metric_data[i] += deviation
                anomalies.append(i)
        
        return anomalies
    
    def save_to_csv(self, df: pd.DataFrame, filepath: str) -> None:
        """Save generated data to CSV"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath, index=False)
        print(f"Data saved to {filepath}")
    
    def save_to_json(self, data: Dict, filepath: str) -> None:
        """Save data to JSON"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Metadata saved to {filepath}")


def generate_sample_data(
    output_dir: str = "./data",
    num_samples: int = 1
) -> List[str]:
    """
    Generate sample datasets.
    
    Args:
        output_dir: Directory to save files
        num_samples: Number of sample datasets to generate
    
    Returns:
        List of generated CSV file paths
    """
    generator = NetworkKPIGenerator(
        num_metrics=5,
        time_steps=1000,
        sampling_interval=60,
        anomaly_probability=0.05,
        anomaly_magnitude=3.0
    )
    
    generated_files = []
    
    for i in range(num_samples):
        df, anomalies = generator.generate_timeseries()
        
        # Save CSV
        csv_path = f"{output_dir}/sample_data_{i+1}.csv"
        generator.save_to_csv(df, csv_path)
        generated_files.append(csv_path)
        
        # Save metadata
        meta_path = f"{output_dir}/sample_data_{i+1}_metadata.json"
        generator.save_to_json(anomalies, meta_path)
    
    return generated_files


if __name__ == "__main__":
    # Generate sample data
    generate_sample_data(num_samples=3)
