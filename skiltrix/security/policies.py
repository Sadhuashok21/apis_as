"""
SkilTrix Universal Security Firewall - Policies and Response Standards
Defines rule definitions, exception structures, and standardized response formats.
"""

from typing import Dict, Any, Optional

ERROR_CODE_SECURITY_VIOLATION = "SECURITY_POLICY_VIOLATION"

# Security Rule Identifiers
RULE_DANGEROUS_FILESYSTEM = "DANGEROUS_FILESYSTEM_OPERATION"
RULE_PATH_TRAVERSAL = "PATH_TRAVERSAL_DETECTED"
RULE_UNAUTHORIZED_SUBPROCESS = "UNAUTHORIZED_SUBPROCESS_EXECUTION"
RULE_NETWORK_VIOLATION = "NETWORK_POLICY_VIOLATION"
RULE_SQL_CONFINEMENT = "SQL_DATABASE_CONFINEMENT_VIOLATION"
RULE_TERMINAL_VIOLATION = "TERMINAL_COMMAND_VIOLATION"
RULE_HTML_SANDBOX_VIOLATION = "HTML_SANDBOX_VIOLATION"
RULE_ABAP_VIOLATION = "ABAP_UNAUTHORIZED_OPERATION"
RULE_RESOURCE_LIMIT = "RESOURCE_LIMIT_EXCEEDED"
RULE_FAIL_CLOSED = "FAIL_CLOSED_INITIALIZATION"
RULE_REFLECTION_OBFUSCATION = "REFLECTION_OBFUSCATION_ATTEMPT"


class SecurityPolicyViolation(Exception):
    """Exception raised when code or command violates security policy."""

    def __init__(
        self,
        message: str,
        rule_triggered: str = RULE_DANGEROUS_FILESYSTEM,
        language: str = "unknown",
        entry_point: str = "runtime",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.rule_triggered = rule_triggered
        self.language = language
        self.entry_point = entry_point
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return make_security_error_response(
            message=self.message,
            rule=self.rule_triggered,
            language=self.language,
            details=self.details,
        )


def make_security_error_response(
    message: str,
    error_code: str = ERROR_CODE_SECURITY_VIOLATION,
    rule: str = "",
    execution_status: str = "blocked",
    language: str = "unknown",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Standardized security error format returned across all IDE execution entry points:
    Run Code, Execute SQL, Terminal, Django endpoints, ABAP engine, HTML Preview, etc.
    """
    return {
        "success": False,
        "status": False,
        "error_code": error_code,
        "message": message,
        "error": message,
        "execution_status": execution_status,
        "rule_triggered": rule,
        "language": language,
        "stdout": "",
        "stderr": f"[SECURITY_POLICY_VIOLATION]: {message}",
        "exit_code": 1,
        "duration_ms": 0.0,
        "memory_kb": 0.0,
        "details": details or {},
    }

