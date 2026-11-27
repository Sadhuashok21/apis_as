"""REST APIs for SkilTrix Coding Assessment module (Student & Admin endpoints)."""

from __future__ import annotations

import csv
from datetime import timedelta
import io
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from sfs.models import AllUsers

from .coding_assessment_serializers import (
    AdminTestCaseSerializer,
    AssessmentAssignmentSerializer,
    CodingAssessmentSummarySerializer,
    CodingProblemAdminSerializer,
    CodingProblemCandidateSerializer,
    CodingSubmissionRecordSerializer,
    StudentBatchSerializer,
    StudentCompactSerializer,
    compute_schedule_status,
)
from .judge_service import (
    DEFAULT_STARTER_CODES,
    evaluate_coding_submission,
    get_starter_codes_for_problem,
    run_coding_code,
)
from .django_assessment_runner import (
    DEFAULT_DJANGO_PROJECT_TEMPLATE,
    compute_locked_files,
    evaluate_django_project_problem,
    parse_django_archive_bytes,
)
from .codelab_models import CodeProject, ProjectFile, WorkspaceSession
from .codelab_runner import sync_db_files_to_workspace, sync_workspace_files_to_db
from .models import (
    AssessmentAssignment,
    AssessmentAttempt,
    AssessmentEvent,
    AssessmentQuestion,
    AssessmentQuestionItem,
    AssessmentSection,
    CodeSubmissions,
    CodingAssessment,
    CodingProblems,
    StudentBatch,
    TestCases,
    UserProblemStatus,
)

TERMINAL_ATTEMPT_STATUSES = ("completed", "timed_out", "disqualified")
ACTIVE_ATTEMPT_STATUS = "in_progress"


class AssessmentRunRateThrottle(UserRateThrottle):
    scope = "assessment_run"

    def get_rate(self):
        return (
            getattr(settings, "REST_FRAMEWORK", {})
            .get("DEFAULT_THROTTLE_RATES", {})
            .get("assessment_run", "30/min")
        )


class AssessmentSubmitRateThrottle(UserRateThrottle):
    scope = "assessment_submit"

    def get_rate(self):
        return (
            getattr(settings, "REST_FRAMEWORK", {})
            .get("DEFAULT_THROTTLE_RATES", {})
            .get("assessment_submit", "15/min")
        )


def _csv_safe(value: Any) -> str:
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def _parse_iso_dt(value: Any):
    if not value:
        return None
    if hasattr(value, "tzinfo"):
        return value
    dt = parse_datetime(str(value))
    if dt is not None and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _get_user_assignments_map(user: AllUsers) -> Dict[str, Dict[str, Any]]:
    """Return {assessment_id: {'start_time': ..., 'end_time': ...}} for user & batches."""
    assignments = (
        AssessmentAssignment.objects.filter(
            Q(student=user) | Q(batch__students=user)
        )
        .select_related("assessment")
        .order_by("created_at")
    )
    mapping: Dict[str, Dict[str, Any]] = {}
    for assign in assignments:
        aid = assign.assessment.assessment_id
        # Direct student assignment overrides batch assignment cleanly
        if aid not in mapping or assign.student_id == user.user_id:
            mapping[aid] = {
                "start_time": assign.start_time,
                "end_time": assign.end_time,
                "assignment_id": assign.assignment_id,
            }
    return mapping


def _check_student_access(
    assessment: CodingAssessment, user: AllUsers
) -> Tuple[bool, Optional[str], Optional[Any], Optional[Any]]:
    """Verify visibility, assignment eligibility, and effective schedule window."""
    if not assessment.active and not user.is_staff:
        return False, "This assessment is currently inactive.", None, None

    assignments = _get_user_assignments_map(user)
    override = assignments.get(assessment.assessment_id)

    if assessment.assignment_mode == "assigned" and not user.is_staff and not override:
        return (
            False,
            "You are not assigned to this assessment. Contact your administrator.",
            None,
            None,
        )

    eff_start = (override.get("start_time") if override else None) or assessment.start_time
    eff_end = (override.get("end_time") if override else None) or assessment.end_time
    return True, None, eff_start, eff_end


def _collect_assessment_entries(assessment: CodingAssessment) -> List[Dict[str, Any]]:
    """Collect unified ordered list of AssessmentQuestionItem + legacy AssessmentQuestion entries."""
    entries: List[Dict[str, Any]] = []
    seen_problem_ids = set()

    items = (
        AssessmentQuestionItem.objects.filter(assessment=assessment, status="Published")
        .select_related("problem", "section")
        .order_by("section__order", "order", "id")
    )
    for item in items:
        if item.problem_id:
            seen_problem_ids.add(item.problem.problem_id)
        entries.append(
            {
                "kind": "item",
                "item_id": item.item_id,
                "item": item,
                "problem": item.problem,
                "question_type": item.question_type,
                "marks": float(item.marks or 1),
                "negative_marks": float(item.negative_marks or 0),
                "section_id": item.section.section_id if item.section else None,
                "section_title": item.section.title if item.section else "General",
                "title": item.title,
                "difficulty": item.difficulty,
            }
        )

    legacy_questions = (
        AssessmentQuestion.objects.filter(assessment=assessment)
        .select_related("problem")
        .order_by("order", "id")
    )
    for aq in legacy_questions:
        if aq.problem.problem_id in seen_problem_ids:
            continue
        entries.append(
            {
                "kind": "legacy",
                "item_id": aq.item_id,
                "item": None,
                "problem": aq.problem,
                "question_type": "coding",
                "marks": float(aq.marks or aq.problem.points or 100),
                "negative_marks": 0.0,
                "section_id": "sec_coding",
                "section_title": "Coding Problems",
                "title": aq.problem.title,
                "difficulty": aq.problem.difficulty,
            }
        )

    return entries


def _strip_option_secrets(raw_options: Any) -> Any:
    """Remove any embedded correctness flags inside stored option JSON objects."""
    if not isinstance(raw_options, list):
        return raw_options
    sanitized = []
    for opt in raw_options:
        if isinstance(opt, dict):
            clean = {
                k: v
                for k, v in opt.items()
                if k not in ("is_correct", "correct", "answer")
            }
            sanitized.append(clean)
        else:
            sanitized.append(opt)
    return sanitized


def _ensure_codelab_project_for_attempt(
    attempt: AssessmentAttempt,
    item_id: str,
    problem: CodingProblems,
    user: AllUsers,
) -> Dict[str, Any]:
    """Ensure an isolated CodeLab CodeProject exists for this (attempt, django_debug item)."""
    drafts = dict(attempt.saved_drafts or {})
    codelab_map = dict(drafts.get("codelab_projects") or {})
    existing_pid = codelab_map.get(item_id)
    locked_paths = compute_locked_files(problem.project_files or {})

    if existing_pid:
        proj = CodeProject.objects.filter(project_id=existing_pid).first()
        if proj is not None:
            return {"codelab_project_id": proj.project_id, "locked_paths": locked_paths}

    proj_id = f"proj_asmt_{uuid.uuid4().hex[:12]}"
    proj = CodeProject.objects.create(
        project_id=proj_id,
        user=user,
        title=problem.title[:180],
        slug=f"{slugify(problem.title)[:40]}-{proj_id[-6:]}",
        project_type="django",
        language="python",
        description=problem.description[:500],
        is_public=False,
        execution_settings={
            "assessment_id": attempt.assessment_id,
            "attempt_id": attempt.attempt_id,
            "item_id": item_id,
            "problem_id": problem.problem_id,
            "locked_paths": locked_paths,
        },
        status="ready",
    )

    starter_files = dict(problem.project_files or {})
    for rel_path, content in starter_files.items():
        clean_path = str(rel_path).replace("\\", "/").lstrip("/")
        if not clean_path:
            continue
        text = str(content or "")
        ProjectFile.objects.create(
            file_id=f"file_{uuid.uuid4().hex[:12]}",
            project=proj,
            path=clean_path,
            name=clean_path.split("/")[-1],
            is_directory=False,
            content=text,
            size_bytes=len(text.encode("utf-8")),
        )

    workspace_dir = sync_db_files_to_workspace(proj)
    try:
        from .codelab_sql import ProjectDatabaseCatalog
        cat = ProjectDatabaseCatalog(workspace_dir=workspace_dir, project_id=proj.project_id)
        cat.set_django_database("default_db")
    except Exception:
        pass

    WorkspaceSession.objects.get_or_create(
        project=proj,
        defaults={
            "session_id": f"sess_{uuid.uuid4().hex[:12]}",
            "user": user,
            "status": "stopped",
        },
    )

    codelab_map[item_id] = proj.project_id
    drafts["codelab_projects"] = codelab_map
    attempt.saved_drafts = drafts
    attempt.save(update_fields=["saved_drafts"])
    return {"codelab_project_id": proj.project_id, "locked_paths": locked_paths}


def _collect_files_for_django_eval(
    attempt: Optional[AssessmentAttempt],
    item_id: str,
    problem: CodingProblems,
    candidate_override: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Assemble candidate workspace files from starter + CodeLab DB files + unsaved overrides."""
    merged: Dict[str, str] = {
        str(k).replace("\\", "/").lstrip("/"): str(v or "")
        for k, v in (problem.project_files or {}).items()
    }
    locked_set = set(compute_locked_files(problem.project_files or {}))

    if attempt is not None:
        codelab_map = (attempt.saved_drafts or {}).get("codelab_projects") or {}
        proj_id = codelab_map.get(item_id)
        if proj_id:
            proj = CodeProject.objects.filter(project_id=proj_id).first()
            if proj is not None:
                try:
                    sync_workspace_files_to_db(proj)
                except Exception:
                    pass
                for pf in ProjectFile.objects.filter(project=proj, is_directory=False):
                    if pf.path not in locked_set:
                        merged[pf.path] = pf.content or ""

    if isinstance(candidate_override, dict):
        for raw_k, raw_v in candidate_override.items():
            clean_k = str(raw_k).replace("\\", "/").lstrip("/")
            if clean_k and clean_k not in locked_set:
                merged[clean_k] = str(raw_v or "")

    return merged


def _serialize_candidate_questions(
    assessment: CodingAssessment,
    *,
    attempt: Optional[AssessmentAttempt] = None,
    user: Optional[AllUsers] = None,
) -> List[Dict[str, Any]]:
    """Serialize all assessment questions WITHOUT exposing hidden tests or answers."""
    entries = _collect_assessment_entries(assessment)
    serialized: List[Dict[str, Any]] = []

    for idx, entry in enumerate(entries, start=1):
        problem = entry["problem"]
        item = entry["item"]
        base: Dict[str, Any] = {
            "index": idx - 1,
            "item_id": entry["item_id"],
            "question_type": entry["question_type"],
            "section_id": entry["section_id"],
            "section_title": entry["section_title"],
            "title": entry["title"],
            "difficulty": entry["difficulty"],
            "marks": entry["marks"],
            "negative_marks": entry["negative_marks"],
            "supported_languages": assessment.supported_languages
            or ["python", "java", "c", "cpp", "javascript"],
        }

        if problem is not None:
            prob_data = CodingProblemCandidateSerializer(problem).data
            base["problem"] = prob_data
            base["prompt"] = prob_data["description"]
            base["input_format"] = prob_data["input_format"]
            base["output_format"] = prob_data["output_format"]
            base["constraints"] = prob_data["constraints"]
            base["public_test_cases"] = prob_data["public_test_cases"]
            base["starter_codes"] = prob_data["starter_codes"]
            base["project_files"] = prob_data.get("project_files") or {}
            if problem.question_type == "django_debug" and attempt is not None and user is not None:
                cl_meta = _ensure_codelab_project_for_attempt(attempt, entry["item_id"], problem, user)
                base["codelab_project_id"] = cl_meta["codelab_project_id"]
                base["locked_paths"] = cl_meta["locked_paths"]
            base["time_limit_seconds"] = prob_data["time_limit_seconds"]
            base["memory_limit_mb"] = prob_data["memory_limit_mb"]
        elif item is not None:
            base["problem"] = None
            base["prompt"] = item.prompt
            base["instructions"] = item.instructions
            base["options"] = _strip_option_secrets(item.options)
            base["buggy_code"] = item.buggy_code
            base["starter_code"] = item.starter_code
            base["examples"] = item.examples
            base["constraints"] = item.constraints
            base["input_format"] = item.input_format
            base["output_format"] = item.output_format
            base["language"] = item.language
            base["public_test_cases"] = [
                {
                    "test_case_id": tc.case_id,
                    "input_data": tc.input_data,
                    "expected_output": tc.expected_output,
                    "explanation": tc.explanation,
                    "points": tc.weight,
                    "order": tc.order,
                }
                for tc in item.test_cases.filter(
                    is_active=True, test_type="Sample"
                ).order_by("order", "case_id")
            ]

        serialized.append(base)

    return serialized


def _find_entry_in_assessment(
    assessment: CodingAssessment, *, item_id: Optional[str] = None, problem_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    entries = _collect_assessment_entries(assessment)
    for entry in entries:
        if item_id and entry["item_id"] == item_id:
            return entry
        if problem_id and entry["problem"] and entry["problem"].problem_id == problem_id:
            return entry
    return None


def _is_mcq_answer_correct(item: AssessmentQuestionItem, selected: Any) -> bool:
    expected = item.correct_answers or []
    if not expected or selected in (None, "", []):
        return False
    if isinstance(selected, list):
        sel_set = {str(x).strip().lower() for x in selected if str(x).strip()}
        exp_set = {str(x).strip().lower() for x in expected if str(x).strip()}
        return sel_set == exp_set and bool(exp_set)
    sel_val = str(selected).strip().lower()
    exp_list = [str(x).strip().lower() for x in expected if str(x).strip()]
    return sel_val in exp_list


def _record_problem_submission(
    *,
    user: AllUsers,
    assessment: CodingAssessment,
    attempt: AssessmentAttempt,
    problem: CodingProblems,
    language: str,
    source_code: str,
    judge_res: Dict[str, Any],
    is_final: bool = False,
) -> CodeSubmissions:
    submission = CodeSubmissions.objects.create(
        submission_id=f"sub_{uuid.uuid4().hex[:12]}",
        user=user,
        problem=problem,
        assessment=assessment,
        attempt=attempt,
        language=judge_res.get("language") or language,
        code=source_code,
        status=judge_res["status"],
        passed_test_cases=int(judge_res["passed_test_cases"]),
        total_test_cases=int(judge_res["total_test_cases"]),
        execution_time_ms=float(judge_res["execution_time_ms"]),
        memory_kb=float(judge_res["memory_used_kb"]),
        error_message=(judge_res.get("compile_output") or judge_res.get("error_message") or "")[:2000],
        score=float(judge_res["score"]),
        max_score=float(judge_res["max_score"]),
        is_final_submission=is_final,
    )

    ups, _ = UserProblemStatus.objects.get_or_create(
        user=user,
        problem=problem,
        defaults={"status_id": f"ups_{uuid.uuid4().hex[:10]}"},
    )
    if not ups.status_id:
        ups.status_id = f"ups_{uuid.uuid4().hex[:10]}"
    ups.attempts = (ups.attempts or 0) + 1
    ups.last_attempt_at = timezone.now()
    if judge_res["status"] == "Accepted":
        ups.solved = True
        if not ups.best_submission or submission.execution_time_ms <= ups.best_submission.execution_time_ms:
            ups.best_submission = submission
    elif not ups.best_submission or submission.score >= ups.best_submission.score:
        ups.best_submission = submission
    ups.save()

    return submission


@transaction.atomic
def finalize_assessment_attempt(
    attempt: AssessmentAttempt, *, auto_submitted: bool = False
) -> Dict[str, Any]:
    """Finalize an attempt safely, evaluate any unsubmitted drafts, and compute analytics."""
    attempt = AssessmentAttempt.objects.select_for_update().select_related(
        "assessment", "user"
    ).get(pk=attempt.pk)
    assessment = attempt.assessment
    entries = _collect_assessment_entries(assessment)
    now = timezone.now()

    already_terminal = attempt.status in TERMINAL_ATTEMPT_STATUSES and attempt.completed_at is not None

    drafts = attempt.saved_drafts or {}
    coding_drafts = drafts.get("coding_drafts") if isinstance(drafts, dict) else {}
    if not isinstance(coding_drafts, dict):
        # Support flat saved_drafts map keyed by item_id or problem_id
        coding_drafts = drafts if isinstance(drafts, dict) else {}

    selected_answers = attempt.selected_answers or {}
    q_states = dict(attempt.question_states or {})

    total_score = 0.0
    max_possible_score = 0.0
    problems_attempted = 0
    problems_solved = 0
    test_cases_passed = 0
    test_cases_total = 0
    section_totals: Dict[str, Dict[str, float]] = {}
    problem_breakdown: List[Dict[str, Any]] = []

    for entry in entries:
        item_id = entry["item_id"]
        marks = float(entry["marks"] or 0.0)
        max_possible_score += marks
        sec_title = entry["section_title"] or "General"
        sec_bucket = section_totals.setdefault(
            sec_title, {"score": 0.0, "max_score": 0.0, "solved": 0, "total": 0}
        )
        sec_bucket["max_score"] += marks
        sec_bucket["total"] += 1

        problem = entry["problem"]
        item = entry["item"]

        if problem is not None:
            # Find latest submission for this attempt + problem
            latest_sub = (
                CodeSubmissions.objects.filter(
                    attempt=attempt, user=attempt.user, problem=problem
                )
                .order_by("-created_at", "-id")
                .first()
            )

            # Evaluate edited draft when finalizing or auto-submitting if unsubmitted or updated,
            # ignoring unmodified starter code templates.
            draft_entry = coding_drafts.get(item_id) or coding_drafts.get(problem.problem_id)
            if not already_terminal and isinstance(draft_entry, dict):
                if problem.question_type == "django_debug" and isinstance(draft_entry.get("files"), dict):
                    draft_files = draft_entry["files"]
                    is_meaningful_edit = draft_files != (problem.project_files or {})
                    serialized_code = json.dumps(draft_files)
                    has_newer_code = latest_sub is None or serialized_code != (latest_sub.code or "")
                    if is_meaningful_edit and has_newer_code:
                        try:
                            judge_res = evaluate_django_project_problem(
                                problem=problem,
                                candidate_files=draft_files,
                                max_marks=marks,
                                include_hidden=True,
                            )
                            latest_sub = _record_problem_submission(
                                user=attempt.user,
                                assessment=assessment,
                                attempt=attempt,
                                problem=problem,
                                language="django",
                                source_code=serialized_code,
                                judge_res=judge_res,
                                is_final=True,
                            )
                        except Exception:
                            pass
                else:
                    draft_code = (draft_entry.get("code") or draft_entry.get("source_code") or "").strip()
                    draft_lang = draft_entry.get("language") or "python"
                    starter_for_lang = (get_starter_codes_for_problem(problem).get(draft_lang) or "").strip()
                    is_meaningful_edit = bool(draft_code) and draft_code != starter_for_lang
                    has_newer_code = latest_sub is None or draft_code != (latest_sub.code or "").strip()
                    if is_meaningful_edit and has_newer_code:
                        try:
                            judge_res = evaluate_coding_submission(
                                problem=problem,
                                source_code=draft_entry.get("code") or draft_entry.get("source_code") or "",
                                language=draft_lang,
                                max_marks=marks,
                                item=item,
                                include_hidden_details=False,
                            )
                            latest_sub = _record_problem_submission(
                                user=attempt.user,
                                assessment=assessment,
                                attempt=attempt,
                                problem=problem,
                                language=draft_lang,
                                source_code=draft_entry.get("code") or draft_entry.get("source_code") or "",
                                judge_res=judge_res,
                                is_final=True,
                            )
                        except Exception:
                            pass

            prob_tc_total = problem.test_cases.count() or (
                1 if (problem.sample_input or problem.sample_output) else 0
            )
            test_cases_total += prob_tc_total

            if latest_sub is not None:
                problems_attempted += 1
                sub_score = min(marks, float(latest_sub.score or 0.0))
                if latest_sub.max_score and latest_sub.max_score != marks:
                    sub_score = round(
                        (float(latest_sub.score or 0.0) / float(latest_sub.max_score)) * marks,
                        2,
                    )
                total_score += sub_score
                sec_bucket["score"] += sub_score
                test_cases_passed += int(latest_sub.passed_test_cases or 0)
                if latest_sub.status == "Accepted":
                    problems_solved += 1
                    sec_bucket["solved"] += 1
                if not already_terminal and latest_sub.id:
                    latest_sub.is_final_submission = True
                    latest_sub.save(update_fields=["is_final_submission"])

                q_states[item_id] = "submitted"
                problem_breakdown.append(
                    {
                        "item_id": item_id,
                        "problem_id": problem.problem_id,
                        "title": problem.title,
                        "question_type": "coding",
                        "difficulty": problem.difficulty,
                        "language": latest_sub.language,
                        "status": latest_sub.status,
                        "passed_test_cases": int(latest_sub.passed_test_cases),
                        "total_test_cases": int(latest_sub.total_test_cases or prob_tc_total),
                        "score": round(sub_score, 2),
                        "max_score": round(marks, 2),
                        "execution_time_ms": latest_sub.execution_time_ms,
                        "memory_kb": latest_sub.memory_kb,
                        "submission_id": latest_sub.submission_id,
                    }
                )
            else:
                problem_breakdown.append(
                    {
                        "item_id": item_id,
                        "problem_id": problem.problem_id,
                        "title": problem.title,
                        "question_type": "coding",
                        "difficulty": problem.difficulty,
                        "language": None,
                        "status": "Not Attempted",
                        "passed_test_cases": 0,
                        "total_test_cases": prob_tc_total,
                        "score": 0.0,
                        "max_score": round(marks, 2),
                        "execution_time_ms": 0.0,
                        "memory_kb": 0.0,
                        "submission_id": None,
                    }
                )
        elif item is not None:
            selected = selected_answers.get(item_id)
            has_answer = selected not in (None, "", [])
            test_cases_total += 1
            if has_answer:
                problems_attempted += 1
                is_correct = _is_mcq_answer_correct(item, selected)
                if is_correct:
                    earned = marks
                    problems_solved += 1
                    test_cases_passed += 1
                    sec_bucket["solved"] += 1
                    item_status = "Correct"
                else:
                    neg = 0.0
                    if assessment.negative_marking:
                        neg = float(
                            item.negative_marks
                            or (marks * float(assessment.negative_marking_percentage or 0) / 100.0)
                        )
                    earned = -neg
                    item_status = "Incorrect"
                total_score += earned
                sec_bucket["score"] += earned
                q_states[item_id] = "submitted"
            else:
                earned = 0.0
                item_status = "Not Attempted"

            problem_breakdown.append(
                {
                    "item_id": item_id,
                    "problem_id": None,
                    "title": item.title,
                    "question_type": item.question_type,
                    "difficulty": item.difficulty,
                    "language": None,
                    "status": item_status,
                    "passed_test_cases": 1 if item_status == "Correct" else 0,
                    "total_test_cases": 1,
                    "score": round(max(0.0, earned), 2),
                    "max_score": round(marks, 2),
                    "execution_time_ms": 0.0,
                    "memory_kb": 0.0,
                    "submission_id": None,
                }
            )

    clamped_score = max(0.0, round(total_score, 2))
    effective_max = round(max_possible_score or float(assessment.total_marks or 100), 2)
    percentage = round((clamped_score / effective_max) * 100.0, 2) if effective_max > 0 else 0.0
    accuracy = (
        round((test_cases_passed / test_cases_total) * 100.0, 2)
        if test_cases_total > 0
        else (
            round((problems_solved / problems_attempted) * 100.0, 2)
            if problems_attempted > 0
            else 0.0
        )
    )
    passed = percentage >= float(assessment.pass_percentage or 50)
    elapsed_sec = int(max(0.0, (now - attempt.started_at).total_seconds()))
    max_duration_sec = int((assessment.duration_minutes or 60) * 60)
    time_taken_seconds = attempt.time_taken_seconds if already_terminal and attempt.time_taken_seconds else min(elapsed_sec, max_duration_sec + 30)

    if not already_terminal:
        attempt.status = "timed_out" if auto_submitted else "completed"
        attempt.completed_at = now
        attempt.total_score = clamped_score
        attempt.max_possible_score = effective_max
        attempt.percentage = percentage
        attempt.passed = passed
        attempt.problems_attempted = problems_attempted
        attempt.problems_solved = problems_solved
        attempt.test_cases_passed = test_cases_passed
        attempt.test_cases_total = test_cases_total
        attempt.time_taken_seconds = time_taken_seconds
        attempt.results_released = bool(assessment.show_results_immediately)
        attempt.question_states = q_states
        attempt.section_scores = {
            k: {
                "score": round(max(0.0, v["score"]), 2),
                "max_score": round(v["max_score"], 2),
                "solved": v["solved"],
                "total": v["total"],
            }
            for k, v in section_totals.items()
        }
        attempt.skill_breakdown = {
            "accuracy": accuracy,
            "auto_submitted": auto_submitted,
            "problem_wise": problem_breakdown,
        }
        attempt.save()

    released = bool(attempt.results_released or assessment.show_results_immediately)
    return {
        "attempt_id": attempt.attempt_id,
        "assessment_id": assessment.assessment_id,
        "assessment_title": assessment.title,
        "assessment_type": assessment.assessment_type,
        "status": attempt.status,
        "auto_submitted": auto_submitted or (attempt.status == "timed_out"),
        "results_released": released,
        "total_score": round(attempt.total_score, 2) if released else None,
        "max_score": round(attempt.max_possible_score, 2),
        "percentage": round(attempt.percentage, 2) if released else None,
        "passed": attempt.passed if released else None,
        "pass_percentage": assessment.pass_percentage,
        "total_problems": len(entries),
        "problems_attempted": attempt.problems_attempted,
        "problems_solved": attempt.problems_solved if released else None,
        "test_cases_passed": attempt.test_cases_passed if released else None,
        "test_cases_total": attempt.test_cases_total,
        "accuracy": accuracy if released else None,
        "time_taken_seconds": attempt.time_taken_seconds,
        "duration_minutes": assessment.duration_minutes,
        "section_scores": attempt.section_scores if released else {},
        "problem_wise_performance": problem_breakdown if released else [],
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
    }


def _check_and_expire_attempt(attempt: AssessmentAttempt) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """If an in-progress attempt has passed expires_at, auto-submit it immediately."""
    if attempt.status == ACTIVE_ATTEMPT_STATUS and timezone.now() >= attempt.expires_at:
        summary = finalize_assessment_attempt(attempt, auto_submitted=True)
        return True, summary
    return False, None


# ==============================================================================
# STUDENT CODING ASSESSMENT ENDPOINTS
# ==============================================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def coding_assessment_list(request):
    """List assessments visible to the student across MCQ, Technical, Coding, Company."""
    user: AllUsers = request.user
    assessment_type = (request.query_params.get("type") or "").strip().lower()
    category = (request.query_params.get("category") or "").strip()
    search = (request.query_params.get("search") or "").strip()

    assignments = _get_user_assignments_map(user)
    assigned_ids = list(assignments.keys())

    qs = CodingAssessment.objects.all()
    if not user.is_staff:
        qs = qs.filter(active=True).filter(
            Q(assignment_mode="public") | Q(assessment_id__in=assigned_ids)
        )

    if assessment_type and assessment_type != "all":
        qs = qs.filter(assessment_type=assessment_type)
    if category:
        qs = qs.filter(category__iexact=category)
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(company_tag__icontains=search)
        )

    assessments = list(qs.order_by("-created_at", "id"))
    attempts_qs = (
        AssessmentAttempt.objects.filter(
            user=user, assessment_id__in=[a.assessment_id for a in assessments]
        )
        .order_by("-started_at")
    )
    user_attempts: Dict[str, AssessmentAttempt] = {}
    for att in attempts_qs:
        if att.assessment_id not in user_attempts:
            user_attempts[att.assessment_id] = att

    serializer = CodingAssessmentSummarySerializer(
        assessments,
        many=True,
        context={"user_attempts": user_attempts, "user_assignments": assignments},
    )
    return Response({"assessments": serializer.data, "count": len(serializer.data)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def coding_assessment_detail(request, assessment_id: str):
    """Return assessment overview, instructions, and candidate-safe problem previews."""
    user: AllUsers = request.user
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    allowed, reason, eff_start, eff_end = _check_student_access(assessment, user)
    if not allowed:
        return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)

    latest_attempt = (
        AssessmentAttempt.objects.filter(user=user, assessment=assessment)
        .order_by("-started_at")
        .first()
    )
    if latest_attempt:
        _check_and_expire_attempt(latest_attempt)
        latest_attempt.refresh_from_db()

    assignments = _get_user_assignments_map(user)
    summary = CodingAssessmentSummarySerializer(
        assessment,
        context={
            "user_attempts": {assessment.assessment_id: latest_attempt} if latest_attempt else {},
            "user_assignments": assignments,
        },
    ).data

    questions = _serialize_candidate_questions(assessment)
    summary["questions"] = questions
    summary["server_now"] = timezone.now()
    return Response(summary)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def coding_assessment_start(request, assessment_id: str):
    """Start or resume an assessment attempt after validating schedule and assignment."""
    user: AllUsers = request.user
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    allowed, reason, eff_start, eff_end = _check_student_access(assessment, user)
    if not allowed:
        return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)

    sched = compute_schedule_status(
        assessment, override_start=eff_start, override_end=eff_end
    )

    active_attempt = (
        AssessmentAttempt.objects.filter(
            user=user, assessment=assessment, status=ACTIVE_ATTEMPT_STATUS
        )
        .order_by("-started_at")
        .first()
    )

    if active_attempt:
        expired, auto_summary = _check_and_expire_attempt(active_attempt)
        if expired:
            return Response(
                {
                    "detail": "Your previous assessment session expired and was auto-submitted.",
                    "auto_submitted": True,
                    "result": auto_summary,
                },
                status=status.HTTP_409_CONFLICT,
            )
    else:
        if sched == "upcoming" and not user.is_staff:
            return Response(
                {"detail": "This assessment has not started yet.", "schedule_status": sched},
                status=status.HTTP_403_FORBIDDEN,
            )
        if sched == "ended" and not user.is_staff:
            return Response(
                {"detail": "The submission window for this assessment has closed.", "schedule_status": sched},
                status=status.HTTP_403_FORBIDDEN,
            )

        now = timezone.now()
        duration_end = now + timedelta(minutes=int(assessment.duration_minutes or 60))
        effective_expires = min(duration_end, eff_end) if eff_end else duration_end

        questions_init = _serialize_candidate_questions(assessment)
        initial_states = {q["item_id"]: "not_visited" for q in questions_init}
        if questions_init:
            initial_states[questions_init[0]["item_id"]] = "not_attempted"

        active_attempt = AssessmentAttempt.objects.create(
            attempt_id=f"att_{uuid.uuid4().hex[:12]}",
            user=user,
            assessment=assessment,
            status=ACTIVE_ATTEMPT_STATUS,
            started_at=now,
            expires_at=effective_expires,
            max_possible_score=float(
                sum(float(q["marks"] or 0) for q in questions_init)
                or assessment.total_marks
                or 100
            ),
            results_released=bool(assessment.show_results_immediately),
            question_states=initial_states,
            saved_drafts={"coding_drafts": {}},
        )

    questions = _serialize_candidate_questions(assessment, attempt=active_attempt, user=user)
    recent_subs = CodingSubmissionRecordSerializer(
        CodeSubmissions.objects.filter(
            attempt=active_attempt, user=user
        ).order_by("-created_at")[:30],
        many=True,
    ).data

    remaining_seconds = max(
        0, int((active_attempt.expires_at - timezone.now()).total_seconds())
    )

    return Response(
        {
            "attempt": {
                "attempt_id": active_attempt.attempt_id,
                "status": active_attempt.status,
                "started_at": active_attempt.started_at,
                "expires_at": active_attempt.expires_at,
                "remaining_seconds": remaining_seconds,
                "selected_answers": active_attempt.selected_answers or {},
                "saved_drafts": active_attempt.saved_drafts or {"coding_drafts": {}},
                "question_states": active_attempt.question_states or {},
                "current_question_index": active_attempt.current_question_index,
                "tab_switch_count": active_attempt.tab_switch_count,
                "fullscreen_exit_count": active_attempt.fullscreen_exit_count,
            },
            "assessment": CodingAssessmentSummarySerializer(assessment).data,
            "questions": questions,
            "submissions": recent_subs,
            "server_now": timezone.now(),
        }
    )


def _resolve_active_attempt(
    request, assessment: CodingAssessment
) -> Tuple[Optional[AssessmentAttempt], Optional[Response]]:
    attempt_id = request.data.get("attempt_id") or request.query_params.get("attempt_id")
    if attempt_id:
        attempt = AssessmentAttempt.objects.filter(
            attempt_id=attempt_id, assessment=assessment
        ).first()
        if not attempt:
            return None, Response(
                {"detail": "Assessment attempt not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if attempt.user_id != request.user.user_id and not request.user.is_staff:
            return None, Response(
                {"detail": "You do not have permission to access this attempt."},
                status=status.HTTP_403_FORBIDDEN,
            )
    else:
        attempt = (
            AssessmentAttempt.objects.filter(
                user=request.user, assessment=assessment, status=ACTIVE_ATTEMPT_STATUS
            )
            .order_by("-started_at")
            .first()
        )
        if not attempt:
            return None, Response(
                {"detail": "No active attempt found. Start the assessment first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if attempt.status in TERMINAL_ATTEMPT_STATUSES:
        return None, Response(
            {"detail": "This assessment attempt has already been submitted.", "status": attempt.status},
            status=status.HTTP_409_CONFLICT,
        )

    expired, auto_summary = _check_and_expire_attempt(attempt)
    if expired:
        return None, Response(
            {
                "detail": "Time limit expired. Your assessment was automatically submitted.",
                "auto_submitted": True,
                "result": auto_summary,
            },
            status=status.HTTP_409_CONFLICT,
        )
    return attempt, None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([AssessmentRunRateThrottle])
def coding_assessment_run(request, assessment_id: str):
    """Run candidate code against custom stdin OR non-hidden sample test cases."""
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    allowed, reason, _, _ = _check_student_access(assessment, request.user)
    if not allowed:
        return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)

    attempt, err_resp = _resolve_active_attempt(request, assessment)
    if err_resp is not None:
        return err_resp

    item_id = request.data.get("item_id")
    problem_id = request.data.get("problem_id")
    language = request.data.get("language") or "python"
    source_code = request.data.get("source_code")
    if source_code is None:
        source_code = request.data.get("code", "")
    custom_input = request.data.get("custom_input")

    entry = _find_entry_in_assessment(
        assessment, item_id=item_id, problem_id=problem_id
    )
    if not entry or not entry.get("problem"):
        return Response(
            {"detail": "Coding problem not found in this assessment."},
            status=status.HTTP_404_NOT_FOUND,
        )

    problem: CodingProblems = entry["problem"]
    files_payload = request.data.get("files")
    try:
        if problem.question_type == "django_debug":
            merged_files = _collect_files_for_django_eval(
                attempt,
                entry["item_id"],
                problem,
                files_payload if isinstance(files_payload, dict) else None,
            )
            result = evaluate_django_project_problem(
                problem=problem,
                candidate_files=merged_files,
                max_marks=entry["marks"],
                include_hidden=False,
            )
        else:
            result = run_coding_code(
                problem=problem,
                source_code=source_code,
                language=language,
                custom_input=custom_input,
                item=entry.get("item"),
            )
    except PermissionError as sec_exc:
        return Response({"detail": str(sec_exc)}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as val_exc:
        return Response({"detail": str(val_exc)}, status=status.HTTP_400_BAD_REQUEST)

    # Mark question as attempted if still unvisited/unattempted
    if attempt is not None:
        states = dict(attempt.question_states or {})
        cur = states.get(entry["item_id"], "not_visited")
        if cur in ("not_visited", "not_attempted"):
            states[entry["item_id"]] = "attempted"
            attempt.question_states = states
            attempt.save(update_fields=["question_states"])

    return Response(result)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def coding_assessment_codelab_reset(request, assessment_id: str):
    """Reset the provisioned CodeLab workspace for a django_debug item back to starter files."""
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    allowed, reason, _, _ = _check_student_access(assessment, request.user)
    if not allowed:
        return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)

    attempt, err_resp = _resolve_active_attempt(request, assessment)
    if err_resp is not None:
        return err_resp

    item_id = request.data.get("item_id")
    problem_id = request.data.get("problem_id")
    entry = _find_entry_in_assessment(assessment, item_id=item_id, problem_id=problem_id)
    if not entry or not entry.get("problem"):
        return Response({"detail": "Coding problem not found."}, status=status.HTTP_404_NOT_FOUND)

    problem: CodingProblems = entry["problem"]
    cl_meta = _ensure_codelab_project_for_attempt(attempt, entry["item_id"], problem, request.user)
    proj = get_object_or_404(CodeProject, project_id=cl_meta["codelab_project_id"])

    with transaction.atomic():
        ProjectFile.objects.filter(project=proj).delete()
        for rel_path, content in (problem.project_files or {}).items():
            clean_path = str(rel_path).replace("\\", "/").lstrip("/")
            if not clean_path:
                continue
            text = str(content or "")
            ProjectFile.objects.create(
                file_id=f"file_{uuid.uuid4().hex[:12]}",
                project=proj,
                path=clean_path,
                name=clean_path.split("/")[-1],
                is_directory=False,
                content=text,
                size_bytes=len(text.encode("utf-8")),
            )

    workspace_dir = sync_db_files_to_workspace(proj)
    try:
        from .codelab_sql import ProjectDatabaseCatalog
        cat = ProjectDatabaseCatalog(workspace_dir=workspace_dir, project_id=proj.project_id)
        cat.set_django_database("default_db")
    except Exception:
        pass

    return Response({"status": True, "codelab_project_id": proj.project_id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([AssessmentSubmitRateThrottle])
def coding_assessment_submit_problem(request, assessment_id: str):
    """Judge candidate code for one problem against all hidden + public test cases."""
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    allowed, reason, _, _ = _check_student_access(assessment, request.user)
    if not allowed:
        return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)

    attempt, err_resp = _resolve_active_attempt(request, assessment)
    if err_resp is not None:
        return err_resp
    assert attempt is not None

    item_id = request.data.get("item_id")
    problem_id = request.data.get("problem_id")
    language = request.data.get("language") or "python"
    source_code = request.data.get("source_code")
    if source_code is None:
        source_code = request.data.get("code", "")

    entry = _find_entry_in_assessment(
        assessment, item_id=item_id, problem_id=problem_id
    )
    if not entry or not entry.get("problem"):
        return Response(
            {"detail": "Coding problem not found in this assessment."},
            status=status.HTTP_404_NOT_FOUND,
        )

    problem: CodingProblems = entry["problem"]
    files_payload = request.data.get("files")
    try:
        if problem.question_type == "django_debug":
            candidate_files = _collect_files_for_django_eval(
                attempt,
                entry["item_id"],
                problem,
                files_payload if isinstance(files_payload, dict) else None,
            )
            judge_res = evaluate_django_project_problem(
                problem=problem,
                candidate_files=candidate_files,
                max_marks=entry["marks"],
                include_hidden=True,
            )
            source_code = json.dumps(candidate_files)
            language = "django"
        else:
            judge_res = evaluate_coding_submission(
                problem=problem,
                source_code=source_code,
                language=language,
                max_marks=entry["marks"],
                item=entry.get("item"),
                include_hidden_details=False,
            )
    except PermissionError as sec_exc:
        return Response({"detail": str(sec_exc)}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as val_exc:
        return Response({"detail": str(val_exc)}, status=status.HTTP_400_BAD_REQUEST)

    submission = _record_problem_submission(
        user=request.user,
        assessment=assessment,
        attempt=attempt,
        problem=problem,
        language=language,
        source_code=source_code,
        judge_res=judge_res,
        is_final=False,
    )

    # Save draft and update 5-state palette indicator -> "submitted"
    drafts = dict(attempt.saved_drafts or {})
    coding_drafts = dict(drafts.get("coding_drafts") or {})
    draft_entry: Dict[str, Any] = {
        "language": judge_res["language"],
        "code": source_code,
        "problem_id": problem.problem_id,
    }
    if problem.question_type == "django_debug" and isinstance(files_payload, dict):
        draft_entry["files"] = files_payload
    coding_drafts[entry["item_id"]] = draft_entry
    drafts["coding_drafts"] = coding_drafts
    states = dict(attempt.question_states or {})
    states[entry["item_id"]] = "submitted"
    attempt.saved_drafts = drafts
    attempt.question_states = states
    attempt.save(update_fields=["saved_drafts", "question_states"])

    judge_res["submission_id"] = submission.submission_id
    judge_res["item_id"] = entry["item_id"]
    judge_res["problem_id"] = problem.problem_id
    judge_res["question_states"] = states
    return Response(judge_res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def coding_assessment_autosave(request, assessment_id: str):
    """Persist code drafts, selected MCQ answers, and 5-state question statuses."""
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    attempt, err_resp = _resolve_active_attempt(request, assessment)
    if err_resp is not None:
        return err_resp
    assert attempt is not None

    coding_drafts_patch = request.data.get("coding_drafts")
    selected_answers_patch = request.data.get("selected_answers")
    question_states_patch = request.data.get("question_states")
    current_idx = request.data.get("current_question_index")
    current_section = request.data.get("current_section")

    if isinstance(coding_drafts_patch, dict):
        drafts = dict(attempt.saved_drafts or {})
        existing_coding = dict(drafts.get("coding_drafts") or {})
        for key, val in coding_drafts_patch.items():
            if isinstance(val, dict):
                draft_obj: Dict[str, Any] = {
                    "language": str(val.get("language") or "python"),
                    "code": str(val.get("code") or val.get("source_code") or "")[:100_000],
                    "problem_id": val.get("problem_id"),
                }
                if isinstance(val.get("files"), dict):
                    draft_obj["files"] = {
                        str(fk): str(fv or "")[:100_000]
                        for fk, fv in val["files"].items()
                    }
                existing_coding[str(key)] = draft_obj
        drafts["coding_drafts"] = existing_coding
        attempt.saved_drafts = drafts

    if isinstance(selected_answers_patch, dict):
        merged_answers = dict(attempt.selected_answers or {})
        merged_answers.update(selected_answers_patch)
        attempt.selected_answers = merged_answers

    if isinstance(question_states_patch, dict):
        valid_states = {
            "not_visited",
            "not_attempted",
            "attempted",
            "marked_for_review",
            "submitted",
        }
        merged_states = dict(attempt.question_states or {})
        for qid, st in question_states_patch.items():
            if st in valid_states:
                merged_states[str(qid)] = st
        attempt.question_states = merged_states

    if isinstance(current_idx, int) and current_idx >= 0:
        attempt.current_question_index = current_idx
    if isinstance(current_section, str) and current_section:
        attempt.current_section = current_section

    attempt.save()
    return Response(
        {
            "saved": True,
            "attempt_id": attempt.attempt_id,
            "remaining_seconds": max(
                0, int((attempt.expires_at - timezone.now()).total_seconds())
            ),
            "question_states": attempt.question_states,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([AssessmentSubmitRateThrottle])
def coding_assessment_submit(request, assessment_id: str):
    """Finalize and grade the complete assessment (supports manual & timer auto-submit)."""
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    attempt_id = request.data.get("attempt_id")
    if attempt_id:
        attempt = get_object_or_404(
            AssessmentAttempt, attempt_id=attempt_id, assessment=assessment
        )
        if attempt.user_id != request.user.user_id and not request.user.is_staff:
            return Response(
                {"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN
            )
    else:
        attempt = (
            AssessmentAttempt.objects.filter(user=request.user, assessment=assessment)
            .order_by("-started_at")
            .first()
        )
        if not attempt:
            return Response(
                {"detail": "No assessment attempt found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    # Persist any last-second draft/answer state included with submit call
    if attempt.status == ACTIVE_ATTEMPT_STATUS:
        if isinstance(request.data.get("coding_drafts"), dict):
            drafts = dict(attempt.saved_drafts or {})
            existing_coding = dict(drafts.get("coding_drafts") or {})
            existing_coding.update(request.data["coding_drafts"])
            drafts["coding_drafts"] = existing_coding
            attempt.saved_drafts = drafts
        if isinstance(request.data.get("selected_answers"), dict):
            merged_answers = dict(attempt.selected_answers or {})
            merged_answers.update(request.data["selected_answers"])
            attempt.selected_answers = merged_answers
        attempt.save()

    auto_submitted = bool(request.data.get("auto_submitted")) or (
        timezone.now() >= attempt.expires_at and attempt.status == ACTIVE_ATTEMPT_STATUS
    )
    summary = finalize_assessment_attempt(attempt, auto_submitted=auto_submitted)
    return Response(summary)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def coding_assessment_result(request, assessment_id: str):
    """Retrieve complete analytics for the authenticated student's completed attempt."""
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    attempt_id = request.query_params.get("attempt_id")
    if attempt_id:
        attempt = get_object_or_404(
            AssessmentAttempt, attempt_id=attempt_id, assessment=assessment
        )
        if attempt.user_id != request.user.user_id and not request.user.is_staff:
            return Response(
                {"detail": "You may only view your own assessment results."},
                status=status.HTTP_403_FORBIDDEN,
            )
    else:
        attempt = (
            AssessmentAttempt.objects.filter(
                user=request.user,
                assessment=assessment,
                status__in=TERMINAL_ATTEMPT_STATUSES,
            )
            .order_by("-completed_at", "-started_at")
            .first()
        )
        if not attempt:
            return Response(
                {"detail": "No completed assessment attempt found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    summary = finalize_assessment_attempt(
        attempt, auto_submitted=(attempt.status == "timed_out")
    )

    submissions = CodeSubmissions.objects.filter(
        attempt=attempt, user=attempt.user
    ).order_by("-created_at")
    summary["submissions"] = CodingSubmissionRecordSerializer(submissions, many=True).data

    if summary["results_released"]:
        # Include problem explanations safely now that attempt is completed & released
        explanations = {}
        for entry in _collect_assessment_entries(assessment):
            if entry.get("problem"):
                explanations[entry["item_id"]] = (
                    entry["problem"].explanation or entry["problem"].sample_explanation or ""
                )
            elif entry.get("item"):
                explanations[entry["item_id"]] = entry["item"].explanation or ""
        summary["explanations"] = explanations

    return Response(summary)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def coding_submissions_list(request):
    """List strictly the authenticated student's own coding submissions."""
    qs = (
        CodeSubmissions.objects.filter(user=request.user)
        .select_related("problem", "assessment", "user")
        .order_by("-created_at")
    )
    assessment_id = request.query_params.get("assessment_id")
    problem_id = request.query_params.get("problem_id")
    if assessment_id:
        qs = qs.filter(assessment__assessment_id=assessment_id)
    if problem_id:
        qs = qs.filter(problem__problem_id=problem_id)

    serializer = CodingSubmissionRecordSerializer(qs[:100], many=True)
    return Response({"submissions": serializer.data, "count": qs.count()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def coding_assessment_event(request, assessment_id: str):
    """Record authenticated proctoring & integrity telemetry strictly for the owner attempt."""
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    attempt, err_resp = _resolve_active_attempt(request, assessment)
    if err_resp is not None:
        return err_resp
    assert attempt is not None

    event_type = (request.data.get("event_type") or "").strip().upper()
    if not event_type:
        return Response({"detail": "event_type is required."}, status=status.HTTP_400_BAD_REQUEST)
    metadata = request.data.get("metadata")

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    AssessmentEvent.objects.create(
        event_id=event_id,
        attempt=attempt,
        user=request.user,
        assessment=assessment,
        event_type=event_type,
        metadata=metadata if isinstance(metadata, dict) else {},
    )

    if event_type == "TAB_SWITCH":
        attempt.tab_switch_count += 1
    elif event_type == "FULLSCREEN_EXIT":
        attempt.fullscreen_exit_count += 1
    elif event_type == "SCREEN_SHARE_STOPPED":
        attempt.screen_share_stop_count += 1
    elif event_type in ("NETWORK_DISCONNECT", "NETWORK_DISCONNECTED"):
        attempt.network_disconnect_count += 1

    deductions = (
        (attempt.tab_switch_count * 5.0)
        + (attempt.fullscreen_exit_count * 8.0)
        + (attempt.screen_share_stop_count * 15.0)
    )
    attempt.integrity_score = max(0.0, round(100.0 - deductions, 1))
    attempt.save(
        update_fields=[
            "tab_switch_count",
            "fullscreen_exit_count",
            "screen_share_stop_count",
            "network_disconnect_count",
            "integrity_score",
        ]
    )

    return Response(
        {
            "event_id": event_id,
            "integrity_score": attempt.integrity_score,
            "tab_switch_count": attempt.tab_switch_count,
            "fullscreen_exit_count": attempt.fullscreen_exit_count,
        }
    )


# ==============================================================================
# ADMIN CODING PROBLEMS, ASSESSMENTS, BATCHES & ANALYTICS ENDPOINTS
# ==============================================================================

def _sync_problem_fields(problem: CodingProblems, data: Dict[str, Any]) -> None:
    editable_fields = [
        "title",
        "difficulty",
        "question_type",
        "category",
        "topics",
        "points",
        "description",
        "input_format",
        "output_format",
        "constraints",
        "expected_complexity",
        "sample_input",
        "sample_output",
        "sample_explanation",
        "time_limit_seconds",
        "memory_limit_mb",
        "supported_languages",
        "starter_python",
        "starter_java",
        "starter_c",
        "starter_cpp",
        "starter_javascript",
        "project_files",
        "hidden_test_files",
        "solution_code",
        "explanation",
        "hints",
        "is_active",
    ]
    for field in editable_fields:
        if field in data:
            setattr(problem, field, data[field])

    if "marks" in data and "points" not in data:
        problem.points = int(data["marks"] or 100)

    starter_codes = data.get("starter_codes")
    if isinstance(starter_codes, dict):
        if "python" in starter_codes:
            problem.starter_python = starter_codes["python"]
        if "java" in starter_codes:
            problem.starter_java = starter_codes["java"]
        if "c" in starter_codes:
            problem.starter_c = starter_codes["c"]
        if "cpp" in starter_codes:
            problem.starter_cpp = starter_codes["cpp"]
        if "javascript" in starter_codes:
            problem.starter_javascript = starter_codes["javascript"]

    if problem.title and not problem.slug:
        problem.slug = f"{slugify(problem.title)[:180]}-{uuid.uuid4().hex[:6]}"


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_parse_django_archive(request):
    """Parse an uploaded Django project .zip archive into project_files and hidden_test_files."""
    uploaded = request.FILES.get("file") or request.FILES.get("archive")
    if uploaded is None:
        return Response(
            {"detail": "Please attach a .zip file in the 'file' field."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if uploaded.size > 12 * 1024 * 1024:
        return Response(
            {"detail": "Uploaded archive is too large (max 12 MB). Exclude venv/__pycache__/sqlite3."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        parsed = parse_django_archive_bytes(uploaded.read())
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(parsed)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_coding_problems(request):
    if request.method == "GET":
        qs = CodingProblems.objects.prefetch_related("test_cases").order_by("-created_at")
        search = (request.query_params.get("search") or "").strip()
        diff = (request.query_params.get("difficulty") or "").strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(category__icontains=search))
        if diff:
            qs = qs.filter(difficulty__iexact=diff)
        return Response(
            {
                "problems": CodingProblemAdminSerializer(qs, many=True).data,
                "default_starter_codes": DEFAULT_STARTER_CODES,
                "default_django_project": DEFAULT_DJANGO_PROJECT_TEMPLATE,
            }
        )

    title = (request.data.get("title") or "").strip()
    if not title:
        return Response({"detail": "Problem title is required."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        problem = CodingProblems(
            problem_id=f"prob_{uuid.uuid4().hex[:10]}",
            title=title,
            slug=f"{slugify(title)[:180]}-{uuid.uuid4().hex[:6]}",
            description=request.data.get("description") or "",
            starter_python=request.data.get("starter_python") or DEFAULT_STARTER_CODES["python"],
            starter_java=request.data.get("starter_java") or DEFAULT_STARTER_CODES["java"],
            starter_c=request.data.get("starter_c") or DEFAULT_STARTER_CODES["c"],
            starter_cpp=request.data.get("starter_cpp") or DEFAULT_STARTER_CODES["cpp"],
            starter_javascript=request.data.get("starter_javascript") or DEFAULT_STARTER_CODES["javascript"],
        )
        _sync_problem_fields(problem, request.data)
        problem.save()

        raw_cases = request.data.get("test_cases")
        if isinstance(raw_cases, list):
            for idx, tc in enumerate(raw_cases, start=1):
                if isinstance(tc, dict):
                    TestCases.objects.create(
                        test_case_id=f"tc_{uuid.uuid4().hex[:10]}",
                        problem=problem,
                        input_data=str(tc.get("input_data", "")),
                        expected_output=str(tc.get("expected_output", "")),
                        is_hidden=bool(tc.get("is_hidden", False)),
                        is_sample=not bool(tc.get("is_hidden", False)),
                        category="Hidden" if tc.get("is_hidden") else "Basic",
                        explanation=str(tc.get("explanation", "")),
                        points=int(tc.get("points") or 10),
                        order=int(tc.get("order") or idx),
                    )

    return Response(CodingProblemAdminSerializer(problem).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_coding_problem_detail(request, problem_id: str):
    problem = get_object_or_404(CodingProblems, problem_id=problem_id)
    if request.method == "GET":
        return Response(CodingProblemAdminSerializer(problem).data)
    if request.method == "DELETE":
        problem.delete()
        return Response({"deleted": True}, status=status.HTTP_204_NO_CONTENT)

    with transaction.atomic():
        _sync_problem_fields(problem, request.data)
        problem.save()
        if isinstance(request.data.get("test_cases"), list):
            problem.test_cases.all().delete()
            for idx, tc in enumerate(request.data["test_cases"], start=1):
                if isinstance(tc, dict):
                    TestCases.objects.create(
                        test_case_id=f"tc_{uuid.uuid4().hex[:10]}",
                        problem=problem,
                        input_data=str(tc.get("input_data", "")),
                        expected_output=str(tc.get("expected_output", "")),
                        is_hidden=bool(tc.get("is_hidden", False)),
                        is_sample=not bool(tc.get("is_hidden", False)),
                        category="Hidden" if tc.get("is_hidden") else "Basic",
                        explanation=str(tc.get("explanation", "")),
                        points=int(tc.get("points") or 10),
                        order=int(tc.get("order") or idx),
                    )

    return Response(CodingProblemAdminSerializer(problem).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_problem_testcases(request, problem_id: str):
    problem = get_object_or_404(CodingProblems, problem_id=problem_id)
    tc = TestCases.objects.create(
        test_case_id=f"tc_{uuid.uuid4().hex[:10]}",
        problem=problem,
        input_data=str(request.data.get("input_data", "")),
        expected_output=str(request.data.get("expected_output", "")),
        is_hidden=bool(request.data.get("is_hidden", False)),
        is_sample=not bool(request.data.get("is_hidden", False)),
        category="Hidden" if request.data.get("is_hidden") else "Basic",
        explanation=str(request.data.get("explanation", "")),
        points=int(request.data.get("points") or 10),
        order=int(request.data.get("order") or (problem.test_cases.count() + 1)),
    )
    return Response(AdminTestCaseSerializer(tc).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_problem_testcase_detail(request, problem_id: str, test_case_id: str):
    problem = get_object_or_404(CodingProblems, problem_id=problem_id)
    tc = get_object_or_404(TestCases, problem=problem, test_case_id=test_case_id)
    if request.method == "DELETE":
        tc.delete()
        return Response({"deleted": True}, status=status.HTTP_204_NO_CONTENT)
    for field in ("input_data", "expected_output", "is_hidden", "explanation", "points", "order"):
        if field in request.data:
            setattr(tc, field, request.data[field])
    tc.is_sample = not tc.is_hidden
    tc.save()
    return Response(AdminTestCaseSerializer(tc).data)


def _sync_assessment_fields(assessment: CodingAssessment, data: Dict[str, Any]) -> None:
    fields = [
        "title",
        "assessment_type",
        "category",
        "company_tag",
        "description",
        "instructions",
        "difficulty",
        "duration_minutes",
        "pass_percentage",
        "total_marks",
        "negative_marking",
        "negative_marking_percentage",
        "supported_languages",
        "assignment_mode",
        "show_results_immediately",
        "is_company_mock",
        "proctoring_enabled",
        "require_fullscreen",
        "max_tab_switches",
        "active",
    ]
    for field in fields:
        if field in data:
            setattr(assessment, field, data[field])

    if "start_time" in data:
        assessment.start_time = _parse_iso_dt(data["start_time"])
    if "end_time" in data:
        assessment.end_time = _parse_iso_dt(data["end_time"])
    if "is_proctored" in data:
        assessment.proctoring_enabled = bool(data["is_proctored"])
    if "is_active" in data:
        assessment.active = bool(data["is_active"])


def _sync_assessment_problems(assessment: CodingAssessment, data: Dict[str, Any]) -> None:
    problem_items = data.get("problem_items")
    if isinstance(problem_items, list):
        AssessmentQuestionItem.objects.filter(
            assessment=assessment, question_type="coding"
        ).delete()
        section, _ = AssessmentSection.objects.get_or_create(
            assessment=assessment,
            title="Coding Problems",
            defaults={
                "section_id": f"sec_{uuid.uuid4().hex[:10]}",
                "section_type": "Coding",
                "order": 1,
                "total_marks": int(assessment.total_marks or 100),
            },
        )
        total_marks = 0
        for idx, row in enumerate(problem_items, start=1):
            pid = row.get("problem_id") if isinstance(row, dict) else str(row)
            marks = int((row.get("marks") if isinstance(row, dict) else None) or 100)
            order = int((row.get("order") if isinstance(row, dict) else None) or idx)
            prob = CodingProblems.objects.filter(problem_id=pid).first()
            if not prob:
                continue
            total_marks += marks
            AssessmentQuestionItem.objects.create(
                item_id=f"aqi_{uuid.uuid4().hex[:10]}",
                assessment=assessment,
                section=section,
                problem=prob,
                question_type="coding",
                title=prob.title,
                slug=f"{slugify(prob.title)[:140]}-{uuid.uuid4().hex[:6]}",
                category=prob.category or "Coding",
                difficulty=prob.difficulty,
                prompt=prob.description,
                marks=marks,
                time_limit_seconds=prob.time_limit_seconds,
                memory_limit_mb=prob.memory_limit_mb,
                input_format=prob.input_format,
                output_format=prob.output_format,
                constraints=prob.constraints,
                order=order,
                status="Published",
            )
        if total_marks > 0 and not data.get("total_marks"):
            assessment.total_marks = total_marks
            assessment.save(update_fields=["total_marks"])


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_coding_assessments(request):
    if request.method == "GET":
        qs = CodingAssessment.objects.all().order_by("-created_at")
        return Response(
            {
                "assessments": CodingAssessmentSummarySerializer(qs, many=True).data,
            }
        )

    title = (request.data.get("title") or "").strip()
    if not title:
        return Response({"detail": "Assessment title is required."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        atype = (request.data.get("assessment_type") or "coding").strip().lower()
        cat_default = {
            "mcq": "MCQ Assessments",
            "technical": "Technical Assessments",
            "coding": "Coding Assessments",
            "company": "Company Mocks",
        }.get(atype, "Coding Assessments")

        assessment = CodingAssessment(
            assessment_id=f"ca_{uuid.uuid4().hex[:10]}",
            title=title,
            slug=f"{slugify(title)[:180]}-{uuid.uuid4().hex[:6]}",
            assessment_type=atype,
            category=request.data.get("category") or cat_default,
        )
        _sync_assessment_fields(assessment, request.data)
        assessment.save()
        _sync_assessment_problems(assessment, request.data)

    detail = CodingAssessmentSummarySerializer(assessment).data
    detail["questions"] = _serialize_candidate_questions(assessment)
    return Response(detail, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_coding_assessment_detail(request, assessment_id: str):
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    if request.method == "GET":
        data = CodingAssessmentSummarySerializer(assessment).data
        data["questions"] = _serialize_candidate_questions(assessment)
        return Response(data)
    if request.method == "DELETE":
        assessment.delete()
        return Response({"deleted": True}, status=status.HTTP_204_NO_CONTENT)

    with transaction.atomic():
        _sync_assessment_fields(assessment, request.data)
        assessment.save()
        _sync_assessment_problems(assessment, request.data)

    data = CodingAssessmentSummarySerializer(assessment).data
    data["questions"] = _serialize_candidate_questions(assessment)
    return Response(data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_batches(request):
    if request.method == "GET":
        batches = StudentBatch.objects.prefetch_related("students").order_by("-created_at")
        return Response({"batches": StudentBatchSerializer(batches, many=True).data})

    name = (request.data.get("name") or "").strip()
    if not name:
        return Response({"detail": "Batch name is required."}, status=status.HTTP_400_BAD_REQUEST)
    batch = StudentBatch.objects.create(
        batch_id=f"batch_{uuid.uuid4().hex[:10]}",
        name=name,
        description=request.data.get("description") or "",
        is_active=bool(request.data.get("is_active", True)),
    )
    student_ids = request.data.get("student_ids")
    if isinstance(student_ids, list) and student_ids:
        users = AllUsers.objects.filter(user_id__in=student_ids)
        batch.students.set(users)
    return Response(StudentBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_batch_detail(request, batch_id: str):
    batch = get_object_or_404(StudentBatch, batch_id=batch_id)
    if request.method == "DELETE":
        batch.delete()
        return Response({"deleted": True}, status=status.HTTP_204_NO_CONTENT)
    for field in ("name", "description", "is_active"):
        if field in request.data:
            setattr(batch, field, request.data[field])
    batch.save()
    if isinstance(request.data.get("student_ids"), list):
        batch.students.set(AllUsers.objects.filter(user_id__in=request.data["student_ids"]))
    return Response(StudentBatchSerializer(batch).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_assessment_assignments(request, assessment_id: str):
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    if request.method == "GET":
        rows = (
            AssessmentAssignment.objects.filter(assessment=assessment)
            .select_related("student", "batch")
            .order_by("-created_at")
        )
        return Response(
            {
                "assignment_mode": assessment.assignment_mode,
                "assignments": AssessmentAssignmentSerializer(rows, many=True).data,
            }
        )

    student_ids = request.data.get("student_ids") or []
    batch_ids = request.data.get("batch_ids") or []
    if request.data.get("student_id"):
        student_ids = list(student_ids) + [request.data["student_id"]]
    if request.data.get("batch_id"):
        batch_ids = list(batch_ids) + [request.data["batch_id"]]

    start_time = _parse_iso_dt(request.data.get("start_time"))
    end_time = _parse_iso_dt(request.data.get("end_time"))
    created: List[AssessmentAssignment] = []

    with transaction.atomic():
        for sid in student_ids:
            student = AllUsers.objects.filter(user_id=sid).first()
            if student:
                obj, _ = AssessmentAssignment.objects.get_or_create(
                    assessment=assessment,
                    student=student,
                    batch=None,
                    defaults={
                        "assignment_id": f"asg_{uuid.uuid4().hex[:10]}",
                        "start_time": start_time,
                        "end_time": end_time,
                        "assigned_by": request.user,
                    },
                )
                created.append(obj)
        for bid in batch_ids:
            batch = StudentBatch.objects.filter(batch_id=bid).first()
            if batch:
                obj, _ = AssessmentAssignment.objects.get_or_create(
                    assessment=assessment,
                    student=None,
                    batch=batch,
                    defaults={
                        "assignment_id": f"asg_{uuid.uuid4().hex[:10]}",
                        "start_time": start_time,
                        "end_time": end_time,
                        "assigned_by": request.user,
                    },
                )
                created.append(obj)

        if assessment.assignment_mode != "assigned" and created:
            assessment.assignment_mode = "assigned"
            assessment.save(update_fields=["assignment_mode"])

    return Response(
        {"assignments": AssessmentAssignmentSerializer(created, many=True).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_assessment_assignment_detail(request, assessment_id: str, assignment_id: str):
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    obj = get_object_or_404(
        AssessmentAssignment, assessment=assessment, assignment_id=assignment_id
    )
    obj.delete()
    return Response({"deleted": True}, status=status.HTTP_204_NO_CONTENT)


def _format_mcq_choice_values(raw_options: Any, value: Any) -> Optional[str]:
    """Map MCQ option IDs ('a', ['b', 'c']) to human-readable 'A) Option text' labels."""
    if value in (None, "", []):
        return None
    opt_map: Dict[str, str] = {}
    if isinstance(raw_options, list):
        for opt in raw_options:
            if isinstance(opt, dict):
                oid = str(opt.get("id") or opt.get("key") or opt.get("value") or "").strip()
                otext = str(opt.get("text") or opt.get("label") or opt.get("title") or "").strip()
                if oid:
                    opt_map[oid.lower()] = f"{oid.upper()}) {otext}" if otext else oid
            elif isinstance(opt, str):
                opt_map[opt.strip().lower()] = opt.strip()

    vals = value if isinstance(value, list) else [value]
    formatted: List[str] = []
    for v in vals:
        s = str(v).strip()
        if not s:
            continue
        formatted.append(opt_map.get(s.lower(), s))
    return ", ".join(formatted) if formatted else None


def _index_attempt_submissions(attempts: List[AssessmentAttempt]) -> Dict[str, Dict[str, CodeSubmissions]]:
    """Bulk-load CodeSubmissions keyed by attempt_id -> submission_id / problem_id."""
    if not attempts:
        return {}
    by_attempt: Dict[str, Dict[str, CodeSubmissions]] = {}
    subs = (
        CodeSubmissions.objects.filter(attempt__in=attempts)
        .select_related("problem")
        .order_by("-is_final_submission", "-created_at")
    )
    for sub in subs:
        att_map = by_attempt.setdefault(sub.attempt_id, {})
        att_map.setdefault(sub.submission_id, sub)
        if sub.problem_id:
            att_map.setdefault(f"prob:{sub.problem_id}", sub)
    return by_attempt


def _build_admin_attempt_payload(
    att: AssessmentAttempt,
    entries_by_asmt: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    subs_by_attempt: Optional[Dict[str, Dict[str, CodeSubmissions]]] = None,
) -> Dict[str, Any]:
    """Build admin attempt summary enriched with per-question MCQ answers and coding source code."""
    entries_cache = entries_by_asmt if entries_by_asmt is not None else {}
    asmt_id = att.assessment.assessment_id
    if asmt_id not in entries_cache:
        entries_cache[asmt_id] = _collect_assessment_entries(att.assessment)
    entries = entries_cache[asmt_id]

    entry_by_item = {e["item_id"]: e for e in entries}
    entry_by_prob = {e["problem"].problem_id: e for e in entries if e.get("problem")}
    all_items_by_id = {
        it.item_id: it
        for it in AssessmentQuestionItem.objects.filter(assessment=att.assessment).select_related("problem")
    }

    raw_breakdown = (
        (att.skill_breakdown or {}).get("problem_wise")
        if isinstance(att.skill_breakdown, dict)
        else None
    )
    if not isinstance(raw_breakdown, list) or not raw_breakdown:
        raw_breakdown = [
            {
                "item_id": e["item_id"],
                "problem_id": e["problem"].problem_id if e.get("problem") else None,
                "title": e["title"],
                "question_type": e["question_type"],
                "difficulty": e["difficulty"],
                "language": None,
                "status": "Not Attempted",
                "passed_test_cases": 0,
                "total_test_cases": e["problem"].test_cases.count() if e.get("problem") else 1,
                "score": 0.0,
                "max_score": round(float(e["marks"]), 2),
                "execution_time_ms": 0.0,
                "memory_kb": 0.0,
                "submission_id": None,
            }
            for e in entries
        ]

    selected_answers = att.selected_answers if isinstance(att.selected_answers, dict) else {}
    drafts_root = att.saved_drafts if isinstance(att.saved_drafts, dict) else {}
    coding_drafts = drafts_root.get("coding_drafts") if isinstance(drafts_root.get("coding_drafts"), dict) else drafts_root
    sub_map = (subs_by_attempt or {}).get(att.attempt_id, {})

    enriched_breakdown: List[Dict[str, Any]] = []
    for row in raw_breakdown:
        item_id = row.get("item_id")
        problem_id = row.get("problem_id")
        entry = entry_by_item.get(item_id) or (entry_by_prob.get(problem_id) if problem_id else None)
        item = (entry.get("item") if entry else None) or (all_items_by_id.get(item_id) if item_id else None)
        problem = (entry.get("problem") if entry else None) or (item.problem if item and item.problem_id else None)

        prompt = ""
        if problem is not None:
            prompt = problem.description or ""
        elif item is not None:
            prompt = item.prompt or ""

        user_answer = None
        user_answer_display = None
        correct_answer_display = None
        source_code = None
        error_message = ""
        language = row.get("language")

        if item is not None and problem is None:
            user_answer = selected_answers.get(item_id)
            user_answer_display = _format_mcq_choice_values(item.options, user_answer)
            correct_answer_display = _format_mcq_choice_values(item.options, item.correct_answers)
        else:
            sub_id = row.get("submission_id")
            sub = (sub_map.get(sub_id) if sub_id else None) or (
                sub_map.get(f"prob:{problem_id}") if problem_id else None
            )
            if sub is not None:
                source_code = sub.code
                language = language or sub.language
                error_message = sub.error_message or ""
            elif isinstance(coding_drafts, dict):
                draft_entry = coding_drafts.get(item_id) or (
                    coding_drafts.get(problem_id) if problem_id else None
                )
                if isinstance(draft_entry, dict) and str(draft_entry.get("code") or "").strip():
                    source_code = draft_entry.get("code")
                    language = language or draft_entry.get("language")

        enriched_breakdown.append(
            {
                **row,
                "prompt": prompt,
                "language": language,
                "user_answer": user_answer,
                "user_answer_display": user_answer_display,
                "correct_answer_display": correct_answer_display,
                "source_code": source_code,
                "error_message": error_message,
            }
        )

    accuracy = (
        round((att.test_cases_passed / att.test_cases_total) * 100.0, 2)
        if att.test_cases_total > 0
        else 0.0
    )
    return {
        "attempt_id": att.attempt_id,
        "assessment_id": asmt_id,
        "assessment_title": att.assessment.title,
        "assessment_type": att.assessment.assessment_type,
        "student_id": att.user.user_id,
        "student_name": f"{att.user.name} {att.user.lastname}".strip() or att.user.username,
        "student_email": att.user.email,
        "status": att.status,
        "total_score": round(att.total_score, 2),
        "max_possible_score": round(att.max_possible_score, 2),
        "percentage": round(att.percentage, 2),
        "passed": att.passed,
        "total_questions": len(enriched_breakdown),
        "problems_attempted": att.problems_attempted,
        "problems_solved": att.problems_solved,
        "test_cases_passed": att.test_cases_passed,
        "test_cases_total": att.test_cases_total,
        "accuracy": accuracy,
        "time_taken_seconds": att.time_taken_seconds,
        "results_released": att.results_released,
        "problem_wise": enriched_breakdown,
        "started_at": att.started_at,
        "completed_at": att.completed_at,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_assessment_analytics(request, assessment_id: str):
    """Aggregate student-wise scoreboard, submissions, and problem-wise success rates."""
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    attempts = list(
        AssessmentAttempt.objects.filter(assessment=assessment)
        .select_related("user", "assessment")
        .order_by("-completed_at", "-started_at")
    )
    submissions = (
        CodeSubmissions.objects.filter(assessment=assessment)
        .select_related("user", "problem")
        .order_by("-created_at")
    )

    entries_cache: Dict[str, List[Dict[str, Any]]] = {}
    subs_by_attempt = _index_attempt_submissions(attempts)
    student_scores = [
        _build_admin_attempt_payload(att, entries_by_asmt=entries_cache, subs_by_attempt=subs_by_attempt)
        for att in attempts
    ]

    entries = _collect_assessment_entries(assessment)
    problem_stats = []
    for entry in entries:
        problem = entry.get("problem")
        if not problem:
            continue
        psubs = submissions.filter(problem=problem)
        distinct_students = psubs.values("user_id").distinct().count()
        accepted_students = (
            psubs.filter(status="Accepted").values("user_id").distinct().count()
        )
        partial_count = psubs.filter(status="Partial Accepted").count()
        avg_score = psubs.aggregate(avg=Avg("score")).get("avg") or 0.0
        avg_time = psubs.aggregate(avg=Avg("execution_time_ms")).get("avg") or 0.0
        success_rate = (
            round((accepted_students / distinct_students) * 100.0, 2)
            if distinct_students > 0
            else 0.0
        )
        problem_stats.append(
            {
                "problem_id": problem.problem_id,
                "title": problem.title,
                "difficulty": problem.difficulty,
                "marks": entry["marks"],
                "total_submissions": psubs.count(),
                "students_attempted": distinct_students,
                "students_solved": accepted_students,
                "partial_submissions": partial_count,
                "success_rate": success_rate,
                "average_score": round(avg_score, 2),
                "average_execution_ms": round(avg_time, 2),
            }
        )

    completed_scores = [s for s in student_scores if s["status"] in TERMINAL_ATTEMPT_STATUSES]
    avg_pct = (
        round(sum(s["percentage"] for s in completed_scores) / len(completed_scores), 2)
        if completed_scores
        else 0.0
    )
    pass_rate = (
        round(
            (sum(1 for s in completed_scores if s["passed"]) / len(completed_scores))
            * 100.0,
            2,
        )
        if completed_scores
        else 0.0
    )

    return Response(
        {
            "assessment": CodingAssessmentSummarySerializer(assessment).data,
            "overview": {
                "total_attempts": len(student_scores),
                "completed_attempts": len(completed_scores),
                "average_percentage": avg_pct,
                "pass_rate": pass_rate,
                "total_submissions": submissions.count(),
            },
            "student_scores": student_scores,
            "problem_stats": problem_stats,
            "submissions": CodingSubmissionRecordSerializer(submissions[:150], many=True).data,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_assessment_release_results(request, assessment_id: str):
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    updated = AssessmentAttempt.objects.filter(
        assessment=assessment, status__in=TERMINAL_ATTEMPT_STATUSES
    ).update(results_released=True)
    if not assessment.show_results_immediately:
        assessment.show_results_immediately = True
        assessment.save(update_fields=["show_results_immediately"])
    return Response({"released_attempts": updated, "show_results_immediately": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_assessment_export(request, assessment_id: str):
    """Export assessment results cleanly as downloadable CSV or JSON."""
    assessment = get_object_or_404(CodingAssessment, assessment_id=assessment_id)
    attempts = (
        AssessmentAttempt.objects.filter(assessment=assessment)
        .select_related("user")
        .order_by("-total_score", "-completed_at")
    )
    export_format = (
        request.query_params.get("export_format")
        or request.query_params.get("type")
        or "csv"
    ).lower()

    rows = []
    for att in attempts:
        accuracy = (
            round((att.test_cases_passed / att.test_cases_total) * 100.0, 2)
            if att.test_cases_total > 0
            else 0.0
        )
        rows.append(
            {
                "attempt_id": att.attempt_id,
                "student_id": att.user.user_id,
                "student_name": f"{att.user.name} {att.user.lastname}".strip() or att.user.username,
                "email": att.user.email,
                "status": att.status,
                "total_score": round(att.total_score, 2),
                "max_score": round(att.max_possible_score, 2),
                "percentage": round(att.percentage, 2),
                "passed": "Passed" if att.passed else "Failed",
                "problems_attempted": att.problems_attempted,
                "problems_solved": att.problems_solved,
                "test_cases_passed": att.test_cases_passed,
                "test_cases_total": att.test_cases_total,
                "accuracy_pct": accuracy,
                "time_taken_seconds": att.time_taken_seconds,
                "completed_at": att.completed_at.isoformat() if att.completed_at else "",
            }
        )

    if export_format == "json":
        return Response({"assessment_id": assessment.assessment_id, "title": assessment.title, "results": rows})

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Attempt ID",
            "Student ID",
            "Student Name",
            "Email",
            "Status",
            "Score",
            "Max Score",
            "Percentage",
            "Result",
            "Problems Attempted",
            "Problems Solved",
            "Test Cases Passed",
            "Total Test Cases",
            "Accuracy (%)",
            "Time Taken (s)",
            "Completed At",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                _csv_safe(row["attempt_id"]),
                _csv_safe(row["student_id"]),
                _csv_safe(row["student_name"]),
                _csv_safe(row["email"]),
                _csv_safe(row["status"]),
                row["total_score"],
                row["max_score"],
                row["percentage"],
                row["passed"],
                row["problems_attempted"],
                row["problems_solved"],
                row["test_cases_passed"],
                row["test_cases_total"],
                row["accuracy_pct"],
                row["time_taken_seconds"],
                _csv_safe(row["completed_at"]),
            ]
        )

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    safe_slug = slugify(assessment.title) or assessment.assessment_id
    response["Content-Disposition"] = f'attachment; filename="{safe_slug}-results.csv"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_students_search(request):
    q = (request.query_params.get("search") or "").strip()
    qs = (
        AllUsers.objects.filter(
            ~Q(platform_name__iexact="sfs_blueprints")
            | Q(accounts_sessions__client_app__client_id="skiltrix")
            | Q(skiltrix_profile__isnull=False)
            | Q(course_enrollments__isnull=False)
            | Q(assessment_attempts__isnull=False)
            | Q(coding_submissions__isnull=False)
        )
        .distinct()
        .order_by("name", "username")
    )
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(lastname__icontains=q)
            | Q(email__icontains=q)
            | Q(username__icontains=q)
            | Q(user_id__icontains=q)
        )
    return Response({"students": StudentCompactSerializer(qs[:50], many=True).data})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_all_submissions(request):
    """Global feed of all assessment attempts & coding submissions for Admin Submissions view."""
    attempts_qs = (
        AssessmentAttempt.objects.select_related("user", "assessment")
        .order_by("-completed_at", "-started_at")
    )
    subs_qs = (
        CodeSubmissions.objects.select_related("user", "problem", "assessment")
        .order_by("-created_at")
    )

    attempts_list = list(attempts_qs[:200])
    entries_cache: Dict[str, List[Dict[str, Any]]] = {}
    subs_by_attempt = _index_attempt_submissions(attempts_list)
    attempt_rows = [
        _build_admin_attempt_payload(att, entries_by_asmt=entries_cache, subs_by_attempt=subs_by_attempt)
        for att in attempts_list
    ]

    return Response(
        {
            "attempts": attempt_rows,
            "coding_submissions": CodingSubmissionRecordSerializer(subs_qs[:200], many=True).data,
            "total_attempts": attempts_qs.count(),
            "total_coding_submissions": subs_qs.count(),
        }
    )
