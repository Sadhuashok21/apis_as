import os
import shutil
from pathlib import Path
from typing import Optional
from .base import BaseRuntime, ExecutionResult
from ..sandbox_policy import ExecutionPolicy


def find_php_executable() -> Optional[str]:
    which_php = shutil.which("php")
    if which_php:
        return which_php

    # WinGet packages directory
    winget_dir = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_dir.exists():
        for p in winget_dir.glob("**/php.exe"):
            if p.is_file():
                return str(p)

    candidates = [
        r"C:\xampp\php\php.exe",
        r"D:\xampp\php\php.exe",
        r"C:\php\php.exe",
        r"D:\php\php.exe",
        r"C:\tools\php\php.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


class PhpRuntime(BaseRuntime):
    language = "php"

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

        php_bin = find_php_executable()
        if not php_bin:
            return ExecutionResult(
                status="failed",
                stdout="",
                stderr="[PHP Runtime Error] PHP CLI executable was not detected on the host system.\n"
                       "Install PHP CLI or enable the Docker CodeLab execution worker container.",
                exit_code=1,
                duration_ms=0.0,
                error_message="PHP CLI not found.",
            )

        src_file = workspace_dir / (entry_file or "index.php")
        if not src_file.exists() or code:
            src_file.write_text(code, encoding="utf-8")

        # Run with memory and time caps
        cmd = [php_bin, "-d", "memory_limit=64M", "-d", "display_errors=1", str(src_file.name)]
        return self.run_process(cmd=cmd, cwd=workspace_dir, stdin=stdin, timeout=timeout)
