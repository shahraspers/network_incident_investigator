"""
LLM Quality Evaluation.
Tracks LLM consistency, hallucination rate, and response quality.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class HallucinationIndicator(Enum):
    """Indicators of LLM hallucinations"""
    CONFLICTING_STATEMENTS = "conflicting_statements"
    UNVERIFIABLE_CLAIMS = "unverifiable_claims"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"
    UNSUPPORTED_RECOMMENDATIONS = "unsupported_recommendations"
    FABRICATED_METRICS = "fabricated_metrics"


@dataclass
class LLMExplanation:
    """Structure for LLM explanation evaluation"""
    explanation_id: str
    timestamp: str
    provider: str
    model: str
    response_time_ms: float
    token_count: int
    has_recommendations: bool
    likely_causes_count: int
    confidence_score: float
    
    def to_dict(self) -> Dict:
        return {
            'explanation_id': self.explanation_id,
            'timestamp': self.timestamp,
            'provider': self.provider,
            'model': self.model,
            'response_time_ms': round(self.response_time_ms, 2),
            'token_count': self.token_count,
            'has_recommendations': self.has_recommendations,
            'likely_causes_count': self.likely_causes_count,
            'confidence_score': round(self.confidence_score, 4)
        }


@dataclass
class LLMHallucinationAnalysis:
    """Analysis of LLM hallucinations"""
    hallucination_detected: bool
    indicators: List[str]
    severity: str  # "low", "medium", "high"
    confidence: float
    recommendation: str
    
    def to_dict(self) -> Dict:
        return {
            'hallucination_detected': self.hallucination_detected,
            'indicators': self.indicators,
            'severity': self.severity,
            'confidence': round(self.confidence, 4),
            'recommendation': self.recommendation
        }


class LLMQualityEvaluator:
    """Evaluate LLM quality, consistency, and hallucination rate"""
    
    def __init__(self):
        self.explanations: List[LLMExplanation] = []
        self.consistency_scores: List[float] = []
        self.hallucination_flags: List[LLMHallucinationAnalysis] = []
    
    def track_explanation(
        self,
        explanation_id: str,
        provider: str,
        model: str,
        response_time_ms: float,
        token_count: int,
        explanation_data: Dict
    ) -> LLMExplanation:
        """Track LLM explanation for quality evaluation"""
        
        explanation = LLMExplanation(
            explanation_id=explanation_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            provider=provider,
            model=model,
            response_time_ms=response_time_ms,
            token_count=token_count,
            has_recommendations=len(explanation_data.get('recommended_actions', [])) > 0,
            likely_causes_count=len(explanation_data.get('likely_causes', [])),
            confidence_score=float(explanation_data.get('confidence', 0.5))
        )
        
        self.explanations.append(explanation)
        return explanation
    
    def detect_hallucinations(
        self,
        explanation_data: Dict,
        context_data: Dict
    ) -> LLMHallucinationAnalysis:
        """
        Detect potential hallucinations in LLM explanation.
        Checks for:
        - Contradictions in causes
        - Unsupported claims (no context)
        - Logical inconsistencies
        - Fabricated metrics
        """
        indicators: List[str] = []
        
        # Check for contradictory causes
        causes = explanation_data.get('likely_causes', [])
        if len(causes) > 1:
            # Simple check: if causes contradict each other's keywords
            cause_text = ' '.join(causes).lower()
            if 'increase' in cause_text and 'decrease' in cause_text:
                indicators.append(HallucinationIndicator.CONFLICTING_STATEMENTS.value)
        
        # Check if recommendations are supported by context
        recommendations = explanation_data.get('recommended_actions', [])
        if recommendations:
            context_summary = context_data.get('incident_indicators', [])
            if len(recommendations) > len(context_summary):
                indicators.append(HallucinationIndicator.UNSUPPORTED_RECOMMENDATIONS.value)
        
        # Check for fabricated metrics (metrics not in context)
        available_metrics = set(context_data.get('metrics', {}).keys())
        summary = explanation_data.get('summary', '').lower()
        if summary and not available_metrics:
            indicators.append(HallucinationIndicator.FABRICATED_METRICS.value)
        
        # Determine severity
        if len(indicators) == 0:
            severity = "low"
            confidence = 0.1
        elif len(indicators) == 1:
            severity = "medium"
            confidence = 0.5
        else:
            severity = "high"
            confidence = 0.9
        
        hallucination_analysis = LLMHallucinationAnalysis(
            hallucination_detected=len(indicators) > 0,
            indicators=indicators,
            severity=severity,
            confidence=confidence,
            recommendation=self._get_hallucination_recommendation(severity, indicators)
        )
        
        self.hallucination_flags.append(hallucination_analysis)
        return hallucination_analysis
    
    @staticmethod
    def _get_hallucination_recommendation(severity: str, indicators: List[str]) -> str:
        """Get recommendation based on hallucination analysis"""
        if severity == "low":
            return "Monitor output; likely acceptable."
        elif severity == "medium":
            return "Review recommendations with subject matter experts."
        else:
            return "Flag for manual review; do not trust recommendations."
    
    def check_consistency(
        self,
        explanations: List[Dict]
    ) -> float:
        """
        Check consistency across multiple explanations for same anomaly.
        Higher score = more consistent.
        """
        if len(explanations) < 2:
            return 1.0
        
        # Compare causes across explanations
        all_causes = [e.get('likely_causes', []) for e in explanations]
        
        # Simple consistency: overlap in top causes
        if all_causes[0]:
            base_causes = set(all_causes[0][:2])  # Top 2 causes
            overlaps = sum(
                1 for causes in all_causes[1:]
                if any(c in base_causes for c in causes[:2])
            )
            consistency_score = overlaps / (len(all_causes) - 1) if len(all_causes) > 1 else 1.0
        else:
            consistency_score = 0.0
        
        self.consistency_scores.append(consistency_score)
        return consistency_score
    
    def get_metrics(self) -> Dict:
        """Get overall LLM quality metrics"""
        if not self.explanations:
            return {}
        
        total_explanations = len(self.explanations)
        avg_response_time = np.mean([e.response_time_ms for e in self.explanations])
        avg_token_count = np.mean([e.token_count for e in self.explanations])
        avg_confidence = np.mean([e.confidence_score for e in self.explanations])
        
        hallucination_rate = len([h for h in self.hallucination_flags if h.hallucination_detected]) / total_explanations if total_explanations > 0 else 0.0
        avg_consistency = np.mean(self.consistency_scores) if self.consistency_scores else 1.0
        
        return {
            'total_explanations': total_explanations,
            'avg_response_time_ms': round(avg_response_time, 2),
            'avg_token_count': round(avg_token_count),
            'avg_confidence_score': round(avg_confidence, 4),
            'hallucination_rate': round(hallucination_rate, 4),
            'avg_consistency_score': round(avg_consistency, 4),
            'explanations_with_recommendations': sum(1 for e in self.explanations if e.has_recommendations),
            'avg_causes_per_explanation': round(np.mean([e.likely_causes_count for e in self.explanations]), 2)
        }
    
    def get_provider_comparison(self) -> Dict[str, Dict]:
        """Compare quality metrics across providers"""
        providers = {}
        
        for exp in self.explanations:
            if exp.provider not in providers:
                providers[exp.provider] = []
            providers[exp.provider].append(exp)
        
        comparison = {}
        for provider, exps in providers.items():
            comparison[provider] = {
                'count': len(exps),
                'avg_response_time_ms': round(np.mean([e.response_time_ms for e in exps]), 2),
                'avg_token_count': round(np.mean([e.token_count for e in exps])),
                'avg_confidence': round(np.mean([e.confidence_score for e in exps]), 4)
            }
        
        return comparison
