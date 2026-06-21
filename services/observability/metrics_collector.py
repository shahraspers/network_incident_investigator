"""
Observability & Metrics Collection.
Tracks API latency, anomaly detection latency, LLM usage, errors, throughput.
"""
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


@dataclass
class LatencyMetric:
    """Latency measurement"""
    timestamp: str
    module: str
    operation: str
    latency_ms: float
    success: bool
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'module': self.module,
            'operation': self.operation,
            'latency_ms': round(self.latency_ms, 2),
            'success': self.success
        }


@dataclass
class TokenUsageMetric:
    """LLM token usage"""
    timestamp: str
    provider: str
    model: str
    tokens_used: int
    estimated_cost_usd: float
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'provider': self.provider,
            'model': self.model,
            'tokens_used': self.tokens_used,
            'estimated_cost_usd': round(self.estimated_cost_usd, 4)
        }


@dataclass
class ErrorMetric:
    """Error tracking"""
    timestamp: str
    module: str
    error_type: str
    error_message: str
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'module': self.module,
            'error_type': self.error_type,
            'error_message': self.error_message
        }


class MetricsCollector:
    """Centralized metrics collection for observability"""
    
    # Token pricing (per 1M tokens)
    TOKEN_PRICING = {
        'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50},
        'gpt-4': {'input': 3.00, 'output': 6.00},
        'ollama_local': {'input': 0.0, 'output': 0.0},  # Local, no cost
        'vertex_ai': {'input': 0.5, 'output': 1.5},
        'azure_openai': {'input': 0.5, 'output': 1.5}
    }
    
    def __init__(self):
        self.latencies: List[LatencyMetric] = []
        self.token_usage: List[TokenUsageMetric] = []
        self.errors: List[ErrorMetric] = []
        self.anomaly_counts: List[Dict] = []  # timestamp, site_id, count
        self.llm_calls: int = 0
        self.request_count: int = 0
    
    def record_latency(
        self,
        module: str,
        operation: str,
        latency_ms: float,
        success: bool = True
    ) -> None:
        """Record operation latency"""
        self.latencies.append(LatencyMetric(
            timestamp=datetime.utcnow().isoformat() + "Z",
            module=module,
            operation=operation,
            latency_ms=latency_ms,
            success=success
        ))
    
    def record_token_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> None:
        """Record LLM token usage"""
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost
        pricing = self.TOKEN_PRICING.get(model, {'input': 0.0, 'output': 0.0})
        cost = (
            (input_tokens / 1_000_000) * pricing['input'] +
            (output_tokens / 1_000_000) * pricing['output']
        )
        
        self.token_usage.append(TokenUsageMetric(
            timestamp=datetime.utcnow().isoformat() + "Z",
            provider=provider,
            model=model,
            tokens_used=total_tokens,
            estimated_cost_usd=cost
        ))
        
        self.llm_calls += 1
    
    def record_error(
        self,
        module: str,
        error_type: str,
        error_message: str
    ) -> None:
        """Record error"""
        self.errors.append(ErrorMetric(
            timestamp=datetime.utcnow().isoformat() + "Z",
            module=module,
            error_type=error_type,
            error_message=error_message
        ))
    
    def record_request(self) -> None:
        """Record API request"""
        self.request_count += 1
    
    def record_anomalies(
        self,
        count: int,
        site_id: Optional[str] = None
    ) -> None:
        """Record anomaly detection results"""
        self.anomaly_counts.append({
            'timestamp': datetime.utcnow().isoformat() + "Z",
            'site_id': site_id,
            'count': count
        })
    
    def get_latency_stats(
        self,
        module: Optional[str] = None,
        operation: Optional[str] = None,
        minutes: int = 60
    ) -> Dict:
        """Get latency statistics"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        metrics = [
            m for m in self.latencies
            if datetime.fromisoformat(m.timestamp.replace('Z', '+00:00')) > cutoff
        ]
        
        if module:
            metrics = [m for m in metrics if m.module == module]
        if operation:
            metrics = [m for m in metrics if m.operation == operation]
        
        if not metrics:
            return {'error': 'No metrics available'}
        
        latencies = [m.latency_ms for m in metrics]
        
        return {
            'count': len(metrics),
            'avg_ms': round(statistics.mean(latencies), 2),
            'median_ms': round(statistics.median(latencies), 2),
            'p95_ms': round(np.percentile(latencies, 95), 2) if len(latencies) > 0 else 0.0,
            'p99_ms': round(np.percentile(latencies, 99), 2) if len(latencies) > 0 else 0.0,
            'min_ms': round(min(latencies), 2),
            'max_ms': round(max(latencies), 2),
            'success_rate': round(sum(1 for m in metrics if m.success) / len(metrics), 4)
        }
    
    def get_token_usage_stats(
        self,
        minutes: int = 60
    ) -> Dict:
        """Get token usage and cost statistics"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        metrics = [
            m for m in self.token_usage
            if datetime.fromisoformat(m.timestamp.replace('Z', '+00:00')) > cutoff
        ]
        
        if not metrics:
            return {
                'total_tokens': 0,
                'total_cost_usd': 0.0,
                'calls': 0,
                'by_provider': {}
            }
        
        by_provider = defaultdict(lambda: {'tokens': 0, 'cost': 0.0, 'calls': 0})
        for m in metrics:
            by_provider[m.provider]['tokens'] += m.tokens_used
            by_provider[m.provider]['cost'] += m.estimated_cost_usd
            by_provider[m.provider]['calls'] += 1
        
        return {
            'total_tokens': sum(m.tokens_used for m in metrics),
            'total_cost_usd': round(sum(m.estimated_cost_usd for m in metrics), 4),
            'calls': len(metrics),
            'avg_tokens_per_call': round(sum(m.tokens_used for m in metrics) / len(metrics), 0),
            'by_provider': {
                provider: {
                    'tokens': data['tokens'],
                    'cost_usd': round(data['cost'], 4),
                    'calls': data['calls']
                }
                for provider, data in by_provider.items()
            }
        }
    
    def get_error_stats(
        self,
        minutes: int = 60
    ) -> Dict:
        """Get error statistics"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        metrics = [
            m for m in self.errors
            if datetime.fromisoformat(m.timestamp.replace('Z', '+00:00')) > cutoff
        ]
        
        if not metrics:
            return {'total_errors': 0, 'error_rate': 0.0, 'by_type': {}}
        
        by_type = defaultdict(int)
        for m in metrics:
            by_type[m.error_type] += 1
        
        error_rate = len(self.errors) / max(self.request_count, 1)
        
        return {
            'total_errors': len(metrics),
            'error_rate': round(error_rate, 4),
            'by_type': dict(by_type),
            'recent_errors': [m.to_dict() for m in metrics[-10:]]
        }
    
    def get_anomaly_stats(
        self,
        minutes: int = 60
    ) -> Dict:
        """Get anomaly detection statistics"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        metrics = [
            m for m in self.anomaly_counts
            if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) > cutoff
        ]
        
        if not metrics:
            return {'total_detections': 0, 'anomalies_detected': 0, 'avg_per_detection': 0.0}
        
        total_anomalies = sum(m['count'] for m in metrics)
        
        return {
            'total_detections': len(metrics),
            'anomalies_detected': total_anomalies,
            'avg_per_detection': round(total_anomalies / len(metrics), 2),
            'anomalies_per_hour': round(total_anomalies * 60 / minutes, 2)
        }
    
    def get_platform_metrics(self) -> Dict:
        """Get comprehensive platform metrics"""
        return {
            'timestamp': datetime.utcnow().isoformat() + "Z",
            'total_requests': self.request_count,
            'total_llm_calls': self.llm_calls,
            'total_errors': len(self.errors),
            'total_latency_measurements': len(self.latencies),
            'latency_stats': self.get_latency_stats(),
            'token_usage_stats': self.get_token_usage_stats(),
            'error_stats': self.get_error_stats(),
            'anomaly_stats': self.get_anomaly_stats()
        }


# Global metrics collector
_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


# Import numpy for percentile calculation
import numpy as np
