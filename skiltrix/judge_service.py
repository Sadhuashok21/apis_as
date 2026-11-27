"""Automated judging service for SkilTrix Coding Assessments.

Executes candidate submissions through isolated sandboxes (never in-process),
evaluates public/hidden test cases, computes Proportional/Weighted scores and
Partial Accepted verdicts, measures time & memory, and strictly redacts
hidden test case inputs/outputs from student-facing payloads.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .execution.sandbox_dispatcher import (
    LANGUAGE_SPECS,
    SandboxExecutionResult,
    canonicalize_language,
    execute_in_sandbox,
)

MAX_SOURCE_CODE_LENGTH = 100_000

_SECURITY_PATTERNS: Dict[str, List[Tuple[re.Pattern, str]]] = {
    "python": [
        (re.compile(r"\b(__import__|eval|exec)\s*\("), "Dynamic code execution is not permitted in assessments."),
        (re.compile(r"\bimport\s+(subprocess|ctypes|socket|multiprocessing|pty)\b"), "Restricted OS/network module import detected."),
        (re.compile(r"\bfrom\s+(subprocess|ctypes|socket|multiprocessing|pty)\s+import\b"), "Restricted OS/network module import detected."),
        (re.compile(r"\bos\.(system|popen|fork|kill|remove|unlink|rmdir)\b"), "Restricted os process/filesystem call detected."),
    ],
    "javascript": [
        (re.compile(r"require\s*\(\s*['\"](child_process|net|http|https|dgram|cluster)['\"]\s*\)"), "Restricted Node module import detected."),
    ],
    "java": [
        (re.compile(r"\b(ProcessBuilder|Runtime\.getRuntime\(\)\.exec|java\.net\.Socket|ServerSocket)\b"), "Restricted JVM process/network API detected."),
    ],
    "c": [
        (re.compile(r"\b(system|popen|fork|execv|execve|execl)\s*\("), "Restricted system/process call detected."),
    ],
    "cpp": [
        (re.compile(r"\b(system|popen|fork|execv|execve|execl)\s*\("), "Restricted system/process call detected."),
    ],
}


def validate_code_security(canonical_lang: str, source_code: str) -> None:
    """Reject blatantly malicious process/network syscalls before container/sandbox dispatch."""
    for pattern, reason in _SECURITY_PATTERNS.get(canonical_lang, []):
        if pattern.search(source_code):
            raise PermissionError(f"Security Policy Violation: {reason}")

DEFAULT_STARTER_CODES: Dict[str, str] = {
    "python": (
        "import sys\n\n"
        "def solve():\n"
        "    data = sys.stdin.read().strip()\n"
        "    # Write your solution here\n"
        "    if data:\n"
        "        print(data)\n\n"
        "if __name__ == '__main__':\n"
        "    solve()\n"
    ),
    "java": (
        "import java.io.*;\n"
        "import java.util.*;\n\n"
        "public class Main {\n"
        "    public static void main(String[] args) throws Exception {\n"
        "        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n"
        "        StringBuilder sb = new StringBuilder();\n"
        "        String line;\n"
        "        while ((line = br.readLine()) != null) {\n"
        "            if (sb.length() > 0) sb.append('\\n');\n"
        "            sb.append(line);\n"
        "        }\n"
        "        // Write your solution here\n"
        "    }\n"
        "}\n"
    ),
    "c": (
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n\n"
        "int main(void) {\n"
        "    /* Read input from stdin and write answer to stdout */\n"
        "    return 0;\n"
        "}\n"
    ),
    "cpp": (
        "#include <bits/stdc++.h>\n"
        "using namespace std;\n\n"
        "int main() {\n"
        "    ios::sync_with_stdio(false);\n"
        "    cin.tie(nullptr);\n"
        "    // Write your solution here\n"
        "    return 0;\n"
        "}\n"
    ),
    "javascript": (
        "'use strict';\n"
        "const fs = require('fs');\n\n"
        "function solve(rawInput) {\n"
        "    const lines = rawInput.trim().split(/\\r?\\n/);\n"
        "    // Write your solution here\n"
        "}\n\n"
        "solve(fs.readFileSync(0, 'utf8'));\n"
    ),
}


def normalize_output(text: Optional[str]) -> str:
    """Normalize line endings and trailing whitespace per line for fair comparison."""
    if text is None:
        return ""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned = [line.rstrip() for line in lines]
    return "\n".join(cleaned).strip()


def validate_language_for_problem(language: str, problem: Any) -> str:
    canonical = canonicalize_language(language)
    supported = getattr(problem, "supported_languages", None)
    if isinstance(supported, list) and supported:
        allowed = {canonicalize_language(lang) for lang in supported if lang}
        if canonical not in allowed:
            raise ValueError(
                f"Language '{canonical}' is not enabled for problem '{problem.title}'."
            )
    return canonical


def get_starter_codes_for_problem(problem: Any) -> Dict[str, str]:
    """Return 5-language starter templates merged cleanly with CodingProblems overrides."""
    merged: Dict[str, str] = {}
    supported = getattr(problem, "supported_languages", None) or list(LANGUAGE_SPECS.keys())

    canonical_supported: List[str] = []
    for raw_lang in supported:
        try:
            canon = canonicalize_language(raw_lang)
        except ValueError:
            continue
        if canon not in canonical_supported:
            canonical_supported.append(canon)

    if not canonical_supported:
        canonical_supported = ["python", "java", "c", "cpp", "javascript"]

    field_map = {
        "python": getattr(problem, "starter_python", "") or "",
        "java": getattr(problem, "starter_java", "") or "",
        "c": getattr(problem, "starter_c", "") or "",
        "cpp": getattr(problem, "starter_cpp", "") or "",
        "javascript": getattr(problem, "starter_javascript", "") or "",
    }
    legacy_dict = getattr(problem, "starter_codes", None) or {}

    for lang in canonical_supported:
        code = field_map.get(lang, "")
        if not code.strip() and isinstance(legacy_dict, dict):
            code = (
                legacy_dict.get(lang)
                or legacy_dict.get(LANGUAGE_SPECS[lang]["display_name"])
                or ""
            )
        merged[lang] = code if isinstance(code, str) and code.strip() else DEFAULT_STARTER_CODES[lang]
    return merged


def _collect_test_cases(problem: Any, item: Any = None, public_only: bool = False) -> List[Dict[str, Any]]:
    """Collect normalized test case dicts from TestCases / AssessmentTestCase / samples."""
    collected: List[Dict[str, Any]] = []

    qs = problem.test_cases.all().order_by("order", "test_case_id")
    if public_only:
        qs = qs.filter(is_hidden=False)
    for tc in qs:
        collected.append(
            {
                "case_id": tc.test_case_id,
                "input_data": tc.input_data or "",
                "expected_output": tc.expected_output or "",
                "is_hidden": bool(tc.is_hidden),
                "marks": float(getattr(tc, "points", None) or 1.0),
            }
        )

    # Support AssessmentQuestionItem-scoped AssessmentTestCase when CodingProblems.test_cases is empty
    if not collected and item is not None and hasattr(item, "test_cases"):
        item_qs = item.test_cases.filter(is_active=True).order_by("order", "case_id")
        if public_only:
            item_qs = item_qs.filter(test_type="Sample")
        for tc in item_qs:
            collected.append(
                {
                    "case_id": tc.case_id,
                    "input_data": tc.input_data or "",
                    "expected_output": tc.expected_output or "",
                    "is_hidden": tc.test_type == "Hidden",
                    "marks": float(getattr(tc, "weight", None) or 1.0),
                }
            )

    # Fallback to CodingProblems explicit sample_input / sample_output
    if not collected and public_only:
        if getattr(problem, "sample_input", "") or getattr(problem, "sample_output", ""):
            collected.append(
                {
                    "case_id": 1,
                    "input_data": problem.sample_input or "",
                    "expected_output": problem.sample_output or "",
                    "is_hidden": False,
                    "marks": 1.0,
                }
            )

    return collected


def run_coding_code(
    *,
    problem: Any,
    source_code: str,
    language: str,
    custom_input: Optional[str] = None,
    item: Any = None,
) -> Dict[str, Any]:
    """Run candidate code against custom stdin or ONLY non-hidden sample tests."""
    if not source_code or not source_code.strip():
        return {
            "status": "Compilation Error",
            "mode": "custom_input" if custom_input is not None else "sample_tests",
            "passed": False,
            "stdout": "",
            "stderr": "Source code cannot be empty.",
            "compile_output": "Source code cannot be empty.",
            "execution_time_ms": 0.0,
            "memory_kb": 0.0,
            "test_case_results": [],
        }

    if len(source_code) > MAX_SOURCE_CODE_LENGTH:
        raise ValueError("Source code exceeds maximum allowed length (100 KB).")

    canonical_lang = validate_language_for_problem(language, problem)
    validate_code_security(canonical_lang, source_code)
    timeout_sec = float(getattr(problem, "time_limit_seconds", 2.0) or 2.0)
    memory_mb = int(getattr(problem, "memory_limit_mb", 256) or 256)

    if custom_input is not None:
        exec_res = execute_in_sandbox(
            language=canonical_lang,
            source_code=source_code,
            stdin_data=custom_input,
            timeout_seconds=timeout_sec,
            memory_limit_mb=memory_mb,
        )
        return {
            "status": "Executed" if exec_res.status == "OK" else exec_res.status,
            "mode": "custom_input",
            "language": canonical_lang,
            "passed": exec_res.status == "OK",
            "stdout": exec_res.stdout,
            "stderr": exec_res.stderr,
            "compile_output": exec_res.compile_output,
            "execution_time_ms": exec_res.execution_time_ms,
            "memory_kb": exec_res.memory_kb,
            "backend_used": exec_res.backend_used,
            "test_case_results": [
                {
                    "case_number": 1,
                    "is_hidden": False,
                    "status": "Executed" if exec_res.status == "OK" else exec_res.status,
                    "passed": exec_res.status == "OK",
                    "input": custom_input,
                    "actual_output": exec_res.stdout,
                    "expected_output": None,
                    "stderr": exec_res.compile_output or exec_res.stderr,
                    "execution_time_ms": exec_res.execution_time_ms,
                    "memory_kb": exec_res.memory_kb,
                }
            ],
        }

    # Run strictly public sample tests (never expose is_hidden=True)
    sample_cases = _collect_test_cases(problem, item=item, public_only=True)
    if not sample_cases:
        exec_res = execute_in_sandbox(
            language=canonical_lang,
            source_code=source_code,
            stdin_data="",
            timeout_seconds=timeout_sec,
            memory_limit_mb=memory_mb,
        )
        return {
            "status": "Executed" if exec_res.status == "OK" else exec_res.status,
            "mode": "sample_tests",
            "language": canonical_lang,
            "passed": exec_res.status == "OK",
            "passed_count": 1 if exec_res.status == "OK" else 0,
            "total_count": 0,
            "stdout": exec_res.stdout,
            "stderr": exec_res.stderr,
            "compile_output": exec_res.compile_output,
            "execution_time_ms": exec_res.execution_time_ms,
            "memory_kb": exec_res.memory_kb,
            "backend_used": exec_res.backend_used,
            "test_case_results": [],
        }

    case_results: List[Dict[str, Any]] = []
    passed_count = 0
    max_time_ms = 0.0
    max_mem_kb = 0.0
    compile_error_msg = ""
    first_stderr = ""
    first_stdout = ""
    backend_used = ""
    failure_status: Optional[str] = None

    for idx, tc in enumerate(sample_cases, start=1):
        exec_res = execute_in_sandbox(
            language=canonical_lang,
            source_code=source_code,
            stdin_data=tc["input_data"],
            timeout_seconds=timeout_sec,
            memory_limit_mb=memory_mb,
        )
        backend_used = exec_res.backend_used
        max_time_ms = max(max_time_ms, exec_res.execution_time_ms)
        max_mem_kb = max(max_mem_kb, exec_res.memory_kb)
        if idx == 1:
            first_stdout = exec_res.stdout
            first_stderr = exec_res.stderr

        if exec_res.status == "Compilation Error":
            compile_error_msg = exec_res.compile_output or exec_res.stderr
            failure_status = "Compilation Error"
            case_results.append(
                {
                    "case_number": idx,
                    "is_hidden": False,
                    "passed": False,
                    "status": "Compilation Error",
                    "input": tc["input_data"],
                    "expected_output": tc["expected_output"],
                    "actual_output": "",
                    "stderr": compile_error_msg,
                    "execution_time_ms": exec_res.execution_time_ms,
                    "memory_kb": exec_res.memory_kb,
                }
            )
            break

        if exec_res.status == "OK":
            actual_norm = normalize_output(exec_res.stdout)
            expected_norm = normalize_output(tc["expected_output"])
            is_match = actual_norm == expected_norm
            case_status = "Accepted" if is_match else "Wrong Answer"
            if is_match:
                passed_count += 1
            elif failure_status is None:
                failure_status = "Wrong Answer"
        else:
            is_match = False
            case_status = exec_res.status
            if failure_status is None:
                failure_status = exec_res.status

        case_results.append(
            {
                "case_number": idx,
                "is_hidden": False,
                "passed": is_match,
                "status": case_status,
                "input": tc["input_data"],
                "expected_output": tc["expected_output"],
                "actual_output": exec_res.stdout,
                "stderr": exec_res.stderr,
                "execution_time_ms": exec_res.execution_time_ms,
                "memory_kb": exec_res.memory_kb,
            }
        )

    all_passed = passed_count == len(sample_cases)
    overall_status = (
        "Accepted"
        if all_passed
        else (failure_status or ("Partial Accepted" if passed_count > 0 else "Wrong Answer"))
    )

    return {
        "status": overall_status,
        "mode": "sample_tests",
        "language": canonical_lang,
        "passed": all_passed,
        "passed_count": passed_count,
        "total_count": len(sample_cases),
        "stdout": first_stdout,
        "stderr": compile_error_msg or first_stderr,
        "compile_output": compile_error_msg,
        "execution_time_ms": round(max_time_ms, 2),
        "memory_kb": round(max_mem_kb, 2),
        "backend_used": backend_used,
        "test_case_results": case_results,
    }


def evaluate_coding_submission(
    *,
    problem: Any,
    source_code: str,
    language: str,
    max_marks: Optional[float] = None,
    item: Any = None,
    include_hidden_details: bool = False,
) -> Dict[str, Any]:
    """Judge student code against all (public + hidden) test cases safely.

    Hidden test cases (`is_hidden=True`) are evaluated server-side and NEVER
    returned with inputs or expected outputs unless `include_hidden_details=True`
    (strictly reserved for verified admin views).
    """
    problem_max_marks = float(max_marks if max_marks is not None else (getattr(problem, "points", 100) or 100))

    if not source_code or not source_code.strip():
        return {
            "status": "Compilation Error",
            "language": (language or "python").strip().lower(),
            "total_test_cases": 0,
            "passed_test_cases": 0,
            "failed_test_cases": 0,
            "score": 0.0,
            "max_score": round(problem_max_marks, 2),
            "execution_time_ms": 0.0,
            "memory_used_kb": 0.0,
            "compile_output": "Source code cannot be empty.",
            "error_message": "Source code cannot be empty.",
            "test_case_results": [],
        }

    if len(source_code) > MAX_SOURCE_CODE_LENGTH:
        raise ValueError("Source code exceeds maximum allowed length (100 KB).")

    canonical_lang = validate_language_for_problem(language, problem)
    validate_code_security(canonical_lang, source_code)
    timeout_sec = float(getattr(problem, "time_limit_seconds", 2.0) or 2.0)
    memory_mb = int(getattr(problem, "memory_limit_mb", 256) or 256)

    test_cases = _collect_test_cases(problem, item=item, public_only=False)
    if not test_cases:
        # Fallback to sample if test_cases table has no entries yet
        test_cases = _collect_test_cases(problem, item=item, public_only=True)

    total_cases = len(test_cases)
    if total_cases == 0:
        return {
            "status": "Runtime Error",
            "language": canonical_lang,
            "total_test_cases": 0,
            "passed_test_cases": 0,
            "failed_test_cases": 0,
            "score": 0.0,
            "max_score": round(problem_max_marks, 2),
            "execution_time_ms": 0.0,
            "memory_used_kb": 0.0,
            "compile_output": "",
            "error_message": "No test cases configured for this coding problem.",
            "test_case_results": [],
        }

    total_case_weight = sum(float(tc.get("marks") or 1.0) for tc in test_cases) or float(total_cases)
    earned_weight = 0.0
    passed_count = 0
    total_time_ms = 0.0
    peak_memory_kb = 0.0
    compile_output = ""
    first_error_msg = ""
    first_failure_verdict: Optional[str] = None
    backend_used = ""
    redacted_results: List[Dict[str, Any]] = []

    for idx, tc in enumerate(test_cases, start=1):
        exec_res: SandboxExecutionResult = execute_in_sandbox(
            language=canonical_lang,
            source_code=source_code,
            stdin_data=tc["input_data"],
            timeout_seconds=timeout_sec,
            memory_limit_mb=memory_mb,
        )
        backend_used = exec_res.backend_used
        total_time_ms += exec_res.execution_time_ms
        peak_memory_kb = max(peak_memory_kb, exec_res.memory_kb)

        if exec_res.status == "Compilation Error":
            compile_output = exec_res.compile_output or exec_res.stderr
            first_error_msg = compile_output
            return {
                "status": "Compilation Error",
                "language": canonical_lang,
                "total_test_cases": total_cases,
                "passed_test_cases": 0,
                "failed_test_cases": total_cases,
                "score": 0.0,
                "max_score": round(problem_max_marks, 2),
                "execution_time_ms": round(exec_res.execution_time_ms, 2),
                "memory_used_kb": round(peak_memory_kb, 2),
                "backend_used": backend_used,
                "compile_output": compile_output,
                "error_message": compile_output,
                "test_case_results": [
                    {
                        "case_number": n,
                        "is_hidden": bool(case["is_hidden"]),
                        "passed": False,
                        "status": "Compilation Error",
                        "execution_time_ms": exec_res.execution_time_ms if n == 1 else 0.0,
                        "memory_kb": 0.0,
                    }
                    for n, case in enumerate(test_cases, start=1)
                ],
            }

        is_passed = False
        case_status = exec_res.status
        if exec_res.status == "OK":
            actual_norm = normalize_output(exec_res.stdout)
            expected_norm = normalize_output(tc["expected_output"])
            is_passed = actual_norm == expected_norm
            case_status = "Accepted" if is_passed else "Wrong Answer"
        else:
            if not first_error_msg and exec_res.stderr:
                first_error_msg = exec_res.stderr

        if is_passed:
            passed_count += 1
            earned_weight += float(tc.get("marks") or 1.0)
        elif first_failure_verdict is None:
            first_failure_verdict = case_status

        row: Dict[str, Any] = {
            "case_number": idx,
            "is_hidden": bool(tc["is_hidden"]),
            "passed": is_passed,
            "status": case_status,
            "execution_time_ms": round(exec_res.execution_time_ms, 2),
            "memory_kb": round(exec_res.memory_kb, 2),
        }
        # Only reveal I/O for non-hidden sample tests or explicit admin calls
        if not tc["is_hidden"] or include_hidden_details:
            row["input"] = tc["input_data"]
            row["expected_output"] = tc["expected_output"]
            row["actual_output"] = exec_res.stdout
            if exec_res.stderr:
                row["stderr"] = exec_res.stderr

        redacted_results.append(row)

    failed_count = total_cases - passed_count
    score = round((earned_weight / total_case_weight) * problem_max_marks, 2) if total_cases > 0 else 0.0

    if passed_count == total_cases:
        final_status = "Accepted"
        score = round(problem_max_marks, 2)
    elif passed_count > 0:
        final_status = "Partial Accepted"
    else:
        final_status = first_failure_verdict or "Wrong Answer"

    return {
        "status": final_status,
        "language": canonical_lang,
        "total_test_cases": total_cases,
        "passed_test_cases": passed_count,
        "failed_test_cases": failed_count,
        "score": score,
        "max_score": round(problem_max_marks, 2),
        "execution_time_ms": round(total_time_ms, 2),
        "memory_used_kb": round(peak_memory_kb, 2),
        "backend_used": backend_used,
        "compile_output": compile_output,
        "error_message": first_error_msg,
        "test_case_results": redacted_results,
    }
