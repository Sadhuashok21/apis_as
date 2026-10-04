import os
import shutil
from pathlib import Path
from typing import Optional
from .base import BaseRuntime, ExecutionResult
from ..sandbox_policy import ExecutionPolicy


def find_node_executable() -> str:
    which_node = shutil.which("node")
    if which_node:
        return which_node
    # Check default install locations
    candidates = [
        r"D:\node\node.exe",
        r"C:\Program Files\nodejs\node.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "node"


class JavaScriptRuntime(BaseRuntime):
    language = "javascript"

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

        target_file = workspace_dir / (entry_file or "index.js")
        if not target_file.exists() or code:
            target_file.write_text(code, encoding="utf-8")

        node_bin = find_node_executable()
        # Flags: limit memory to 256MB
        cmd = [node_bin, "--max-old-space-size=256", str(target_file.name)]
        return self.run_process(cmd=cmd, cwd=workspace_dir, stdin=stdin, timeout=timeout)
