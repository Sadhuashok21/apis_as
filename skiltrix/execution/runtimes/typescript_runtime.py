import os
import shutil
from pathlib import Path
from typing import Optional
from .base import BaseRuntime, ExecutionResult
from .javascript_runtime import find_node_executable
from ..sandbox_policy import ExecutionPolicy


class TypeScriptRuntime(BaseRuntime):
    language = "typescript"

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

        target_file = workspace_dir / (entry_file or "index.ts")
        if not target_file.exists() or code:
            target_file.write_text(code, encoding="utf-8")

        node_bin = find_node_executable()
        # Node v24 (which is installed at D:\node\node.exe) supports experimental strip types directly!
        cmd = [node_bin, "--experimental-strip-types", "--max-old-space-size=256", str(target_file.name)]
        return self.run_process(cmd=cmd, cwd=workspace_dir, stdin=stdin, timeout=timeout)
