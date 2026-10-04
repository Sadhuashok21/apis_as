import os
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from django.conf import settings

from .sandbox_policy import ExecutionPolicy
from .runtimes import (
    BaseRuntime,
    ExecutionResult,
    PythonRuntime,
    JavaScriptRuntime,
    TypeScriptRuntime,
    JavaRuntime,
    CppRuntime,
    PhpRuntime,
    SqlRuntime,
)

TEMP_EXECUTION_ROOT = Path(settings.MEDIA_ROOT) / "execution_tmp"
TEMP_EXECUTION_ROOT.mkdir(parents=True, exist_ok=True)


RUNTIME_REGISTRY = {
    "python": PythonRuntime,
    "py": PythonRuntime,
    "python3": PythonRuntime,
    "javascript": JavaScriptRuntime,
    "js": JavaScriptRuntime,
    "node": JavaScriptRuntime,
    "nodejs": JavaScriptRuntime,
    "typescript": TypeScriptRuntime,
    "ts": TypeScriptRuntime,
    "java": JavaRuntime,
    "cpp": CppRuntime,
    "c++": CppRuntime,
    "c": CppRuntime,
    "php": PhpRuntime,
    "sql": SqlRuntime,
}


def execute_code_job(
    language: str,
    code: str,
    stdin: str = "",
    workspace_dir: Optional[Path] = None,
    entry_file: Optional[str] = None,
    timeout: float = ExecutionPolicy.DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    Primary API entry point for running untrusted user code.
    Selects the appropriate runtime, enforces security policies,
    and returns a standardized dictionary of results.
    """
    lang_key = language.lower().strip()
    runtime_cls = RUNTIME_REGISTRY.get(lang_key)

    if not runtime_cls:
        return {
            "status": "failed",
            "stdout": "",
            "stderr": f"Unsupported execution runtime: '{language}'. Supported languages: {list(RUNTIME_REGISTRY.keys())}",
            "exit_code": 1,
            "duration_ms": 0.0,
            "memory_kb": 0.0,
            "error_message": f"Unsupported language: {language}",
        }

    is_ephemeral = False
    if workspace_dir is None:
        is_ephemeral = True
        ephemeral_id = f"job_{uuid.uuid4().hex[:12]}"
        workspace_dir = TEMP_EXECUTION_ROOT / ephemeral_id
        workspace_dir.mkdir(parents=True, exist_ok=True)

    # Enforce Universal Security Firewall pre-execution validation
    from ..security import UniversalSecurityEngine
    sec_violation = UniversalSecurityEngine.evaluate_code(
        language=lang_key,
        code=code,
        workspace_dir=workspace_dir,
    )
    if sec_violation:
        if is_ephemeral and workspace_dir.exists():
            shutil.rmtree(workspace_dir, ignore_errors=True)
        return sec_violation

    try:
        runtime_instance: BaseRuntime = runtime_cls()
        result: ExecutionResult = runtime_instance.execute(
            code=code,
            stdin=stdin,
            workspace_dir=workspace_dir,
            entry_file=entry_file,
            timeout=timeout,
        )
        return result.to_dict()

    finally:
        # Guarantee ephemeral scratch directories are purged immediately
        if is_ephemeral and workspace_dir.exists():
            shutil.rmtree(workspace_dir, ignore_errors=True)
