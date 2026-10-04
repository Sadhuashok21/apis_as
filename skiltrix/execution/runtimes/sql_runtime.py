import time
from pathlib import Path
from typing import Optional
from .base import BaseRuntime, ExecutionResult
from ..sandbox_policy import ExecutionPolicy
from ...codelab_sql import ProjectDatabaseCatalog, SqlStatementDispatcher


class SqlRuntime(BaseRuntime):
    language = "sql"

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

        start_time = time.perf_counter()
        output_sections = []
        stderr_msg = ""
        exit_code = 0
        status_str = "completed"

        try:
            catalog = ProjectDatabaseCatalog(workspace_dir=workspace_dir)
            dispatcher = SqlStatementDispatcher(catalog)
            result = dispatcher.execute_script(code, timeout_seconds=timeout)

            if not result.get("status"):
                stderr_msg = f"SQL Syntax / Execution Error:\n{result.get('error', 'Execution failed.')}"
                exit_code = 1
                status_str = "failed"
            else:
                for item in result.get("results", []):
                    if item.get("is_query"):
                        columns = item.get("columns", [])
                        rows = item.get("rows", [])
                        header_row = " | ".join(str(c) for c in columns)
                        divider = "-" * max(30, len(header_row))
                        lines = [header_row, divider]
                        for row in rows:
                            lines.append(" | ".join("NULL" if val is None else str(val) for val in row))
                        lines.append(f"({len(rows)} row(s) returned)\n")
                        output_sections.append("\n".join(lines))
                    else:
                        output_sections.append(item.get("message", "Query OK."))

        except Exception as exc:
            stderr_msg = f"Database Playground Exception: {str(exc)}"
            exit_code = 1
            status_str = "failed"

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        stdout_text = "\n".join(output_sections)

        return ExecutionResult(
            status=status_str,
            stdout=stdout_text,
            stderr=stderr_msg,
            exit_code=exit_code,
            duration_ms=duration_ms,
        )
