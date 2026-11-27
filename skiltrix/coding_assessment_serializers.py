"""Serializers for SkilTrix Coding Assessment module (Candidate & Admin views)."""

from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from sfs.models import AllUsers

from .judge_service import get_starter_codes_for_problem
from .models import (
    AssessmentAssignment,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentQuestionItem,
    CodeSubmissions,
    CodingAssessment,
    CodingProblems,
    StudentBatch,
    TestCases,
)


def compute_schedule_status(assessment: CodingAssessment, override_start=None, override_end=None) -> str:
    """Determine schedule state (`upcoming`, `live`, `ended`, or `inactive`)."""
    if not assessment.active:
        return "inactive"
    now = timezone.now()
    start = override_start if override_start is not None else assessment.start_time
    end = override_end if override_end is not None else assessment.end_time
    if start and now < start:
        return "upcoming"
    if end and now > end:
        return "ended"
    return "live"


class PublicTestCaseSerializer(serializers.ModelSerializer):
    """Non-hidden sample test case exposed safely to candidates."""

    class Meta:
        model = TestCases
        fields = [
            "test_case_id",
            "input_data",
            "expected_output",
            "explanation",
            "points",
            "order",
        ]


class AdminTestCaseSerializer(serializers.ModelSerializer):
    """Full test case serializer strictly for authenticated admin endpoints."""

    class Meta:
        model = TestCases
        fields = [
            "test_case_id",
            "input_data",
            "expected_output",
            "is_sample",
            "is_hidden",
            "category",
            "explanation",
            "points",
            "order",
            "created_at",
        ]
        read_only_fields = ["test_case_id", "created_at"]


class CodingProblemCandidateSerializer(serializers.ModelSerializer):
    """Candidate-safe coding problem serializer (never includes hidden tests or solutions)."""

    public_test_cases = serializers.SerializerMethodField()
    starter_codes = serializers.SerializerMethodField()
    hidden_test_count = serializers.SerializerMethodField()
    total_test_count = serializers.SerializerMethodField()
    marks = serializers.SerializerMethodField()

    class Meta:
        model = CodingProblems
        fields = [
            "problem_id",
            "title",
            "slug",
            "difficulty",
            "question_type",
            "category",
            "topics",
            "marks",
            "points",
            "description",
            "input_format",
            "output_format",
            "constraints",
            "sample_input",
            "sample_output",
            "sample_explanation",
            "time_limit_seconds",
            "memory_limit_mb",
            "supported_languages",
            "starter_codes",
            "project_files",
            "public_test_cases",
            "hidden_test_count",
            "total_test_count",
        ]

    def get_marks(self, obj: CodingProblems) -> int:
        return int(obj.points or 100)

    def get_starter_codes(self, obj: CodingProblems):
        return get_starter_codes_for_problem(obj)

    def get_public_test_cases(self, obj: CodingProblems):
        if obj.question_type == "django_debug":
            return []
        qs = obj.test_cases.filter(is_hidden=False).order_by("order", "test_case_id")
        data = PublicTestCaseSerializer(qs, many=True).data
        if not data and (obj.sample_input or obj.sample_output):
            return [
                {
                    "test_case_id": "sample_1",
                    "input_data": obj.sample_input,
                    "expected_output": obj.sample_output,
                    "explanation": obj.sample_explanation or "",
                    "points": 1,
                    "order": 1,
                }
            ]
        return data

    def get_hidden_test_count(self, obj: CodingProblems) -> int:
        if obj.question_type == "django_debug":
            import re
            return sum(
                len(re.findall(r"^\s*def\s+test_", str(src or ""), re.MULTILINE))
                for src in (obj.hidden_test_files or {}).values()
            )
        return obj.test_cases.filter(is_hidden=True).count()

    def get_total_test_count(self, obj: CodingProblems) -> int:
        if obj.question_type == "django_debug":
            import re
            pub = sum(
                len(re.findall(r"^\s*def\s+test_", str(src or ""), re.MULTILINE))
                for src in (obj.project_files or {}).values()
            )
            return pub + self.get_hidden_test_count(obj)
        cnt = obj.test_cases.count()
        if cnt == 0 and (obj.sample_input or obj.sample_output):
            return 1
        return cnt


class CodingProblemAdminSerializer(serializers.ModelSerializer):
    """Full coding problem serializer for Admins (includes test cases & solutions)."""

    test_cases = AdminTestCaseSerializer(many=True, read_only=True)
    starter_codes = serializers.SerializerMethodField()
    public_test_count = serializers.SerializerMethodField()
    hidden_test_count = serializers.SerializerMethodField()

    class Meta:
        model = CodingProblems
        fields = [
            "problem_id",
            "title",
            "slug",
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
            "starter_codes",
            "project_files",
            "hidden_test_files",
            "solution_code",
            "explanation",
            "hints",
            "status",
            "is_active",
            "public_test_count",
            "hidden_test_count",
            "test_cases",
            "created_at",
        ]

    def get_starter_codes(self, obj: CodingProblems):
        return get_starter_codes_for_problem(obj)

    def get_public_test_count(self, obj: CodingProblems) -> int:
        return obj.test_cases.filter(is_hidden=False).count()

    def get_hidden_test_count(self, obj: CodingProblems) -> int:
        return obj.test_cases.filter(is_hidden=True).count()


class CodingAssessmentSummarySerializer(serializers.ModelSerializer):
    """Unified Assessment hub summary serializer across MCQ, Technical, Coding, Company types."""

    question_count = serializers.SerializerMethodField()
    coding_problem_count = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    schedule_status = serializers.SerializerMethodField()
    latest_attempt = serializers.SerializerMethodField()
    effective_start_time = serializers.SerializerMethodField()
    effective_end_time = serializers.SerializerMethodField()

    class Meta:
        model = CodingAssessment
        fields = [
            "assessment_id",
            "title",
            "slug",
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
            "start_time",
            "end_time",
            "effective_start_time",
            "effective_end_time",
            "schedule_status",
            "assignment_mode",
            "show_results_immediately",
            "is_company_mock",
            "proctoring_enabled",
            "require_fullscreen",
            "max_tab_switches",
            "active",
            "question_count",
            "coding_problem_count",
            "attempt_count",
            "latest_attempt",
            "created_at",
        ]

    def _get_override_window(self, obj: CodingAssessment):
        assignments = self.context.get("user_assignments", {})
        return assignments.get(obj.assessment_id)

    def get_effective_start_time(self, obj: CodingAssessment):
        ov = self._get_override_window(obj)
        return (ov.get("start_time") if ov else None) or obj.start_time

    def get_effective_end_time(self, obj: CodingAssessment):
        ov = self._get_override_window(obj)
        return (ov.get("end_time") if ov else None) or obj.end_time

    def get_schedule_status(self, obj: CodingAssessment) -> str:
        ov = self._get_override_window(obj)
        return compute_schedule_status(
            obj,
            override_start=ov.get("start_time") if ov else None,
            override_end=ov.get("end_time") if ov else None,
        )

    def get_question_count(self, obj: CodingAssessment) -> int:
        item_cnt = obj.question_items.filter(status="Published").count()
        if item_cnt:
            return item_cnt
        return obj.questions.count()

    def get_coding_problem_count(self, obj: CodingAssessment) -> int:
        cnt = obj.question_items.filter(
            status="Published", question_type="coding"
        ).count()
        if cnt:
            return cnt
        return obj.questions.count()

    def get_attempt_count(self, obj: CodingAssessment) -> int:
        return obj.attempts.count()

    def get_latest_attempt(self, obj: CodingAssessment):
        attempts_map = self.context.get("user_attempts", {})
        attempt = attempts_map.get(obj.assessment_id)
        if not attempt:
            return None
        return {
            "attempt_id": attempt.attempt_id,
            "status": attempt.status,
            "total_score": attempt.total_score,
            "max_possible_score": attempt.max_possible_score,
            "percentage": attempt.percentage,
            "passed": attempt.passed,
            "results_released": attempt.results_released or obj.show_results_immediately,
            "problems_attempted": attempt.problems_attempted,
            "problems_solved": attempt.problems_solved,
            "started_at": attempt.started_at,
            "completed_at": attempt.completed_at,
        }


class CodingSubmissionRecordSerializer(serializers.ModelSerializer):
    """Student submission history serializer (never exposes hidden test I/O)."""

    problem_id = serializers.CharField(source="problem.problem_id", read_only=True)
    problem_title = serializers.CharField(source="problem.title", read_only=True)
    assessment_id = serializers.CharField(
        source="assessment.assessment_id", read_only=True, default=None
    )
    assessment_title = serializers.CharField(
        source="assessment.title", read_only=True, default=None
    )
    student_id = serializers.CharField(source="user.user_id", read_only=True)
    student_name = serializers.SerializerMethodField()
    source_code = serializers.CharField(source="code", read_only=True)

    class Meta:
        model = CodeSubmissions
        fields = [
            "submission_id",
            "student_id",
            "student_name",
            "problem_id",
            "problem_title",
            "assessment_id",
            "assessment_title",
            "language",
            "source_code",
            "status",
            "passed_test_cases",
            "total_test_cases",
            "score",
            "max_score",
            "execution_time_ms",
            "memory_kb",
            "error_message",
            "is_final_submission",
            "created_at",
        ]

    def get_student_name(self, obj: CodeSubmissions) -> str:
        full = f"{obj.user.name} {obj.user.lastname}".strip()
        return full or obj.user.username or obj.user.email


class StudentCompactSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = AllUsers
        fields = ["user_id", "username", "name", "lastname", "full_name", "email"]

    def get_full_name(self, obj: AllUsers) -> str:
        return f"{obj.name} {obj.lastname}".strip() or obj.username


class StudentBatchSerializer(serializers.ModelSerializer):
    student_ids = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    students_detail = StudentCompactSerializer(source="students", many=True, read_only=True)
    student_count = serializers.SerializerMethodField()
    course_id = serializers.CharField(
        source="course.course_id", read_only=True, default=None
    )

    class Meta:
        model = StudentBatch
        fields = [
            "batch_id",
            "name",
            "description",
            "course_id",
            "is_active",
            "student_count",
            "student_ids",
            "students_detail",
            "created_at",
        ]
        read_only_fields = ["batch_id", "created_at"]

    def get_student_count(self, obj: StudentBatch) -> int:
        return obj.students.count()


class AssessmentAssignmentSerializer(serializers.ModelSerializer):
    assessment_id = serializers.CharField(
        source="assessment.assessment_id", read_only=True
    )
    student_id = serializers.CharField(
        source="student.user_id", read_only=True, default=None
    )
    student_name = serializers.SerializerMethodField()
    batch_id = serializers.CharField(
        source="batch.batch_id", read_only=True, default=None
    )
    batch_name = serializers.CharField(
        source="batch.name", read_only=True, default=None
    )

    class Meta:
        model = AssessmentAssignment
        fields = [
            "assignment_id",
            "assessment_id",
            "student_id",
            "student_name",
            "batch_id",
            "batch_name",
            "start_time",
            "end_time",
            "created_at",
        ]

    def get_student_name(self, obj: AssessmentAssignment):
        if not obj.student:
            return None
        return f"{obj.student.name} {obj.student.lastname}".strip() or obj.student.email
