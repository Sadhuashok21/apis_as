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
            # Provide non-revealing failure category/hint if failed
            res_item = {
                "test_case_id": tc.test_case_id,
                "order": tc.order,
                "is_sample": False,
                "is_hidden": True,
                "category": getattr(tc, "category", "Basic"),
                "verdict": verdict,
                "execution_time_ms": duration,
                "memory_kb": memory,
            }
            if verdict != "Accepted" and getattr(tc, "explanation", ""):
                res_item["failure_category"] = getattr(tc, "category", "Boundary")
                res_item["note"] = f"Failed on {getattr(tc, 'category', 'Hidden')} test condition."
            test_results.append(res_item)
        else:
            # Public sample test case
            test_results.append({
                "test_case_id": tc.test_case_id,
                "order": tc.order,
                "is_sample": tc.is_sample,
                "is_hidden": False,
                "category": getattr(tc, "category", "Sample"),
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

    # Evaluate performance efficiency
    avg_duration = (total_duration_ms / total_count) if total_count > 0 else 0
    performance_status = "Optimal"
    if overall_verdict == "Accepted":
        if avg_duration > 1500:
            performance_status = "Needs improvement"
        else:
            performance_status = "Optimal"

    return {
        "verdict": overall_verdict,
        "passed_count": passed_count,
        "total_count": total_count,
        "total_duration_ms": round(total_duration_ms, 2),
        "max_memory_kb": round(max_memory_kb, 2),
        "performance_status": performance_status,
        "expected_complexity": getattr(problem, "expected_complexity", ""),
        "test_results": test_results,
    }


def evaluate_assessment_question_item(
    question_item,
    language: str,
    code: str,
    is_sample_only: bool = False,
    is_admin_test: bool = False,
    timeout_per_case: float = 4.0
) -> Dict[str, Any]:
    """
    Executes submitted code against an AssessmentQuestionItem's test cases
    (or falls back to linked problem's test cases).
    Protects confidential hidden test cases for students; allows admin inspection if is_admin_test=True.
    """
    direct_tests = list(question_item.test_cases.filter(is_active=True).order_by("order", "id"))

    if not direct_tests and question_item.problem:
        return evaluate_test_cases(
            problem=question_item.problem,
            language=language,
            code=code,
            is_sample_only=is_sample_only,
            timeout_per_case=timeout_per_case
        )

    if is_sample_only:
        test_cases = [tc for tc in direct_tests if tc.test_type == "Public"]
    else:
        test_cases = direct_tests

    if not test_cases:
        return {
            "verdict": "Accepted" if code.strip() else "Wrong Answer",
            "passed_count": 1 if code.strip() else 0,
            "total_count": 1,
            "total_duration_ms": 1.0,
            "max_memory_kb": 128,
            "performance_status": "Optimal",
            "expected_complexity": getattr(question_item, "expected_complexity", ""),
            "test_results": []
        }

    passed_count = 0
    test_results: List[Dict[str, Any]] = []
    total_duration_ms = 0.0
    max_memory_kb = 0.0
    first_failure_verdict = None

    for tc in test_cases:
        is_hidden = (tc.test_type == "Hidden")
        exec_code, stdin_data = build_execution_harness(language, code, tc.input_data or "", question_item.slug or "question")

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

        if status_str == "compile_error":
            verdict = "Compile Error"
        elif status_str == "timeout":
            verdict = "Time Limit Exceeded"
        elif exit_code != 0:
            verdict = "Runtime Error"
        else:
            norm_actual = normalize_output(stdout_raw)
            norm_expected = normalize_output(tc.expected_output or "")
            if norm_actual == norm_expected or (not norm_expected and exit_code == 0):
                verdict = "Accepted"
            else:
                verdict = "Wrong Answer"

        if verdict == "Accepted":
            passed_count += 1
        elif first_failure_verdict is None:
            first_failure_verdict = verdict

        if is_hidden and not is_admin_test and not is_sample_only:
            # STRICT CONFIDENTIALITY: Hidden test case details are NEVER exposed to candidates
            res_item = {
                "test_case_id": tc.case_id or f"tc_{tc.id}",
                "order": tc.order,
                "is_sample": False,
                "is_hidden": True,
                "verdict": verdict,
                "execution_time_ms": duration,
                "memory_kb": memory,
            }
            if verdict != "Accepted" and tc.explanation:
                res_item["note"] = f"Failed on hidden edge condition."
            test_results.append(res_item)
        else:
            test_results.append({
                "test_case_id": tc.case_id or f"tc_{tc.id}",
                "order": tc.order,
                "is_sample": not is_hidden,
                "is_hidden": is_hidden,
                "input_data": tc.input_data,
                "expected_output": tc.expected_output,
                "actual_output": stdout_raw.strip(),
                "verdict": verdict,
                "execution_time_ms": duration,
                "memory_kb": memory,
                "error_message": stderr_raw.strip(),
            })

    total_count = len(test_cases)
    overall_verdict = "Accepted" if (passed_count == total_count) else (first_failure_verdict or "Wrong Answer")
    avg_duration = (total_duration_ms / total_count) if total_count > 0 else 0
    performance_status = "Optimal" if (overall_verdict == "Accepted" and avg_duration <= 1500) else "Needs improvement"

    return {
        "verdict": overall_verdict,
        "passed_count": passed_count,
        "total_count": total_count,
        "total_duration_ms": round(total_duration_ms, 2),
        "max_memory_kb": round(max_memory_kb, 2),
        "performance_status": performance_status,
        "expected_complexity": getattr(question_item, "expected_complexity", ""),
        "test_results": test_results,
    }

