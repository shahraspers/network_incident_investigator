"""
Anomaly context builder for GenAI reasoning.
Constructs rich context from detected anomalies for LLM analysis.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class AnomalyContextBuilder:
    """Build structured context for anomaly explanation"""
    
    def __init__(
        self,
        history_window: int = 20,
        correlation_threshold: float = 0.6,
        recent_history_size: int = 10
    ):
        """
        Initialize context builder.
        
        Args:
            history_window: Number of historical records to include in context
            correlation_threshold: Threshold for identifying correlated metrics
            recent_history_size: Number of recent data points for trend analysis
        """
        self.history_window = history_window
        self.correlation_threshold = correlation_threshold
        self.recent_history_size = recent_history_size
    
    def build_anomaly_context(
        self,
        df: pd.DataFrame,
        anomaly_row: pd.Series,
        anomaly_scores: Optional[pd.Series] = None,
        metric_columns: Optional[List[str]] = None,
        site_col: str = "site_id",
        time_col: str = "timestamp"
    ) -> Dict:
        """
        Build comprehensive anomaly context for LLM reasoning.
        
        Args:
            df: Full DataFrame with all metrics and history
            anomaly_row: The row with detected anomalies (pd.Series)
            anomaly_scores: Anomaly scores for each metric (optional)
            metric_columns: List of metric column names
            site_col: Name of site_id column
            time_col: Name of timestamp column
        
        Returns:
            Structured context dict:
            {
                "site_id": str,
                "timestamp": str,
                "anomalies": {
                    metric_name: {
                        "is_anomaly": bool,
                        "value": float,
                        "score": float,
                        "change_from_avg": float,
                        "change_from_recent": float
                    }
                },
                "metrics": {
                    metric_name: {
                        "value": float,
                        "min": float,
                        "max": float,
                        "avg": float,
                        "std": float,
                        "unit": str
                    }
                },
                "history_summary": {
                    "recent_trend": str,
                    "volatility": float,
                    "baseline_metrics": dict
                },
                "correlated_metrics": {
                    metric_name: {
                        "correlation": float,
                        "is_anomaly": bool,
                        "value": float
                    }
                },
                "incident_indicators": list[str]
            }
        """
        # Extract basic info
        site_id = str(anomaly_row.get(site_col, "Unknown"))
        timestamp = str(anomaly_row.get(time_col, "Unknown"))
        
        # Determine metric columns if not provided
        if metric_columns is None:
            exclude_cols = {site_col, time_col, "is_anomaly", "anomaly_score"}
            metric_columns = [
                col for col in df.columns 
                if col not in exclude_cols and df[col].dtype in [np.float64, np.int64]
            ]
        
        # Build anomalies section
        anomalies = self._build_anomalies_section(
            anomaly_row, anomaly_scores, metric_columns, df
        )
        
        # Build metrics section
        metrics = self._build_metrics_section(
            anomaly_row, metric_columns, df, site_id
        )
        
        # Build history summary
        history_summary = self._build_history_summary(
            df, site_id, metric_columns, time_col, site_col
        )
        
        # Find correlated metrics
        correlated_metrics = self._find_correlated_metrics(
            df, anomaly_row, metric_columns, site_id, site_col
        )
        
        # Detect incident indicators
        incident_indicators = self._detect_incident_indicators(
            anomalies, correlated_metrics
        )
        
        return {
            "site_id": site_id,
            "timestamp": timestamp,
            "anomalies": anomalies,
            "metrics": metrics,
            "history_summary": history_summary,
            "correlated_metrics": correlated_metrics,
            "incident_indicators": incident_indicators
        }
    
    def _build_anomalies_section(
        self,
        anomaly_row: pd.Series,
        anomaly_scores: Optional[pd.Series],
        metric_columns: List[str],
        df: pd.DataFrame
    ) -> Dict:
        """Build anomalies section of context"""
        anomalies = {}
        
        for metric in metric_columns:
            value = float(anomaly_row.get(metric, np.nan))
            
            if pd.isna(value):
                continue
            
            # Check if is_anomaly column exists
            is_anomaly = anomaly_row.get("is_anomaly", False)
            if isinstance(is_anomaly, pd.Series):
                is_anomaly = is_anomaly.get(metric, False)
            
            # Get anomaly score
            score = 0.0
            if anomaly_scores is not None:
                score = float(anomaly_scores.get(metric, 0.0))
            elif f"{metric}_score" in anomaly_row:
                score = float(anomaly_row.get(f"{metric}_score", 0.0))
            
            # Calculate deviations
            col_data = df[metric].dropna()
            col_avg = float(col_data.mean()) if len(col_data) > 0 else value
            col_std = float(col_data.std()) if len(col_data) > 1 else 1.0
            
            change_from_avg = (value - col_avg) / col_std if col_std > 0 else 0.0
            
            # Recent change
            recent_data = col_data.tail(self.recent_history_size)
            recent_avg = float(recent_data.mean()) if len(recent_data) > 0 else value
            change_from_recent = ((value - recent_avg) / recent_avg * 100) if recent_avg != 0 else 0.0
            
            anomalies[metric] = {
                "is_anomaly": bool(is_anomaly),
                "value": value,
                "score": float(score),
                "change_from_avg": float(change_from_avg),
                "change_from_recent_percent": float(change_from_recent)
            }
        
        return anomalies
    
    def _build_metrics_section(
        self,
        anomaly_row: pd.Series,
        metric_columns: List[str],
        df: pd.DataFrame,
        site_id: str
    ) -> Dict:
        """Build metrics section with statistics"""
        metrics = {}
        
        # Filter df for this site
        site_df = df[df.get("site_id") == site_id] if "site_id" in df.columns else df
        
        for metric in metric_columns:
            value = float(anomaly_row.get(metric, np.nan))
            
            if pd.isna(value):
                continue
            
            col_data = site_df[metric].dropna()
            
            metrics[metric] = {
                "value": value,
                "min": float(col_data.min()) if len(col_data) > 0 else value,
                "max": float(col_data.max()) if len(col_data) > 0 else value,
                "avg": float(col_data.mean()) if len(col_data) > 0 else value,
                "std": float(col_data.std()) if len(col_data) > 1 else 0.0,
                "p95": float(col_data.quantile(0.95)) if len(col_data) > 0 else value,
                "p05": float(col_data.quantile(0.05)) if len(col_data) > 0 else value
            }
        
        return metrics
    
    def _build_history_summary(
        self,
        df: pd.DataFrame,
        site_id: str,
        metric_columns: List[str],
        time_col: str = "timestamp",
        site_col: str = "site_id"
    ) -> Dict:
        """Build history summary for context"""
        
        # Filter for this site
        site_df = df[df[site_col] == site_id] if site_col in df.columns else df
        
        if len(site_df) == 0:
            return {
                "recent_trend": "insufficient_data",
                "volatility": 0.0,
                "baseline_metrics": {}
            }
        
        # Sort by time
        if time_col in site_df.columns:
            site_df = site_df.sort_values(time_col)
        
        # Calculate trend and volatility
        recent_data = site_df.tail(self.recent_history_size)
        baseline_data = site_df.tail(self.history_window)
        
        volatility = 0.0
        for metric in metric_columns:
            if metric in recent_data.columns:
                col_std = float(recent_data[metric].std())
                col_avg = float(recent_data[metric].mean())
                if col_avg != 0:
                    cv = col_std / col_avg  # Coefficient of variation
                    volatility = max(volatility, cv)
        
        # Determine trend
        recent_trend = self._determine_trend(recent_data, metric_columns)
        
        # Baseline metrics
        baseline_metrics = {}
        for metric in metric_columns:
            if metric in baseline_data.columns:
                baseline_metrics[metric] = {
                    "avg": float(baseline_data[metric].mean()),
                    "std": float(baseline_data[metric].std())
                }
        
        return {
            "recent_trend": recent_trend,
            "volatility": float(volatility),
            "baseline_metrics": baseline_metrics,
            "observation_count": len(site_df),
            "recent_sample_size": len(recent_data)
        }
    
    def _find_correlated_metrics(
        self,
        df: pd.DataFrame,
        anomaly_row: pd.Series,
        metric_columns: List[str],
        site_id: str,
        site_col: str = "site_id"
    ) -> Dict:
        """Identify metrics correlated with the anomaly"""
        correlated_metrics = {}
        
        # Filter for site
        site_df = df[df[site_col] == site_id] if site_col in df.columns else df
        
        # Find which metrics are anomalous
        anomalous_metrics = []
        for metric in metric_columns:
            is_anomaly = anomaly_row.get("is_anomaly")
            if isinstance(is_anomaly, (dict, pd.Series)):
                if is_anomaly.get(metric) or anomaly_row.get(f"{metric}_is_anomaly"):
                    anomalous_metrics.append(metric)
            elif is_anomaly and metric in anomaly_row.index:
                anomalous_metrics.append(metric)
        
        if not anomalous_metrics:
            return {}
        
        # Calculate correlations
        numeric_data = site_df[metric_columns].select_dtypes(include=[np.number])
        
        if len(numeric_data) < 2:
            return {}
        
        for metric1 in anomalous_metrics:
            if metric1 not in numeric_data.columns:
                continue
            
            for metric2 in metric_columns:
                if metric2 == metric1 or metric2 not in numeric_data.columns:
                    continue
                
                try:
                    correlation = float(
                        numeric_data[metric1].corr(numeric_data[metric2])
                    )
                    
                    # Only include strong correlations
                    if abs(correlation) >= self.correlation_threshold:
                        metric2_value = float(anomaly_row.get(metric2, np.nan))
                        correlated_metrics[metric2] = {
                            "correlation": correlation,
                            "is_anomaly": anomaly_row.get(f"{metric2}_is_anomaly", False),
                            "value": metric2_value
                        }
                except Exception:
                    continue
        
        return correlated_metrics
    
    def _determine_trend(
        self,
        recent_data: pd.DataFrame,
        metric_columns: List[str]
    ) -> str:
        """Determine overall trend in recent data"""
        if len(recent_data) < 2:
            return "insufficient_data"
        
        upward_count = 0
        downward_count = 0
        stable_count = 0
        
        for metric in metric_columns:
            if metric not in recent_data.columns:
                continue
            
            col = recent_data[metric].dropna()
            if len(col) < 2:
                stable_count += 1
                continue
            
            first_half_avg = float(col.iloc[:len(col)//2].mean())
            second_half_avg = float(col.iloc[len(col)//2:].mean())
            
            change_pct = ((second_half_avg - first_half_avg) / first_half_avg * 100) \
                if first_half_avg != 0 else 0
            
            if change_pct > 5:
                upward_count += 1
            elif change_pct < -5:
                downward_count += 1
            else:
                stable_count += 1
        
        total = upward_count + downward_count + stable_count
        if total == 0:
            return "no_data"
        
        if upward_count >= total * 0.6:
            return "upward"
        elif downward_count >= total * 0.6:
            return "downward"
        else:
            return "stable"
    
    def _detect_incident_indicators(
        self,
        anomalies: Dict,
        correlated_metrics: Dict
    ) -> List[str]:
        """Detect severity indicators based on anomaly patterns"""
        indicators = []
        
        # Check for multiple metric anomalies
        anomaly_count = sum(1 for a in anomalies.values() if a.get("is_anomaly"))
        
        if anomaly_count >= 3:
            indicators.append("multiple_metric_anomalies")
        
        # Check for correlated anomalies
        correlated_anomaly_count = sum(
            1 for m in correlated_metrics.values() if m.get("is_anomaly")
        )
        
        if correlated_anomaly_count >= 2:
            indicators.append("correlated_anomalies")
        
        # Check for extreme deviations
        for metric, data in anomalies.items():
            if abs(data.get("change_from_avg", 0)) > 3:
                indicators.append("extreme_deviation")
                break
        
        # Check for high anomaly scores
        max_score = max(
            (a.get("score", 0) for a in anomalies.values()),
            default=0
        )
        
        if max_score > 0.8:
            indicators.append("high_confidence_anomaly")
        
        return indicators


def build_anomaly_context(
    df: pd.DataFrame,
    anomaly_row: pd.Series,
    anomaly_scores: Optional[pd.Series] = None,
    metric_columns: Optional[List[str]] = None,
    site_col: str = "site_id",
    time_col: str = "timestamp",
    history_window: int = 20
) -> Dict:
    """
    Convenience function to build anomaly context.
    
    Args:
        df: Full DataFrame with metrics and history
        anomaly_row: Row with detected anomalies
        anomaly_scores: Optional anomaly scores per metric
        metric_columns: List of metric column names
        site_col: Site ID column name
        time_col: Timestamp column name
        history_window: Historical window size for trend analysis
    
    Returns:
        Structured anomaly context for LLM reasoning
    """
    builder = AnomalyContextBuilder(history_window=history_window)
    return builder.build_anomaly_context(
        df=df,
        anomaly_row=anomaly_row,
        anomaly_scores=anomaly_scores,
        metric_columns=metric_columns,
        site_col=site_col,
        time_col=time_col
    )


if __name__ == "__main__":
    # Example usage
    from data.synthetic_kpi_generator import NetworkKPIGenerator
    
    # Generate sample data
    generator = NetworkKPIGenerator(num_metrics=4, time_steps=100)
    df, anomalies = generator.generate_timeseries()
    
    # Create sample anomaly row
    anomaly_row = df.iloc[-1].copy()
    
    # Build context
    context = build_anomaly_context(df, anomaly_row)
    
    import json
    print(json.dumps(context, indent=2, default=str))
