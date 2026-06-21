"""
Audit Logging: Track who did what and when.
Provides immutable audit trail for governance and compliance.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json


class AuditAction(Enum):
    """Audit action types"""
    # Detection actions
    RUN_ANOMALY_DETECTION = "run_anomaly_detection"
    UPLOAD_DATA = "upload_data"
    
    # GenAI actions
    GENERATE_EXPLANATION = "generate_explanation"
    CHANGE_LLM_PROVIDER = "change_llm_provider"
    
    # Data access
    VIEW_METRICS = "view_metrics"
    VIEW_RESULTS = "view_results"
    DOWNLOAD_REPORT = "download_report"
    
    # Governance
    CREATE_USER = "create_user"
    CHANGE_USER_ROLE = "change_user_role"
    CREATE_API_KEY = "create_api_key"
    REVOKE_API_KEY = "revoke_api_key"
    
    # System
    SYSTEM_ERROR = "system_error"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class AuditLog:
    """Immutable audit log entry"""
    audit_id: str
    timestamp: str
    actor: str  # username or service
    action: str  # AuditAction value
    resource_type: str  # e.g., "anomaly_detection", "user", "api_key"
    resource_id: str  # e.g., site_id, user_id, key_id
    status: str  # "success" or "failure"
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}
    
    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Centralized audit logging"""
    
    def __init__(self, log_file: str = "logs/audit.jsonl"):
        self.log_file = log_file
        self.in_memory_logs: List[AuditLog] = []
        self._audit_id_counter = 0
    
    def _generate_audit_id(self) -> str:
        """Generate unique audit ID"""
        self._audit_id_counter += 1
        return f"audit_{datetime.utcnow().strftime('%Y%m%d')}_{self._audit_id_counter:06d}"
    
    def log_action(
        self,
        actor: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log audit action"""
        audit_log = AuditLog(
            audit_id=self._generate_audit_id(),
            timestamp=datetime.utcnow().isoformat() + "Z",
            actor=actor,
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            details=details,
            ip_address=ip_address
        )
        
        self.in_memory_logs.append(audit_log)
        
        # Write to file (append mode)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(audit_log.to_json() + '\n')
        except Exception as e:
            print(f"Warning: Could not write audit log to file: {e}")
        
        return audit_log
    
    # Convenience logging methods
    
    def log_detection_run(
        self,
        actor: str,
        site_id: str,
        metrics_count: int,
        anomalies_detected: int,
        status: str = "success",
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log anomaly detection execution"""
        return self.log_action(
            actor=actor,
            action=AuditAction.RUN_ANOMALY_DETECTION,
            resource_type="anomaly_detection",
            resource_id=site_id,
            status=status,
            details={
                'metrics_count': metrics_count,
                'anomalies_detected': anomalies_detected
            },
            ip_address=ip_address
        )
    
    def log_explanation_generated(
        self,
        actor: str,
        anomaly_id: str,
        llm_provider: str,
        status: str = "success",
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log LLM explanation generation"""
        return self.log_action(
            actor=actor,
            action=AuditAction.GENERATE_EXPLANATION,
            resource_type="explanation",
            resource_id=anomaly_id,
            status=status,
            details={'llm_provider': llm_provider},
            ip_address=ip_address
        )
    
    def log_data_upload(
        self,
        actor: str,
        file_name: str,
        row_count: int,
        status: str = "success",
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log data upload"""
        return self.log_action(
            actor=actor,
            action=AuditAction.UPLOAD_DATA,
            resource_type="data",
            resource_id=file_name,
            status=status,
            details={'row_count': row_count},
            ip_address=ip_address
        )
    
    def log_user_created(
        self,
        actor: str,
        new_user_id: str,
        role: str,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log user creation"""
        return self.log_action(
            actor=actor,
            action=AuditAction.CREATE_USER,
            resource_type="user",
            resource_id=new_user_id,
            details={'role': role},
            ip_address=ip_address
        )
    
    def log_unauthorized_access(
        self,
        actor: str,
        resource_type: str,
        resource_id: str,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log unauthorized access attempt"""
        return self.log_action(
            actor=actor,
            action=AuditAction.UNAUTHORIZED_ACCESS,
            resource_type=resource_type,
            resource_id=resource_id,
            status="failure",
            ip_address=ip_address
        )
    
    def get_audit_trail(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query audit logs with filters"""
        logs = self.in_memory_logs
        
        if actor:
            logs = [l for l in logs if l.actor == actor]
        if action:
            logs = [l for l in logs if l.action == action]
        if resource_type:
            logs = [l for l in logs if l.resource_type == resource_type]
        
        # Return most recent first
        logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)
        
        return [l.to_dict() for l in logs[:limit]]
    
    def get_user_actions(self, actor: str, limit: int = 50) -> List[Dict]:
        """Get all actions performed by a user"""
        return self.get_audit_trail(actor=actor, limit=limit)
    
    def get_resource_access_history(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get access history for a resource"""
        logs = [
            l for l in self.in_memory_logs
            if l.resource_type == resource_type and l.resource_id == resource_id
        ]
        logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)
        return [l.to_dict() for l in logs[:limit]]


# Global audit logger
_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger"""
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger()
    return _global_audit_logger
