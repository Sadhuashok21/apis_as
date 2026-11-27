"""Comprehensive tests for SkilTrix Coding Assessment sandbox, judging, APIs & security."""

from __future__ import annotations

from datetime import timedelta
import json
from unittest.mock import MagicMock, patch
import uuid

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from sfs.models import AllUsers
from skiltrix.execution.sandbox_dispatcher import SandboxExecutionResult, execute_in_sandbox
from skiltrix.judge_service import evaluate_coding_submission, run_coding_code
from skiltrix.models import (
    AssessmentAttempt,
    AssessmentQuestionItem,
    CodeSubmissions,
    CodingAssessment,
    CodingProblems,
    StudentBatch,
    TestCases,
)


class SandboxAndJudgeTests(APITestCase):
    def setUp(self):
        self.problem = CodingProblems.objects.create(
            problem_id=f"prob_t_{uuid.uuid4().hex[:8]}",
            title="Sum Two Numbers",
            slug=f"sum-two-{uuid.uuid4().hex[:6]}",
            difficulty="Easy",
            points=100,
            description="Read two ints a and b, print a+b.",
            time_limit_seconds=2.0,
            memory_limit_mb=256,
            supported_languages=["python", "java", "c", "cpp", "javascript"],
        )
        TestCases.objects.create(
            test_case_id=f"tc_pub_{uuid.uuid4().hex[:6]}",
            problem=self.problem,
            input_data="2 3",
            expected_output="5",
            is_hidden=False,
            is_sample=True,
            points=25,
            order=1,
        )
        TestCases.objects.create(
            test_case_id=f"tc_hid1_{uuid.uuid4().hex[:6]}",
            problem=self.problem,
            input_data="10 25",
            expected_output="35",
            is_hidden=True,
            is_sample=False,
            points=25,
            order=2,
        )
        TestCases.objects.create(
            test_case_id=f"tc_hid2_{uuid.uuid4().hex[:6]}",
            problem=self.problem,
            input_data="-4 9",
            expected_output="5",
            is_hidden=True,
            is_sample=False,
            points=25,
            order=3,
        )
        TestCases.objects.create(
            test_case_id=f"tc_hid3_{uuid.uuid4().hex[:6]}",
            problem=self.problem,
            input_data="100 200",
            expected_output="300",
            is_hidden=True,
            is_sample=False,
            points=25,
            order=4,
        )

    def test_python_accepted_and_hidden_case_redaction(self):
        res = evaluate_coding_submission(
            problem=self.problem,
            source_code="a, b = map(int, input().split()); print(a + b)",
            language="python",
        )
        self.assertEqual(res["status"], "Accepted")
        self.assertEqual(res["passed_test_cases"], 4)
        self.assertEqual(res["total_test_cases"], 4)
        self.assertEqual(res["score"], 100.0)
        self.assertGreaterEqual(res["execution_time_ms"], 0.0)

        # Public case exposes details; hidden cases MUST redact input/expected/actual
        pub = res["test_case_results"][0]
        self.assertFalse(pub["is_hidden"])
        self.assertIn("input", pub)
        for hidden_row in res["test_case_results"][1:]:
            self.assertTrue(hidden_row["is_hidden"])
            self.assertNotIn("input", hidden_row)
            self.assertNotIn("expected_output", hidden_row)
            self.assertNotIn("actual_output", hidden_row)

    def test_javascript_and_java_real_execution(self):
        js_code = (
            "const fs = require('fs');\n"
            "const [a, b] = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "console.log(a + b);\n"
        )
        js_res = evaluate_coding_submission(
            problem=self.problem, source_code=js_code, language="javascript"
        )
        self.assertEqual(js_res["status"], "Accepted")
        self.assertEqual(js_res["passed_test_cases"], 4)

        java_code = (
            "import java.util.*;\n"
            "public class Main {\n"
            "  public static void main(String[] args) {\n"
            "    Scanner sc = new Scanner(System.in);\n"
            "    System.out.println(sc.nextInt() + sc.nextInt());\n"
            "  }\n"
            "}\n"
        )
        java_res = evaluate_coding_submission(
            problem=self.problem, source_code=java_code, language="java"
        )
        self.assertEqual(java_res["status"], "Accepted")
        self.assertEqual(java_res["passed_test_cases"], 4)

    def test_partial_accepted_wrong_answer_runtime_error_and_tle(self):
        # Partial Accepted: pass public (2,3->5) and hid1 (10,25->35), fail hid2 & hid3
        partial_code = (
            "a, b = map(int, input().split())\n"
            "if a == 2 or a == 10:\n"
            "    print(a + b)\n"
            "else:\n"
            "    print(999)\n"
        )
        partial = evaluate_coding_submission(
            problem=self.problem, source_code=partial_code, language="python"
        )
        self.assertEqual(partial["status"], "Partial Accepted")
        self.assertEqual(partial["passed_test_cases"], 2)
        self.assertEqual(partial["failed_test_cases"], 2)
        self.assertEqual(partial["score"], 50.0)

        # Wrong Answer
        wrong = evaluate_coding_submission(
            problem=self.problem, source_code="print(-1)", language="python"
        )
        self.assertEqual(wrong["status"], "Wrong Answer")
        self.assertEqual(wrong["score"], 0.0)

        # Runtime Error
        runtime_err = evaluate_coding_submission(
            problem=self.problem, source_code="print(1 // 0)", language="python"
        )
        self.assertEqual(runtime_err["status"], "Runtime Error")

        # Compilation Error (Java)
        compile_err = evaluate_coding_submission(
            problem=self.problem,
            source_code="public class Main { broken syntax }",
            language="java",
        )
        self.assertEqual(compile_err["status"], "Compilation Error")

        # Time Limit Exceeded
        self.problem.time_limit_seconds = 0.5
        self.problem.save()
        tle = run_coding_code(
            problem=self.problem,
            source_code="while True:\n    pass",
            language="python",
            custom_input="1 2",
        )
        self.assertEqual(tle["status"], "Time Limit Exceeded")

    def test_security_policy_blocks_dangerous_code(self):
        with self.assertRaises(PermissionError):
            evaluate_coding_submission(
                problem=self.problem,
                source_code="import subprocess\nsubprocess.run(['whoami'])",
                language="python",
            )

    @patch("skiltrix.execution.sandbox_dispatcher.requests.post")
    def test_c_and_cpp_judge0_backend_and_mle(self, mock_post):
        mock_ok = MagicMock()
        mock_ok.json.return_value = {
            "status": {"id": 3, "description": "Accepted"},
            "stdout": "5\n",
            "stderr": "",
            "compile_output": "",
            "time": "0.012",
            "memory": 2048,
            "exit_code": 0,
        }
        mock_post.return_value = mock_ok

        with self.settings(EXECUTION_BACKEND="judge0", JUDGE0_API_URL="https://judge0.local"):
            c_res = execute_in_sandbox("c", "#include <stdio.h>\nint main(){printf(\"5\");}", "2 3")
            self.assertEqual(c_res.status, "OK")
            self.assertEqual(c_res.stdout, "5\n")
            cpp_res = execute_in_sandbox("cpp", "#include <iostream>\nint main(){std::cout<<5;}", "2 3")
            self.assertEqual(cpp_res.status, "OK")

            # Verify MLE detection when reported memory > memory_limit_mb
            mock_ok.json.return_value = {
                "status": {"id": 11, "description": "Memory limit exceeded"},
                "stdout": "",
                "stderr": "",
                "compile_output": "",
                "time": "0.100",
                "memory": 300000,
                "exit_code": 137,
            }
            mle_res = execute_in_sandbox("cpp", "int main(){}", "", memory_limit_mb=64)
            self.assertEqual(mle_res.status, "Memory Limit Exceeded")


class CodingAssessmentAPITests(APITestCase):
    def setUp(self):
        self.student_a = AllUsers.objects.create(
            username="student_a",
            name="Alice",
            lastname="Dev",
            email="alice@skiltrix.test",
            user_type="user",
            platform="web",
            platform_name="skiltrix",
            type="user",
            user_id="usr_alice_01",
            ip="127.0.0.1",
        )
        self.student_b = AllUsers.objects.create(
            username="student_b",
            name="Bob",
            lastname="Coder",
            email="bob@skiltrix.test",
            user_type="user",
            platform="web",
            platform_name="skiltrix",
            type="user",
            user_id="usr_bob_02",
            ip="127.0.0.1",
        )
        self.admin_user = AllUsers.objects.create(
            username="admin_st",
            name="Admin",
            lastname="Root",
            email="admin@skiltrix.test",
            user_type="admin",
            platform="web",
            platform_name="skiltrix",
            type="admin",
            user_id="usr_admin_01",
            ip="127.0.0.1",
        )

        self.problem = CodingProblems.objects.create(
            problem_id="prob_api_mul",
            title="Multiply Pair",
            slug="multiply-pair",
            difficulty="Easy",
            points=100,
            description="Read two integers a and b and output a*b.",
            sample_input="3 4",
            sample_output="12",
            time_limit_seconds=2.0,
            memory_limit_mb=256,
            supported_languages=["python", "java", "c", "cpp", "javascript"],
        )
        TestCases.objects.create(
            test_case_id="tc_api_pub",
            problem=self.problem,
            input_data="3 4",
            expected_output="12",
            is_hidden=False,
            is_sample=True,
            points=50,
            order=1,
        )
        TestCases.objects.create(
            test_case_id="tc_api_hid",
            problem=self.problem,
            input_data="7 8",
            expected_output="56",
            is_hidden=True,
            is_sample=False,
            points=50,
            order=2,
        )

        self.assessment = CodingAssessment.objects.create(
            assessment_id="ca_test_public",
            title="Public Coding Round",
            slug="public-coding-round",
            assessment_type="coding",
            category="Coding Assessments",
            difficulty="Easy",
            duration_minutes=60,
            pass_percentage=60,
            total_marks=100,
            supported_languages=["python", "java", "c", "cpp", "javascript"],
            assignment_mode="public",
            show_results_immediately=True,
            active=True,
        )
        self.item = AssessmentQuestionItem.objects.create(
            item_id="aqi_api_1",
            assessment=self.assessment,
            problem=self.problem,
            question_type="coding",
            title=self.problem.title,
            slug="aqi-multiply-pair",
            marks=100,
            order=1,
            status="Published",
        )

        self.client = APIClient()

    def test_authentication_and_cross_student_isolation(self):
        # Unauthenticated rejected
        unauth = self.client.get("/apps/skiltrix/api/assessments/coding/")
        self.assertIn(unauth.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        # Student A starts, runs custom stdin, submits problem, finalizes test
        self.client.force_authenticate(user=self.student_a)
        list_resp = self.client.get("/apps/skiltrix/api/assessments/coding/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(list_resp.data["count"], 1)

        start_resp = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/start/",
            {},
            format="json",
        )
        self.assertEqual(start_resp.status_code, status.HTTP_200_OK)
        attempt_id = start_resp.data["attempt"]["attempt_id"]

        # Candidate GET /start/ must NEVER leak hidden test cases
        q_payload = start_resp.data["questions"][0]["problem"]
        self.assertEqual(len(q_payload["public_test_cases"]), 1)
        self.assertNotIn("7 8", json.dumps(start_resp.data, default=str))

        # Run custom input
        run_resp = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/run/",
            {
                "attempt_id": attempt_id,
                "item_id": self.item.item_id,
                "language": "python",
                "source_code": "a, b = map(int, input().split()); print(a * b)",
                "custom_input": "9 9",
            },
            format="json",
        )
        self.assertEqual(run_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(run_resp.data["stdout"].strip(), "81")

        # Submit problem against public + hidden cases
        sub_prob = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/submit-problem/",
            {
                "attempt_id": attempt_id,
                "item_id": self.item.item_id,
                "language": "python",
                "source_code": "a, b = map(int, input().split()); print(a * b)",
            },
            format="json",
        )
        self.assertEqual(sub_prob.status_code, status.HTTP_200_OK)
        self.assertEqual(sub_prob.data["status"], "Accepted")
        self.assertEqual(sub_prob.data["score"], 100.0)
        hidden_row = sub_prob.data["test_case_results"][1]
        self.assertTrue(hidden_row["is_hidden"])
        self.assertNotIn("input", hidden_row)
        self.assertNotIn("expected_output", hidden_row)
        self.assertNotIn("actual_output", hidden_row)

        # Final submit
        fin_resp = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/submit/",
            {"attempt_id": attempt_id},
            format="json",
        )
        self.assertEqual(fin_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(fin_resp.data["total_score"], 100.0)
        self.assertEqual(fin_resp.data["accuracy"], 100.0)
        self.assertTrue(fin_resp.data["passed"])

        # Student B cannot view Student A's attempt result or submissions
        self.client.force_authenticate(user=self.student_b)
        forbidden_res = self.client.get(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/result/?attempt_id={attempt_id}"
        )
        self.assertEqual(forbidden_res.status_code, status.HTTP_403_FORBIDDEN)

        subs_b = self.client.get("/apps/skiltrix/api/assessments/coding/submissions/")
        self.assertEqual(subs_b.status_code, status.HTTP_200_OK)
        self.assertEqual(subs_b.data["count"], 0)

    def test_timer_expiration_autosubmits_saved_draft(self):
        self.client.force_authenticate(user=self.student_a)
        start = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/start/",
            {},
            format="json",
        ).data
        att_id = start["attempt"]["attempt_id"]

        # Autosave working solution without pressing problem submit
        save_resp = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/autosave/",
            {
                "attempt_id": att_id,
                "coding_drafts": {
                    self.item.item_id: {
                        "language": "python",
                        "code": "a, b = map(int, input().split()); print(a * b)",
                        "problem_id": self.problem.problem_id,
                    }
                },
            },
            format="json",
        )
        self.assertEqual(save_resp.status_code, status.HTTP_200_OK)

        # Force timer expiration
        AssessmentAttempt.objects.filter(attempt_id=att_id).update(
            expires_at=timezone.now() - timedelta(seconds=5)
        )
        late_run = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/run/",
            {
                "attempt_id": att_id,
                "item_id": self.item.item_id,
                "language": "python",
                "source_code": "print(0)",
            },
            format="json",
        )
        self.assertEqual(late_run.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(late_run.data["auto_submitted"])
        self.assertEqual(late_run.data["result"]["total_score"], 100.0)
        self.assertEqual(late_run.data["result"]["status"], "timed_out")

    def test_admin_batch_assignment_analytics_and_csv_export(self):
        # Student cannot access admin APIs
        self.client.force_authenticate(user=self.student_a)
        denied = self.client.get("/apps/skiltrix/api/assessments/coding/admin/problems/")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        # Admin creates assigned-only assessment for Batch containing Student A only
        self.client.force_authenticate(user=self.admin_user)
        batch_resp = self.client.post(
            "/apps/skiltrix/api/assessments/coding/admin/batches/",
            {"name": "Batch Alpha", "student_ids": [self.student_a.user_id]},
            format="json",
        )
        self.assertEqual(batch_resp.status_code, status.HTTP_201_CREATED)

        asmt_resp = self.client.post(
            "/apps/skiltrix/api/assessments/coding/admin/assessments/",
            {
                "title": "Restricted Batch Coding",
                "assessment_type": "coding",
                "duration_minutes": 45,
                "assignment_mode": "assigned",
                "problem_items": [{"problem_id": self.problem.problem_id, "marks": 100}],
            },
            format="json",
        )
        self.assertEqual(asmt_resp.status_code, status.HTTP_201_CREATED)
        restricted_id = asmt_resp.data["assessment_id"]

        assign_resp = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/admin/assessments/{restricted_id}/assignments/",
            {"batch_ids": [batch_resp.data["batch_id"]]},
            format="json",
        )
        self.assertEqual(assign_resp.status_code, status.HTTP_201_CREATED)

        # Student B (not in batch) gets 403; Student A gets 200
        self.client.force_authenticate(user=self.student_b)
        self.assertEqual(
            self.client.get(f"/apps/skiltrix/api/assessments/coding/{restricted_id}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(user=self.student_a)
        self.assertEqual(
            self.client.get(f"/apps/skiltrix/api/assessments/coding/{restricted_id}/").status_code,
            status.HTTP_200_OK,
        )

        # Admin analytics & CSV export
        self.client.force_authenticate(user=self.admin_user)
        analytics = self.client.get(
            f"/apps/skiltrix/api/assessments/coding/admin/assessments/{self.assessment.assessment_id}/analytics/"
        )
        self.assertEqual(analytics.status_code, status.HTTP_200_OK)
        self.assertIn("problem_stats", analytics.data)
        self.assertIn("student_scores", analytics.data)

        csv_resp = self.client.get(
            f"/apps/skiltrix/api/assessments/coding/admin/assessments/{self.assessment.assessment_id}/export/?export_format=csv"
        )
        self.assertEqual(csv_resp.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", csv_resp["Content-Type"])

        # Global admin submissions feed includes attempts across all assessments
        global_subs = self.client.get("/apps/skiltrix/api/assessments/coding/admin/submissions/")
        self.assertEqual(global_subs.status_code, status.HTTP_200_OK)
        self.assertIn("attempts", global_subs.data)
        self.assertIn("coding_submissions", global_subs.data)

        self.client.force_authenticate(user=self.student_a)
        self.assertEqual(
            self.client.get("/apps/skiltrix/api/assessments/coding/admin/submissions/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_mcq_assessment_and_rate_limiting(self):
        # Verify MCQ assessment grading & negative marking
        mcq_asmt = CodingAssessment.objects.create(
            assessment_id="ca_test_mcq",
            title="MCQ Negative Test",
            slug="mcq-negative-test",
            assessment_type="mcq",
            category="MCQ Assessments",
            duration_minutes=15,
            pass_percentage=50,
            total_marks=20,
            negative_marking=True,
            negative_marking_percentage=25,
            show_results_immediately=True,
            active=True,
        )
        q1 = AssessmentQuestionItem.objects.create(
            item_id="aqi_mcq_t1",
            assessment=mcq_asmt,
            question_type="mcq_single",
            title="Q1",
            slug="mcq-t1",
            options=[{"id": "a", "text": "Correct"}, {"id": "b", "text": "Wrong"}],
            correct_answers=["a"],
            marks=10,
            negative_marks=2.5,
            order=1,
            status="Published",
        )
        q2 = AssessmentQuestionItem.objects.create(
            item_id="aqi_mcq_t2",
            assessment=mcq_asmt,
            question_type="mcq_single",
            title="Q2",
            slug="mcq-t2",
            options=[{"id": "a", "text": "Wrong"}, {"id": "b", "text": "Correct"}],
            correct_answers=["b"],
            marks=10,
            negative_marks=2.5,
            order=2,
            status="Published",
        )

        self.client.force_authenticate(user=self.student_a)
        started = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{mcq_asmt.assessment_id}/start/",
            {},
            format="json",
        )
        self.assertEqual(started.status_code, status.HTTP_200_OK)
        # Ensure answer key is stripped from candidate payload
        self.assertNotIn("correct_answers", json.dumps(started.data, default=str))
        att_id = started.data["attempt"]["attempt_id"]

        res = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{mcq_asmt.assessment_id}/submit/",
            {
                "attempt_id": att_id,
                "selected_answers": {q1.item_id: "a", q2.item_id: "a"},
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # 10 (correct) - 2.5 (wrong) = 7.5
        self.assertEqual(res.data["total_score"], 7.5)

        # Admin submissions & analytics inspect endpoints expose candidate MCQ answers cleanly
        self.client.force_authenticate(user=self.admin_user)
        admin_subs = self.client.get("/apps/skiltrix/api/assessments/coding/admin/submissions/")
        self.assertEqual(admin_subs.status_code, status.HTTP_200_OK)
        mcq_attempt = next(a for a in admin_subs.data["attempts"] if a["attempt_id"] == att_id)
        self.assertEqual(mcq_attempt["total_questions"], 2)
        self.assertEqual(mcq_attempt["problem_wise"][0]["user_answer_display"], "A) Correct")
        self.assertEqual(mcq_attempt["problem_wise"][0]["correct_answer_display"], "A) Correct")
        self.assertEqual(mcq_attempt["problem_wise"][1]["user_answer_display"], "A) Wrong")
        self.assertEqual(mcq_attempt["problem_wise"][1]["correct_answer_display"], "B) Correct")
        self.client.force_authenticate(user=self.student_a)

        # Verify rate limiting kicks in on run endpoint when configured to 2/min
        from django.core.cache import cache
        cache.clear()
        self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/start/",
            {},
            format="json",
        )
        with self.settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"assessment_run": "2/min", "assessment_submit": "15/min"}}):
            r1 = self.client.post(
                f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/run/",
                {"item_id": self.item.item_id, "language": "python", "source_code": "print(1)"},
                format="json",
            )
            r2 = self.client.post(
                f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/run/",
                {"item_id": self.item.item_id, "language": "python", "source_code": "print(1)"},
                format="json",
            )
            r3 = self.client.post(
                f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/run/",
                {"item_id": self.item.item_id, "language": "python", "source_code": "print(1)"},
                format="json",
            )
            self.assertEqual(r1.status_code, status.HTTP_200_OK)
            self.assertEqual(r2.status_code, status.HTTP_200_OK)
            self.assertEqual(r3.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_starter_template_ignored_and_authenticated_proctoring_event(self):
        self.client.force_authenticate(user=self.student_a)
        start = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/start/",
            {},
            format="json",
        ).data
        att_id = start["attempt"]["attempt_id"]

        # Record owner proctoring event and confirm Student B cannot spoof it
        evt_ok = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/event/",
            {"attempt_id": att_id, "event_type": "TAB_SWITCH"},
            format="json",
        )
        self.assertEqual(evt_ok.status_code, status.HTTP_200_OK)
        self.assertEqual(evt_ok.data["tab_switch_count"], 1)

        self.client.force_authenticate(user=self.student_b)
        evt_forbidden = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/event/",
            {"attempt_id": att_id, "event_type": "TAB_SWITCH"},
            format="json",
        )
        self.assertEqual(evt_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # Switching language and leaving only unmodified starter code should count 0 attempted
        from skiltrix.judge_service import DEFAULT_STARTER_CODES

        self.client.force_authenticate(user=self.student_a)
        fin = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/submit/",
            {
                "attempt_id": att_id,
                "coding_drafts": {
                    self.item.item_id: {
                        "language": "python",
                        "code": DEFAULT_STARTER_CODES["python"],
                    }
                },
            },
            format="json",
        )
        self.assertEqual(fin.status_code, status.HTTP_200_OK)
        self.assertEqual(fin.data["problems_attempted"], 0)
        self.assertEqual(fin.data["total_score"], 0.0)


class DjangoDebugAssessmentTests(APITestCase):
    def setUp(self):
        from skiltrix.django_assessment_runner import (
            DEFAULT_AMAZON_HIDDEN_TEST_FILES,
            DEFAULT_AMAZON_PROJECT_FILES,
        )

        self.starter_files = dict(DEFAULT_AMAZON_PROJECT_FILES)
        self.hidden_files = dict(DEFAULT_AMAZON_HIDDEN_TEST_FILES)
        self.student = AllUsers.objects.create(
            username=f"dj_stu_{uuid.uuid4().hex[:6]}",
            name="Django",
            lastname="Candidate",
            email=f"dj_stu_{uuid.uuid4().hex[:6]}@example.com",
            user_type="user",
            platform="web",
            platform_name="skiltrix",
            type="user",
            user_id=f"usr_dj_{uuid.uuid4().hex[:8]}",
            ip="127.0.0.1",
        )
        self.problem = CodingProblems.objects.create(
            problem_id=f"prob_dj_{uuid.uuid4().hex[:8]}",
            title="Fix Django Post Upload Endpoint",
            slug=f"fix-django-post-{uuid.uuid4().hex[:6]}",
            difficulty="Medium",
            question_type="django_debug",
            points=150,
            description="Fix POST /api/posts/ JSON parsing, blank validation, unique slug, and 201 status.",
            time_limit_seconds=25.0,
            memory_limit_mb=512,
            supported_languages=["django"],
            project_files=self.starter_files,
            hidden_test_files=self.hidden_files,
        )
        self.assessment = CodingAssessment.objects.create(
            assessment_id=f"asmt_dj_{uuid.uuid4().hex[:6]}",
            title="Amazon Django Debug Assessment",
            slug=f"amazon-dj-{uuid.uuid4().hex[:6]}",
            assessment_type="coding",
            difficulty="Medium",
            duration_minutes=60,
            pass_percentage=60,
            total_marks=150,
            supported_languages=["django"],
            assignment_mode="public",
            show_results_immediately=True,
            active=True,
        )
        self.item = AssessmentQuestionItem.objects.create(
            item_id=f"item_dj_{uuid.uuid4().hex[:6]}",
            assessment=self.assessment,
            problem=self.problem,
            question_type="coding",
            title=self.problem.title,
            slug=f"item-dj-{uuid.uuid4().hex[:6]}",
            difficulty="Medium",
            marks=150,
            order=1,
            status="Published",
        )

    def test_django_debug_full_flow_and_hidden_protection(self):
        self.client.force_authenticate(user=self.student)
        start = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/start/",
            {},
            format="json",
        )
        self.assertEqual(start.status_code, status.HTTP_200_OK)
        q_node = start.data["questions"][0]
        self.assertIn("posts/views.py", q_node["project_files"])
        self.assertIn("README.md", q_node["project_files"])
        self.assertTrue(q_node.get("codelab_project_id"))
        self.assertIn("posts/tests.py", q_node.get("locked_paths", []))
        self.assertNotIn("posts/tests_hidden.py", q_node["project_files"])
        self.assertNotIn("hidden_test_files", q_node)
        att_id = start.data["attempt"]["attempt_id"]
        cl_pid = q_node["codelab_project_id"]

        # Locked file cannot be overwritten via CodeLab save endpoint
        lock_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{cl_pid}/files/save/",
            {"path": "posts/tests.py", "content": "# tamper", "expected_revision": 1},
            format="json",
        )
        self.assertEqual(lock_res.status_code, status.HTTP_403_FORBIDDEN)

        # Buggy starter fails public tests on run/
        bug_run = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/run/",
            {
                "attempt_id": att_id,
                "item_id": self.item.item_id,
                "language": "django",
                "files": self.starter_files,
            },
            format="json",
        )
        self.assertEqual(bug_run.status_code, status.HTTP_200_OK)
        self.assertFalse(bug_run.data["passed"])
        self.assertEqual(bug_run.data["total_test_cases"], 2)
        self.assertEqual(bug_run.data["passed_test_cases"], 0)

        # Fixed posts/views.py passes all 5 public + hidden tests even if candidate tries to tamper tests_hidden.py
        fixed_views = """import json
from django.http import JsonResponse
from django.utils.text import slugify
from .models import Post


def blog_home(request):
    return JsonResponse({"ok": True})


def posts_collection(request):
    if request.method == "GET":
        rows = list(Post.objects.values("id", "title", "slug", "content", "author_email", "is_published"))
        return JsonResponse({"status": True, "posts": rows}, status=200)

    if request.method == "POST":
        payload = {}
        if request.content_type and "application/json" in request.content_type:
            try:
                payload = json.loads(request.body.decode("utf-8") or "{}")
            except (ValueError, TypeError):
                return JsonResponse({"status": False, "error": "Invalid JSON"}, status=400)
        else:
            payload = request.POST

        title = str(payload.get("title") or "").strip()
        content = str(payload.get("content") or "").strip()
        author_email = str(payload.get("author_email") or "").strip()
        if not title or not content:
            return JsonResponse({"status": False, "error": "Title and content are required"}, status=400)

        base_slug = slugify(title) or "post"
        slug = base_slug
        idx = 2
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{idx}"
            idx += 1

        post = Post.objects.create(
            title=title,
            slug=slug,
            content=content,
            author_email=author_email,
        )
        return JsonResponse(
            {
                "status": True,
                "post": {
                    "id": post.id,
                    "title": post.title,
                    "slug": post.slug,
                    "content": post.content,
                    "author_email": post.author_email,
                },
            },
            status=201,
        )

    return JsonResponse({"status": False, "error": "Method not allowed"}, status=405)
"""
        fixed_files = dict(self.starter_files)
        fixed_files["posts/views.py"] = fixed_views
        fixed_files["posts/tests_hidden.py"] = "# malicious overwrite attempt"

        sub = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/submit-problem/",
            {
                "attempt_id": att_id,
                "item_id": self.item.item_id,
                "language": "django",
                "files": fixed_files,
            },
            format="json",
        )
        self.assertEqual(sub.status_code, status.HTTP_200_OK)
        self.assertEqual(sub.data["status"], "Accepted")
        self.assertEqual(sub.data["passed_test_cases"], 5)
        self.assertEqual(sub.data["total_test_cases"], 5)
        self.assertEqual(sub.data["score"], 150.0)

        fin = self.client.post(
            f"/apps/skiltrix/api/assessments/coding/{self.assessment.assessment_id}/submit/",
            {"attempt_id": att_id},
            format="json",
        )
        self.assertEqual(fin.status_code, status.HTTP_200_OK)
        self.assertEqual(fin.data["total_score"], 150.0)
        self.assertTrue(fin.data["passed"])

    def test_admin_upload_custom_django_zip_archive_and_dynamic_locks(self):
        import io
        import zipfile
        from django.core.files.uploadedfile import SimpleUploadedFile

        admin_user = AllUsers.objects.create(
            user_id="usr_django_archive_admin",
            username="django_archive_admin",
            email="django_archive_admin@skiltrix.com",
            name="Django Archive Admin",
            user_type="admin",
            platform="web",
            platform_name="skiltrix",
            type="admin",
            ip="127.0.0.1",
        )
        self.client.force_authenticate(user=admin_user)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("orders_bug/README.md", "# Orders Bug\nFix order total calculation.")
            zf.writestr("orders_bug/manage.py", "#!/usr/bin/env python\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')\n")
            zf.writestr("orders_bug/core/settings.py", "SECRET_KEY='x'\n")
            zf.writestr("orders_bug/core/urls.py", "urlpatterns = []\n")
            zf.writestr("orders_bug/orders/views.py", "def create_order(req): pass\n")
            zf.writestr("orders_bug/orders/tests.py", "class T:\n    def test_one(self): pass\n")
            zf.writestr("orders_bug/orders/tests_hidden.py", "class H:\n    def test_two(self): pass\n    def test_three(self): pass\n")
            zf.writestr("orders_bug/orders/__pycache__/views.cpython-312.pyc", b"\x00\x01\x02")
            zf.writestr("orders_bug/db.sqlite3", b"SQLite format 3\x00")
            zf.writestr("orders_bug/.venv/lib/site.py", "ignored")

        upload = SimpleUploadedFile("orders_bug.zip", buf.getvalue(), content_type="application/zip")
        res = self.client.post(
            "/apps/skiltrix/api/assessments/coding/admin/problems/parse-django-archive/",
            {"file": upload},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["stats"]["has_manage_py"])
        self.assertEqual(res.data["stats"]["public_test_count"], 1)
        self.assertEqual(res.data["stats"]["hidden_test_count"], 2)
        self.assertIn("orders/views.py", res.data["project_files"])
        self.assertIn("orders/tests.py", res.data["project_files"])
        self.assertNotIn("orders/tests_hidden.py", res.data["project_files"])
        self.assertIn("orders/tests_hidden.py", res.data["hidden_test_files"])
        self.assertNotIn("db.sqlite3", res.data["project_files"])
        self.assertIn("orders/tests.py", res.data["locked_files"])
        self.assertIn("core/settings.py", res.data["locked_files"])
        self.assertIn("core/urls.py", res.data["locked_files"])
        self.assertNotIn("orders/views.py", res.data["locked_files"])


