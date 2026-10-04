import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .diagnostics import diagnose_source


class SourceDiagnosticProviderTests(unittest.TestCase):
    def test_python_undefined_global_name_is_reported_without_execution(self):
        result = diagnose_source("app.py", "def show_total():\n    return total_missing\n")
        self.assertEqual(result[0]["code"], "PY_UNDEFINED_NAME")
        self.assertEqual(result[0]["startLine"], 2)
        self.assertEqual(diagnose_source("app.py", "total = 3\ndef show_total():\n    return total\n"), [])

    def test_python_parser_returns_exact_syntax_location_and_clears_on_valid_source(self):
        broken = diagnose_source("app.py", "def add(a, b)\n    return a + b\n")
        self.assertEqual(broken[0]["code"], "PY_SYNTAX_ERROR")
        self.assertEqual((broken[0]["startLine"], broken[0]["startColumn"]), (1, 14))
        self.assertEqual(diagnose_source("app.py", "def add(a, b):\n    return a + b\n"), [])

    def test_php_lint_reports_parse_line_or_tool_unavailable(self):
        result = diagnose_source("index.php", "<?php\nif (true) {\n echo 'x'\n}\n")
        if shutil.which("php"):
            if result[0]["code"] == "TOOL_UNAVAILABLE":
                self.assertEqual(result[0]["severity"], "info")
            else:
                self.assertEqual(result[0]["code"], "PHP_PARSE_ERROR")
                self.assertIsNotNone(result[0].get("startLine"))
        else:
            self.assertEqual(result[0]["code"], "TOOL_UNAVAILABLE")

    def test_php_unavailable_is_explicit(self):
        with patch("skiltrix.execution.runtimes.php_runtime.find_php_executable", return_value=None):
            result = diagnose_source("index.php", "<?php echo 1;")
        self.assertEqual(result[0]["severity"], "info")
        self.assertIn("not installed", result[0]["message"])

    def test_abap_unsupported_statement_is_not_called_a_syntax_error(self):
        result = diagnose_source("main.prog.abap", "REPORT ztest.\nFOO BAR.\n")
        if result:
            self.assertNotEqual(result[0]["code"], "ABAP_SYNTAX_ERROR")
            self.assertEqual(result[0]["category"], "simulator_compatibility")

    def test_sql_uses_project_sqlite_schema_without_executing_statement(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            database_dir = workspace / "databases"
            database_dir.mkdir()
            db_path = database_dir / "default_db.sqlite3"
            connection = sqlite3.connect(db_path)
            connection.execute("CREATE TABLE people (id INTEGER)")
            connection.commit()
            connection.close()
            diagnostics = diagnose_source("query.sql", "SELECT missing FROM people", workspace)
            self.assertEqual(diagnostics[0]["code"], "SQLITE_PREPARE_ERROR")
            self.assertIn("no such column", diagnostics[0]["message"].lower())
            self.assertEqual(diagnose_source("query.sql", "INSERT INTO people VALUES (1)", workspace), [])
            connection = sqlite3.connect(db_path)
            self.assertEqual(connection.execute("SELECT count(*) FROM people").fetchone()[0], 0)
            connection.close()

    def test_sql_syntax_uses_actual_sqlite_parser(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            database_dir = workspace / "databases"
            database_dir.mkdir()
            sqlite3.connect(database_dir / "default_db.sqlite3").close()
            result = diagnose_source("query.sql", "SELEC * FROM people", workspace)
            self.assertEqual(result[0]["code"], "SQLITE_PREPARE_ERROR")
            self.assertEqual((result[0]["startLine"], result[0]["startColumn"]), (1, 1))
            self.assertEqual(diagnose_source("query.sql", "SELECT 1", workspace, "../escape")[0]["code"], "SQL_DATABASE_UNAVAILABLE")

    def test_typescript_compiler_reports_type_errors_or_tool_unavailable(self):
        result = diagnose_source("src.ts", 'const total: number = "wrong";')
        if (Path(__file__).resolve().parents[2] / "skiltrix" / "node_modules" / "typescript" / "bin" / "tsc").exists():
            self.assertTrue(any(item["code"].startswith("TS") for item in result))
        else:
            self.assertEqual(result[0]["code"], "TOOL_UNAVAILABLE")

    def test_java_parser_reports_type_errors_or_tool_unavailable(self):
        result = diagnose_source("Main.java", "class Main { int count = \"bad\"; }")
        if shutil.which("javac"):
            self.assertTrue(any(item["code"] == "JAVA_COMPILE_ERROR" for item in result))
        else:
            self.assertEqual(result[0]["code"], "TOOL_UNAVAILABLE")

    def test_native_compiler_unavailability_is_clear(self):
        with patch("skiltrix.diagnostics.shutil.which", return_value=None):
            result = diagnose_source("main.c", "int main(void) { return 0; }")
        self.assertEqual(result[0]["code"], "TOOL_UNAVAILABLE")

    def test_html_parser_reports_unclosed_element_without_flagging_valid_markup(self):
        self.assertEqual(diagnose_source("index.html", "<main><p>ok</p></main>"), [])
        result = diagnose_source("index.html", "<main><p>broken</main>")
        self.assertTrue(result)
        self.assertTrue(any(item["severity"] in ("error", "warning") for item in result))

    def test_django_template_engine_parses_template_syntax(self):
        invalid = diagnose_source("templates/page.html", "{% if user %}hello")
        self.assertEqual(invalid[0]["code"], "DJANGO_TEMPLATE_ERROR")
        self.assertEqual(diagnose_source("templates/page.html", "{% if user %}hello{% endif %}"), [])

    def test_diagnostic_compilation_does_not_execute_python_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sentinel = Path(temp_dir) / "must-not-exist"
            code = f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('ran')\n"
            self.assertEqual(diagnose_source("main.py", code), [])
            self.assertFalse(sentinel.exists())

    def test_missing_compiler_tools_return_tooling_message(self):
        with patch("skiltrix.diagnostics.shutil.which", return_value=None):
            result = diagnose_source("Main.java", "class Main {}")
        self.assertEqual(result[0]["category"], "tooling")
        self.assertIn("javac is not installed", result[0]["message"])

    def test_python_project_files_are_checked_without_django_setup_execution(self):
        class File:
            def __init__(self, path, content):
                self.path, self.content = path, content

        class Files:
            def filter(self, **kwargs):
                return self
            def order_by(self, *_args):
                return self
            def __getitem__(self, key):
                return [File("manage.py", "def broken()\n pass")][key]

        class Project:
            files = Files()

        from .diagnostics import diagnose_project
        results = diagnose_project(Project(), Path(tempfile.gettempdir()))
        self.assertEqual(results[0]["file"], "manage.py")
        self.assertEqual(results[0]["code"], "PY_SYNTAX_ERROR")
        updated = diagnose_project(Project(), Path(tempfile.gettempdir()), source_overrides={"manage.py": "def fixed(): pass"})
        self.assertEqual(updated, [])

    def test_django_static_check_reports_missing_local_url_module(self):
        from .diagnostics import _django_static_checks

        class File:
            def __init__(self, path, content):
                self.path, self.content = path, content

        result = _django_static_checks([
            File("urls.py", "from django.urls import include\nurlpatterns = [include('blog.urls')]\n"),
            File("blog/__init__.py", ""),
        ])
        self.assertEqual(result[0]["code"], "DJANGO_LOCAL_MODULE_MISSING")
        self.assertEqual(result[0]["startLine"], 2)

    def test_css_postcss_parser_reports_syntax_error_when_available(self):
        css_parser = Path(__file__).resolve().parents[2] / "skiltrix" / "node_modules" / "postcss"
        result = diagnose_source("site.css", "body { color: red;")
        if css_parser.exists() and shutil.which("node"):
            self.assertEqual(result[0]["code"], "CSS_PARSE_ERROR")
            self.assertEqual(result[0]["startLine"], 1)
        else:
            self.assertEqual(result[0]["code"], "TOOL_UNAVAILABLE")

