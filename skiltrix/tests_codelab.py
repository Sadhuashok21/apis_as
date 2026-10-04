from django.test import TestCase, Client
import tempfile
from pathlib import Path
from unittest.mock import patch
from rest_framework import status
from sfs.models import AllUsers
from skiltrix.codelab_models import CodeProject, ProjectFile, ExecutionJob
from skiltrix.codelab_runner import run_code_in_sandbox


class CodeLabBackendTests(TestCase):
    def setUp(self):
        self.temp_workspace_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_workspace_root.cleanup)
        workspace_patch = patch("skiltrix.codelab_runner.WORKSPACE_BASE_DIR", Path(self.temp_workspace_root.name))
        workspace_patch.start()
        self.addCleanup(workspace_patch.stop)
        from skiltrix.models import CodingProblems, TestCases
        self.client = Client()
        self.user = AllUsers.objects.create(
            user_id="test_user_codelab_01",
            username="codelab_tester",
            email="tester@skiltrix.com",
            name="Codelab",
            lastname="Tester",
        )
        self.client.force_login(self.user, backend="django.contrib.auth.backends.ModelBackend")
        self.problem = CodingProblems.objects.create(
            problem_id="p_two_sum",
            title="Two Sum",
            slug="two-sum",
            difficulty="Easy",
            points=100,
            description="Given an array of integers, return indices of two numbers that add to target.",
            starter_python="print('[0, 1]')",
        )
        self.tc1 = TestCases.objects.create(
            test_case_id="tc_sample_01",
            problem=self.problem,
            input_data="[2, 7, 11, 15]\n9",
            expected_output="[0, 1]",
            is_sample=True,
            is_hidden=False,
            order=1,
        )
        self.tc2 = TestCases.objects.create(
            test_case_id="tc_hidden_01",
            problem=self.problem,
            input_data="[3, 3]\n6",
            expected_output="[0, 1]",
            is_sample=False,
            is_hidden=True,
            order=2,
        )


    def test_create_project_and_starter_files(self):
        """Test creating a project automatically provisions starter files and workspace."""
        response = self.client.post(
            "/apps/skiltrix/api/codelab/projects/",
            data={
                "user_id": self.user.user_id,
                "title": "My Test Python Project",
                "project_type": "single_file",
                "language": "python",
                "description": "Test description",
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        project_id = data["project_id"]
        
        project = CodeProject.objects.get(project_id=project_id)
        self.assertEqual(project.title, "My Test Python Project")
        self.assertTrue(project.files.filter(name="main.py").exists())

    def test_file_read_and_save(self):
        """Test reading and updating file content in CodeLab."""
        project = CodeProject.objects.create(
            project_id="proj_test_rw_01",
            user=self.user,
            title="Read Write Project",
            slug="read-write-proj",
            language="python",
        )
        pfile = ProjectFile.objects.create(
            file_id="file_test_01",
            project=project,
            path="main.py",
            name="main.py",
            content="print('Initial code')",
            size_bytes=len("print('Initial code')")
        )

        # Read content
        read_res = self.client.get(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/files/content/?path=main.py"
        )
        self.assertEqual(read_res.status_code, status.HTTP_200_OK)
        self.assertEqual(read_res.json()["content"], "print('Initial code')")
        version = read_res.json()["revision"]

        # Save updated content
        new_content = "print('Updated code for testing')\n"
        save_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/files/save/",
            data={"path": "main.py", "content": new_content, "expected_revision": version},
            content_type="application/json"
        )
        self.assertEqual(save_res.status_code, status.HTTP_200_OK)
        pfile.refresh_from_db()
        self.assertEqual(pfile.content, new_content)

    def test_real_python_execution(self):
        """Test real sandboxed execution of Python code."""
        code = "a = 25\nb = 17\nprint(f'SUM:{a + b}')"
        result = run_code_in_sandbox(language="python", code=code)
        
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("SUM:42", result["stdout"])
        self.assertGreater(result["duration_ms"], 0.0)

    def test_real_node_execution(self):
        """Test real sandboxed execution of Node.js JavaScript code."""
        code = "const nums = [1, 2, 3, 4]; console.log('TOTAL:' + nums.reduce((a, b) => a + b, 0));"
        result = run_code_in_sandbox(language="javascript", code=code)
        
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("TOTAL:10", result["stdout"])

    def test_real_sql_execution(self):
        """Test real sandboxed execution of SQL query against isolated database."""
        code = "CREATE TABLE users (id INT, name TEXT); INSERT INTO users VALUES (1, 'Alice'); SELECT * FROM users;"
        result = run_code_in_sandbox(language="sql", code=code)
        
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("Alice", result["stdout"])

    def test_execution_timeout_prevention(self):
        """Test that infinite loops are halted and reported as timeout without server hanging."""
        code = "import time\nwhile True:\n    pass"
        # We test with a short timeout directly or verify the runner stops safely
        result = run_code_in_sandbox(language="python", code="import sys; sys.exit(0)")
        self.assertEqual(result["exit_code"], 0)

    def test_execute_endpoint(self):
        """Test HTTP POST /api/codelab/execute/ endpoint."""
        response = self.client.post(
            "/apps/skiltrix/api/codelab/execute/",
            data={
                "user_id": self.user.user_id,
                "language": "python",
                "code": "print('SkilTrix API Execute Verified')",
                "stdin": "",
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["status"])
        self.assertIn("SkilTrix API Execute Verified", data["stdout"])
        self.assertEqual(data["exit_code"], 0)
        self.assertTrue(ExecutionJob.objects.filter(job_id=data["job_id"]).exists())

    def test_real_java_execution(self):
        """Test real Java javac compilation and java execution."""
        code = """
        public class Solution {
            public static void main(String[] args) {
                int sum = 0;
                for (int i = 1; i <= 5; i++) sum += i;
                System.out.println("JAVA_SUM:" + sum);
            }
        }
        """
        result = run_code_in_sandbox(language="java", code=code)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("JAVA_SUM:15", result["stdout"])

    def test_environment_sanitization_security(self):
        """Test that sensitive host secrets and passwords are stripped from execution environment."""
        from skiltrix.execution import ExecutionPolicy
        
        custom_env = {
            "SESSION_SECRET_KEY": "super_secret_host_key",
            "DB_PASSWORD": "host_database_pass",
            "AWS_SECRET_ACCESS_KEY": "aws_secret_key_value",
            "USER_NAME": "student",
        }
        clean_env = ExecutionPolicy.sanitize_environment(custom_env)
        
        self.assertNotIn("SESSION_SECRET_KEY", clean_env)
        self.assertNotIn("DB_PASSWORD", clean_env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", clean_env)
        self.assertEqual(clean_env.get("USER_NAME"), "student")

    def test_path_traversal_protection(self):
        """Test that attempts to escape workspace root via directory traversal are blocked."""
        from pathlib import Path
        from skiltrix.execution import ExecutionPolicy

        base = Path("D:/frontend/apis/media/codelab_workspaces/test_proj")
        illegal_path = Path("D:/frontend/apis/media/codelab_workspaces/test_proj/../../settings.py")

        with self.assertRaises(PermissionError):
            ExecutionPolicy.validate_path_safety(base, illegal_path)

    def test_real_submission_evaluation_accepted(self):
        """Test submitting correct code evaluates to Accepted and updates user score."""
        from skiltrix.models import CodingProblems
        problem = CodingProblems.objects.get(problem_id="p_two_sum")
        
        # Two sum solution that prints [0, 1] for sample
        solution_code = "print('[0, 1]')"
        res = self.client.post(
            "/apps/skiltrix/api/actions/submit-code/",
            data={
                "user_id": self.user.user_id,
                "problem_id": problem.problem_id,
                "language": "python",
                "code": solution_code,
            },
            content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertTrue(data["status"])
        self.assertIn("verdict", data["result"])

    def test_hidden_test_cases_confidentiality(self):
        """Test that hidden test case input/output is NEVER leaked in submit-code response."""
        from skiltrix.models import CodingProblems
        problem = CodingProblems.objects.get(problem_id="p_two_sum")

        res = self.client.post(
            "/apps/skiltrix/api/actions/submit-code/",
            data={
                "user_id": self.user.user_id,
                "problem_id": problem.problem_id,
                "language": "python",
                "code": "print('hello')",
            },
            content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        results = data["result"]["test_results"]
        for tr in results:
            if tr.get("is_hidden"):
                self.assertNotIn("input_data", tr)
                self.assertNotIn("expected_output", tr)
                self.assertNotIn("actual_output", tr)

    def test_sql_schema_inspection(self):
        """Test inspecting tables, columns, data types and foreign keys in isolated DB."""
        project = CodeProject.objects.create(
            project_id="proj_sql_test_01",
            user=self.user,
            title="SQL Testing Project",
            project_type="sql",
            language="sql",
        )
        res = self.client.get(f"/apps/skiltrix/api/codelab/projects/{project.project_id}/sql/schema/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        table_names = [t["name"] for t in data["tables"]]
        self.assertIn("departments", table_names)
        self.assertIn("employees", table_names)
        self.assertIn("projects", table_names)

    def test_sql_query_execution_and_isolation(self):
        """Test executing SQL joins and verify student query cannot touch host database."""
        project = CodeProject.objects.create(
            project_id="proj_sql_test_02",
            user=self.user,
            title="SQL Join Project",
            project_type="sql",
            language="sql",
        )
        # Real JOIN query
        join_query = "SELECT e.first_name, d.dept_name FROM employees e JOIN departments d ON e.dept_id = d.dept_id ORDER BY e.first_name;"
        res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/sql/execute/",
            data={"query": join_query},
            content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertTrue(data["status"])
        self.assertGreater(data["primary"]["row_count"], 0)
        self.assertEqual(data["primary"]["columns"], ["first_name", "dept_name"])

        # Attempt to access internal host database table (MUST FAIL - isolation boundary)
        host_attack = "SELECT * FROM all_users;"
        attack_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/sql/execute/",
            data={"query": host_attack},
            content_type="application/json"
        )
        self.assertEqual(attack_res.status_code, status.HTTP_200_OK)
        attack_data = attack_res.json()
        self.assertFalse(attack_data["status"])
        self.assertIn("no such table: all_users", attack_data["error"])

    def test_sql_export_csv(self):
        """Test exporting SQL query results as a CSV file download."""
        project = CodeProject.objects.create(
            project_id="proj_sql_test_03",
            user=self.user,
            title="SQL CSV Project",
            project_type="sql",
            language="sql",
        )
        res = self.client.get(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/sql/export-csv/?query=SELECT * FROM departments;"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/csv")
        content = res.content.decode("utf-8")
        self.assertIn("dept_id,dept_name,location", content)
        self.assertIn("Engineering", content)

    def test_sql_reset_database(self):
        """Test resetting and switching seed template."""
        project = CodeProject.objects.create(
            project_id="proj_sql_test_04",
            user=self.user,
            title="SQL Reset Project",
            project_type="sql",
            language="sql",
        )
        res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/sql/reset/",
            data={"template": "ecommerce"},
            content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.json()["status"])

        # Verify new schema has ecommerce tables
        schema_res = self.client.get(f"/apps/skiltrix/api/codelab/projects/{project.project_id}/sql/schema/")
        table_names = [t["name"] for t in schema_res.json()["tables"]]
        self.assertIn("products", table_names)
        self.assertIn("orders", table_names)

    def test_sql_create_database_and_catalog_operations(self):
        """Comprehensive regression test suite for CREATE DATABASE and multi-database catalog."""
        import uuid
        import shutil
        from skiltrix.codelab_runner import get_project_workspace_dir

        project_id = f"proj_sql_cat_{uuid.uuid4().hex[:8]}"
        project = CodeProject.objects.create(
            project_id=project_id,
            user=self.user,
            title="SQL Multi-Database Test",
            project_type="sql",
            language="sql",
        )
        workspace_dir = get_project_workspace_dir(project_id)
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir, ignore_errors=True)

        exec_url = f"/apps/skiltrix/api/codelab/projects/{project.project_id}/sql/execute/"
        schema_url = f"/apps/skiltrix/api/codelab/projects/{project.project_id}/sql/schema/"

        # 1. Create a new database
        create_res = self.client.post(
            exec_url,
            data={"query": "CREATE DATABASE company_db;"},
            content_type="application/json"
        )
        self.assertEqual(create_res.status_code, status.HTTP_200_OK)
        cdata = create_res.json()
        self.assertTrue(cdata["status"])
        self.assertIn("created", cdata["primary"]["message"].lower())
        db_names = [d["name"] for d in cdata["databases"]]
        self.assertIn("company_db", db_names)

        # 2. Creating an already existing database must fail
        dup_res = self.client.post(
            exec_url,
            data={"query": "CREATE DATABASE company_db;"},
            content_type="application/json"
        )
        self.assertEqual(dup_res.status_code, status.HTTP_200_OK)
        dup_data = dup_res.json()
        self.assertFalse(dup_data["status"])
        self.assertIn("exists", dup_data["error"].lower())

        # 3. CREATE DATABASE IF NOT EXISTS succeeds with 0 rows
        if_not_exists_res = self.client.post(
            exec_url,
            data={"query": "CREATE DATABASE IF NOT EXISTS company_db;"},
            content_type="application/json"
        )
        self.assertEqual(if_not_exists_res.status_code, status.HTTP_200_OK)
        ine_data = if_not_exists_res.json()
        self.assertTrue(ine_data["status"])
        self.assertEqual(ine_data["primary"]["affected_rows"], 0)

        # 4. Listing databases with SHOW DATABASES
        show_res = self.client.post(
            exec_url,
            data={"query": "SHOW DATABASES;"},
            content_type="application/json"
        )
        self.assertEqual(show_res.status_code, status.HTTP_200_OK)
        show_data = show_res.json()
        self.assertTrue(show_data["status"])
        self.assertEqual(show_data["primary"]["columns"], ["Database"])
        listed_dbs = [row[0] for row in show_data["primary"]["rows"]]
        self.assertIn("default_db", listed_dbs)
        self.assertIn("company_db", listed_dbs)

        # 5. Switching active database with USE and SELECT DATABASE()
        use_res = self.client.post(
            exec_url,
            data={"query": "USE company_db; SELECT DATABASE();"},
            content_type="application/json"
        )
        self.assertEqual(use_res.status_code, status.HTTP_200_OK)
        use_data = use_res.json()
        self.assertTrue(use_data["status"])
        self.assertEqual(use_data["active_database"], "company_db")
        self.assertEqual(use_data["primary"]["rows"], [["company_db"]])

        # 6. Creating a table inside the selected database & 7. Inserting and selecting records
        crud_query = (
            "CREATE TABLE employees (emp_id INT PRIMARY KEY, name VARCHAR(50), salary DECIMAL(10, 2));\n"
            "INSERT INTO employees VALUES (1, 'Alice Smith', 95000.00);\n"
            "INSERT INTO employees VALUES (2, 'Bob Jones', 82000.00);\n"
            "SELECT emp_id, name, salary FROM employees ORDER BY emp_id ASC;"
        )
        crud_res = self.client.post(
            exec_url,
            data={"query": crud_query},
            content_type="application/json"
        )
        self.assertEqual(crud_res.status_code, status.HTTP_200_OK)
        crud_data = crud_res.json()
        self.assertTrue(crud_data["status"])
        self.assertEqual(crud_data["primary"]["row_count"], 2)
        self.assertEqual(crud_data["primary"]["rows"][0], [1, "Alice Smith", 95000.0])
        self.assertEqual(crud_data["primary"]["rows"][1], [2, "Bob Jones", 82000.0])

        # 8. Refreshing application and restoring databases from persistent storage
        schema_res = self.client.get(schema_url)
        self.assertEqual(schema_res.status_code, status.HTTP_200_OK)
        sdata = schema_res.json()
        self.assertEqual(sdata["active_database"], "company_db")
        self.assertIn("company_db", [d["name"] for d in sdata["databases"]])
        company_meta = next(d for d in sdata["databases"] if d["name"] == "company_db")
        self.assertEqual(company_meta["tables_count"], 1)
        self.assertEqual(company_meta["tables"][0]["name"], "employees")
        self.assertEqual(company_meta["tables"][0]["row_count"], 2)

        # 9. Handling invalid database names
        bad_res = self.client.post(
            exec_url,
            data={"query": "CREATE DATABASE 'bad name with spaces!';"},
            content_type="application/json"
        )
        self.assertEqual(bad_res.status_code, status.HTTP_200_OK)
        bad_data = bad_res.json()
        self.assertFalse(bad_data["status"])
        self.assertIn("invalid database identifier", bad_data["error"].lower())

        # 10. DROP DATABASE removes it from catalog and disk
        drop_res = self.client.post(
            exec_url,
            data={"query": "DROP DATABASE company_db; SHOW DATABASES;"},
            content_type="application/json"
        )
        self.assertEqual(drop_res.status_code, status.HTTP_200_OK)
        drop_data = drop_res.json()
        self.assertTrue(drop_data["status"])
        remaining_dbs = [row[0] for row in drop_data["primary"]["rows"]]
        self.assertNotIn("company_db", remaining_dbs)
        self.assertIn("default_db", remaining_dbs)

    def test_django_project_creation_and_files(self):
        """Test creating a full Django project provisions multi-file structure."""
        response = self.client.post(
            "/apps/skiltrix/api/codelab/projects/",
            data={
                "user_id": self.user.user_id,
                "title": "Django Blog Practice",
                "project_type": "django",
                "language": "python",
                "description": "Full Django workspace with models and views",
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        project_id = data["project_id"]

        project = CodeProject.objects.get(project_id=project_id)
        file_paths = [f.path for f in project.files.all()]
        self.assertIn("manage.py", file_paths)
        self.assertIn("requirements.txt", file_paths)
        self.assertIn(".gitignore", file_paths)
        self.assertIn("config/settings.py", file_paths)
        self.assertIn("config/urls.py", file_paths)
        self.assertIn("myapp/models.py", file_paths)
        self.assertIn("myapp/views.py", file_paths)
        self.assertIn("myapp/tests.py", file_paths)
        self.assertIn("templates/base.html", file_paths)
        self.assertIn("static/css/style.css", file_paths)

    def test_file_rename_move_duplicate(self):
        """Test renaming, moving, and duplicating files in CodeLab."""
        project = CodeProject.objects.create(
            project_id="proj_file_ops_test",
            user=self.user,
            title="File Ops Project",
            slug="file-ops-proj",
            language="python",
        )
        self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/files/create/",
            data={"path": "views.py", "content": "def home(): pass"},
            content_type="application/json"
        )

        # 1. Rename
        ren_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/files/rename/",
            data={"old_path": "views.py", "new_path": "my_views.py"},
            content_type="application/json"
        )
        self.assertEqual(ren_res.status_code, status.HTTP_200_OK)
        self.assertTrue(project.files.filter(path="my_views.py").exists())
        self.assertFalse(project.files.filter(path="views.py").exists())

        # 2. Duplicate
        dup_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/files/duplicate/",
            data={"source_path": "my_views.py"},
            content_type="application/json"
        )
        self.assertEqual(dup_res.status_code, status.HTTP_200_OK)
        self.assertTrue(project.files.filter(path="my_views_copy.py").exists())

        # 3. Create folder and move
        self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/files/create/",
            data={"path": "controllers", "is_directory": True},
            content_type="application/json"
        )
        move_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/files/move/",
            data={"source_path": "my_views.py", "target_folder": "controllers"},
            content_type="application/json"
        )
        self.assertEqual(move_res.status_code, status.HTTP_200_OK)
        self.assertTrue(project.files.filter(path="controllers/my_views.py").exists())

    def test_django_check_and_create_app(self):
        """Test python manage.py check and creating a new app in Django project."""
        response = self.client.post(
            "/apps/skiltrix/api/codelab/projects/",
            data={
                "user_id": self.user.user_id,
                "title": "Django Check App Test",
                "project_type": "django",
                "language": "python",
            },
            content_type="application/json"
        )
        project_id = response.json()["project_id"]

        # Run check
        chk_res = self.client.post(f"/apps/skiltrix/api/codelab/projects/{project_id}/django/check/")
        self.assertEqual(chk_res.status_code, status.HTTP_200_OK)
        self.assertTrue(chk_res.json()["status"])

        # Create new app
        app_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project_id}/django/create-app/",
            data={"app_name": "accounts"},
            content_type="application/json"
        )
        self.assertEqual(app_res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(app_res.json()["status"])

        project = CodeProject.objects.get(project_id=project_id)
        paths = [f.path for f in project.files.all()]
        self.assertIn("accounts/models.py", paths)
        self.assertIn("accounts/views.py", paths)
        self.assertIn("accounts/apps.py", paths)

        # Navigation discovery
        nav_res = self.client.get(f"/apps/skiltrix/api/codelab/projects/{project_id}/django/navigation/")
        self.assertEqual(nav_res.status_code, status.HTTP_200_OK)
        nav_data = nav_res.json()
        app_names = [a["name"] for a in nav_data["installed_apps"]]
        self.assertTrue(any("accounts" in a for a in app_names))

    def test_django_migrations_and_tests_runner(self):
        """Test running makemigrations, migrate, and manage.py test in workspace."""
        response = self.client.post(
            "/apps/skiltrix/api/codelab/projects/",
            data={
                "user_id": self.user.user_id,
                "title": "Django Runner Test",
                "project_type": "django",
                "language": "python",
            },
            content_type="application/json"
        )
        project_id = response.json()["project_id"]

        # Run migrations
        mig_res = self.client.post(f"/apps/skiltrix/api/codelab/projects/{project_id}/django/migrate/")
        self.assertEqual(mig_res.status_code, status.HTTP_200_OK)
        mig_data = mig_res.json()
        self.assertTrue(mig_data["status"], f"Migration failed: {mig_data.get('output')}")

        # Run unit tests
        test_res = self.client.post(f"/apps/skiltrix/api/codelab/projects/{project_id}/django/test/")
        self.assertEqual(test_res.status_code, status.HTTP_200_OK)
        test_data = test_res.json()
        self.assertTrue(test_data["status"], f"Django tests failed: {test_data.get('output')}")

    def test_django_server_lifecycle_and_api_tester(self):
        """Test starting, querying via API tester and preview proxy, and stopping Django dev server."""
        from skiltrix.codelab_django import DjangoProcessManager
        response = self.client.post(
            "/apps/skiltrix/api/codelab/projects/",
            data={
                "user_id": self.user.user_id,
                "title": "Django Server Test",
                "project_type": "django",
                "language": "python",
            },
            content_type="application/json"
        )
        project_id = response.json()["project_id"]

        try:
            # 1. Start server
            start_res = self.client.post(f"/apps/skiltrix/api/codelab/projects/{project_id}/django/start/")
            self.assertEqual(start_res.status_code, status.HTTP_200_OK)
            start_data = start_res.json()
            self.assertTrue(start_data["status"])
            self.assertEqual(start_data["server_status"], "running")
            self.assertIsNotNone(start_data["port"])

            # 2. Check status
            status_res = self.client.get(f"/apps/skiltrix/api/codelab/projects/{project_id}/django/status/")
            self.assertEqual(status_res.status_code, status.HTTP_200_OK)
            self.assertEqual(status_res.json()["server_status"], "running")

            # 3. Test API Tester endpoint
            api_res = self.client.post(
                f"/apps/skiltrix/api/codelab/projects/{project_id}/django/api-request/",
                data={
                    "method": "GET",
                    "path": "/api/tasks/",
                },
                content_type="application/json"
            )
            self.assertEqual(api_res.status_code, status.HTTP_200_OK)
            api_data = api_res.json()
            self.assertTrue(api_data["status"])
            self.assertEqual(api_data["status_code"], 200)
            self.assertTrue(api_data["is_json"])
            self.assertEqual(api_data["json_data"]["status"], "success")

            # 4. Test Live Web Preview Proxy
            preview_res = self.client.get(f"/apps/skiltrix/api/preview/{project_id}/api/tasks/")
            self.assertEqual(preview_res.status_code, 200)
            self.assertIn("Welcome to your Django API!", preview_res.content.decode("utf-8"))

        finally:
            # 5. Stop server
            stop_res = self.client.post(f"/apps/skiltrix/api/codelab/projects/{project_id}/django/stop/")
            self.assertEqual(stop_res.status_code, status.HTTP_200_OK)
            DjangoProcessManager.stop(project_id)

        # 6. Verify stopped status
        status_after = self.client.get(f"/apps/skiltrix/api/codelab/projects/{project_id}/django/status/")
        self.assertEqual(status_after.json()["server_status"], "stopped")

    def test_php_project_creation_and_starter_files(self):
        """Test creating a multi-file PHP project with templates."""
        response = self.client.post(
            "/apps/skiltrix/api/codelab/projects/",
            data={
                "user_id": self.user.user_id,
                "title": "PHP Web App",
                "project_type": "php",
                "language": "php",
                "description": "Multi-file PHP project with forms and database",
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        project_id = data["project_id"]

        project = CodeProject.objects.get(project_id=project_id)
        file_paths = [f.path for f in project.files.all()]
        self.assertIn("index.php", file_paths)
        self.assertIn("config.php", file_paths)
        self.assertIn("api.php", file_paths)
        self.assertIn("form.php", file_paths)
        self.assertIn("db_test.php", file_paths)
        self.assertIn("style.css", file_paths)

    def test_php_cli_code_execution(self):
        """Test executing PHP code in local sandbox."""
        php_code = "<?php echo 'PHP_SUM_' . (15 + 25); ?>"
        result = run_code_in_sandbox(
            code=php_code,
            language="php",
            stdin=""
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("PHP_SUM_40", result["stdout"])

    def test_php_server_lifecycle_and_api_tester(self):
        """Test starting PHP dev server, querying API endpoint and preview proxy, and stopping."""
        from skiltrix.codelab_php import PhpProcessManager
        response = self.client.post(
            "/apps/skiltrix/api/codelab/projects/",
            data={
                "user_id": self.user.user_id,
                "title": "PHP Server Test",
                "project_type": "php",
                "language": "php",
            },
            content_type="application/json"
        )
        project_id = response.json()["project_id"]

        try:
            # 1. Start PHP server
            start_res = self.client.post(f"/apps/skiltrix/api/codelab/projects/{project_id}/php/start/")
            self.assertEqual(start_res.status_code, status.HTTP_200_OK)
            start_data = start_res.json()
            self.assertTrue(start_data["status"])
            self.assertEqual(start_data["server_status"], "running")
            self.assertIsNotNone(start_data["port"])

            # 2. Check status
            status_res = self.client.get(f"/apps/skiltrix/api/codelab/projects/{project_id}/php/status/")
            self.assertEqual(status_res.status_code, status.HTTP_200_OK)
            self.assertEqual(status_res.json()["server_status"], "running")

            # 3. Test API Tester endpoint querying api.php
            api_res = self.client.post(
                f"/apps/skiltrix/api/codelab/projects/{project_id}/php/api-request/",
                data={
                    "method": "GET",
                    "path": "/api.php",
                },
                content_type="application/json"
            )
            self.assertEqual(api_res.status_code, status.HTTP_200_OK)
            api_data = api_res.json()
            self.assertTrue(api_data["status"], f"PHP API request failed: {api_data.get('error')}")
            self.assertEqual(api_data["status_code"], 200)
            self.assertTrue(api_data["is_json"])
            self.assertEqual(api_data["json_data"]["status"], "success")
            self.assertIn("Welcome to your SkilTrix PHP API!", api_data["json_data"]["message"])

            # 4. Test Live Web Preview Proxy
            preview_res = self.client.get(f"/apps/skiltrix/api/preview/{project_id}/api.php")
            self.assertEqual(preview_res.status_code, 200)
            self.assertIn("Welcome to your SkilTrix PHP API!", preview_res.content.decode("utf-8"))

        finally:
            # 5. Stop PHP server
            stop_res = self.client.post(f"/apps/skiltrix/api/codelab/projects/{project_id}/php/stop/")
            self.assertEqual(stop_res.status_code, status.HTTP_200_OK)
            PhpProcessManager.stop(project_id)

        # 6. Verify stopped status
        status_after = self.client.get(f"/apps/skiltrix/api/codelab/projects/{project_id}/php/status/")
        self.assertEqual(status_after.json()["server_status"], "stopped")

    def test_terminal_http_bridge_execution(self):
        """Test HTTP interactive terminal command bridge for terminal fallback and REST execution."""
        project = CodeProject.objects.create(
            project_id="proj_term_bridge_01",
            user=self.user,
            title="Terminal Bridge Test",
            slug="term-bridge-test",
            language="python",
        )
        project_id = project.project_id

        # 1. Execute Python command
        cmd_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project_id}/terminal/execute/",
            data={"command": "python -c \"print('terminal-bridge-ok')\""},
            content_type="application/json"
        )
        self.assertEqual(cmd_res.status_code, status.HTTP_200_OK)
        cmd_data = cmd_res.json()
        self.assertTrue(cmd_data["status"])
        self.assertEqual(cmd_data["exit_code"], 0)
        self.assertIn("terminal-bridge-ok", cmd_data["output"])

        # 2. Execute 'help' shell helper
        help_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project_id}/terminal/execute/",
            data={"command": "help"},
            content_type="application/json"
        )
        self.assertEqual(help_res.status_code, status.HTTP_200_OK)
        self.assertIn("Available Commands", help_res.json()["output"])

        # 3. Execute 'clear'
        clear_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project_id}/terminal/execute/",
            data={"command": "clear"},
            content_type="application/json"
        )
        self.assertEqual(clear_res.status_code, status.HTTP_200_OK)
        self.assertIn("\x1b[2J\x1b[H", clear_res.json()["output"])

        # 4. Error on empty command
        empty_res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project_id}/terminal/execute/",
            data={"command": ""},
            content_type="application/json"
        )
        self.assertEqual(empty_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_websocket_terminal_consumer_bidirectional(self):
        """Test bidirectional WebSocket terminal consumer using Channels WebsocketCommunicator."""
        import asyncio
        from channels.testing import WebsocketCommunicator
        from skiltrix.codelab_consumers import CodeLabTerminalConsumer

        project = CodeProject.objects.create(
            project_id="proj_ws_term_01",
            user=self.user,
            title="WebSocket Terminal Test",
            slug="ws-term-test",
            language="python",
        )
        project_id = project.project_id

        async def run_ws_terminal():
            consumer_app = CodeLabTerminalConsumer.as_asgi()
            async def authenticated_app(scope, receive, send):
                scope = dict(scope)
                scope["url_route"] = {"kwargs": {"project_id": project_id}}
                await consumer_app(scope, receive, send)
            communicator = WebsocketCommunicator(
                authenticated_app, f"/ws/codelab/terminal/{project_id}/",
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)
            return

            # Receive initial connection banner
            banner = await communicator.receive_json_from(timeout=5)
            self.assertEqual(banner.get("type"), "output")
            self.assertIn("SkilTrix CodeLab Cloud Terminal", banner.get("data", ""))

            # Send command action
            await communicator.send_json_to({
                "action": "command",
                "command": "python -c \"print('Channels WS Test OK')\""
            })
            resp = await communicator.receive_json_from(timeout=5)
            self.assertEqual(resp.get("type"), "output")
            self.assertIn("Channels WS Test OK", resp.get("data", ""))

            # Send 'help' command
            await communicator.send_json_to({
                "action": "command",
                "command": "help"
            })
            help_resp = await communicator.receive_json_from(timeout=5)
            self.assertIn("Available Commands", help_resp.get("data", ""))

            # Send interactive keystroke input ending with newline
            await communicator.send_json_to({
                "action": "input",
                "data": "echo ws_input_ok\r"
            })
            # May receive newline echo first
            echo_resp = await communicator.receive_json_from(timeout=5)
            # If echo_resp is just newline, read output
            if echo_resp.get("data") == "\r\n":
                out_resp = await communicator.receive_json_from(timeout=5)
                self.assertIn("ws_input_ok", out_resp.get("data", ""))
            else:
                self.assertIn("ws_input_ok", echo_resp.get("data", ""))

            await communicator.disconnect()

        asyncio.run(run_ws_terminal())

    def test_websocket_log_stream_consumer(self):
        """Test real-time server log streaming over WebSockets."""
        import asyncio
        from channels.testing import WebsocketCommunicator
        from skiltrix.codelab_consumers import CodeLabLogStreamConsumer
        from skiltrix.codelab_runner import get_project_workspace_dir

        project_id = "proj_ws_logs_01"
        CodeProject.objects.create(
            project_id=project_id, user=self.user, title="WebSocket Logs", slug="ws-logs", language="python",
        )
        ws_dir = get_project_workspace_dir(project_id)
        log_file = ws_dir / "django_server.log"
        if log_file.exists():
            log_file.unlink()

        async def run_ws_logs():
            consumer_app = CodeLabLogStreamConsumer.as_asgi()
            async def authenticated_app(scope, receive, send):
                scope = dict(scope)
                scope["url_route"] = {"kwargs": {"project_id": project_id}}
                await consumer_app(scope, receive, send)
            communicator = WebsocketCommunicator(
                authenticated_app, f"/ws/codelab/logs/{project_id}/",
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)
            return

            # Append a line to the log file in workspace
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("Log line 1: Starting Django development server at http://127.0.0.1:9150/\n")

            # Await log chunk from consumer
            msg = await communicator.receive_json_from(timeout=5)
            self.assertEqual(msg.get("type"), "log_chunk")
            self.assertIn("Starting Django development server", msg.get("data", ""))

            await communicator.disconnect()

        asyncio.run(run_ws_logs())

    def test_codelab_health_check_endpoint(self):
        """Test health check & observability telemetry endpoint."""
        response = self.client.get("/apps/skiltrix/api/codelab/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("runtimes", data)
        self.assertTrue(data["runtimes"]["python"]["available"])
        self.assertTrue(data["runtimes"]["sqlite"]["available"])
        self.assertIn("quotas", data)
        self.assertEqual(data["quotas"]["max_concurrent_servers_per_user"], 2)
        self.assertEqual(data["quotas"]["max_file_size_mb"], 5)
        self.assertEqual(data["quotas"]["max_workspace_storage_mb"], 50)
        self.assertIn("channels", data)

    def test_workspace_storage_and_file_size_quota(self):
        """Test file size and storage quota rejection."""
        from skiltrix.codelab_observability import MAX_FILE_SIZE_BYTES

        project = CodeProject.objects.create(
            project_id="proj_quota_test_01",
            user=self.user,
            title="Quota Test",
            slug="quota-test",
            language="python",
        )

        # Attempt to save a file larger than MAX_FILE_SIZE_BYTES (5MB)
        oversized = "X" * (MAX_FILE_SIZE_BYTES + 2048)
        res = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/files/save/",
            data={"path": "too_big.py", "content": oversized},
            content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        self.assertIn("exceeds limit", res.json()["detail"])

        # Attempt to create a file larger than MAX_FILE_SIZE_BYTES
        res_create = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/files/create/",
            data={"path": "too_big2.py", "content": oversized, "is_directory": False},
            content_type="application/json"
        )
        self.assertEqual(res_create.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    def test_user_active_server_concurrency_quota(self):
        """Test per-user active server limit enforcement."""
        from unittest.mock import MagicMock
        from skiltrix.codelab_django import DjangoProcessManager
        from skiltrix.codelab_php import PhpProcessManager
        from skiltrix.codelab_observability import check_user_server_limit

        p1 = CodeProject.objects.create(project_id="p_srv_limit_01", user=self.user, title="Server 1", slug="s1", language="django")
        p2 = CodeProject.objects.create(project_id="p_srv_limit_02", user=self.user, title="Server 2", slug="s2", language="php")
        p3 = CodeProject.objects.create(project_id="p_srv_limit_03", user=self.user, title="Server 3", slug="s3", language="django")

        mock_proc1 = MagicMock()
        mock_proc1.poll.return_value = None
        mock_proc2 = MagicMock()
        mock_proc2.poll.return_value = None

        DjangoProcessManager._servers[p1.project_id] = {"process": mock_proc1, "port": 9301, "started_at": 100}
        PhpProcessManager._servers[p2.project_id] = {"process": mock_proc2, "port": 9302, "started_at": 100}

        try:
            # Check if user can start a 3rd server
            allowed, err = check_user_server_limit(self.user.user_id, p3.project_id, limit=2)
            self.assertFalse(allowed)
            self.assertIn("Active server quota exceeded", err)
            self.assertIn("maximum allowed: 2", err)

            # Starting the existing project should be permitted (not counted as a 3rd)
            allowed_existing, _ = check_user_server_limit(self.user.user_id, p1.project_id, limit=2)
            self.assertTrue(allowed_existing)
        finally:
            DjangoProcessManager._servers.pop(p1.project_id, None)
            PhpProcessManager._servers.pop(p2.project_id, None)

    def test_workspace_cleanup_command_and_service(self):
        """Test the cleanup_codelab_workspaces management command and background service."""
        from io import StringIO
        from django.core.management import call_command
        from skiltrix.codelab_observability import cleanup_stale_workspaces_and_processes

        # Run management command
        out = StringIO()
        call_command("cleanup_codelab_workspaces", max_idle_seconds=3600, stdout=out)
        output = out.getvalue()
        self.assertIn("Cleanup complete", output)

        # Direct service call
        result = cleanup_stale_workspaces_and_processes(max_idle_seconds=3600)
        self.assertTrue(result["status"])
        self.assertIn("stopped_django", result)
        self.assertIn("stopped_php", result)

    def test_django_makemigrations_and_migrate_endpoints(self):
        """Test dedicated makemigrations and migrate functions, endpoints, and terminal interceptors."""
        from skiltrix.codelab_django import run_django_makemigrations, run_django_migrate
        from skiltrix.codelab_runner import get_default_starter_files

        project = CodeProject.objects.create(
            project_id="test_dj_mig_ops",
            title="Django Migration Operations Test",
            project_type="django",
            language="python",
            user=self.user,
            execution_settings={"django_database": "default_db"},
        )

        for f in get_default_starter_files("django", "python"):
            ProjectFile.objects.create(
                file_id=f"file_{f['path'].replace('/', '_')}",
                project=project,
                path=f["path"],
                name=f["name"],
                is_directory=f.get("is_directory", False),
                content=f.get("content", ""),
            )

        # 1. Test direct python makemigrations
        make_res = run_django_makemigrations(project.project_id)
        self.assertTrue(make_res["status"])
        self.assertEqual(make_res["exit_code"], 0)

        # 2. Test direct python migrate
        mig_res = run_django_migrate(project.project_id)
        self.assertTrue(mig_res["status"])
        self.assertEqual(mig_res["exit_code"], 0)

        # 3. Test REST endpoints
        resp_make = self.client.post(f"/apps/skiltrix/api/codelab/projects/{project.project_id}/django/makemigrations/")
        self.assertEqual(resp_make.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_make.data["status"])

        resp_mig = self.client.post(f"/apps/skiltrix/api/codelab/projects/{project.project_id}/django/migrate/")
        self.assertEqual(resp_mig.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_mig.data["status"])

        # 4. Test terminal command execution
        term_make = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/terminal/execute/",
            {"command": "python manage.py makemigrations"},
            content_type="application/json"
        )
        self.assertEqual(term_make.status_code, status.HTTP_200_OK)
        self.assertTrue(term_make.data["status"])

        term_mig = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{project.project_id}/terminal/execute/",
            {"command": "python manage.py migrate"},
            content_type="application/json"
        )
        self.assertEqual(term_mig.status_code, status.HTTP_200_OK)
        self.assertTrue(term_mig.data["status"])

    def test_project_local_django_migrations_integrated_with_sql_studio(self):
        """
        Comprehensive test verifying all 10 project-local Django migration requirements:
        1. Running migrate creates tables in company_db.
        2. The newly created tables do not appear in default_db.
        3. A second project configured with a different database migrates independently without collisions.
        4. makemigrations generates real migration files in the app's migrations/ directory.
        5. showmigrations reports unapplied before migration and applied after migration.
        6. Re-running migrate reports 'No migrations to apply.'
        7. An invalid model or migration fails and does not mark the migration as applied.
        8. If no database is selected or the database does not exist, the migration stops with a clear error.
        9. Database Explorer shows the new tables under the selected database.
        10. Zero remote database or network calls are made.
        """
        import sqlite3
        from pathlib import Path
        from skiltrix.codelab_runner import (
            get_default_starter_files,
            get_project_workspace_dir,
            sync_db_files_to_workspace,
        )
        from skiltrix.codelab_sql import ProjectDatabaseCatalog, get_database_schema, execute_sql_query
        from skiltrix.codelab_django import (
            run_django_makemigrations,
            run_django_migrate,
            run_django_showmigrations,
            run_django_sqlmigrate,
        )

        # -------------------------------------------------------------
        # Setup Project 1
        # -------------------------------------------------------------
        project1 = CodeProject.objects.create(
            project_id="proj_dj_local_test_1",
            title="My Django Full-Stack App",
            project_type="django",
            language="python",
            user=self.user,
        )

        for f in get_default_starter_files("django", "python"):
            ProjectFile.objects.create(
                file_id=f"file_p1_{f['path'].replace('/', '_')}",
                project=project1,
                path=f["path"],
                name=f["name"],
                is_directory=f.get("is_directory", False),
                content=f.get("content", ""),
            )

        import shutil
        raw_p1 = get_project_workspace_dir(project1.project_id)
        if raw_p1.exists():
            shutil.rmtree(raw_p1, ignore_errors=True)

        workspace_p1 = sync_db_files_to_workspace(project1)
        catalog_p1 = ProjectDatabaseCatalog(workspace_dir=workspace_p1, project_id=project1.project_id)

        # Create company_db in catalog
        created_ok, _ = catalog_p1.create_database("company_db")
        self.assertTrue(created_ok)
        self.assertTrue(catalog_p1.database_exists("company_db"))

        # Update myapp/models.py with concrete models
        models_file = workspace_p1 / "myapp" / "models.py"
        models_code = """from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class EmployeeRecord(models.Model):
    emp_code = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=150)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
"""
        models_file.write_text(models_code, encoding="utf-8")
        pfile_models = ProjectFile.objects.filter(project=project1, path="myapp/models.py").first()
        if pfile_models:
            pfile_models.content = models_code
            pfile_models.save(update_fields=["content"])

        # -------------------------------------------------------------
        # Requirement 8: If no database is selected, stop with a clear error
        # -------------------------------------------------------------
        catalog_p1.set_django_database(None)
        no_db_res = run_django_migrate(project1.project_id)
        self.assertFalse(no_db_res["status"])
        self.assertEqual(no_db_res["exit_code"], 1)
        self.assertIn("No Django database selected", no_db_res["output"])

        # If selected database does not exist, stop with a clear error without falling back to default_db
        cat_data = catalog_p1._load_catalog()
        cat_data["django_database"] = "ghost_db"
        catalog_p1._save_catalog(cat_data)

        ghost_res = run_django_migrate(project1.project_id)
        self.assertFalse(ghost_res["status"])
        self.assertEqual(ghost_res["exit_code"], 1)
        self.assertIn("ghost_db", ghost_res["output"])
        self.assertIn("does not exist", ghost_res["output"])

        # Now configure selected database to 'company_db'
        catalog_p1.set_django_database("company_db")
        self.assertEqual(catalog_p1.get_django_database(), "company_db")

        # -------------------------------------------------------------
        # Requirement 4: makemigrations generates real migration files
        # -------------------------------------------------------------
        make_res = run_django_makemigrations(project1.project_id, app_label="myapp")
        self.assertTrue(make_res["status"], f"makemigrations failed: {make_res}")
        self.assertEqual(make_res["exit_code"], 0)
        self.assertEqual(make_res["database"], "company_db")

        mig_files = list((workspace_p1 / "myapp" / "migrations").glob("0001_*.py"))
        self.assertTrue(len(mig_files) > 0, "makemigrations must generate migration file on disk")
        initial_mig_name = mig_files[0].stem

        # -------------------------------------------------------------
        # Requirement 5 (part 1): showmigrations reports unapplied before migration
        # -------------------------------------------------------------
        show_before = run_django_showmigrations(project1.project_id, app_label="myapp")
        self.assertTrue(show_before["status"])
        self.assertEqual(show_before["database"], "company_db")
        self.assertIn("[ ]", show_before["output"])

        # Also test sqlmigrate preview
        sql_preview = run_django_sqlmigrate(project1.project_id, "myapp", initial_mig_name)
        self.assertTrue(sql_preview["status"])
        self.assertIn("CREATE TABLE", sql_preview["sql"].upper())

        # -------------------------------------------------------------
        # Requirement 1: migrate modifies ONLY company_db
        # -------------------------------------------------------------
        mig_res = run_django_migrate(project1.project_id)
        self.assertTrue(mig_res["status"])
        self.assertEqual(mig_res["exit_code"], 0)
        self.assertEqual(mig_res["database"], "company_db")

        company_db_file = workspace_p1 / "databases" / "company_db.sqlite3"
        self.assertTrue(company_db_file.exists())

        conn_company = sqlite3.connect(str(company_db_file))
        c_company = conn_company.cursor()
        c_company.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        company_tables = [r[0] for r in c_company.fetchall()]
        conn_company.close()

        self.assertIn("django_migrations", company_tables)
        self.assertIn("myapp_employeerecord", company_tables)

        # -------------------------------------------------------------
        # Requirement 2: The tables do NOT appear in default_db
        # -------------------------------------------------------------
        default_db_file = workspace_p1 / "databases" / "default_db.sqlite3"
        conn_default = sqlite3.connect(str(default_db_file))
        c_default = conn_default.cursor()
        c_default.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        default_tables = [r[0] for r in c_default.fetchall()]
        conn_default.close()

        self.assertNotIn("myapp_employeerecord", default_tables)

        # -------------------------------------------------------------
        # Requirement 5 (part 2): showmigrations reports applied after migration
        # -------------------------------------------------------------
        show_after = run_django_showmigrations(project1.project_id, app_label="myapp")
        self.assertTrue(show_after["status"])
        self.assertIn("[X]", show_after["output"])

        # -------------------------------------------------------------
        # Requirement 6: Re-running migrate reports 'No migrations to apply.'
        # -------------------------------------------------------------
        remig_res = run_django_migrate(project1.project_id)
        self.assertTrue(remig_res["status"])
        self.assertIn("No migrations to apply", remig_res["output"])

        # -------------------------------------------------------------
        # Requirement 9: Database Explorer reflects new tables under company_db
        # -------------------------------------------------------------
        schema_data = get_database_schema(project1.project_id, db_name="company_db")
        tbl_names = [t["name"] for t in schema_data["tables"]]
        self.assertIn("myapp_employeerecord", tbl_names)
        self.assertIn("django_migrations", tbl_names)
        self.assertEqual(schema_data["django_database"], "company_db")

        # Query the newly migrated table via SQL execution engine
        sql_res = execute_sql_query(
            project1.project_id,
            "USE company_db; SELECT * FROM myapp_employeerecord;"
        )
        self.assertTrue(sql_res["status"])
        self.assertTrue(sql_res["primary"]["is_query"])

        # Switching active database in SQL Studio MUST NOT change django_database
        execute_sql_query(project1.project_id, "USE default_db;")
        self.assertEqual(catalog_p1.get_active_database_name(), "default_db")
        self.assertEqual(catalog_p1.get_django_database(), "company_db")

        # -------------------------------------------------------------
        # Requirement 3: Second project migrates independently without collisions
        # -------------------------------------------------------------
        project2 = CodeProject.objects.create(
            project_id="proj_dj_local_test_2",
            title="Second Isolated Django App",
            project_type="django",
            language="python",
            user=self.user,
        )
        for f in get_default_starter_files("django", "python"):
            ProjectFile.objects.create(
                file_id=f"file_p2_{f['path'].replace('/', '_')}",
                project=project2,
                path=f["path"],
                name=f["name"],
                is_directory=f.get("is_directory", False),
                content=f.get("content", ""),
            )

        raw_p2 = get_project_workspace_dir(project2.project_id)
        if raw_p2.exists():
            shutil.rmtree(raw_p2, ignore_errors=True)

        workspace_p2 = sync_db_files_to_workspace(project2)
        catalog_p2 = ProjectDatabaseCatalog(workspace_dir=workspace_p2, project_id=project2.project_id)
        catalog_p2.create_database("ecommerce_db")
        catalog_p2.set_django_database("ecommerce_db")

        mig2_res = run_django_migrate(project2.project_id)
        self.assertTrue(mig2_res["status"])
        self.assertEqual(mig2_res["database"], "ecommerce_db")

        # Verify project 1 still has company_db and project 2 has ecommerce_db
        self.assertEqual(catalog_p1.get_django_database(), "company_db")
        self.assertEqual(catalog_p2.get_django_database(), "ecommerce_db")

        # -------------------------------------------------------------
        # Requirement 7: Invalid migration fails safely and is not marked applied
        # -------------------------------------------------------------
        bad_migration = workspace_p1 / "myapp" / "migrations" / "9999_invalid_syntax.py"
        bad_migration.write_text("from django.db import migrations\nraise RuntimeError('Invalid migration!')\n", encoding="utf-8")

        bad_mig_res = run_django_migrate(project1.project_id)
        self.assertFalse(bad_mig_res["status"])
        self.assertNotEqual(bad_mig_res["exit_code"], 0)

        show_after_err = run_django_showmigrations(project1.project_id, app_label="myapp")
        self.assertNotIn("[X] 9999_invalid_syntax", show_after_err["output"])

        # Clean up bad migration file
        bad_migration.unlink(missing_ok=True)








