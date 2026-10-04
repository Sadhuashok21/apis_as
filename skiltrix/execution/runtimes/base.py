import os
import time
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from ..sandbox_policy import ExecutionPolicy, ResourceLimitExceeded


@dataclass
class ExecutionResult:
    status: str  # "completed", "failed", "timeout", "compile_error"
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    memory_kb: float = 12000.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "status": self.status,
            "success": self.status == "completed",
            "execution_status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "memory_kb": self.memory_kb,
            "error_message": self.error_message,
        }
        if self.status == "timeout":
            data["error_code"] = "RESOURCE_LIMIT_EXCEEDED"
            data["message"] = "Execution exceeded maximum permitted CPU execution time."
        return data


class BaseRuntime:
    """Base class for language-specific execution runtimes."""
    language: str = "base"

    def __init__(self, policy: Optional[ExecutionPolicy] = None):
        self.policy = policy or ExecutionPolicy()

    def run_process(
        self,
        cmd: List[str],
        cwd: Path,
        stdin: str = "",
        timeout: float = ExecutionPolicy.DEFAULT_TIMEOUT_SECONDS,
        custom_env: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """
        Executes a command line process under sandbox constraints.
        Enforces timeout limits, captures stdout and stderr, sanitizes environment.
        """
        clean_env = self.policy.sanitize_environment(custom_env)
        start_time = time.perf_counter()

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=clean_env,
            )

            try:
                stdout_data, stderr_data = proc.communicate(
                    input=stdin,
                    timeout=timeout,
                )
                exit_code = proc.returncode
                status_str = "completed" if exit_code == 0 else "failed"
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout_data, stderr_data = proc.communicate()
                status_str = "timeout"
                exit_code = 124
                stderr_data += f"\n[Execution Timeout: exceeded limit of {timeout}s]"

        except Exception as exc:
            stdout_data = ""
            stderr_data = f"Failed to invoke runtime executable: {str(exc)}"
            exit_code = 1
            status_str = "failed"

        end_time = time.perf_counter()
        duration_ms = round((end_time - start_time) * 1000.0, 2)

        # Buffer truncation
        max_bytes = self.policy.MAX_OUTPUT_BYTES
        if len(stdout_data) > max_bytes:
            stdout_data = stdout_data[:max_bytes] + "\n...[Output truncated due to buffer limit]..."
        if len(stderr_data) > max_bytes:
            stderr_data = stderr_data[:max_bytes] + "\n...[Errors truncated due to buffer limit]..."

        return ExecutionResult(
            status=status_str,
            stdout=stdout_data,
            stderr=stderr_data,
            exit_code=exit_code,
            duration_ms=duration_ms,
        )

    def execute(
        self,
        code: str,
        stdin: str = "",
        workspace_dir: Optional[Path] = None,
        entry_file: Optional[str] = None,
        timeout: float = ExecutionPolicy.DEFAULT_TIMEOUT_SECONDS,
    ) -> ExecutionResult:
        """Subclasses must implement actual language execution pipeline."""
        raise NotImplementedError
