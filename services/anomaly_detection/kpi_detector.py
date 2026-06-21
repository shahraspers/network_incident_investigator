"""
Enhanced anomaly detection service for network KPIs.
Supports per-metric and per-site configuration with multiple detection methods.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnomalyDetectionConfig:
    """Configuration for anomaly detection per metric"""
    metric_name: str
    method: str = "zscore"  # zscore, isolation_forest, mad, stl
    threshold: float = 3.0
    window_size: int = 30
    min_samples: int = 10
    contamination: float = 0.1
    seasonal_period: Optional[int] = None  # For STL decomposition
    

class AnomalyDetector:
    """Base anomaly detector"""
    
    def detect(
        self,
        data: np.ndarray,
        config: AnomalyDetectionConfig
    ) -> Tuple[np.ndarray, Dict]:
        """
        Detect anomalies.
        
        Returns:
            Tuple of (anomaly_scores, metadata)
        """
        raise NotImplementedError


class ZScoreDetector(AnomalyDetector):
    """Z-Score anomaly detection"""
    
    def detect(
        self,
        data: np.ndarray,
        config: AnomalyDetectionConfig
    ) -> Tuple[np.ndarray, Dict]:
        """
        Detect anomalies using Z-Score method.
        
        Z-score = (value - mean) / std_dev
        Anomaly if |z-score| > threshold
        """
        data = np.asarray(data).flatten()
        
        # Handle edge cases
        if len(data) < config.min_samples:
            return np.zeros(len(data)), {
                "method": "zscore",
                "status": "insufficient_data",
                "min_samples_required": config.min_samples
            }
        
        # Calculate z-scores
        mean = np.nanmean(data)
        std = np.nanstd(data)
        
        if std == 0:
            # All values are the same
            return np.zeros(len(data)), {
                "method": "zscore",
                "status": "zero_variance",
                "anomaly_count": 0
            }
        
        z_scores = np.abs((data - mean) / std)
        
        anomalies = z_scores > config.threshold
        
        return z_scores, {
            "method": "zscore",
            "threshold": config.threshold,
            "mean": float(mean),
            "std": float(std),
            "num_anomalies": int(np.sum(anomalies)),
            "anomaly_ratio": float(np.sum(anomalies) / len(anomalies))
        }


class MADDetector(AnomalyDetector):
    """Median Absolute Deviation anomaly detection"""
    
    def detect(
        self,
        data: np.ndarray,
        config: AnomalyDetectionConfig
    ) -> Tuple[np.ndarray, Dict]:
        """
        Detect anomalies using MAD method.
        Robust to outliers compared to z-score.
        """
        data = np.asarray(data).flatten()
        
        if len(data) < config.min_samples:
            return np.zeros(len(data)), {
                "method": "mad",
                "status": "insufficient_data"
            }
        
        # Calculate MAD
        median = np.nanmedian(data)
        mad = np.nanmedian(np.abs(data - median))
        
        if mad == 0:
            return np.zeros(len(data)), {
                "method": "mad",
                "status": "zero_variance"
            }
        
        # Modified z-score using MAD
        # Modified_z_score = 0.6745 * (value - median) / MAD
        modified_z = 0.6745 * (data - median) / mad
        mod_z_scores = np.abs(modified_z)
        
        anomalies = mod_z_scores > config.threshold
        
        return mod_z_scores, {
            "method": "mad",
            "threshold": config.threshold,
            "median": float(median),
            "mad": float(mad),
            "num_anomalies": int(np.sum(anomalies)),
            "anomaly_ratio": float(np.sum(anomalies) / len(anomalies))
        }


class IsolationForestDetector(AnomalyDetector):
    """Isolation Forest anomaly detection"""
    
    def detect(
        self,
        data: np.ndarray,
        config: AnomalyDetectionConfig
    ) -> Tuple[np.ndarray, Dict]:
        """
        Detect anomalies using Isolation Forest.
        """
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            logger.warning("scikit-learn not available, using MAD instead")
            return MADDetector().detect(data, config)
        
        data = np.asarray(data).flatten().reshape(-1, 1)
        
        if len(data) < config.min_samples:
            return np.zeros(len(data)), {
                "method": "isolation_forest",
                "status": "insufficient_data"
            }
        
        model = IsolationForest(
            contamination=config.contamination,
            random_state=42
        )
        
        predictions = model.fit_predict(data)
        scores = -model.score_samples(data)  # Negate so higher = more anomalous
        
        anomalies = predictions == -1
        
        return scores, {
            "method": "isolation_forest",
            "contamination": config.contamination,
            "num_anomalies": int(np.sum(anomalies)),
            "anomaly_ratio": float(np.sum(anomalies) / len(anomalies))
        }


class STLDetector(AnomalyDetector):
    """STL (Seasonal and Trend decomposition) based detection"""
    
    def detect(
        self,
        data: np.ndarray,
        config: AnomalyDetectionConfig
    ) -> Tuple[np.ndarray, Dict]:
        """
        Detect anomalies using STL decomposition.
        Good for seasonal data.
        """
        try:
            from statsmodels.tsa.seasonal import STL
        except ImportError:
            logger.warning("statsmodels not available, using MAD instead")
            return MADDetector().detect(data, config)
        
        data = np.asarray(data).flatten()
        
        if len(data) < max(config.min_samples, 14):
            return np.zeros(len(data)), {
                "method": "stl",
                "status": "insufficient_data"
            }
        
        try:
            seasonal_period = config.seasonal_period or max(
                len(data) // 4, 7
            )
            
            stl = STL(
                data,
                seasonal=seasonal_period,
                trend=seasonal_period + 1
            )
            result = stl.fit()
            
            # Calculate residual z-scores
            residuals = result.resid
            residual_zscore = np.abs((residuals - np.mean(residuals)) / np.std(residuals))
            
            anomalies = residual_zscore > config.threshold
            
            return residual_zscore, {
                "method": "stl",
                "threshold": config.threshold,
                "seasonal_period": seasonal_period,
                "num_anomalies": int(np.sum(anomalies)),
                "anomaly_ratio": float(np.sum(anomalies) / len(anomalies))
            }
        except Exception as e:
            logger.warning(f"STL decomposition failed: {e}, using MAD")
            return MADDetector().detect(data, config)


class NetworkKPIAnomalyDetectionService:
    """
    Main anomaly detection service for network KPIs.
    Supports per-metric and per-site configuration.
    """
    
    def __init__(self):
        """Initialize the service"""
        self.detectors = {
            "zscore": ZScoreDetector(),
            "mad": MADDetector(),
            "isolation_forest": IsolationForestDetector(),
            "stl": STLDetector()
        }
        self.metric_configs: Dict[str, AnomalyDetectionConfig] = {}
    
    def configure_metric(
        self,
        metric_name: str,
        method: str = "zscore",
        threshold: float = 3.0,
        window_size: int = 30,
        **kwargs
    ) -> None:
        """
        Configure anomaly detection for a specific metric.
        
        Args:
            metric_name: Name of the metric
            method: Detection method (zscore, mad, isolation_forest, stl)
            threshold: Anomaly threshold
            window_size: Window size for calculations
            **kwargs: Additional parameters
        """
        self.metric_configs[metric_name] = AnomalyDetectionConfig(
            metric_name=metric_name,
            method=method,
            threshold=threshold,
            window_size=window_size,
            **kwargs
        )
        logger.info(f"Configured {metric_name} with {method} (threshold={threshold})")
    
    def detect_anomalies(
        self,
        df: pd.DataFrame,
        metrics: List[str],
        site_col: str = "site_id",
        time_col: str = "timestamp",
        method: Optional[str] = None,
        config: Optional[Dict] = None,
    ) -> pd.DataFrame:
        """
        Detect anomalies in DataFrame.
        
        Args:
            df: Input DataFrame
            metrics: List of metric columns to analyze
            site_col: Site ID column name
            time_col: Timestamp column name
            method: Optional override for detection method
            config: Optional override for detection config
        
        Returns:
            DataFrame with additional columns:
            - is_anomaly_{metric}: Boolean flag
            - anomaly_score_{metric}: Anomaly score
            - anomaly_reason_{metric}: Reason for anomaly (if any)
        """
        df_result = df.copy()
        
        # Process each metric
        for metric in metrics:
            if metric not in df_result.columns:
                logger.warning(f"Metric {metric} not found in DataFrame")
                continue
            
            # Get or create config for this metric
            if metric in self.metric_configs:
                metric_config = self.metric_configs[metric]
            else:
                # Use provided config or create default
                if config:
                    metric_config = AnomalyDetectionConfig(
                        metric_name=metric,
                        method=method or config.get("method", "zscore"),
                        threshold=config.get("threshold", 3.0),
                        window_size=config.get("window_size", 30)
                    )
                else:
                    metric_config = AnomalyDetectionConfig(
                        metric_name=metric,
                        method=method or "zscore",
                        threshold=3.0
                    )
            
            # Get detector
            detector = self.detectors.get(metric_config.method)
            if not detector:
                logger.warning(f"Unknown detection method: {metric_config.method}")
                continue
            
            # Detect anomalies per site
            is_anomaly_list = []
            anomaly_score_list = []
            
            for site_id in df_result[site_col].unique():
                site_mask = df_result[site_col] == site_id
                site_data = df_result.loc[site_mask, metric].values
                
                # Run detector
                scores, meta = detector.detect(site_data, metric_config)
                
                # Calculate anomaly threshold
                threshold = metric_config.threshold
                anomaly_mask = scores > threshold
                
                # Store results
                is_anomaly_list.extend(anomaly_mask)
                anomaly_score_list.extend(scores)
            
            # Add columns to result
            df_result[f"is_anomaly_{metric}"] = is_anomaly_list
            df_result[f"anomaly_score_{metric}"] = anomaly_score_list
            
            # Add reason column
            reasons = []
            for is_anom, score in zip(is_anomaly_list, anomaly_score_list):
                if is_anom:
                    reasons.append(f"{metric_config.method}:{score:.2f}")
                else:
                    reasons.append("")
            
            df_result[f"anomaly_reason_{metric}"] = reasons
        
        # Create composite anomaly flag
        anomaly_cols = [col for col in df_result.columns if col.startswith("is_anomaly_")]
        if anomaly_cols:
            df_result["is_anomaly"] = df_result[anomaly_cols].any(axis=1)
        
        return df_result
    
    def detect_anomalies_timeseries(
        self,
        df: pd.DataFrame,
        metric_col: str,
        window_size: int = 30,
        method: str = "zscore",
        site_col: Optional[str] = None,
        **config_kwargs
    ) -> Dict:
        """
        Detect anomalies using sliding window for time-series.
        
        Args:
            df: Input DataFrame
            metric_col: Column name of metric
            window_size: Sliding window size
            method: Detection method
            site_col: Optional site column for per-site analysis
            **config_kwargs: Additional config parameters
        
        Returns:
            Detection results with anomaly indices per window
        """
        if metric_col not in df.columns:
            raise ValueError(f"Metric {metric_col} not found")
        
        detector = self.detectors.get(method)
        if not detector:
            raise ValueError(f"Unknown detection method: {method}")
        
        config = AnomalyDetectionConfig(
            metric_name=metric_col,
            method=method,
            window_size=window_size,
            **config_kwargs
        )
        
        results = {
            "metric": metric_col,
            "method": method,
            "window_size": window_size,
            "windows": []
        }
        
        data = df[metric_col].values
        
        # Sliding window detection
        for i in range(len(data) - window_size + 1):
            window = data[i:i + window_size]
            scores, meta = detector.detect(window, config)
            
            anomaly_indices = np.where(scores > config.threshold)[0]
            
            results["windows"].append({
                "window_start": i,
                "window_end": i + window_size,
                "anomaly_indices": anomaly_indices.tolist(),
                "num_anomalies": len(anomaly_indices),
                "metadata": meta
            })
        
        return results


def detect_anomalies(
    df: pd.DataFrame,
    metrics: List[str],
    site_col: str = "site_id",
    time_col: str = "timestamp",
    method: str = "zscore",
    config: Optional[Dict] = None,
) -> pd.DataFrame:
    """
    Convenience function to detect anomalies.
    
    Args:
        df: Input DataFrame
        metrics: List of metric columns
        site_col: Site ID column name
        time_col: Timestamp column name
        method: Detection method
        config: Optional configuration
    
    Returns:
        DataFrame with anomaly columns
    
    Example:
        >>> df = load_data()
        >>> result_df = detect_anomalies(
        ...     df,
        ...     metrics=['rsrp', 'sinr', 'throughput_mbps'],
        ...     method='zscore',
        ...     config={'threshold': 3.0}
        ... )
    """
    service = NetworkKPIAnomalyDetectionService()
    return service.detect_anomalies(
        df=df,
        metrics=metrics,
        site_col=site_col,
        time_col=time_col,
        method=method,
        config=config
    )


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    from data.cell_site_kpi_generator import generate_synthetic_kpi_data
    
    # Generate sample data
    df = generate_synthetic_kpi_data(num_sites=2, num_hours=12, save_files=False)
    
    # Configure service
    service = NetworkKPIAnomalyDetectionService()
    service.configure_metric("rsrp", method="zscore", threshold=2.5)
    service.configure_metric("throughput_mbps", method="mad", threshold=3.0)
    service.configure_metric("latency_ms", method="isolation_forest", contamination=0.1)
    
    # Detect anomalies
    result_df = service.detect_anomalies(
        df,
        metrics=["rsrp", "throughput_mbps", "latency_ms"],
        method="zscore"
    )
    
    print("\nAnomalies detected:")
    print(result_df[result_df["is_anomaly"]][
        ["timestamp", "site_id", "rsrp", "throughput_mbps", "latency_ms", "is_anomaly"]
    ].head(10))
