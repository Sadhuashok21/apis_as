import os
import shutil
import time
import subprocess
from pathlib import Path
from typing import Optional
from .base import BaseRuntime, ExecutionResult
from ..sandbox_policy import ExecutionPolicy


def find_cpp_compiler() -> Optional[str]:
    for comp in ["g++", "clang++", "gcc"]:
        which_comp = shutil.which(comp)
        if which_comp:
            return which_comp
    # Check common MinGW install paths on Windows
    common_paths = [
        r"C:\msys64\mingw64\bin\g++.exe",
        r"C:\MinGW\bin\g++.exe",
        r"C:\TDM-GCC-64\bin\g++.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None


class CppRuntime(BaseRuntime):
    language = "cpp"

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

        compiler = find_cpp_compiler()
        if not compiler:
            return ExecutionResult(
                status="compile_error",
                stdout="",
                stderr="[Compiler Error] No C/C++ compiler (g++/gcc/clang) was detected in the host environment.\n"
                       "For local development on Windows, install MinGW or use Docker Execution Worker.",
                exit_code=1,
                duration_ms=0.0,
                error_message="C++ compiler unavailable.",
            )

        src_file = workspace_dir / (entry_file or "main.cpp")
        src_file.write_text(code, encoding="utf-8")
        out_bin = workspace_dir / "program.exe"

        start_time = time.perf_counter()
        clean_env = self.policy.sanitize_environment()

        # Phase 1: Compile (-O2 optimization, warnings enabled, C++17)
        compile_cmd = [compiler, "-O2", "-std=c++17", str(src_file.name), "-o", str(out_bin.name)]
        comp_proc = subprocess.Popen(
            compile_cmd,
            cwd=str(workspace_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=clean_env,
        )
        c_out, c_err = comp_proc.communicate(timeout=10.0)

        if comp_proc.returncode != 0:
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return ExecutionResult(
                status="compile_error",
                stdout="",
                stderr=f"[Compilation Error]\n{c_err}",
                exit_code=comp_proc.returncode,
                duration_ms=duration_ms,
                error_message="C++ compilation failed.",
            )

        # Phase 2: Execute binary
        cmd = [str(out_bin)]
        return self.run_process(cmd=cmd, cwd=workspace_dir, stdin=stdin, timeout=timeout)
