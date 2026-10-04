"""
SkilTrix Universal Security Firewall - Audit Logging Subsystem
Provides secure, structured audit logging of all security policy violations
without leaking sensitive server paths, credentials, or internal details.
"""

import re
import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from collections import deque
import threading

logger = logging.getLogger("skiltrix.security.audit")

# Redaction patterns for secrets and sensitive host info
SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(password|secret|token|key|api_key)\s*[:=]\s*[\'"][^\'"]+[\'"]'), r'\1="[REDACTED]"'),
    (re.compile(r'[a-zA-Z]:\\[a-zA-Z0-9_.\-\\]+'), r'[HOST_PATH]'),
    (re.compile(r'/(?:home|etc|var|usr|root)/[a-zA-Z0-9_.\-/]+'), r'[HOST_PATH]'),
]


def sanitize_audit_text(text: str) -> str:
    """Sanitizes messages and logs to ensure no host paths or secrets are leaked."""
    if not text:
        return ""
    sanitized = str(text)
    for pattern, repl in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(repl, sanitized)
    return sanitized


@dataclass
class SecurityViolationRecord:
    violation_id: str
    timestamp: str
    user_id: Optional[str]
    project_id: Optional[str]
    entry_point: str
    language: str
    rule_triggered: str
    message: str
    execution_status: str = "blocked"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SecurityAuditLogger:
    """
    Thread-safe audit logger for security policy violations.
    Stores structured audit events and records them to standard logging.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._buffer = deque(maxlen=2000)
                cls._instance._buffer_lock = threading.Lock()
            return cls._instance

    def record_violation(
        self,
        entry_point: str,
        rule_triggered: str,
        message: str,
        language: str = "unknown",
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> SecurityViolationRecord:
        safe_msg = sanitize_audit_text(message)
        clean_details = {}
        if details:
            for k, v in details.items():
                if isinstance(v, str):
                    clean_details[k] = sanitize_audit_text(v)
                else:
                    clean_details[k] = v

        record = SecurityViolationRecord(
            violation_id=f"sec_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
            project_id=project_id,
            entry_point=entry_point,
            language=language,
            rule_triggered=rule_triggered,
            message=safe_msg,
            execution_status="blocked",
            details=clean_details,
        )

        with self._buffer_lock:
            self._buffer.append(record)

        logger.warning(
            "SECURITY VIOLATION [%s] rule=%s user=%s project=%s lang=%s: %s",
            record.violation_id,
            rule_triggered,
            user_id,
            project_id,
            language,
            safe_msg,
        )

        return record

    def get_recent_violations(
        self,
        limit: int = 50,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._buffer_lock:
            records = list(self._buffer)

        if user_id:
            records = [r for r in records if r.user_id == user_id]
        if project_id:
            records = [r for r in records if r.project_id == project_id]

        return [r.to_dict() for r in reversed(records[-limit:])]

    def clear(self) -> None:
        with self._buffer_lock:
            self._buffer.clear()


# Global singleton helper
audit_logger = SecurityAuditLogger()

