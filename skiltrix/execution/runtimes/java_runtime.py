import re
import time
import subprocess
from pathlib import Path
from typing import Optional
from .base import BaseRuntime, ExecutionResult
from ..sandbox_policy import ExecutionPolicy


class JavaRuntime(BaseRuntime):
    language = "java"

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

        # Detect class name from code
        match = re.search(r"\bpublic\s+(?:final\s+)?class\s+([A-Za-z_$][\w$]*)", code)
        class_name = match.group(1) if match else "Solution"

        java_file = workspace_dir / f"{class_name}.java"
        java_file.write_text(code, encoding="utf-8")

        start_time = time.perf_counter()
        clean_env = self.policy.sanitize_environment()

        # Phase 1: Compile with javac
        compile_proc = subprocess.Popen(
            ["javac", f"{class_name}.java"],
            cwd=str(workspace_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=clean_env,
        )
        c_out, c_err = compile_proc.communicate(timeout=10.0)

        if compile_proc.returncode != 0:
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return ExecutionResult(
                status="compile_error",
                stdout="",
                stderr=f"[Compilation Error]\n{c_err}",
                exit_code=compile_proc.returncode,
                duration_ms=duration_ms,
                error_message="Java compilation failed.",
            )

        # Phase 2: Execute with memory limits
        cmd = ["java", "-Xmx256m", "-Xms32m", class_name]
        return self.run_process(cmd=cmd, cwd=workspace_dir, stdin=stdin, timeout=timeout)
