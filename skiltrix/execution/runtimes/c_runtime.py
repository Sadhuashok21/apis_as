import os
import shutil
from pathlib import Path
from typing import Optional

from .base import BaseRuntime, ExecutionResult
from ..sandbox_dispatcher import execute_in_sandbox
from ..sandbox_policy import ExecutionPolicy


def find_c_compiler() -> Optional[str]:
    gcc_bin = shutil.which("gcc")
    if gcc_bin:
        return gcc_bin
    for candidate in (
        r"C:\msys64\mingw64\bin\gcc.exe",
        r"C:\mingw64\bin\gcc.exe",
        r"C:\MinGW\bin\gcc.exe",
    ):
        if os.path.isfile(candidate):
            return candidate
    return shutil.which("clang")


class CRuntime(BaseRuntime):
    """Dedicated C11 runtime (gcc) with sandboxed fallback support."""

    language = "c"

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

        src_file = workspace_dir / (entry_file or "main.c")
        if code:
            src_file.write_text(code, encoding="utf-8")

        gcc_bin = find_c_compiler()
        if gcc_bin:
            out_bin = workspace_dir / ("main.exe" if os.name == "nt" else "main.out")
            compile_cmd = [gcc_bin, "-O2", "-std=c11", str(src_file), "-o", str(out_bin), "-lm"]
            comp_res = self.run_process(cmd=compile_cmd, cwd=workspace_dir, stdin="", timeout=max(10.0, timeout))
            if comp_res.status != "completed" or comp_res.exit_code != 0:
                return ExecutionResult(
                    status="failed",
                    stdout="",
                    stderr=comp_res.stderr or comp_res.stdout or "C compilation failed.",
                    exit_code=comp_res.exit_code or 1,
                    duration_ms=comp_res.duration_ms,
                    error_message="Compilation Error",
                )
            return self.run_process(cmd=[str(out_bin)], cwd=workspace_dir, stdin=stdin, timeout=timeout)

        # Fallback through sandbox_dispatcher (Docker or configured Judge0)
        res = execute_in_sandbox(
            language="c",
            source_code=code,
            stdin_data=stdin,
            timeout_seconds=timeout,
            memory_limit_mb=256,
        )
        mapped_status = "completed" if res.status == "OK" else ("timeout" if res.status == "Time Limit Exceeded" else "failed")
        return ExecutionResult(
            status=mapped_status,
            stdout=res.stdout,
            stderr=res.compile_output or res.stderr,
            exit_code=res.exit_code if res.exit_code is not None else (0 if res.status == "OK" else 1),
            duration_ms=res.execution_time_ms,
            memory_kb=res.memory_kb,
            error_message=None if res.status == "OK" else res.status,
        )
