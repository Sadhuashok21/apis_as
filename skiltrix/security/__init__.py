"""
SkilTrix Universal Security Firewall Engine
A centralized code security, sandbox isolation, and resource boundary enforcement system.
"""

from .policies import (
    ERROR_CODE_SECURITY_VIOLATION,
    RULE_DANGEROUS_FILESYSTEM,
    RULE_PATH_TRAVERSAL,
    RULE_UNAUTHORIZED_SUBPROCESS,
    RULE_NETWORK_VIOLATION,
    RULE_SQL_CONFINEMENT,
    RULE_TERMINAL_VIOLATION,
    RULE_HTML_SANDBOX_VIOLATION,
    RULE_ABAP_VIOLATION,
    RULE_RESOURCE_LIMIT,
    RULE_FAIL_CLOSED,
    RULE_REFLECTION_OBFUSCATION,
    SecurityPolicyViolation,
    make_security_error_response,
)
from .audit_log import SecurityAuditLogger, audit_logger
from .static_analyzer import StaticCodeAnalyzer
from .terminal_firewall import TerminalSecurityFirewall
from .sql_guard import SqlSecurityGuard
from .engine import UniversalSecurityEngine

__all__ = [
    "UniversalSecurityEngine",
    "SecurityAuditLogger",
    "audit_logger",
    "SecurityPolicyViolation",
    "make_security_error_response",
    "ERROR_CODE_SECURITY_VIOLATION",
    "RULE_DANGEROUS_FILESYSTEM",
    "RULE_PATH_TRAVERSAL",
    "RULE_UNAUTHORIZED_SUBPROCESS",
    "RULE_NETWORK_VIOLATION",
    "RULE_SQL_CONFINEMENT",
    "RULE_TERMINAL_VIOLATION",
    "RULE_HTML_SANDBOX_VIOLATION",
    "RULE_ABAP_VIOLATION",
    "RULE_RESOURCE_LIMIT",
    "RULE_FAIL_CLOSED",
    "RULE_REFLECTION_OBFUSCATION",
    "StaticCodeAnalyzer",
    "TerminalSecurityFirewall",
    "SqlSecurityGuard",
]

