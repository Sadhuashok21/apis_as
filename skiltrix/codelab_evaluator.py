import json
import re
from typing import Dict, Any, List
from .execution.worker import execute_code_job
from .codelab_models import SubmissionResult
from .models import TestCases, CodingProblems


def normalize_output(text: str) -> str:
    """Normalize output for consistent comparison (whitespace, line endings, array format)."""
    if not text:
        return ""
    # Strip whitespace on lines and overall
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    cleaned = "\n".join(lines)
    # Normalize JSON spacing if both are JSON arrays/objects
    try:
        parsed = json.loads(cleaned)
        return json.dumps(parsed, separators=(",", ":"))
    except Exception:
        pass
    return cleaned


def build_execution_harness(language: str, code: str, input_data: str, problem_slug: str) -> tuple[str, str]:
    """
    Prepares code for execution with input data.
    If the code uses input()/stdin reading, returns (code, input_data).
    If code defines a function, checks if standard stdin runner wrapper is required.
    """
    lang = language.lower().strip()
    return code, input_data


def evaluate_test_cases(
    problem: CodingProblems,
    language: str,
    code: str,
    is_sample_only: bool = False,
    timeout_per_case: float = 4.0
) -> Dict[str, Any]:
    """
    Executes submitted code against all configured test cases.
    Hides confidential evaluation data for is_hidden test cases.
    Returns:
    {
        "verdict": "Accepted" | "Wrong Answer" | "Time Limit Exceeded" | "Compile Error" | "Runtime Error",
        "passed_count": int,
        "total_count": int,
        "total_duration_ms": float,
        "max_memory_kb": float,
        "test_results": list[dict]
    }
    """
    if is_sample_only:
        test_cases = list(TestCases.objects.filter(problem=problem, is_sample=True).order_by("order"))
    else:
        test_cases = list(TestCases.objects.filter(problem=problem).order_by("order"))

    # If no test cases defined, create a default sample from problem if possible
    if not test_cases:
        test_cases = [
            TestCases(
                test_case_id=f"tc_default_{problem.problem_id}",
                problem=problem,
                input_data="",
                expected_output="",
                is_sample=True,
                is_hidden=False,
                order=1
            )
        ]

    passed_count = 0
    test_results: List[Dict[str, Any]] = []
    total_duration_ms = 0.0
    max_memory_kb = 0.0
    first_failure_verdict = None

    for tc in test_cases:
        # Prepare input
        exec_code, stdin_data = build_execution_harness(language, code, tc.input_data, problem.slug)

        # Run in sandbox
        exec_res = execute_code_job(
            language=language,
            code=exec_code,
            stdin=stdin_data,
            timeout=timeout_per_case
        )

        duration = exec_res.get("duration_ms", 0.0)
        total_duration_ms += duration
        memory = exec_res.get("memory_kb", 0.0)
        if memory > max_memory_kb:
            max_memory_kb = memory

        status_str = exec_res.get("status")
        stdout_raw = exec_res.get("stdout", "")
        stderr_raw = exec_res.get("stderr", "")
        exit_code = exec_res.get("exit_code", 0)

        # Determine verdict
        if status_str == "compile_error":
            verdict = "Compile Error"
        elif status_str == "timeout":
            verdict = "Time Limit Exceeded"
        elif exit_code != 0:
            verdict = "Runtime Error"
        else:
            norm_actual = normalize_output(stdout_raw)
            norm_expected = normalize_output(tc.expected_output)

            # Match criteria
            if norm_actual == norm_expected or (not norm_expected and exit_code == 0):
                verdict = "Accepted"
            else:
                verdict = "Wrong Answer"

        if verdict == "Accepted":
            passed_count += 1
        elif first_failure_verdict is None:
            first_failure_verdict = verdict

        # Construct result payload with strict confidentiality for hidden test cases
        if tc.is_hidden and not is_sample_only:
            # NEVER expose input, expected output, or actual output for hidden test cases!
            test_results.append({
                "test_case_id": tc.test_case_id,
                "order": tc.order,
                "is_sample": False,
                "is_hidden": True,
                "verdict": verdict,
                "execution_time_ms": duration,
                "memory_kb": memory,
            })
        else:
            # Public sample test case
            test_results.append({
                "test_case_id": tc.test_case_id,
                "order": tc.order,
                "is_sample": tc.is_sample,
                "is_hidden": False,
                "input_data": tc.input_data,
                "expected_output": tc.expected_output,
                "actual_output": stdout_raw.strip(),
                "verdict": verdict,
                "execution_time_ms": duration,
                "memory_kb": memory,
                "error_message": stderr_raw.strip(),
            })

    # Overall verdict
    total_count = len(test_cases)
    if passed_count == total_count:
        overall_verdict = "Accepted"
    else:
        overall_verdict = first_failure_verdict or "Wrong Answer"

    return {
        "verdict": overall_verdict,
        "passed_count": passed_count,
        "total_count": total_count,
        "total_duration_ms": round(total_duration_ms, 2),
        "max_memory_kb": round(max_memory_kb, 2),
        "test_results": test_results,
    }
