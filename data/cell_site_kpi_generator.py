"""
Synthetic cell site KPI data generator.
Generates realistic LTE/5G network metrics with injected anomalies.

Metrics:
- RSRP: Reference Signal Received Power (dBm)
- RSRQ: Reference Signal Received Quality (dB)
- SINR: Signal-to-Interference Ratio (dB)
- throughput_mbps: Data throughput (Mbps)
- latency_ms: Round-trip latency (ms)
- dropped_call_rate: Call drop percentage (%)
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path


class CellSiteKPIGenerator:
    """Generate synthetic cell site metrics with realistic anomalies"""
    
    # Baseline KPI ranges and characteristics
    BASELINE_RANGES = {
        "rsrp": {
            "min": -140,
            "max": -50,
            "nominal": -90,
            "unit": "dBm",
            "direction": "higher_is_better"
        },
        "rsrq": {
            "min": -20,
            "max": -5,
            "nominal": -12,
            "unit": "dB",
            "direction": "higher_is_better"
        },
        "sinr": {
            "min": -10,
            "max": 30,
            "nominal": 10,
            "unit": "dB",
            "direction": "higher_is_better"
        },
        "throughput_mbps": {
            "min": 0.5,
            "max": 500,
            "nominal": 150,
            "unit": "Mbps",
            "direction": "higher_is_better"
        },
        "latency_ms": {
            "min": 5,
            "max": 200,
            "nominal": 30,
            "unit": "ms",
            "direction": "lower_is_better"
        },
        "dropped_call_rate": {
            "min": 0,
            "max": 5,
            "nominal": 0.5,
            "unit": "%",
            "direction": "lower_is_better"
        }
    }
    
    def __init__(
        self,
        num_sites: int = 3,
        num_hours: int = 24,
        interval_minutes: int = 5,
        anomaly_probability: float = 0.05,
        anomaly_magnitude: float = 2.5,
        seed: int = 42
    ):
        """
        Initialize cell site KPI generator.
        
        Args:
            num_sites: Number of cell sites to generate
            num_hours: Number of hours of data to generate
            interval_minutes: Sampling interval in minutes
            anomaly_probability: Probability of anomaly injection (0-1)
            anomaly_magnitude: Magnitude of anomalies (in std deviations)
            seed: Random seed for reproducibility
        """
        self.num_sites = num_sites
        self.num_hours = num_hours
        self.interval_minutes = interval_minutes
        self.anomaly_probability = anomaly_probability
        self.anomaly_magnitude = anomaly_magnitude
        
        np.random.seed(seed)
        
        # Generate site IDs
        self.site_ids = [f"CELL_{i+1:03d}" for i in range(num_sites)]
        
        # Calculate number of time steps
        self.num_steps = int((num_hours * 60) / interval_minutes)
    
    def generate_data(self) -> Tuple[pd.DataFrame, Dict]:
        """
        Generate synthetic cell site data.
        
        Returns:
            Tuple of (DataFrame with all metrics and sites, anomaly metadata)
        """
        data = []
        anomaly_info = {}
        
        # Generate timestamps
        now = datetime.now()
        start_time = now - timedelta(hours=self.num_hours)
        timestamps = [
            start_time + timedelta(minutes=i * self.interval_minutes)
            for i in range(self.num_steps)
        ]
        
        # Generate data for each site
        for site_id in self.site_ids:
            site_anomalies = {}
            
            # Generate each metric
            metrics_data = {}
            for metric_name in self.BASELINE_RANGES.keys():
                values, anomalies = self._generate_metric_timeseries(metric_name)
                metrics_data[metric_name] = values
                site_anomalies[metric_name] = anomalies
            
            # Add correlated anomalies (when one metric fails, others degrade)
            metrics_data = self._inject_correlated_anomalies(metrics_data)
            
            # Combine site data
            for i, timestamp in enumerate(timestamps):
                row = {
                    "timestamp": timestamp,
                    "site_id": site_id
                }
                
                for metric_name in self.BASELINE_RANGES.keys():
                    row[metric_name] = metrics_data[metric_name][i]
                
                data.append(row)
            
            anomaly_info[site_id] = site_anomalies
        
        df = pd.DataFrame(data)
        df = df.sort_values(["site_id", "timestamp"]).reset_index(drop=True)
        
        return df, anomaly_info
    
    def _generate_metric_timeseries(
        self,
        metric_name: str
    ) -> Tuple[np.ndarray, List[int]]:
        """Generate time-series for a single metric"""
        
        config = self.BASELINE_RANGES[metric_name]
        min_val = config["min"]
        max_val = config["max"]
        nominal = config["nominal"]
        
        # Start from nominal value
        values = np.ones(self.num_steps) * nominal
        
        # Add drift and seasonality
        drift = np.linspace(0, (max_val - min_val) * 0.1, self.num_steps)
        
        # Daily seasonality (peak during business hours)
        hours = np.arange(self.num_steps) * self.interval_minutes / 60
        seasonality = 5 * np.sin(2 * np.pi * hours / 24)
        
        # Add noise
        noise = np.random.normal(0, (max_val - min_val) * 0.05, self.num_steps)
        
        values = values + drift + seasonality + noise
        
        # Inject anomalies
        anomalies = self._inject_anomalies(values, metric_name)
        
        # Clip to valid range
        values = np.clip(values, min_val, max_val)
        
        return values, anomalies
    
    def _inject_anomalies(
        self,
        metric_data: np.ndarray,
        metric_name: str
    ) -> List[int]:
        """Inject anomalies into metric data"""
        anomalies = []
        anomaly_types = [
            "gradual_degradation",
            "sudden_spike",
            "sudden_drop",
            "oscillation"
        ]
        
        config = self.BASELINE_RANGES[metric_name]
        min_val = config["min"]
        max_val = config["max"]
        range_val = max_val - min_val
        
        for i in range(len(metric_data)):
            if np.random.random() < self.anomaly_probability:
                anomaly_type = np.random.choice(anomaly_types)
                
                if anomaly_type == "sudden_spike":
                    # Sudden deviation (good or bad depending on metric)
                    if config["direction"] == "higher_is_better":
                        metric_data[i] += self.anomaly_magnitude * range_val * 0.1
                    else:
                        metric_data[i] += self.anomaly_magnitude * range_val * 0.1
                
                elif anomaly_type == "sudden_drop":
                    # Sudden drop (bad)
                    if config["direction"] == "higher_is_better":
                        metric_data[i] -= self.anomaly_magnitude * range_val * 0.15
                    else:
                        metric_data[i] += self.anomaly_magnitude * range_val * 0.15
                
                elif anomaly_type == "gradual_degradation":
                    # Gradual degradation over next few points
                    duration = np.random.randint(5, 15)
                    for j in range(min(duration, len(metric_data) - i)):
                        if config["direction"] == "higher_is_better":
                            metric_data[i + j] -= (self.anomaly_magnitude * range_val * 0.05)
                        else:
                            metric_data[i + j] += (self.anomaly_magnitude * range_val * 0.05)
                
                elif anomaly_type == "oscillation":
                    # Oscillation pattern
                    duration = np.random.randint(3, 10)
                    for j in range(min(duration, len(metric_data) - i)):
                        metric_data[i + j] += range_val * 0.1 * np.sin(j)
                
                anomalies.append(i)
        
        return anomalies
    
    def _inject_correlated_anomalies(
        self,
        metrics_data: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        Inject correlated anomalies.
        When signal quality degrades, other metrics degrade too.
        """
        metrics_data = {k: v.copy() for k, v in metrics_data.items()}
        
        # Check for RSRP drops (signal strength) - correlate with throughput and latency
        rsrp = metrics_data["rsrp"]
        rsrp_baseline = np.percentile(rsrp, 50)
        
        for i in range(len(rsrp)):
            # If RSRP is significantly lower, degrade throughput and increase latency
            if rsrp[i] < rsrp_baseline - 10:
                # Reduce throughput
                metrics_data["throughput_mbps"][i] *= np.random.uniform(0.3, 0.8)
                # Increase latency
                metrics_data["latency_ms"][i] *= np.random.uniform(1.5, 3.0)
                # Increase dropped calls
                metrics_data["dropped_call_rate"][i] += np.random.uniform(0.5, 2.0)
        
        # Check for SINR degradation - correlate with throughput and call drops
        sinr = metrics_data["sinr"]
        sinr_baseline = np.percentile(sinr, 50)
        
        for i in range(len(sinr)):
            if sinr[i] < sinr_baseline - 5:
                metrics_data["throughput_mbps"][i] *= np.random.uniform(0.5, 0.85)
                metrics_data["dropped_call_rate"][i] += np.random.uniform(0.2, 1.0)
        
        # Ensure all values stay within valid ranges
        for metric_name, values in metrics_data.items():
            config = self.BASELINE_RANGES[metric_name]
            metrics_data[metric_name] = np.clip(
                values, config["min"], config["max"]
            )
        
        return metrics_data
    
    def save_to_csv(self, df: pd.DataFrame, filepath: str) -> None:
        """Save generated data to CSV"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath, index=False)
        logger_info = f"Saved {len(df)} rows to {filepath}"
        print(logger_info)
    
    def save_metadata(self, anomaly_info: Dict, filepath: str) -> None:
        """Save anomaly metadata to JSON"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(anomaly_info, f, indent=2, default=str)
        print(f"Saved metadata to {filepath}")


def generate_synthetic_kpi_data(
    num_sites: int = 3,
    num_hours: int = 24,
    interval_minutes: int = 5,
    output_dir: str = "./data",
    save_files: bool = True
) -> pd.DataFrame:
    """
    Generate synthetic cell site KPI data.
    
    Args:
        num_sites: Number of cell sites
        num_hours: Number of hours of data
        interval_minutes: Sampling interval in minutes
        output_dir: Directory to save output files
        save_files: Whether to save to CSV
    
    Returns:
        DataFrame with generated data
    
    Example:
        >>> df = generate_synthetic_kpi_data(num_sites=5, num_hours=48)
        >>> print(df.head())
        >>> print(df.columns)
    """
    generator = CellSiteKPIGenerator(
        num_sites=num_sites,
        num_hours=num_hours,
        interval_minutes=interval_minutes
    )
    
    df, anomalies = generator.generate_data()
    
    if save_files:
        csv_path = f"{output_dir}/cell_site_metrics_{num_sites}sites_{num_hours}h.csv"
        meta_path = f"{output_dir}/cell_site_metrics_{num_sites}sites_{num_hours}h_anomalies.json"
        
        generator.save_to_csv(df, csv_path)
        generator.save_metadata(anomalies, meta_path)
    
    return df


if __name__ == "__main__":
    # Generate sample data
    print("Generating synthetic cell site KPI data...")
    df = generate_synthetic_kpi_data(
        num_sites=3,
        num_hours=24,
        interval_minutes=5
    )
    
    print("\nGenerated data:")
    print(df.head(10))
    print(f"\nShape: {df.shape}")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nSites: {df['site_id'].unique()}")
