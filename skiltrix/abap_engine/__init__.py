"""
SkilTrix SAP ABAP Lab - Educational ABAP Simulator Engine
Provides AST tokenization, parsing, syntax diagnostics, and runtime execution
for the documented subset of SAP ABAP statements and Open SQL.
"""

import time
from typing import Dict, Any, List

from .lexer import preprocess_abap
from .parser import ABAPParser
from .interpreter import ABAPInterpreter
from .datasets import STANDARD_DATASETS, get_standard_table, query_synthetic_table


def check_abap_syntax(source_code: str) -> Dict[str, Any]:
    """
    Performs static syntax verification on ABAP code.
    Returns syntax diagnostics, warnings, and errors.
    """
    diagnostics: List[Dict[str, Any]] = []

    try:
        statements = preprocess_abap(source_code)
        parser = ABAPParser(statements)
        ast_nodes = parser.parse()

        for diag in parser.diagnostics:
            diagnostics.append({
                "line": diag.line,
                "column": diag.column,
                "severity": diag.severity,
                "message": diag.message,
                "code": diag.code,
            })

        valid = not any(d["severity"] == "error" for d in diagnostics)

    except Exception as exc:
        valid = False
        diagnostic = {
            "severity": "error",
            "message": f"ABAP Syntax Analysis Error: {str(exc)}",
        }
        exception_line = getattr(exc, "line", None)
        if isinstance(exception_line, int) and exception_line > 0:
            diagnostic["line"] = exception_line
        diagnostics.append(diagnostic)

    return {
        "valid": valid,
        "diagnostics": diagnostics,
    }


def execute_abap_code(source_code: str, max_steps: int = 15000, user_id: str = None, project_id: str = None) -> Dict[str, Any]:
    """
    Parses and executes ABAP source code using the AST Simulator.
    Returns standard spool list output, execution duration, diagnostics,
    and state of internal and database tables.
    """
    start_time = time.perf_counter()

    try:
        # 1. Preprocess & tokenize
        statements = preprocess_abap(source_code)

        # 2. Parse AST
        parser = ABAPParser(statements)
        ast_nodes = parser.parse()

        syntax_errors = [
            {"line": diag.line, "column": diag.column, "severity": diag.severity,
             "message": diag.message, "code": diag.code}
            for diag in parser.diagnostics if diag.severity == "error"
        ]
        if syntax_errors:
            return {
                "status": False,
                "output": "Compilation failed. Fix the ABAP syntax errors before running the program.",
                "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "diagnostics": syntax_errors,
                "execution_mode": "simulator",
                "internal_tables_state": {},
                "database_tables_state": {},
                "system_fields": {},
            }

        # 3. Interpret & evaluate
        interpreter = ABAPInterpreter(max_steps=max_steps, user_id=user_id, project_id=project_id)
        eval_result = interpreter.execute(ast_nodes)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Combine parser warnings and interpreter diagnostics
        all_diagnostics = []
        for diag in parser.diagnostics:
            all_diagnostics.append({
                "line": diag.line,
                "column": diag.column,
                "severity": diag.severity,
                "message": diag.message,
                "code": diag.code,
            })
        all_diagnostics.extend(eval_result.get("diagnostics", []))

        return {
            "status": eval_result.get("status", True),
            "output": eval_result.get("output", ""),
            "execution_time_ms": duration_ms,
            "diagnostics": all_diagnostics,
            "execution_mode": "simulator",
            "internal_tables_state": eval_result.get("internal_tables", {}),
            "database_tables_state": eval_result.get("system_fields", {}),
            "system_fields": eval_result.get("system_fields", {}),
        }

    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": False,
            "output": f"[SIMULATOR INTERNAL ERROR]: {str(exc)}",
            "execution_time_ms": duration_ms,
            "diagnostics": [{"line": 1, "severity": "error", "message": str(exc)}],
            "execution_mode": "simulator",
            "internal_tables_state": {},
            "database_tables_state": {},
            "system_fields": {},
        }


__all__ = [
    "preprocess_abap",
    "ABAPParser",
    "ABAPInterpreter",
    "check_abap_syntax",
    "execute_abap_code",
    "STANDARD_DATASETS",
    "get_standard_table",
    "query_synthetic_table",
]

