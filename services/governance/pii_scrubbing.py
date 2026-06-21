"""
PII Scrubbing: Remove or mask personally identifiable information in logs.
Even though KPIs don't contain PII, metadata and logs might.
"""
import re
from typing import Dict, Any, Optional
import json


class PIIScrubber:
    """Scrub PII from logs and data"""
    
    # Patterns for common PII
    PATTERNS = {
        'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        'api_key': re.compile(r'(?:api[_-]?key|apikey|api_secret|secret)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})'),
        'password': re.compile(r'(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)'),
    }
    
    SENSITIVE_KEYS = {
        'password', 'api_key', 'secret', 'token', 'authorization',
        'credentials', 'api_secret', 'private_key', 'access_token'
    }
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email: name@example.com -> n***@example.com"""
        parts = email.split('@')
        if len(parts) == 2:
            local = parts[0]
            domain = parts[1]
            if len(local) > 2:
                masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
            else:
                masked_local = '*' * len(local)
            return f"{masked_local}@{domain}"
        return email
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone: 123-456-7890 -> 123-456-****"""
        return re.sub(r'\d{4}$', '****', phone)
    
    @staticmethod
    def mask_credit_card(card: str) -> str:
        """Mask credit card: show last 4 digits"""
        digits = re.sub(r'\D', '', card)
        if len(digits) >= 4:
            return '*' * (len(digits) - 4) + digits[-4:]
        return '*' * len(digits)
    
    @staticmethod
    def mask_generic(value: str, keep_chars: int = 3) -> str:
        """Generic masking: keep first and last few chars"""
        if len(value) <= keep_chars * 2:
            return '*' * len(value)
        return value[:keep_chars] + '*' * (len(value) - keep_chars * 2) + value[-keep_chars:]
    
    @classmethod
    def scrub_text(cls, text: str) -> str:
        """Scrub PII from text"""
        if not isinstance(text, str):
            return text
        
        # Scrub emails
        text = cls.PATTERNS['email'].sub(cls.mask_email, text)
        
        # Scrub phone numbers
        text = cls.PATTERNS['phone'].sub(cls.mask_phone, text)
        
        # Scrub credit cards
        text = cls.PATTERNS['credit_card'].sub(cls.mask_credit_card, text)
        
        # Scrub SSNs
        text = cls.PATTERNS['ssn'].sub('***-**-****', text)
        
        # Scrub API keys
        text = cls.PATTERNS['api_key'].sub(lambda m: m.group(0)[:20] + '...', text)
        
        # Scrub passwords
        text = cls.PATTERNS['password'].sub(lambda m: m.group(0).split('=')[0] + '=****', text)
        
        return text
    
    @classmethod
    def scrub_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub PII from dictionary"""
        if not isinstance(data, dict):
            return data
        
        scrubbed = {}
        
        for key, value in data.items():
            # Check if key is sensitive
            if any(sensitive in key.lower() for sensitive in cls.SENSITIVE_KEYS):
                scrubbed[key] = cls.mask_generic(str(value))
            elif isinstance(value, dict):
                scrubbed[key] = cls.scrub_dict(value)
            elif isinstance(value, str):
                scrubbed[key] = cls.scrub_text(value)
            elif isinstance(value, list):
                scrubbed[key] = [
                    cls.scrub_dict(item) if isinstance(item, dict)
                    else cls.scrub_text(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                scrubbed[key] = value
        
        return scrubbed
    
    @classmethod
    def scrub_json(cls, json_str: str) -> str:
        """Scrub PII from JSON string"""
        try:
            data = json.loads(json_str)
            scrubbed_data = cls.scrub_dict(data)
            return json.dumps(scrubbed_data)
        except json.JSONDecodeError:
            # If not valid JSON, treat as text
            return cls.scrub_text(json_str)
    
    @classmethod
    def scrub_log_line(cls, log_line: str) -> str:
        """Scrub a log line (typically JSON)"""
        return cls.scrub_json(log_line)


# Example usage function
def scrub_before_logging(message: str, data: Optional[Dict] = None) -> tuple[str, Optional[Dict]]:
    """
    Scrub message and data before logging.
    Usage:
        msg, data = scrub_before_logging("Processing...", {'email': 'user@example.com'})
        logger.info(msg, **data)
    """
    scrubbed_message = PIIScrubber.scrub_text(message)
    scrubbed_data = PIIScrubber.scrub_dict(data) if data else None
    return scrubbed_message, scrubbed_data
