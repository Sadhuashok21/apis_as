import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from skiltrix.models import (
    CodingProblems,
    TestCases,
    CodingAssessment,
    AssessmentQuestion,
    AssessmentAttempt,
)


class CodeLabAssessmentTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create DSA problem
        self.dsa_prob = CodingProblems.objects.create(
            problem_id="prob_test_dsa",
            slug="max-subarray-sum",
            title="Max Subarray Sum",
            difficulty="Easy",
            category="DSA",
            question_type="algorithmic",
            description="Find maximum subarray sum.",
            constraints="1 <= N <= 1000",
            expected_complexity="O(N) Time, O(1) Space",
            starter_python="def maxSubArray(nums):\n    return max(nums)",
            explanation="Kadane's algorithm runs in O(N) time.",
        )
        TestCases.objects.create(
            test_case_id="tc_dsa_1",
            problem=self.dsa_prob,
            input_data="[-2,1,-3,4,-1,2,1,-5,4]",
            expected_output="6",
            is_sample=True,
            is_hidden=False,
            category="Sample",
        )
        TestCases.objects.create(
            test_case_id="tc_dsa_2",
            problem=self.dsa_prob,
            input_data="[1]",
            expected_output="1",
            is_sample=False,
            is_hidden=True,
            category="Boundary",
        )

        # Create Backend Debugging problem
        self.debug_prob = CodingProblems.objects.create(
            problem_id="prob_test_debug",
            slug="fix-serializer-many-true",
            title="Fix Serializer many=True",
            difficulty="Medium",
            category="Backend Debugging",
            question_type="debugging",
            description="Fix 500 error on serializer.",
            error_snippet="AttributeError: 'QuerySet' object has no attribute 'title'",
            expected_behavior="Return serialized JSON list with status 200.",
            expected_complexity="O(N) Serialization",
            starter_python="def serialize_items(items):\n    return [item.title for item in items]",
            explanation="Ensure many=True is passed when serializing QuerySets.",
        )
        TestCases.objects.create(
            test_case_id="tc_debug_1",
            problem=self.debug_prob,
            input_data="[{'title': 'Alpha'}, {'title': 'Beta'}]",
            expected_output="['Alpha', 'Beta']",
            is_sample=True,
            is_hidden=False,
            category="Sample",
        )
        TestCases.objects.create(
            test_case_id="tc_debug_2",
            problem=self.debug_prob,
            input_data="[]",
            expected_output="[]",
            is_sample=False,
            is_hidden=True,
            category="Edge Case",
        )

        # Create Assessment
        self.assessment = CodingAssessment.objects.create(
            assessment_id="asmt_test_sde",
            slug="test-sde-assessment",
            title="Test SDE Assessment",
            duration_minutes=60,
            description="Assessment testing DSA and backend debugging.",
        )
        AssessmentQuestion.objects.create(
            item_id="item_asmt_1",
            assessment=self.assessment,
            problem=self.dsa_prob,
            order=1,
            marks=50,
        )
        AssessmentQuestion.objects.create(
            item_id="item_asmt_2",
            assessment=self.assessment,
            problem=self.debug_prob,
            order=2,
            marks=50,
        )

    def test_problem_listing_and_filtering(self):
        """Test problem listing and category filtering."""
        res = self.client.get("/apps/skiltrix/api/problems/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 2)

        debug_res = self.client.get("/apps/skiltrix/api/problems/?category=Backend Debugging")
        self.assertEqual(debug_res.status_code, status.HTTP_200_OK)
        debug_ids = [p["problem_id"] for p in debug_res.data]
        self.assertIn("prob_test_debug", debug_ids)
        self.assertNotIn("prob_test_dsa", debug_ids)

    def test_hidden_test_cases_not_leaked_in_public_endpoint(self):
        """Hidden test cases must not expose inputs or outputs via public problem detail."""
        res = self.client.get(f"/apps/skiltrix/api/problems/{self.dsa_prob.problem_id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data
        self.assertNotIn("solution", data)
        # sample_test_cases should only have sample test cases
        samples = data.get("sample_test_cases", [])
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["input_data"], "[-2,1,-3,4,-1,2,1,-5,4]")

    def test_editorial_security_locked_without_attempt(self):
        """Editorial should return 403 locked response when user hasn't attempted problem."""
        res = self.client.get(f"/apps/skiltrix/api/problems/{self.dsa_prob.problem_id}/explanation/?user_id=new_user_123")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(res.data.get("status"))
        self.assertIn("unlock after your first submission", res.data.get("message"))

    def test_sample_execution(self):
        """Running sample test cases evaluates correctly."""
        payload = {
            "problem_id": self.dsa_prob.problem_id,
            "language": "python",
            "code": "print('6')",
        }
        res = self.client.post("/apps/skiltrix/api/actions/run-sample-code/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("test_results", res.data)

    def test_assessment_flow_start_autosave_submit(self):
        """Test complete assessment lifecycle with scorecard generation."""
        # 1. Start assessment
        start_res = self.client.post(
            "/apps/skiltrix/api/actions/start-assessment/",
            {"user_id": "test_candidate_1", "assessment_id": self.assessment.assessment_id},
            format="json",
        )
        self.assertEqual(start_res.status_code, status.HTTP_200_OK)
        attempt_id = start_res.data.get("attempt_id")
        self.assertIsNotNone(attempt_id)
        self.assertEqual(len(start_res.data["assessment"]["questions"]), 2)

        # 2. Autosave draft
        save_res = self.client.post(
            "/apps/skiltrix/api/actions/autosave-assessment-draft/",
            {
                "attempt_id": attempt_id,
                "problem_id": "prob_test_dsa",
                "code": "def solve(): pass",
                "language": "python",
            },
            format="json",
        )
        self.assertEqual(save_res.status_code, status.HTTP_200_OK)
        self.assertTrue(save_res.data.get("status"))

        # 3. Final submission
        submit_res = self.client.post(
            "/apps/skiltrix/api/actions/submit-assessment/",
            {
                "attempt_id": attempt_id,
                "submissions": {
                    "prob_test_dsa": {"code": "print(6)", "language": "python"},
                    "prob_test_debug": {"code": "print(['Alpha', 'Beta'])", "language": "python"},
                },
            },
            format="json",
        )
        self.assertEqual(submit_res.status_code, status.HTTP_200_OK)
        self.assertTrue(submit_res.data.get("status"))
        self.assertIn("score_summary", submit_res.data)
        summary = submit_res.data["score_summary"]
        self.assertIn("skill_breakdown", summary)
        self.assertIn("problem_evaluations", submit_res.data)

        # Verify attempt in DB is completed
        attempt = AssessmentAttempt.objects.get(attempt_id=attempt_id)
        self.assertEqual(attempt.status, "completed")
