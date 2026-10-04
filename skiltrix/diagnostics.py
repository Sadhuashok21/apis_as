"""Read-only, workspace-scoped source diagnostics for CodeLab."""

import ast
import builtins
import html.parser
import json
import os
import re
import shutil
import sqlite3
import symtable
import subprocess
import tempfile
import time
from urllib.parse import quote
from pathlib import Path

MAX_SOURCE_BYTES = 1_000_000
MAX_DIAGNOSTICS = 300


def _diag(path, severity, code, message, source, category, line=None, column=None,
          end_line=None, end_column=None):
    item = {
        "file": path, "severity": severity, "code": code, "message": message,
        "source": source, "category": category,
    }
    if line is not None:
        item["startLine"] = int(line)
    if column is not None:
        item["startColumn"] = int(column)
    if end_line is not None:
        item["endLine"] = int(end_line)
    if end_column is not None:
        item["endColumn"] = int(end_column)
    return item


def _python(path, source):
    try:
        compile(source, path, "exec")
    except SyntaxError as exc:
        return [_diag(path, "error", "PY_SYNTAX_ERROR", exc.msg, "Python", "syntax",
                      exc.lineno, exc.offset, exc.end_lineno, exc.end_offset)]
    except (ValueError, TypeError) as exc:
        return [_diag(path, "error", "PY_SOURCE_INVALID", str(exc), "Python", "syntax")]

    # symtable uses Python's own compiler symbol analysis without importing or
    # executing the user's source. It catches undefined globals like Pyflakes.
    try:
        module = symtable.symtable(source, path, "exec")
    except (SyntaxError, ValueError):
        return []  # compile() already reports syntax errors above.
    module_symbols = {item.get_name(): item for item in module.get_symbols()}
    built_in_names = set(dir(builtins)) | {"__name__", "__file__", "__package__", "__doc__", "__builtins__"}
    loaded_name_lines = {}
    for node in ast.walk(ast.parse(source, filename=path)):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            loaded_name_lines.setdefault(node.id, []).append(node.lineno)
    results = []

    def inspect_scope(scope):
        for symbol in scope.get_symbols():
            name = symbol.get_name()
            if (symbol.is_referenced() and symbol.is_global() and name not in built_in_names
                    and not symbol.is_assigned()):
                defined = module_symbols.get(name)
                if defined is None or not (defined.is_assigned() or defined.is_imported()):
                    scope_line = scope.get_lineno()
                    name_line = next((line for line in loaded_name_lines.get(name, ()) if line >= scope_line), None)
                    results.append(_diag(path, "error", "PY_UNDEFINED_NAME",
                                          f"Undefined name '{name}'.", "Python symbol table", "type",
                                          name_line))
        for child in scope.get_children():
            inspect_scope(child)

    inspect_scope(module)
    return results


def _php(path, source):
    from .execution.runtimes.php_runtime import find_php_executable
    executable = find_php_executable()
    if not executable:
        return [_diag(path, "info", "TOOL_UNAVAILABLE", "PHP syntax check unavailable: PHP CLI is not installed.", "PHP -l", "tooling")]
    with tempfile.TemporaryDirectory(prefix="skiltrix-php-check-") as temp_dir:
        file_path = Path(temp_dir) / (Path(path).name or "source.php")
        file_path.write_text(source, encoding="utf-8")
        try:
            result = subprocess.run([executable, "-n", "-l", str(file_path)], capture_output=True,
                                    text=True, timeout=4, cwd=temp_dir)
        except subprocess.TimeoutExpired:
            return [_diag(path, "warning", "PHP_LINT_TIMEOUT", "PHP lint exceeded its 4 second time limit.", "PHP -l", "tooling")]
        except OSError as exc:
            return [_diag(path, "info", "TOOL_UNAVAILABLE", f"PHP CLI was found but could not be started: {exc}", "PHP -l", "tooling")]
    if result.returncode == 0:
        return []
    output = result.stderr or result.stdout
    match = re.search(r"on line (\d+)", output)
    line = int(match.group(1)) if match else None
    message = re.sub(r"\s+in\s+.+?\s+on line\s+\d+", "", output.strip())
    return [_diag(path, "error", "PHP_PARSE_ERROR", message or "PHP parser rejected this file.", "PHP -l", "syntax", line)]


def _typescript(path, source, allow_js=False):
    node = shutil.which("node")
    repo_root = Path(__file__).resolve().parents[2]
    compiler = repo_root / "skiltrix" / "node_modules" / "typescript" / "bin" / "tsc"
    if not node or not compiler.is_file():
        return [_diag(path, "info", "TOOL_UNAVAILABLE", "TypeScript diagnostics unavailable: Node.js and the project TypeScript compiler are required.", "TypeScript", "tooling")]
    with tempfile.TemporaryDirectory(prefix="skiltrix-ts-check-") as temp_dir:
        temp_file = Path(temp_dir) / (Path(path).name or ("source.js" if allow_js else "source.ts"))
        temp_file.write_text(source, encoding="utf-8")
        command = [node, str(compiler), "--noEmit", "--pretty", "false", "--skipLibCheck",
                   "--noResolve", "--target", "ES2022", "--module", "ESNext"]
        if allow_js:
            command += ["--allowJs", "--checkJs"]
        if temp_file.suffix.lower() in (".tsx", ".jsx"):
            command += ["--jsx", "react-jsx"]
        command.append(str(temp_file))
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=6, cwd=temp_dir)
        except subprocess.TimeoutExpired:
            return [_diag(path, "warning", "TS_CHECK_TIMEOUT", "TypeScript diagnostics exceeded the 6 second time limit.", "TypeScript", "tooling")]
        except OSError as exc:
            return [_diag(path, "info", "TOOL_UNAVAILABLE", f"TypeScript compiler could not be started: {exc}", "TypeScript", "tooling")]
    diagnostics = []
    pattern = re.compile(r"\((\d+),(\d+)\): error (TS\d+): (.*)")
    for output_line in result.stdout.splitlines() + result.stderr.splitlines():
        match = pattern.search(output_line)
        if match:
            line, col, code, message = match.groups()
            diagnostics.append(_diag(path, "error", code, message, "TypeScript", "type",
                                     int(line), int(col), int(line), int(col) + 1))
    return diagnostics


def _java(path, source):
    javac = shutil.which("javac")
    if not javac:
        return [_diag(path, "info", "TOOL_UNAVAILABLE", "Java diagnostics unavailable: javac is not installed.", "javac", "tooling")]
    with tempfile.TemporaryDirectory(prefix="skiltrix-java-check-") as temp_dir:
        source_file = Path(temp_dir) / (Path(path).name or "Source.java")
        source_file.write_text(source, encoding="utf-8")
        try:
            result = subprocess.run([javac, "-proc:none", "-XDrawDiagnostics", "-d", temp_dir, str(source_file)],
                                    capture_output=True, text=True, timeout=6, cwd=temp_dir)
        except subprocess.TimeoutExpired:
            return [_diag(path, "warning", "JAVAC_TIMEOUT", "Java diagnostics exceeded the 6 second time limit.", "javac", "tooling")]
        except OSError as exc:
            return [_diag(path, "info", "TOOL_UNAVAILABLE", f"javac was found but could not be started: {exc}", "javac", "tooling")]
    diagnostics = []
    for output_line in result.stderr.splitlines():
        match = re.search(r":(\d+): (?:compiler\.)?err\.(.*)", output_line)
        if match:
            diagnostics.append(_diag(path, "error", "JAVA_COMPILE_ERROR", match.group(2).replace(".", " "),
                                     "javac", "type", int(match.group(1))))
        else:
            match = re.search(r":(\d+): error: (.*)", output_line)
            if match:
                diagnostics.append(_diag(path, "error", "JAVA_COMPILE_ERROR", match.group(2),
                                         "javac", "type", int(match.group(1))))
    return diagnostics


def _native(path, source, language):
    if language == "c":
        candidates, standard = ("gcc", "clang"), "c11"
    else:
        candidates, standard = ("g++", "clang++"), "c++17"
    executable = next((shutil.which(candidate) for candidate in candidates if shutil.which(candidate)), None)
    if not executable:
        return [_diag(path, "info", "TOOL_UNAVAILABLE", f"{language.upper()} diagnostics unavailable: GCC or Clang is not installed.",
                      "Compiler", "tooling")]
    with tempfile.TemporaryDirectory(prefix="skiltrix-native-check-") as temp_dir:
        try:
            result = subprocess.run([executable, "-fsyntax-only", "-fdiagnostics-color=never", "-x", language,
                                     f"-std={standard}", "-"], input=source, capture_output=True,
                                    text=True, timeout=6, cwd=temp_dir)
        except subprocess.TimeoutExpired:
            return [_diag(path, "warning", "COMPILER_TIMEOUT", "Compiler diagnostics exceeded the 6 second time limit.", executable, "tooling")]
        except OSError as exc:
            return [_diag(path, "info", "TOOL_UNAVAILABLE", f"{Path(executable).name} could not be started: {exc}", "Compiler", "tooling")]
    diagnostics = []
    for line in result.stderr.splitlines():
        match = re.search(r"<stdin>:(\d+):(\d+): (fatal )?error: (.*)", line)
        if match:
            row, col, _, message = match.groups()
            diagnostics.append(_diag(path, "error", "NATIVE_COMPILE_ERROR", message, Path(executable).name,
                                     "syntax", int(row), int(col), int(row), int(col) + 1))
            continue
        match = re.search(r"<stdin>:(\d+):(\d+): warning: (.*)", line)
        if match:
            row, col, message = match.groups()
            diagnostics.append(_diag(path, "warning", "NATIVE_WARNING", message, Path(executable).name,
                                     "lint", int(row), int(col), int(row), int(col) + 1))
    return diagnostics


class _MarkupChecker(html.parser.HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    OPTIONAL_END = {"li", "p", "dt", "dd", "option", "tr", "td", "th"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.issues = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append((tag, self.getpos()))

    def handle_startendtag(self, tag, attrs):
        if tag not in self.VOID:
            self.handle_starttag(tag, attrs)
            if self.stack and self.stack[-1][0] == tag:
                self.stack.pop()

    def handle_endtag(self, tag):
        if tag in self.VOID:
            self.issues.append((self.getpos(), f"Void element <{tag}> must not have a closing tag."))
            return
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        elif tag in self.OPTIONAL_END:
            for index in range(len(self.stack) - 1, -1, -1):
                if self.stack[index][0] == tag:
                    self.stack = self.stack[:index]
                    return
        else:
            self.issues.append((self.getpos(), f"Unexpected closing tag </{tag}>."))


def _html(path, source):
    checker = _MarkupChecker()
    try:
        checker.feed(source)
        checker.close()
    except ValueError as exc:
        return [_diag(path, "error", "HTML_PARSE_ERROR", str(exc), "HTMLParser", "syntax")]
    results = [_diag(path, "error", "HTML_UNMATCHED_TAG", msg, "HTMLParser", "syntax", pos[0] + 1, pos[1] + 1)
               for pos, msg in checker.issues]
    for tag, (line, col) in checker.stack:
        if tag in checker.OPTIONAL_END:
            continue
        results.append(_diag(path, "warning", "HTML_UNCLOSED_TAG", f"Unclosed <{tag}> element.",
                             "HTMLParser", "syntax", line + 1, col + 1))
    return results


def _css(path, source):
    node = shutil.which("node")
    postcss = Path(__file__).resolve().parents[2] / "skiltrix" / "node_modules" / "postcss"
    if not node or not postcss.exists():
        return [_diag(path, "info", "TOOL_UNAVAILABLE", "CSS parsing unavailable: Node.js PostCSS is not installed.", "PostCSS", "tooling")]
    script = "const fs=require('fs');const p=require(process.argv[1]);try{p.parse(fs.readFileSync(0,'utf8'));process.stdout.write('{}')}catch(e){process.stdout.write(JSON.stringify({line:e.line,column:e.column,message:e.reason||e.message}))}"
    try:
        result = subprocess.run([node, "-e", script, str(postcss)], input=source, capture_output=True,
                                text=True, timeout=4)
        payload = json.loads(result.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return [_diag(path, "warning", "CSS_CHECK_FAILED", "PostCSS did not return a diagnostic result.", "PostCSS", "tooling")]
    except OSError as exc:
        return [_diag(path, "info", "TOOL_UNAVAILABLE", f"PostCSS parser could not be started: {exc}", "PostCSS", "tooling")]
    if payload.get("message"):
        return [_diag(path, "error", "CSS_PARSE_ERROR", payload["message"], "PostCSS", "syntax",
                      payload.get("line"), payload.get("column"))]
    return []


def _django_template(path, source):
    try:
        from django.template import Engine, TemplateSyntaxError
        Engine().from_string(source)
    except TemplateSyntaxError as exc:
        line = getattr(exc, "token", None)
        line = getattr(line, "lineno", None)
        if line is None:
            match = re.search(r"on line (\d+)", str(exc))
            line = int(match.group(1)) if match else None
        return [_diag(path, "error", "DJANGO_TEMPLATE_ERROR", str(exc), "Django Template Engine", "syntax", line)]
    return []


def _sql(path, source, workspace_dir, database_name):
    from .codelab_sql import split_sql_statements, validate_database_identifier
    statements = split_sql_statements(source)
    if not statements:
        return []
    root = Path(workspace_dir).resolve()
    try:
        db_name = validate_database_identifier(database_name or "default_db")
    except ValueError as exc:
        return [_diag(path, "error", "SQL_DATABASE_UNAVAILABLE", str(exc), "SQLite 3", "configuration")]
    db_path = (root / "databases" / f"{db_name}.sqlite3").resolve()
    if root not in db_path.parents or not db_path.is_file():
        return [_diag(path, "error", "SQL_DATABASE_UNAVAILABLE", f"Database '{db_name}' is not available in this workspace.",
                      "SQLite 3", "configuration")]
    try:
        connection = sqlite3.connect(f"file:{quote(db_path.as_posix(), safe='/:')}?mode=ro", uri=True, timeout=1)
        connection.execute("PRAGMA query_only=ON")
    except sqlite3.Error as exc:
        return [_diag(path, "error", "SQL_DATABASE_UNAVAILABLE", str(exc), "SQLite 3", "configuration")]
    diagnostics = []
    search_from = 0
    custom_validators = (
        re.compile(r"^CREATE\s+(?:DATABASE|SCHEMA)\s+(?:IF\s+NOT\s+EXISTS\s+)?[A-Za-z_][A-Za-z0-9_]*$", re.I),
        re.compile(r"^DROP\s+(?:DATABASE|SCHEMA)\s+(?:IF\s+EXISTS\s+)?[A-Za-z_][A-Za-z0-9_]*$", re.I),
        re.compile(r"^USE\s+[A-Za-z_][A-Za-z0-9_]*$", re.I),
        re.compile(r"^SHOW\s+(?:DATABASES|SCHEMAS|TABLES)$", re.I),
        re.compile(r"^SELECT\s+DATABASE\s*\(\s*\)$", re.I),
    )
    try:
        for statement in statements:
            statement_pos = source.find(statement, search_from)
            if statement_pos < 0:
                statement_pos = 0
            search_from = statement_pos + len(statement)
            if re.match(r"^(?:CREATE\s+(?:DATABASE|SCHEMA)|DROP\s+(?:DATABASE|SCHEMA)|USE\b|SHOW\b|SELECT\s+DATABASE\s*\()", statement.strip(), re.I):
                if not any(validator.fullmatch(statement.strip()) for validator in custom_validators):
                    diagnostics.append(_diag(path, "error", "SKILTRIX_SQL_SYNTAX", "Invalid SkilTrix SQLite dialect command.", "SkilTrix SQL dispatcher", "syntax"))
                continue
            try:
                connection.execute("EXPLAIN " + statement)
            except sqlite3.Error as exc:
                message = str(exc)
                near = re.search(r"near [\"'](.+?)[\"']", message)
                token = near.group(1) if near else None
                if not token:
                    missing = re.search(r"(?:no such (?:column|table)|ambiguous column name):\s*([A-Za-z_][A-Za-z0-9_]*)", message, re.I)
                    token = missing.group(1) if missing else None
                offset = statement.find(token, 0) if token else -1
                if offset >= 0:
                    absolute = statement_pos + offset
                    line = source.count("\n", 0, absolute) + 1
                    column = absolute - source.rfind("\n", 0, absolute)
                else:
                    line = column = None
                diagnostics.append(_diag(path, "error", "SQLITE_PREPARE_ERROR", message, "SQLite 3", "syntax", line, column))
    finally:
        connection.close()
    return diagnostics


def diagnose_source(path, source, workspace_dir=None, database_name=None, django_template=False, project_language=None):
    """Run a non-executing parser/compiler check for one authorized source file."""
    source = source or ""
    if len(source.encode("utf-8", errors="replace")) > MAX_SOURCE_BYTES:
        return [_diag(path, "error", "SOURCE_TOO_LARGE", "Live diagnostics are limited to 1 MB per file.", "SkilTrix", "configuration")]
    name = Path(path).name.lower()
    extension = Path(path).suffix.lower()
    normalized_path = "/" + path.replace("\\", "/").lower()
    if extension in (".html", ".htm") and (django_template or "/templates/" in normalized_path):
        return _django_template(path, source)
    if extension == ".py":
        return _python(path, source)
    if extension == ".php":
        return _php(path, source)
    if extension in (".ts", ".tsx"):
        return _typescript(path, source)
    if extension in (".js", ".jsx", ".mjs", ".cjs"):
        return _typescript(path, source, allow_js=True)
    if extension == ".java":
        return _java(path, source)
    if extension == ".c":
        return _native(path, source, "c")
    if extension == ".h":
        return _native(path, source, "c++" if (project_language or "").lower() in {"cpp", "c++", "cxx"} else "c")
    if extension in (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"):
        return _native(path, source, "c++")
    if extension in (".abap", ".prog") or name.endswith(".prog.abap"):
        from .abap_engine import check_abap_syntax
        result = check_abap_syntax(source)
        diagnostics = []
        for item in result.get("diagnostics", []):
            code = item.get("code")
            is_unsupported = (
                item.get("severity") == "info"
                or code in ("ABAP_UNSUPPORTED_STATEMENT", "ABAP_SIMULATOR_LIMITATION")
                or "not valid ABAP syntax" in item.get("message", "")
                or "recognized" in item.get("message", "").lower()
            )
            diag_code = (
                "ABAP_UNSUPPORTED_STATEMENT"
                if is_unsupported
                else (code or "ABAP_SYNTAX_ERROR")
            )
            diag_category = "simulator_compatibility" if is_unsupported else "syntax"
            diagnostics.append(_diag(
                path,
                "info" if item.get("severity") == "info" else item.get("severity", "error"),
                diag_code,
                item.get("message", "ABAP parser diagnostic"),
                "SkilTrix ABAP parser",
                diag_category,
                item.get("line"),
                item.get("column"),
                item.get("endLine"),
                item.get("endColumn")
            ))
        return diagnostics
    if extension == ".sql":
        return _sql(path, source, workspace_dir, database_name) if workspace_dir else []
    if extension in (".css", ".scss", ".less"):
        if extension != ".css":
            return [_diag(path, "info", "TOOL_UNAVAILABLE", f"{extension[1:].upper()} diagnostics are unavailable; only CSS is parsed with PostCSS.", "SkilTrix", "tooling")]
        return _css(path, source)
    if extension in (".html", ".htm"):
        return _html(path, source)
    if extension == ".json":
        try:
            json.loads(source)
        except json.JSONDecodeError as exc:
            return [_diag(path, "error", "JSON_PARSE_ERROR", exc.msg, "Python JSON parser", "syntax",
                          exc.lineno, exc.colno)]
    if extension in {".go", ".rs", ".cs", ".kt", ".kts", ".rb", ".swift", ".scala", ".pl", ".r"}:
        return [_diag(path, "info", "DIAGNOSTIC_PROVIDER_UNAVAILABLE",
                      f"No configured parser/compiler provider is available for {extension[1:]} files.",
                      "SkilTrix diagnostics", "tooling")]
    return []


def diagnose_project(project, workspace_dir, database_name=None, source_overrides=None):
    """Check tracked project source without running it; bounded to 300 markers."""
    diagnostics = []
    files = list(project.files.filter(is_directory=False).order_by("path")[:101])
    truncated = len(files) > 100
    files = files[:100]
    started_at = time.monotonic()
    for pfile in files:
        if time.monotonic() - started_at > 10:
            diagnostics.append(_diag("", "info", "PROJECT_DIAGNOSTIC_TIME_LIMIT",
                                     "Project diagnostics stopped after the 10 second time budget.",
                                     "SkilTrix diagnostics", "tooling"))
            break
        diagnostics.extend(diagnose_source(pfile.path, (source_overrides or {}).get(pfile.path, pfile.content), workspace_dir, database_name,
                                           django_template=getattr(project, "project_type", "") == "django",
                                           project_language=getattr(project, "language", None)))
        if len(diagnostics) >= MAX_DIAGNOSTICS:
            return diagnostics[:MAX_DIAGNOSTICS]
    if truncated:
        diagnostics.append(_diag("", "info", "PROJECT_DIAGNOSTIC_FILE_LIMIT",
                                 "Project diagnostics are limited to the first 100 tracked files per check.",
                                 "SkilTrix diagnostics", "tooling"))
    if getattr(project, "project_type", "") == "django":
        diagnostics.extend(_django_static_checks(files))
        diagnostics.append(_diag("", "info", "DJANGO_SYSTEM_CHECK_NOT_RUN",
                                 "Live checks parse Django source and templates without importing the project or connecting to its database. Run Django's system check in the project's isolated environment for framework and dependency validation.",
                                 "SkilTrix static Django checks", "configuration"))
    return diagnostics[:MAX_DIAGNOSTICS]


def _django_static_checks(files):
    """Inspect local Django imports/URLs using AST only; never import project code."""
    file_map = {item.path.replace("\\", "/"): item.content for item in files}
    top_level = set()
    for path in file_map:
        parts = path.split("/")
        if len(parts) > 1 and (f"{parts[0]}/__init__.py" in file_map or any(p.startswith(parts[0] + "/") for p in file_map)):
            top_level.add(parts[0])
        elif len(parts) == 1 and parts[0].endswith(".py"):
            top_level.add(parts[0][:-3])

    diagnostics = []
    for path, content in file_map.items():
        if not path.endswith(".py"):
            continue
        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError:
            continue  # The source provider already returned its exact syntax marker.
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            assignment_name = next((target.id for target in targets if isinstance(target, ast.Name)), None)
            if assignment_name not in {"INSTALLED_APPS", "MIDDLEWARE"}:
                continue
            try:
                values = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            if not isinstance(values, (list, tuple)) or not all(isinstance(value, str) for value in values):
                continue
            seen = set()
            for value in values:
                if value in seen:
                    diagnostics.append(_diag(path, "warning", f"DJANGO_DUPLICATE_{assignment_name}",
                                             f"'{value}' appears more than once in {assignment_name}.",
                                             "SkilTrix Django static checks", "configuration",
                                             node.lineno, node.col_offset + 1,
                                             getattr(node, "end_lineno", node.lineno),
                                             getattr(node, "end_col_offset", node.col_offset + 1) + 1))
                seen.add(value)
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "include" and node.args:
                if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    module = node.args[0].value
            if not module:
                continue
            parts = module.split(".")
            if parts[0] not in top_level:
                continue
            candidate = "/".join(parts)
            if f"{candidate}.py" not in file_map and f"{candidate}/__init__.py" not in file_map:
                diagnostics.append(_diag(path, "error", "DJANGO_LOCAL_MODULE_MISSING",
                                         f"Local module '{module}' has no matching project file.",
                                         "SkilTrix Django static checks", "import", node.lineno,
                                         node.col_offset + 1, getattr(node, "end_lineno", node.lineno),
                                         getattr(node, "end_col_offset", node.col_offset + 1) + 1))
    migration_files = [path for path in file_map if re.match(r".+/migrations/[^/]+\.py$", path) and not path.endswith("/migrations/__init__.py")]
    for migration_path in migration_files:
        package_init = migration_path.split("/migrations/", 1)[0] + "/migrations/__init__.py"
        if package_init not in file_map:
            diagnostics.append(_diag(package_init, "warning", "DJANGO_MIGRATIONS_PACKAGE_MISSING",
                                     "The migrations package has no __init__.py file.",
                                     "SkilTrix Django static checks", "configuration"))
    return diagnostics
