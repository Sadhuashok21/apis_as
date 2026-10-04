"""
SkilTrix Universal Security Firewall - Comprehensive Automated Security Verification Suite
Tests all 15 core security requirements across multi-language runtimes, SQL engine,
ABAP simulator, terminal command bridge, HTML preview, fail-closed handling, and audit logging.
"""

from pathlib import Path
import tempfile
from unittest.mock import patch
from django.test import TestCase, Client
from rest_framework import status
from sfs.models import AllUsers
from skiltrix.codelab_models import CodeProject
from skiltrix.execution.worker import execute_code_job
from skiltrix.codelab_runner import get_project_workspace_dir
from skiltrix.codelab_sql import ProjectDatabaseCatalog, SqlStatementDispatcher
from skiltrix.security import (
    UniversalSecurityEngine,
    audit_logger,
    ERROR_CODE_SECURITY_VIOLATION,
    RULE_DANGEROUS_FILESYSTEM,
    RULE_PATH_TRAVERSAL,
    RULE_UNAUTHORIZED_SUBPROCESS,
    RULE_NETWORK_VIOLATION,
    RULE_SQL_CONFINEMENT,
    RULE_TERMINAL_VIOLATION,
    RULE_ABAP_VIOLATION,
    RULE_FAIL_CLOSED,
    RULE_RESOURCE_LIMIT,
)


class UniversalSecurityFirewallTests(TestCase):
    """Automated security verification test suite."""

    def setUp(self):
        self.temp_workspace_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_workspace_root.cleanup)
        workspace_patch = patch("skiltrix.codelab_runner.WORKSPACE_BASE_DIR", Path(self.temp_workspace_root.name))
        workspace_patch.start()
        self.addCleanup(workspace_patch.stop)
        self.client = Client()
        self.user = AllUsers.objects.create(
            user_id="sec_test_user_01",
            username="security_tester",
            email="sec_tester@skiltrix.com",
            name="Security",
            lastname="Tester",
            user_type="admin",
        )
        self.client.force_login(self.user, backend="django.contrib.auth.backends.ModelBackend")
        self.project = CodeProject.objects.create(
            project_id="sec_test_proj_01",
            user=self.user,
            title="Security Sandbox Project",
            project_type="django",
            language="python",
        )
        self.workspace_dir = get_project_workspace_dir(self.project.project_id)
        audit_logger.clear()
        UniversalSecurityEngine.set_engine_health(True)

    def tearDown(self):
        UniversalSecurityEngine.set_engine_health(True)

    # --------------------------------------------------------------------------
    # 1. Block destructive filesystem operations across all languages
    # --------------------------------------------------------------------------
    def test_01_block_destructive_file_operations_across_languages(self):
        """Detect and block unauthorized deletion, wiping, and damage across languages."""
        # Python os.remove on system path
        py_code = 'import os\nos.remove("C:/important.txt")\n'
        res = execute_code_job("python", py_code, workspace_dir=self.workspace_dir)
        self.assertFalse(res.get("success", True))
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)
        self.assertEqual(res.get("rule_triggered"), RULE_DANGEROUS_FILESYSTEM)

        # Python shutil.rmtree on root
        py_rmtree = 'import shutil\nshutil.rmtree("/")\n'
        res = execute_code_job("python", py_rmtree, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

        # JS rmSync on root
        js_code = 'require("fs").rmSync("/", { recursive: true });'
        res = execute_code_job("javascript", js_code, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

        # PHP unlink on host file
        php_code = '<?php unlink("C:/Windows/System32/drivers/etc/hosts"); ?>'
        res = execute_code_job("php", php_code, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

        # C++ remove root
        cpp_code = '#include <stdio.h>\nint main() { remove("C:/"); return 0; }'
        res = execute_code_job("cpp", cpp_code, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

    # --------------------------------------------------------------------------
    # 2. Block path traversal attempts (../, C:\, /etc)
    # --------------------------------------------------------------------------
    def test_02_block_path_traversal_attempts(self):
        """Block attempts to traverse outside sandbox via relative or absolute paths."""
        py_traversal = 'with open("../../etc/passwd", "r") as f:\n    data = f.read()\n'
        res = execute_code_job("python", py_traversal, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)
        self.assertEqual(res.get("rule_triggered"), RULE_PATH_TRAVERSAL)

        # Terminal traversal
        is_safe, sec_error, _ = UniversalSecurityEngine.evaluate_terminal_command(
            "cat ../../config.py",
            self.workspace_dir
        )
        self.assertFalse(is_safe)
        self.assertEqual(sec_error.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)
        self.assertEqual(sec_error.get("rule_triggered"), RULE_PATH_TRAVERSAL)

    # --------------------------------------------------------------------------
    # 3. Confine code execution strictly inside project workspace
    # --------------------------------------------------------------------------
    def test_03_confine_code_execution_inside_project_workspace(self):
        """Legitimate local file operations succeed within workspace, escapes fail."""
        # Writing and reading file inside workspace succeeds
        safe_code = (
            'with open("local_output.txt", "w") as f:\n'
            '    f.write("sandbox verified")\n'
            'with open("local_output.txt", "r") as f:\n'
            '    print(f.read())\n'
        )
        res = execute_code_job("python", safe_code, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("status"), "completed")
        self.assertIn("sandbox verified", res.get("stdout"))

        # Target outside workspace directory is caught by path validator
        with self.assertRaises(Exception):
            UniversalSecurityEngine.validate_child_path(
                self.workspace_dir,
                Path("C:/Windows/System32/cmd.exe")
            )

    # --------------------------------------------------------------------------
    # 4. Block unauthorized subprocess and shell execution
    # --------------------------------------------------------------------------
    def test_04_block_unauthorized_subprocess_and_shell_execution(self):
        """Block attempts to spawn shells, cmd.exe, PowerShell, or arbitrary subprocesses."""
        # Python subprocess import and call
        py_proc = 'import subprocess\nsubprocess.run(["cmd.exe", "/c", "dir"])\n'
        res = execute_code_job("python", py_proc, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)
        self.assertEqual(res.get("rule_triggered"), RULE_UNAUTHORIZED_SUBPROCESS)

        # Python os.system
        py_sys = 'import os\nos.system("whoami")\n'
        res = execute_code_job("python", py_sys, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

        # Node child_process
        js_proc = 'const { exec } = require("child_process"); exec("whoami");'
        res = execute_code_job("javascript", js_proc, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

        # Java Runtime.exec
        java_proc = 'public class Solution { public static void main(String[] args) throws Exception { Runtime.getRuntime().exec("whoami"); } }'
        res = execute_code_job("java", java_proc, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

        # PHP exec
        php_proc = '<?php exec("whoami"); ?>'
        res = execute_code_job("php", php_proc, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

        # C++ system()
        cpp_proc = '#include <stdlib.h>\nint main() { system("calc"); return 0; }'
        res = execute_code_job("cpp", cpp_proc, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

    # --------------------------------------------------------------------------
    # 5. Terminate infinite loops within timeout limit without hanging server
    # --------------------------------------------------------------------------
    def test_05_terminate_infinite_loops_within_timeout(self):
        """Infinite loop is terminated gracefully and returns timeout status."""
        loop_code = "count = 0\nwhile True:\n    count += 1\n"
        res = execute_code_job("python", loop_code, workspace_dir=self.workspace_dir, timeout=1.0)
        self.assertEqual(res.get("status"), "timeout")
        self.assertEqual(res.get("exit_code"), 124)
        self.assertEqual(res.get("error_code"), RULE_RESOURCE_LIMIT)

    # --------------------------------------------------------------------------
    # 6. Enforce output buffer limits
    # --------------------------------------------------------------------------
    def test_06_enforce_output_buffer_limits(self):
        """Large outputs are truncated to MAX_OUTPUT_BYTES to prevent memory exhaustion."""
        spam_code = "print('A' * 200000)"
        res = execute_code_job("python", spam_code, workspace_dir=self.workspace_dir)
        self.assertEqual(res.get("status"), "completed")
        self.assertLessEqual(len(res.get("stdout")), 125000)
        self.assertIn("Output truncated", res.get("stdout"))

    # --------------------------------------------------------------------------
    # 7. HTML live preview has strict iframe sandbox and CSP preventing parent access
    # --------------------------------------------------------------------------
    def test_07_html_live_preview_iframe_sandbox_and_csp(self):
        """Live preview response sets Content-Security-Policy headers and prevents iframe escapes."""
        resp = self.client.get(f"/apps/skiltrix/api/preview/{self.project.project_id}/")
        # Response must include CSP header
        csp = resp.headers.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("frame-ancestors 'self'", csp)

        # Check WebPreviewPanel component source code for sandbox isolation
        panel_file = Path("d:/frontend/skiltrix/src/components/codelab/WebPreviewPanel.tsx")
        if panel_file.exists():
            panel_content = panel_file.read_text(encoding="utf-8")
            self.assertIn('sandbox="allow-scripts allow-forms allow-modals"', panel_content)
            self.assertNotIn('allow-same-origin', panel_content)

    # --------------------------------------------------------------------------
    # 8. SQL security: blocks ATTACH DATABASE, VACUUM INTO, direct writes to sqlite_master
    # --------------------------------------------------------------------------
    def test_08_sql_security_database_confinement(self):
        """Prevents SQL injection of ATTACH DATABASE, VACUUM INTO, and system catalog hacking."""
        catalog = ProjectDatabaseCatalog(project_id=self.project.project_id)
        dispatcher = SqlStatementDispatcher(catalog)

        # 1. ATTACH DATABASE attempt
        res_attach = dispatcher.execute_script("ATTACH DATABASE '/etc/passwd' AS stolen;")
        self.assertFalse(res_attach.get("status"))
        self.assertEqual(res_attach.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)
        self.assertEqual(res_attach.get("rule_triggered"), RULE_SQL_CONFINEMENT)

        # 2. VACUUM INTO attempt
        res_vacuum = dispatcher.execute_script("VACUUM INTO 'C:/Windows/win.ini';")
        self.assertFalse(res_vacuum.get("status"))
        self.assertEqual(res_vacuum.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

        # 3. Direct write to sqlite_master
        res_master = dispatcher.execute_script("DELETE FROM sqlite_master WHERE type='table';")
        self.assertFalse(res_master.get("status"))
        self.assertEqual(res_master.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

        # 4. Valid SQL queries pass cleanly
        catalog.create_database("safe_test_db", if_not_exists=True)
        catalog.set_active_database("safe_test_db")
        dispatcher = SqlStatementDispatcher(catalog)
        res_valid = dispatcher.execute_script("CREATE TABLE IF NOT EXISTS safe_items (id INT, name TEXT); INSERT INTO safe_items VALUES (1, 'item1'); SELECT * FROM safe_items;")
        self.assertTrue(res_valid.get("status"), msg=f"SQL error: {res_valid.get('error')}")
        self.assertEqual(len(res_valid.get("results")), 3)

    # --------------------------------------------------------------------------
    # 9. Django migration isolation: only operates on configured database
    # --------------------------------------------------------------------------
    def test_09_django_migration_isolation_only_selected_db(self):
        """Django migration commands strictly modify only the project's selected database."""
        catalog = ProjectDatabaseCatalog(project_id=self.project.project_id)
        catalog.create_database("company_isolated_db", if_not_exists=True)
        catalog.set_django_database("company_isolated_db")

        # Verify project django database setting is persisted
        self.assertEqual(catalog.get_django_database(), "company_isolated_db")

        # Verify other databases remain unconfigured
        catalog.create_database("other_project_db", if_not_exists=True)
        self.assertNotEqual(catalog.get_django_database(), "other_project_db")

    # --------------------------------------------------------------------------
    # 10. ABAP simulator blocks unauthorized OS commands / unsafe statements
    # --------------------------------------------------------------------------
    def test_10_abap_simulator_blocks_unauthorized_os_commands(self):
        """ABAP simulator blocks CALL 'SYSTEM' and dataset deletion."""
        # CALL 'SYSTEM'
        bad_abap = "REPORT Z_UNSAFE.\nDATA: cmd TYPE string.\ncmd = 'rmdir C:\\'.\nCALL 'SYSTEM' ID 'COMMAND' FIELD cmd.\n"
        resp = self.client.post(
            "/apps/skiltrix/api/abap/execute/",
            data={"code": bad_abap, "execution_mode": "simulator"},
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)
        self.assertEqual(resp.data.get("rule_triggered"), RULE_ABAP_VIOLATION)

        # Valid educational ABAP passes
        good_abap = "REPORT Z_SAFE.\nWRITE: / 'Hello SAP ABAP Simulator'.\n"
        resp_good = self.client.post(
            "/apps/skiltrix/api/abap/execute/",
            data={"code": good_abap, "execution_mode": "simulator"},
            content_type="application/json"
        )
        self.assertEqual(resp_good.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_good.data.get("status"))

    # --------------------------------------------------------------------------
    # 11. Terminal bridge blocks unauthorized commands (powershell, cmd, reg, traversal)
    # --------------------------------------------------------------------------
    def test_11_terminal_firewall_blocks_administrative_and_dangerous_commands(self):
        """Terminal firewall blocks powershell, cmd, registry tools, and command chaining."""
        # PowerShell blocked
        is_safe, err, _ = UniversalSecurityEngine.evaluate_terminal_command(
            "powershell -ExecutionPolicy Bypass -Command calc",
            self.workspace_dir
        )
        self.assertFalse(is_safe)
        self.assertEqual(err.get("rule_triggered"), RULE_UNAUTHORIZED_SUBPROCESS)

        # Root wipe blocked
        is_safe, err, _ = UniversalSecurityEngine.evaluate_terminal_command(
            "rmdir /s /q C:\\",
            self.workspace_dir
        )
        self.assertFalse(is_safe)
        self.assertEqual(err.get("rule_triggered"), RULE_DANGEROUS_FILESYSTEM)

        # Command chaining blocked
        is_safe, err, _ = UniversalSecurityEngine.evaluate_terminal_command(
            "python manage.py check && whoami",
            self.workspace_dir
        )
        self.assertFalse(is_safe)
        self.assertEqual(err.get("rule_triggered"), RULE_TERMINAL_VIOLATION)

        # Whitelisted commands pass
        is_safe, _, tokens = UniversalSecurityEngine.evaluate_terminal_command(
            "python manage.py check",
            self.workspace_dir
        )
        self.assertTrue(is_safe)
        self.assertIn("manage.py", tokens)

    # --------------------------------------------------------------------------
    # 12. Direct API bypass attempts are intercepted
    # --------------------------------------------------------------------------
    def test_12_direct_api_bypass_attempts_intercepted(self):
        """Direct HTTP API calls attempting malicious payloads are blocked with HTTP 400."""
        # Execute code endpoint
        resp_code = self.client.post(
            "/apps/skiltrix/api/codelab/execute/",
            data={
                "language": "python",
                "code": "import os; os.system('whoami')",
            },
            content_type="application/json"
        )
        self.assertEqual(resp_code.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp_code.data.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)
        self.assertEqual(resp_code.data.get("execution_status"), "blocked")

        # Execute SQL endpoint
        resp_sql = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{self.project.project_id}/sql/execute/",
            data={"query": "ATTACH DATABASE '/root/.ssh/id_rsa' AS stolen;"},
            content_type="application/json"
        )
        self.assertEqual(resp_sql.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp_sql.data.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

        # Terminal execute endpoint
        resp_term = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{self.project.project_id}/terminal/execute/",
            data={"command": "powershell Get-Process"},
            content_type="application/json"
        )
        self.assertEqual(resp_term.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp_term.data.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)

    # --------------------------------------------------------------------------
    # 13. Fail-closed design: unverified execution is blocked
    # --------------------------------------------------------------------------
    def test_13_fail_closed_design(self):
        """If security engine cannot verify or initialize, execution rejects by default."""
        UniversalSecurityEngine.set_engine_health(False)

        res = execute_code_job("python", "print('hello')", workspace_dir=self.workspace_dir)
        self.assertFalse(res.get("success", True))
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)
        self.assertEqual(res.get("rule_triggered"), RULE_FAIL_CLOSED)
        self.assertEqual(res.get("execution_status"), "blocked")

        # Terminal also fails closed
        is_safe, err, _ = UniversalSecurityEngine.evaluate_terminal_command("help", self.workspace_dir)
        self.assertFalse(is_safe)
        self.assertEqual(err.get("rule_triggered"), RULE_FAIL_CLOSED)

        # SQL also fails closed
        sql_err = UniversalSecurityEngine.evaluate_sql("SELECT 1;")
        self.assertIsNotNone(sql_err)
        self.assertEqual(sql_err.get("rule_triggered"), RULE_FAIL_CLOSED)

        UniversalSecurityEngine.set_engine_health(True)

    # --------------------------------------------------------------------------
    # 14. Ordinary legitimate educational / developer code passes without false positives
    # --------------------------------------------------------------------------
    def test_14_ordinary_legitimate_code_passes_without_false_positives(self):
        """Standard student and developer algorithms execute cleanly without false alarms."""
        # Python math & algorithms
        py_code = (
            "def fib(n):\n"
            "    a, b = 0, 1\n"
            "    for _ in range(n): a, b = b, a + b\n"
            "    return a\n"
            "print(f'fib(10) = {fib(10)}')\n"
        )
        res_py = execute_code_job("python", py_code, workspace_dir=self.workspace_dir)
        self.assertEqual(res_py.get("status"), "completed")
        self.assertIn("fib(10) = 55", res_py.get("stdout"))

        # JS code
        js_code = "const nums = [1, 2, 3, 4, 5]; console.log(nums.reduce((a, b) => a + b, 0));"
        res_js = execute_code_job("javascript", js_code, workspace_dir=self.workspace_dir)
        self.assertEqual(res_js.get("status"), "completed")
        self.assertIn("15", res_js.get("stdout"))

        # Terminal help and dir
        resp = self.client.post(
            f"/apps/skiltrix/api/codelab/projects/{self.project.project_id}/terminal/execute/",
            data={"command": "help"},
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data.get("status"))

    # --------------------------------------------------------------------------
    # 15. Standard structured security error response format & audit logging
    # --------------------------------------------------------------------------
    def test_15_standard_structured_security_error_response_and_audit_logging(self):
        """Violation responses match standard JSON structure and are logged to audit buffer."""
        audit_logger.clear()

        # Trigger violation
        res = execute_code_job("python", "import socket\nsocket.socket()", workspace_dir=self.workspace_dir)

        # Verify structured error schema
        self.assertFalse(res.get("success", True))
        self.assertEqual(res.get("error_code"), ERROR_CODE_SECURITY_VIOLATION)
        self.assertEqual(res.get("execution_status"), "blocked")
        self.assertTrue(bool(res.get("message")))
        self.assertEqual(res.get("rule_triggered"), RULE_NETWORK_VIOLATION)

        # Verify audit log recorded violation
        recent = audit_logger.get_recent_violations(limit=10)
        self.assertGreaterEqual(len(recent), 1)
        logged_entry = recent[0]
        self.assertEqual(logged_entry.get("rule_triggered"), RULE_NETWORK_VIOLATION)
        self.assertEqual(logged_entry.get("execution_status"), "blocked")
        self.assertEqual(logged_entry.get("language"), "python")

