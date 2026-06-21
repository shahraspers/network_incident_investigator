"""
Evaluation Layer: Anomaly Detection Quality Metrics.
Tracks precision, recall, false positives/negatives.
Designed for validation against labeled datasets.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AnomalyMetrics:
    """Anomaly detection evaluation metrics"""
    timestamp: str
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1_score: float
    specificity: float
    accuracy: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'true_positives': self.true_positives,
            'false_positives': self.false_positives,
            'false_negatives': self.false_negatives,
            'true_negatives': self.true_negatives,
            'precision': round(self.precision, 4),
            'recall': round(self.recall, 4),
            'f1_score': round(self.f1_score, 4),
            'specificity': round(self.specificity, 4),
            'accuracy': round(self.accuracy, 4)
        }


class AnomalyQualityEvaluator:
    """Evaluate anomaly detection quality against ground truth"""
    
    def __init__(self):
        self.history: List[AnomalyMetrics] = []
    
    @staticmethod
    def calculate_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> AnomalyMetrics:
        """
        Calculate anomaly detection metrics.
        
        Args:
            y_true: Ground truth labels (1 = anomaly, 0 = normal)
            y_pred: Predicted labels (1 = anomaly, 0 = normal)
        
        Returns:
            AnomalyMetrics with precision, recall, F1, etc.
        """
        assert len(y_true) == len(y_pred), "Arrays must have same length"
        
        # Confusion matrix elements
        tp = np.sum((y_true == 1) & (y_pred == 1))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        fn = np.sum((y_true == 1) & (y_pred == 0))
        tn = np.sum((y_true == 0) & (y_pred == 0))
        
        # Calculate metrics with safe division
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        accuracy = (tp + tn) / len(y_true)
        
        return AnomalyMetrics(
            timestamp=datetime.utcnow().isoformat() + "Z",
            true_positives=int(tp),
            false_positives=int(fp),
            false_negatives=int(fn),
            true_negatives=int(tn),
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            specificity=float(specificity),
            accuracy=float(accuracy)
        )
    
    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> AnomalyMetrics:
        """Evaluate and store metrics"""
        metrics = self.calculate_metrics(y_true, y_pred)
        self.history.append(metrics)
        return metrics
    
    def get_history(self) -> List[Dict]:
        """Get metrics history"""
        return [m.to_dict() for m in self.history]
    
    def get_average_metrics(self) -> Optional[Dict]:
        """Get average metrics across all evaluations"""
        if not self.history:
            return None
        
        return {
            'avg_precision': round(np.mean([m.precision for m in self.history]), 4),
            'avg_recall': round(np.mean([m.recall for m in self.history]), 4),
            'avg_f1_score': round(np.mean([m.f1_score for m in self.history]), 4),
            'avg_accuracy': round(np.mean([m.accuracy for m in self.history]), 4),
            'evaluations_count': len(self.history)
        }


@dataclass
class FalsePositiveAnalysis:
    """Analysis of false positives"""
    count: int
    rate: float
    common_metrics: List[str]
    common_sites: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'count': self.count,
            'rate': round(self.rate, 4),
            'common_metrics': self.common_metrics,
            'common_sites': self.common_sites
        }


def analyze_false_positives(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    df: pd.DataFrame,
    metric_col: str = 'metric',
    site_col: str = 'site_id'
) -> FalsePositiveAnalysis:
    """
    Analyze false positives in detection results.
    Helps identify systematic issues in anomaly detector.
    """
    # Find false positives
    fp_mask = (y_true == 0) & (y_pred == 1)
    fp_indices = np.where(fp_mask)[0]
    
    fp_count = len(fp_indices)
    fp_rate = fp_count / len(y_true) if len(y_true) > 0 else 0.0
    
    # Get common characteristics
    if len(fp_indices) > 0:
        fp_data = df.iloc[fp_indices]
        common_metrics = fp_data[metric_col].value_counts().head(5).index.tolist() if metric_col in df.columns else []
        common_sites = fp_data[site_col].value_counts().head(5).index.tolist() if site_col in df.columns else []
    else:
        common_metrics = []
        common_sites = []
    
    return FalsePositiveAnalysis(
        count=int(fp_count),
        rate=float(fp_rate),
        common_metrics=[str(m) for m in common_metrics],
        common_sites=[str(s) for s in common_sites]
    )
