import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from sfs.models import AllUsers
from .codelab_models import CodeProject, ProjectFile


class WorkspaceOwnershipAPITests(TestCase):
    def setUp(self):
        self.temp_workspace_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_workspace_root.cleanup)
        workspace_patch = patch("skiltrix.codelab_runner.WORKSPACE_BASE_DIR", Path(self.temp_workspace_root.name))
        workspace_patch.start()
        self.addCleanup(workspace_patch.stop)
        self.user_a = AllUsers.objects.create(
            user_id="workspace_user_a", username="workspace_a", email="workspace-a@example.test",
            name="Workspace", lastname="A",
        )
        self.user_b = AllUsers.objects.create(
            user_id="workspace_user_b", username="workspace_b", email="workspace-b@example.test",
            name="Workspace", lastname="B",
        )
        self.project_a = CodeProject.objects.create(
            project_id="workspace_project_a", user=self.user_a, title="Same name", slug="same-a",
        )
        self.project_b = CodeProject.objects.create(
            project_id="workspace_project_b", user=self.user_b, title="Same name", slug="same-b",
        )
        self.secret_file = ProjectFile.objects.create(
            file_id="workspace_file_b", project=self.project_b, path="secret.py", name="secret.py",
            content="private", size_bytes=7,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user_a)

    def test_project_list_is_scoped_to_authenticated_user(self):
        response = self.client.get("/apps/skiltrix/api/codelab/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([project["project_id"] for project in response.data], [self.project_a.project_id])

    def test_client_user_id_cannot_change_new_project_owner(self):
        response = self.client.post("/apps/skiltrix/api/codelab/projects/", {
            "title": "Same name", "user_id": self.user_b.user_id,
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(CodeProject.objects.get(project_id=response.data["project_id"]).user_id, self.user_a.user_id)

    def test_another_users_file_is_not_readable(self):
        response = self.client.get(
            f"/apps/skiltrix/api/codelab/projects/{self.project_b.project_id}/files/content/",
            {"path": self.secret_file.path},
        )
        self.assertEqual(response.status_code, 404)

    def test_diagnostics_are_scoped_to_owned_projects_and_files(self):
        foreign_project = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{self.project_b.project_id}/diagnostics/",
            {"path": self.secret_file.path, "source": "def x(): pass"}, format="json",
        )
        self.assertEqual(foreign_project.status_code, 404)

        foreign_project_wide = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{self.project_b.project_id}/diagnostics/",
            {"project_wide": True}, format="json",
        )
        self.assertEqual(foreign_project_wide.status_code, 404)

        own_project_foreign_file = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{self.project_a.project_id}/diagnostics/",
            {"path": "../secret.py", "source": "private"}, format="json",
        )
        self.assertEqual(own_project_foreign_file.status_code, 400)

    def test_stale_file_version_returns_conflict(self):
        content_url = f"/apps/skiltrix/api/codelab/projects/{self.project_a.project_id}/files/content/"
        save_url = f"/apps/skiltrix/api/codelab/projects/{self.project_a.project_id}/files/save/"
        ProjectFile.objects.create(
            file_id="workspace_file_a", project=self.project_a, path="main.py", name="main.py",
            content="initial", size_bytes=7,
        )
        version = self.client.get(content_url, {"path": "main.py"}).data["revision"]
        saved = self.client.post(save_url, {
            "path": "main.py", "content": "first edit", "expected_revision": version,
        }, format="json")
        self.assertEqual(saved.status_code, 200)
        conflict = self.client.post(save_url, {
            "path": "main.py", "content": "stale edit", "expected_revision": version,
        }, format="json")
        self.assertEqual(conflict.status_code, 409)

    def test_workspace_endpoints_require_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/apps/skiltrix/api/codelab/projects/")
        self.assertEqual(response.status_code, 403)

    def test_signin_establishes_server_session_for_workspace_api(self):
        self.user_a.set_password("correct-horse-battery")
        self.user_a.save(update_fields=["password"])
        browser = APIClient()
        login = browser.post("/signin/", {
            "username": self.user_a.username,
            "password": "correct-horse-battery",
        }, format="json")
        self.assertEqual(login.status_code, 200)
        self.assertIn("sessionid", browser.cookies)
        projects = browser.get("/apps/skiltrix/api/codelab/projects/")
        self.assertEqual(projects.status_code, 200)
        self.assertEqual([project["project_id"] for project in projects.data], [self.project_a.project_id])
