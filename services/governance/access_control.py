"""
Governance: Role-Based Access Control (RBAC) and API Key Management.
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import secrets


class Role(Enum):
    """User roles"""
    VIEWER = "viewer"  # Read-only
    ANALYST = "analyst"  # Run detection, view explanations
    ADMIN = "admin"  # Full access
    API_SERVICE = "api_service"  # External integrations


class Permission(Enum):
    """Permissions"""
    VIEW_METRICS = "view_metrics"
    RUN_DETECTION = "run_detection"
    VIEW_EXPLANATIONS = "view_explanations"
    MANAGE_LLM_PROVIDERS = "manage_llm_providers"
    MANAGE_DATA_SOURCES = "manage_data_sources"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_ACCESS = "manage_access"
    MANAGE_CONFIG = "manage_config"


# Role-permission mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.VIEW_METRICS,
    },
    Role.ANALYST: {
        Permission.VIEW_METRICS,
        Permission.RUN_DETECTION,
        Permission.VIEW_EXPLANATIONS,
    },
    Role.ADMIN: {
        Permission.VIEW_METRICS,
        Permission.RUN_DETECTION,
        Permission.VIEW_EXPLANATIONS,
        Permission.MANAGE_LLM_PROVIDERS,
        Permission.MANAGE_DATA_SOURCES,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_ACCESS,
        Permission.MANAGE_CONFIG,
    },
    Role.API_SERVICE: {
        Permission.RUN_DETECTION,
        Permission.VIEW_EXPLANATIONS,
    }
}


@dataclass
class User:
    """User with role and permissions"""
    user_id: str
    username: str
    role: Role
    created_at: str
    last_login: Optional[str] = None
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission"""
        return permission in ROLE_PERMISSIONS.get(self.role, set())
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'role': self.role.value,
            'created_at': self.created_at,
            'last_login': self.last_login
        }


@dataclass
class APIKey:
    """API key for service-to-service authentication"""
    key_id: str
    service_name: str
    role: Role
    key_hash: str  # SHA256 hash of actual key
    created_at: str
    last_used: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict:
        return {
            'key_id': self.key_id,
            'service_name': self.service_name,
            'role': self.role.value,
            'created_at': self.created_at,
            'last_used': self.last_used,
            'is_active': self.is_active
        }


class AccessController:
    """Manage RBAC and API keys"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self._init_default_users()
    
    def _init_default_users(self) -> None:
        """Initialize default admin user"""
        admin_user = User(
            user_id="admin_001",
            username="admin",
            role=Role.ADMIN,
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        self.users["admin"] = admin_user
    
    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash API key"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate random API key (32 bytes = 256 bits)"""
        return secrets.token_urlsafe(32)
    
    def create_user(
        self,
        username: str,
        role: Role,
        user_id: Optional[str] = None
    ) -> User:
        """Create new user"""
        if username in self.users:
            raise ValueError(f"User {username} already exists")
        
        user_id = user_id or f"user_{len(self.users):04d}"
        
        user = User(
            user_id=user_id,
            username=username,
            role=role,
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        
        self.users[username] = user
        return user
    
    def get_user(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.users.get(username)
    
    def create_api_key(
        self,
        service_name: str,
        role: Role
    ) -> tuple[str, APIKey]:
        """
        Create API key for service.
        Returns: (plaintext_key, api_key_object)
        Store plaintext_key on client, store api_key_object for validation
        """
        plaintext_key = self.generate_api_key()
        key_hash = self._hash_key(plaintext_key)
        key_id = f"key_{len(self.api_keys):04d}"
        
        api_key = APIKey(
            key_id=key_id,
            service_name=service_name,
            role=role,
            key_hash=key_hash,
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        
        self.api_keys[key_id] = api_key
        return plaintext_key, api_key
    
    def verify_api_key(self, plaintext_key: str) -> Optional[APIKey]:
        """Verify API key and return associated API key object"""
        key_hash = self._hash_key(plaintext_key)
        
        for api_key in self.api_keys.values():
            if api_key.key_hash == key_hash and api_key.is_active:
                # Update last_used
                api_key.last_used = datetime.utcnow().isoformat() + "Z"
                return api_key
        
        return None
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key"""
        if key_id in self.api_keys:
            self.api_keys[key_id].is_active = False
            return True
        return False
    
    def list_api_keys(self, active_only: bool = True) -> List[Dict]:
        """List API keys"""
        keys = [
            k.to_dict() for k in self.api_keys.values()
            if not active_only or k.is_active
        ]
        return keys
    
    def list_users(self) -> List[Dict]:
        """List all users"""
        return [u.to_dict() for u in self.users.values()]
    
    def check_permission(self, username: str, permission: Permission) -> bool:
        """Check if user has permission"""
        user = self.get_user(username)
        if not user:
            return False
        return user.has_permission(permission)


# Global access controller
_global_access_controller: Optional[AccessController] = None


def get_access_controller() -> AccessController:
    """Get or create global access controller"""
    global _global_access_controller
    if _global_access_controller is None:
        _global_access_controller = AccessController()
    return _global_access_controller
