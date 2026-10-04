import sys
from pathlib import Path
from typing import Optional
from .base import BaseRuntime, ExecutionResult
from ..sandbox_policy import ExecutionPolicy


class PythonRuntime(BaseRuntime):
    language = "python"

    def execute(
        self,
        code: str,
        stdin: str = "",
        workspace_dir: Optional[Path] = None,
        entry_file: Optional[str] = None,
        timeout: float = ExecutionPolicy.DEFAULT_TIMEOUT_SECONDS,
    ) -> ExecutionResult:
        if not workspace_dir:
            raise ValueError("workspace_dir is required for execution.")

        target_file = workspace_dir / (entry_file or "main.py")
        if not target_file.exists() or code:
            target_file.write_text(code, encoding="utf-8")

        # Execute with unbuffered output (-u) and bytecode generation disabled (-B)
        cmd = [sys.executable, "-u", "-B", str(target_file.name)]
        return self.run_process(cmd=cmd, cwd=workspace_dir, stdin=stdin, timeout=timeout)
