"""
Drift Detection: Monitor KPI distributions and anomaly frequency.
Uses Population Stability Index (PSI) and KL divergence.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from scipy.stats import entropy
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DriftAnalysis:
    """KPI drift analysis results"""
    timestamp: str
    metric: str
    site_id: Optional[str]
    psi_score: float
    drift_detected: bool
    severity: str  # "no_drift", "minor", "moderate", "severe"
    baseline_mean: float
    baseline_std: float
    current_mean: float
    current_std: float
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'metric': self.metric,
            'site_id': self.site_id,
            'psi_score': round(self.psi_score, 4),
            'drift_detected': self.drift_detected,
            'severity': self.severity,
            'baseline_mean': round(self.baseline_mean, 4),
            'baseline_std': round(self.baseline_std, 4),
            'current_mean': round(self.current_mean, 4),
            'current_std': round(self.current_std, 4)
        }


@dataclass
class AnomalyFrequencyDrift:
    """Anomaly frequency changes over time"""
    timestamp: str
    site_id: Optional[str]
    baseline_frequency: float
    current_frequency: float
    frequency_change_pct: float
    drift_detected: bool
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'site_id': self.site_id,
            'baseline_frequency': round(self.baseline_frequency, 4),
            'current_frequency': round(self.current_frequency, 4),
            'frequency_change_pct': round(self.frequency_change_pct, 2),
            'drift_detected': self.drift_detected
        }


class DriftDetector:
    """Detect data drift and anomaly frequency changes"""
    
    # PSI thresholds
    PSI_THRESHOLD_MINOR = 0.1
    PSI_THRESHOLD_MODERATE = 0.25
    PSI_THRESHOLD_SEVERE = 0.5
    
    # Anomaly frequency change threshold
    ANOMALY_FREQUENCY_THRESHOLD = 0.2  # 20% change
    
    def __init__(self, baseline_df: Optional[pd.DataFrame] = None):
        self.baseline_df = baseline_df
        self.drift_history: List[DriftAnalysis] = []
        self.anomaly_frequency_history: List[AnomalyFrequencyDrift] = []
    
    @staticmethod
    def calculate_psi(
        baseline_distribution: np.ndarray,
        current_distribution: np.ndarray,
        n_bins: int = 10
    ) -> float:
        """
        Calculate Population Stability Index (PSI).
        PSI measures how much a distribution has shifted.
        
        PSI > 0.5: significant drift
        PSI 0.25-0.5: moderate drift
        PSI 0.1-0.25: minor drift
        PSI < 0.1: no drift
        """
        # Create bins from baseline
        baseline_min = baseline_distribution.min()
        baseline_max = baseline_distribution.max()
        bins = np.linspace(baseline_min, baseline_max, n_bins + 1)
        
        # Calculate distributions
        baseline_counts, _ = np.histogram(baseline_distribution, bins=bins)
        current_counts, _ = np.histogram(current_distribution, bins=bins)
        
        # Normalize to get proportions
        baseline_prop = baseline_counts / baseline_counts.sum()
        current_prop = current_counts / current_counts.sum()
        
        # Avoid log(0)
        baseline_prop = np.where(baseline_prop > 0, baseline_prop, 1e-5)
        current_prop = np.where(current_prop > 0, current_prop, 1e-5)
        
        # Calculate PSI
        psi = np.sum(current_prop * np.log(current_prop / baseline_prop))
        
        return float(psi)
    
    @staticmethod
    def calculate_kl_divergence(
        p: np.ndarray,
        q: np.ndarray
    ) -> float:
        """Calculate KL divergence between two distributions"""
        p = p / p.sum()
        q = q / q.sum()
        
        # Handle zeros
        p = np.where(p > 0, p, 1e-10)
        q = np.where(q > 0, q, 1e-10)
        
        return float(entropy(p, q))
    
    def detect_kpi_drift(
        self,
        metric_name: str,
        current_values: np.ndarray,
        site_id: Optional[str] = None,
        baseline_values: Optional[np.ndarray] = None
    ) -> DriftAnalysis:
        """
        Detect drift in KPI metric.
        
        Args:
            metric_name: Name of metric (e.g., 'rsrp')
            current_values: Current metric values
            site_id: Site ID (optional)
            baseline_values: Baseline values (if None, uses initialization baseline)
        
        Returns:
            DriftAnalysis with PSI score and severity
        """
        # Use provided baseline or initialization baseline
        if baseline_values is None:
            if self.baseline_df is not None and metric_name in self.baseline_df.columns:
                baseline_values = self.baseline_df[metric_name].values
            else:
                # No baseline available
                return DriftAnalysis(
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    metric=metric_name,
                    site_id=site_id,
                    psi_score=0.0,
                    drift_detected=False,
                    severity="no_drift",
                    baseline_mean=0.0,
                    baseline_std=0.0,
                    current_mean=float(np.mean(current_values)),
                    current_std=float(np.std(current_values))
                )
        
        # Calculate PSI
        psi_score = self.calculate_psi(baseline_values, current_values)
        
        # Determine severity
        if psi_score < self.PSI_THRESHOLD_MINOR:
            severity = "no_drift"
            drift_detected = False
        elif psi_score < self.PSI_THRESHOLD_MODERATE:
            severity = "minor"
            drift_detected = True
        elif psi_score < self.PSI_THRESHOLD_SEVERE:
            severity = "moderate"
            drift_detected = True
        else:
            severity = "severe"
            drift_detected = True
        
        analysis = DriftAnalysis(
            timestamp=datetime.utcnow().isoformat() + "Z",
            metric=metric_name,
            site_id=site_id,
            psi_score=psi_score,
            drift_detected=drift_detected,
            severity=severity,
            baseline_mean=float(np.mean(baseline_values)),
            baseline_std=float(np.std(baseline_values)),
            current_mean=float(np.mean(current_values)),
            current_std=float(np.std(current_values))
        )
        
        self.drift_history.append(analysis)
        return analysis
    
    def detect_anomaly_frequency_drift(
        self,
        baseline_anomalies: int,
        baseline_total: int,
        current_anomalies: int,
        current_total: int,
        site_id: Optional[str] = None
    ) -> AnomalyFrequencyDrift:
        """
        Detect changes in anomaly frequency.
        If frequency increased significantly, detector may need recalibration.
        """
        baseline_freq = baseline_anomalies / baseline_total if baseline_total > 0 else 0.0
        current_freq = current_anomalies / current_total if current_total > 0 else 0.0
        
        frequency_change = abs(current_freq - baseline_freq) / (baseline_freq + 1e-10)
        drift_detected = frequency_change > self.ANOMALY_FREQUENCY_THRESHOLD
        
        analysis = AnomalyFrequencyDrift(
            timestamp=datetime.utcnow().isoformat() + "Z",
            site_id=site_id,
            baseline_frequency=baseline_freq,
            current_frequency=current_freq,
            frequency_change_pct=frequency_change * 100,
            drift_detected=drift_detected
        )
        
        self.anomaly_frequency_history.append(analysis)
        return analysis
    
    def get_drift_report(self) -> Dict:
        """Get comprehensive drift analysis report"""
        if not self.drift_history:
            return {'error': 'No drift analysis available'}
        
        drifted_metrics = [d for d in self.drift_history if d.drift_detected]
        severe_drifts = [d for d in self.drift_history if d.severity == "severe"]
        
        return {
            'total_analyses': len(self.drift_history),
            'metrics_with_drift': len(drifted_metrics),
            'severe_drifts': len(severe_drifts),
            'avg_psi_score': round(np.mean([d.psi_score for d in self.drift_history]), 4),
            'metrics_by_severity': {
                'no_drift': sum(1 for d in self.drift_history if d.severity == "no_drift"),
                'minor': sum(1 for d in self.drift_history if d.severity == "minor"),
                'moderate': sum(1 for d in self.drift_history if d.severity == "moderate"),
                'severe': sum(1 for d in self.drift_history if d.severity == "severe")
            },
            'severe_metrics': [d.metric for d in severe_drifts]
        }
    
    def get_anomaly_frequency_report(self) -> Dict:
        """Get anomaly frequency drift report"""
        if not self.anomaly_frequency_history:
            return {'error': 'No frequency analysis available'}
        
        drifted = [a for a in self.anomaly_frequency_history if a.drift_detected]
        
        return {
            'total_sites_analyzed': len(self.anomaly_frequency_history),
            'sites_with_frequency_drift': len(drifted),
            'avg_frequency_change_pct': round(np.mean([abs(a.frequency_change_pct) for a in self.anomaly_frequency_history]), 2),
            'sites_with_drift': [
                {'site_id': a.site_id, 'change_pct': round(a.frequency_change_pct, 2)}
                for a in drifted
            ]
        }
