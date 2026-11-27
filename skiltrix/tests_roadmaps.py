"""Tests for SkilTrix Career Roadmaps DB seeding, auth gating, and admin CRUD."""

from __future__ import annotations

import uuid
from rest_framework import status
from rest_framework.test import APITestCase

from sfs.models import AllUsers
from skiltrix.models import LearningRoadmap


class CareerRoadmapTests(APITestCase):
    def setUp(self):
        self.student = AllUsers.objects.create(
            username=f"rm_stu_{uuid.uuid4().hex[:6]}",
            name="Roadmap",
            lastname="Learner",
            email=f"rm_stu_{uuid.uuid4().hex[:6]}@example.com",
            user_type="user",
            platform="web",
            platform_name="skiltrix",
            type="user",
            user_id=f"usr_rm_{uuid.uuid4().hex[:8]}",
            ip="127.0.0.1",
        )
        self.admin_user = AllUsers.objects.create(
            username=f"rm_adm_{uuid.uuid4().hex[:6]}",
            name="Roadmap",
            lastname="Admin",
            email=f"rm_adm_{uuid.uuid4().hex[:6]}@example.com",
            user_type="admin",
            platform="web",
            platform_name="skiltrix",
            type="admin",
            user_id=f"adm_rm_{uuid.uuid4().hex[:8]}",
            ip="127.0.0.1",
        )

    def test_seeded_roadmaps_list_and_auth_gate_on_detail(self):
        # 7 official roadmaps seeded by migration 0029
        self.assertGreaterEqual(LearningRoadmap.objects.count(), 7)

        # Public visitor can view summary list
        res_list = self.client.get("/apps/skiltrix/api/learning-roadmaps/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertTrue(res_list.data["requires_auth"])
        self.assertGreaterEqual(res_list.data["count"], 7)

        # Public visitor CANNOT access full roadmap detail (nor spoof via X-User-Id)
        res_anon = self.client.get(
            "/apps/skiltrix/api/learning-roadmaps/frontend_roadmap/",
            HTTP_X_USER_ID=self.student.user_id,
        )
        self.assertIn(
            res_anon.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

        # Authenticated user CAN access full roadmap detail & toggle stage
        self.client.force_authenticate(user=self.student)
        res_auth = self.client.get("/apps/skiltrix/api/learning-roadmaps/frontend_roadmap/")
        self.assertEqual(res_auth.status_code, status.HTTP_200_OK)
        self.assertEqual(res_auth.data["roadmap"]["key"], "frontend_roadmap")
        self.assertGreaterEqual(len(res_auth.data["roadmap"]["stages"]), 1)

        tog = self.client.post(
            "/apps/skiltrix/api/learning-roadmaps/frontend_roadmap/stage/1/toggle/",
            {"completed": True},
            format="json",
        )
        self.assertEqual(tog.status_code, status.HTTP_200_OK)
        self.assertTrue(tog.data["completed"])

    def test_admin_roadmap_crud_and_permissions(self):
        # Student forbidden from admin roadmap endpoints
        self.client.force_authenticate(user=self.student)
        res_forbid = self.client.get("/apps/skiltrix/api/admin/roadmaps/")
        self.assertEqual(res_forbid.status_code, status.HTTP_403_FORBIDDEN)

        # Admin can create, update, and delete a roadmap
        self.client.force_authenticate(user=self.admin_user)
        created = self.client.post(
            "/apps/skiltrix/api/admin/roadmaps/",
            {
                "key": "devops_cloud_roadmap",
                "title": "DevOps & Cloud Roadmap",
                "category": "Cloud & DevOps",
                "estimated_weeks": "10-14 Weeks",
                "accent_color": "#0EA5E9",
                "description": "Docker, Kubernetes, Terraform & CI/CD.",
                "stages": [
                    {
                        "stage_number": 1,
                        "badge_text": "STEP 01",
                        "title": "Linux & Containers",
                        "description": "Shell scripting and Docker internals",
                        "difficulty": "Beginner",
                        "estimated_hours": "12 Hours",
                        "topics": ["Bash", "Docker", "Compose"],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["key"], "devops_cloud_roadmap")
        self.assertEqual(len(created.data["stages"]), 1)

        patched = self.client.patch(
            "/apps/skiltrix/api/admin/roadmaps/devops_cloud_roadmap/",
            {"title": "DevOps & SRE Roadmap"},
            format="json",
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(patched.data["title"], "DevOps & SRE Roadmap")

        deleted = self.client.delete("/apps/skiltrix/api/admin/roadmaps/devops_cloud_roadmap/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LearningRoadmap.objects.filter(key="devops_cloud_roadmap").exists())
