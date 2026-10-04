"""
SkilTrix Universal Security Firewall - Central Security Engine
Coordinates language analysis, terminal firewalling, SQL isolation,
workspace path confinement, fail-closed enforcement, and audit logging.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .audit_log import audit_logger
from .policies import (
    SecurityPolicyViolation,
    make_security_error_response,
    RULE_FAIL_CLOSED,
    RULE_PATH_TRAVERSAL,
    RULE_RESOURCE_LIMIT,
)
from .static_analyzer import StaticCodeAnalyzer
from .terminal_firewall import TerminalSecurityFirewall
from .sql_guard import SqlSecurityGuard


class UniversalSecurityEngine:
    """
    Central coordinator enforcing security policies across all languages,
    compilers, simulators, and execution entry points in SkilTrix.
    """

    _initialized = True

    @classmethod
    def set_engine_health(cls, healthy: bool):
        """Allows toggling health state to test fail-closed design."""
        cls._initialized = healthy

    @classmethod
    def evaluate_code(
        cls,
        language: str,
        code: str,
        workspace_dir: Optional[Path] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Pre-execution security evaluation for user source code.
        Returns None if safe, or structured error dict if blocked.
        """
        # Fail-closed enforcement: if engine is not healthy, block execution
        if not cls._initialized:
            msg = "Security engine initialization failed; execution safely blocked (fail-closed)."
            audit_logger.record_violation(
                entry_point="evaluate_code",
                rule_triggered=RULE_FAIL_CLOSED,
                message=msg,
                language=language,
                user_id=user_id,
                project_id=project_id,
            )
            return make_security_error_response(
                message=msg,
                rule=RULE_FAIL_CLOSED,
                language=language,
            )

        try:
            # 1. Path confinement check on workspace if provided
            if workspace_dir:
                cls.validate_workspace_path(workspace_dir)

            # 2. Static AST / Token analysis
            StaticCodeAnalyzer.analyze(language=language, code=code)
            return None

        except SecurityPolicyViolation as spv:
            audit_logger.record_violation(
                entry_point="evaluate_code",
                rule_triggered=spv.rule_triggered,
                message=spv.message,
                language=spv.language or language,
                user_id=user_id,
                project_id=project_id,
                details=spv.details,
            )
            return spv.to_dict()

        except Exception as exc:
            # Any unhandled exception during security evaluation causes fail-closed abort
            msg = f"Security inspection error; execution aborted (fail-closed): {str(exc)}"
            audit_logger.record_violation(
                entry_point="evaluate_code",
                rule_triggered=RULE_FAIL_CLOSED,
                message=msg,
                language=language,
                user_id=user_id,
                project_id=project_id,
            )
            return make_security_error_response(
                message=msg,
                rule=RULE_FAIL_CLOSED,
                language=language,
            )

    @classmethod
    def evaluate_terminal_command(
        cls,
        command: str,
        workspace_dir: Path,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
        """
        Validates interactive terminal command.
        Returns: (is_safe, error_response_dict_or_none, parsed_tokens)
        """
        if not cls._initialized:
            msg = "Security firewall unavailable; terminal command blocked (fail-closed)."
            audit_logger.record_violation(
                entry_point="terminal",
                rule_triggered=RULE_FAIL_CLOSED,
                message=msg,
                language="shell",
                user_id=user_id,
                project_id=project_id,
            )
            return False, make_security_error_response(message=msg, rule=RULE_FAIL_CLOSED, language="shell"), []

        try:
            tokens = TerminalSecurityFirewall.validate_command(command, workspace_dir)
            return True, None, tokens

        except SecurityPolicyViolation as spv:
            audit_logger.record_violation(
                entry_point="terminal",
                rule_triggered=spv.rule_triggered,
                message=spv.message,
                language="shell",
                user_id=user_id,
                project_id=project_id,
                details=spv.details,
            )
            return False, spv.to_dict(), []

        except Exception as exc:
            msg = f"Terminal security inspection failure (fail-closed): {str(exc)}"
            audit_logger.record_violation(
                entry_point="terminal",
                rule_triggered=RULE_FAIL_CLOSED,
                message=msg,
                language="shell",
                user_id=user_id,
                project_id=project_id,
            )
            return False, make_security_error_response(message=msg, rule=RULE_FAIL_CLOSED, language="shell"), []

    @classmethod
    def evaluate_sql(
        cls,
        script: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Validates SQL statements before execution."""
        if not cls._initialized:
            msg = "Security engine offline; SQL query blocked (fail-closed)."
            audit_logger.record_violation(
                entry_point="sql",
                rule_triggered=RULE_FAIL_CLOSED,
                message=msg,
                language="sql",
                user_id=user_id,
                project_id=project_id,
            )
            return make_security_error_response(message=msg, rule=RULE_FAIL_CLOSED, language="sql")

        try:
            SqlSecurityGuard.validate_script(script)
            return None

        except SecurityPolicyViolation as spv:
            audit_logger.record_violation(
                entry_point="sql",
                rule_triggered=spv.rule_triggered,
                message=spv.message,
                language="sql",
                user_id=user_id,
                project_id=project_id,
                details=spv.details,
            )
            return spv.to_dict()

        except Exception as exc:
            msg = f"SQL security inspection error (fail-closed): {str(exc)}"
            audit_logger.record_violation(
                entry_point="sql",
                rule_triggered=RULE_FAIL_CLOSED,
                message=msg,
                language="sql",
                user_id=user_id,
                project_id=project_id,
            )
            return make_security_error_response(message=msg, rule=RULE_FAIL_CLOSED, language="sql")

    @classmethod
    def evaluate_abap(
        cls,
        code: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Validates ABAP code before execution."""
        if not cls._initialized:
            msg = "Security engine offline; ABAP execution blocked (fail-closed)."
            audit_logger.record_violation(
                entry_point="abap",
                rule_triggered=RULE_FAIL_CLOSED,
                message=msg,
                language="abap",
                user_id=user_id,
                project_id=project_id,
            )
            return make_security_error_response(message=msg, rule=RULE_FAIL_CLOSED, language="abap")

        try:
            StaticCodeAnalyzer.analyze_abap(code)
            return None

        except SecurityPolicyViolation as spv:
            audit_logger.record_violation(
                entry_point="abap",
                rule_triggered=spv.rule_triggered,
                message=spv.message,
                language="abap",
                user_id=user_id,
                project_id=project_id,
                details=spv.details,
            )
            return spv.to_dict()

        except Exception as exc:
            msg = f"ABAP security validation failed (fail-closed): {str(exc)}"
            audit_logger.record_violation(
                entry_point="abap",
                rule_triggered=RULE_FAIL_CLOSED,
                message=msg,
                language="abap",
                user_id=user_id,
                project_id=project_id,
            )
            return make_security_error_response(message=msg, rule=RULE_FAIL_CLOSED, language="abap")

    @classmethod
    def validate_workspace_path(cls, workspace_dir: Path) -> Path:
        """Validates that workspace directory is safe and properly formatted."""
        try:
            resolved = workspace_dir.resolve()
            if not resolved.exists():
                resolved.mkdir(parents=True, exist_ok=True)
            return resolved
        except Exception as err:
            raise SecurityPolicyViolation(
                message=f"Invalid workspace path: {workspace_dir}",
                rule_triggered=RULE_PATH_TRAVERSAL,
                entry_point="filesystem",
            ) from err

    @classmethod
    def validate_child_path(cls, base_dir: Path, target_path: Path) -> Path:
        """Confines target_path strictly inside base_dir."""
        try:
            resolved_base = base_dir.resolve()
            resolved_target = target_path.resolve()
            resolved_target.relative_to(resolved_base)
            return resolved_target
        except Exception as err:
            raise SecurityPolicyViolation(
                message=f"Path traversal detected: {target_path} is outside {base_dir}",
                rule_triggered=RULE_PATH_TRAVERSAL,
                entry_point="filesystem",
            ) from err
