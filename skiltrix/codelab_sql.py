import os
import io
import re
import csv
import json
import time
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from django.conf import settings
from .codelab_runner import get_project_workspace_dir


SEED_TEMPLATES = {
    "company_hr": {
        "title": "Company HR & Payroll",
        "description": "Departments, employees, job titles, and salaries database.",
        "sql": """
CREATE TABLE departments (
    dept_id INTEGER PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL
);

CREATE TABLE employees (
    emp_id INTEGER PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    dept_id INTEGER,
    salary DECIMAL(10, 2) NOT NULL,
    hire_date DATE NOT NULL,
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);

CREATE TABLE projects (
    project_id INTEGER PRIMARY KEY,
    project_name VARCHAR(100) NOT NULL,
    dept_id INTEGER,
    budget DECIMAL(12, 2),
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);

INSERT INTO departments VALUES
(1, 'Engineering', 'San Francisco'),
(2, 'Marketing', 'New York'),
(3, 'Finance', 'Chicago'),
(4, 'Human Resources', 'Austin');

INSERT INTO employees VALUES
(101, 'Alex', 'Rivera', 'alex.rivera@skiltrix.com', 1, 125000.00, '2021-03-15'),
(102, 'Maya', 'Patel', 'maya.patel@skiltrix.com', 1, 142000.00, '2020-07-01'),
(103, 'Liam', 'Chen', 'liam.chen@skiltrix.com', 2, 92000.00, '2022-01-10'),
(104, 'Sophia', 'Kim', 'sophia.kim@skiltrix.com', 3, 118000.00, '2019-11-20'),
(105, 'Marcus', 'Johnson', 'marcus.j@skiltrix.com', 1, 98000.00, '2023-04-12'),
(106, 'Elena', 'Rostova', 'elena.r@skiltrix.com', 2, 88000.00, '2022-08-15'),
(107, 'David', 'O''Connor', 'david.oc@skiltrix.com', 4, 85000.00, '2021-09-01'),
(108, 'Amina', 'Diallo', 'amina.d@skiltrix.com', 1, 135000.00, '2020-12-05');

INSERT INTO projects VALUES
(201, 'Cloud Migration', 1, 250000.00),
(202, 'Brand Relaunch', 2, 80000.00),
(203, 'Annual Audit', 3, 45000.00),
(204, 'CodeLab Platform', 1, 500000.00);
"""
    },
    "ecommerce": {
        "title": "E-Commerce & Orders",
        "description": "Online store with customers, product catalog, orders, and order items.",
        "sql": """
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category_id INTEGER,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    country VARCHAR(50)
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    order_date DATE NOT NULL,
    total_amount DECIMAL(10, 2),
    status VARCHAR(20) DEFAULT 'completed',
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

INSERT INTO categories VALUES
(1, 'Electronics'),
(2, 'Books'),
(3, 'Apparel');

INSERT INTO products VALUES
(1, 'Mechanical Keyboard', 1, 129.99, 45),
(2, 'UltraWide 4K Monitor', 1, 499.99, 18),
(3, 'Algorithms & Data Structures Book', 2, 59.50, 120),
(4, 'Noise-Cancelling Headphones', 1, 249.00, 30),
(5, 'Developer Hoodie', 3, 65.00, 80);

INSERT INTO customers VALUES
(1, 'Sarah Miller', 'sarah@example.com', 'USA'),
(2, 'Rajesh Sharma', 'rajesh@example.com', 'India'),
(3, 'Claire Dubois', 'claire@example.com', 'France'),
(4, 'Kenji Sato', 'kenji@example.com', 'Japan');

INSERT INTO orders VALUES
(1001, 1, '2023-10-01', 629.98, 'completed'),
(1002, 2, '2023-10-03', 129.99, 'completed'),
(1003, 3, '2023-10-05', 308.50, 'completed'),
(1004, 1, '2023-10-08', 59.50, 'shipped');
"""
    },
    "university": {
        "title": "University Academic Portal",
        "description": "Courses, students, professors, and grade enrollments.",
        "sql": """
CREATE TABLE departments (
    dept_code VARCHAR(10) PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL
);

CREATE TABLE professors (
    prof_id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    dept_code VARCHAR(10),
    FOREIGN KEY (dept_code) REFERENCES departments(dept_code)
);

CREATE TABLE courses (
    course_id VARCHAR(20) PRIMARY KEY,
    course_name VARCHAR(150) NOT NULL,
    credits INTEGER NOT NULL,
    prof_id INTEGER,
    FOREIGN KEY (prof_id) REFERENCES professors(prof_id)
);

CREATE TABLE students (
    student_id INTEGER PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    major VARCHAR(50),
    enrollment_year INTEGER
);

CREATE TABLE enrollments (
    enrollment_id INTEGER PRIMARY KEY,
    student_id INTEGER,
    course_id VARCHAR(20),
    grade VARCHAR(2),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

INSERT INTO departments VALUES
('CS', 'Computer Science'),
('MATH', 'Mathematics'),
('PHYS', 'Physics');

INSERT INTO professors VALUES
(1, 'Dr. Alan Turing', 'CS'),
(2, 'Dr. Ada Lovelace', 'CS'),
(3, 'Dr. Carl Gauss', 'MATH');

INSERT INTO courses VALUES
('CS101', 'Introduction to Computer Science', 4, 1),
('CS201', 'Data Structures & Algorithms', 4, 2),
('MATH101', 'Calculus I', 3, 3);

INSERT INTO students VALUES
(202301, 'Jordan Smith', 'Computer Science', 2023),
(202302, 'Emily White', 'Computer Science', 2023),
(202303, 'Daniel Lee', 'Mathematics', 2022);

INSERT INTO enrollments VALUES
(1, 202301, 'CS101', 'A'),
(2, 202301, 'MATH101', 'B+'),
(3, 202302, 'CS101', 'A'),
(4, 202302, 'CS201', 'A-'),
(5, 202303, 'MATH101', 'A');
"""
    }
}


DEFAULT_DATABASE_NAME = "default_db"
IDENTIFIER_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def validate_database_identifier(name: str) -> str:
    """
    Validates that a database name conforms to standard SQL identifier rules.
    Strips backticks or quotes if enclosed.
    """
    cleaned = name.strip()
    if (cleaned.startswith('`') and cleaned.endswith('`')) or \
       (cleaned.startswith('"') and cleaned.endswith('"')) or \
       (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()

    if not cleaned:
        raise ValueError("Database identifier cannot be empty.")
    if len(cleaned) > 64:
        raise ValueError(f"Database identifier '{cleaned}' is too long (maximum 64 characters).")
    if not IDENTIFIER_REGEX.match(cleaned):
        raise ValueError(
            f"Invalid database identifier '{cleaned}'. Database names must start with a letter "
            f"or underscore and contain only alphanumeric characters and underscores."
        )
    if cleaned.lower() in ("sqlite_master", "sqlite_sequence", "sqlite_temp_master", "catalog"):
        raise ValueError(f"Database name '{cleaned}' is reserved for internal system use.")

    return cleaned


def split_sql_statements(sql: str) -> List[str]:
    """
    Splits multi-statement SQL script into individual statements by semicolon,
    respecting single quotes, double quotes, backticks, line comments (--), and block comments (/* */).
    """
    statements = []
    current: List[str] = []
    in_single_quote = False
    in_double_quote = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False

    i = 0
    n = len(sql)
    while i < n:
        char = sql[i]
        next_char = sql[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if char == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_single_quote:
            current.append(char)
            if char == "'":
                if next_char == "'":
                    current.append(next_char)
                    i += 2
                    continue
                else:
                    in_single_quote = False
            i += 1
            continue

        if in_double_quote:
            current.append(char)
            if char == '"':
                if next_char == '"':
                    current.append(next_char)
                    i += 2
                    continue
                else:
                    in_double_quote = False
            i += 1
            continue

        if in_backtick:
            current.append(char)
            if char == '`':
                in_backtick = False
            i += 1
            continue

        # Check comment starts
        if char == "-" and next_char == "-":
            in_line_comment = True
            i += 2
            continue

        if char == "/" and next_char == "*":
            in_block_comment = True
            i += 2
            continue

        # Check quote starts
        if char == "'":
            in_single_quote = True
            current.append(char)
            i += 1
            continue

        if char == '"':
            in_double_quote = True
            current.append(char)
            i += 1
            continue

        if char == '`':
            in_backtick = True
            current.append(char)
            i += 1
            continue

        if char == ";":
            stmt_text = "".join(current).strip()
            if stmt_text:
                statements.append(stmt_text)
            current = []
            i += 1
            continue

        current.append(char)
        i += 1

    remaining = "".join(current).strip()
    if remaining:
        statements.append(remaining)

    return statements


class ProjectDatabaseCatalog:
    """
    Manages persistent SQLite databases for a CodeLab project.
    Stores each database as an isolated SQLite file under <workspace>/databases/
    and tracks active context and metadata in catalog.json.
    """

    def __init__(self, project_id: Optional[str] = None, workspace_dir: Optional[Path] = None):
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        elif project_id:
            self.workspace_dir = get_project_workspace_dir(project_id)
        else:
            raise ValueError("Either project_id or workspace_dir must be provided.")

        self.project_id = project_id
        self.databases_dir = self.workspace_dir / "databases"
        self.databases_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_path = self.databases_dir / "catalog.json"
        self._ensure_catalog()

    def _load_catalog(self) -> Dict[str, Any]:
        if not self.catalog_path.exists():
            return {"active_database": DEFAULT_DATABASE_NAME, "databases": {}}
        try:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"active_database": DEFAULT_DATABASE_NAME, "databases": {}}

    def _save_catalog(self, data: Dict[str, Any]) -> None:
        temp_path = self.catalog_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        shutil.move(temp_path, self.catalog_path)

    def _provision_seed_database(self, db_path: Path, template_key: str = "company_hr") -> None:
        template = SEED_TEMPLATES.get(template_key, SEED_TEMPLATES["company_hr"])
        if db_path.exists():
            db_path.unlink()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.executescript(template["sql"])
        conn.commit()
        conn.close()

    def _ensure_catalog(self) -> None:
        """Initializes default database and catalog if not present."""
        legacy_db = self.workspace_dir / "database.sqlite3"
        default_db_file = self.databases_dir / f"{DEFAULT_DATABASE_NAME}.sqlite3"

        catalog_data = self._load_catalog()
        databases = catalog_data.get("databases", {})

        # If legacy database exists but default_db.sqlite3 does not, migrate it
        if legacy_db.exists() and not default_db_file.exists():
            try:
                shutil.copy2(legacy_db, default_db_file)
            except Exception:
                pass

        # If no default database file exists anywhere, seed it
        if not default_db_file.exists():
            self._provision_seed_database(default_db_file, "company_hr")

        if DEFAULT_DATABASE_NAME not in databases:
            databases[DEFAULT_DATABASE_NAME] = {
                "name": DEFAULT_DATABASE_NAME,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_default": True,
            }

        active_db = catalog_data.get("active_database", DEFAULT_DATABASE_NAME)
        if active_db not in databases:
            active_db = DEFAULT_DATABASE_NAME

        catalog_data["active_database"] = active_db
        catalog_data["databases"] = databases
        self._save_catalog(catalog_data)

        # Mirror active db to legacy database.sqlite3 path so backwards compatibility is maintained
        self._sync_legacy_mirror(active_db)

    def _sync_legacy_mirror(self, active_db_name: str) -> None:
        """Keeps workspace_dir / 'database.sqlite3' mirrored to current active database."""
        try:
            active_file = self.databases_dir / f"{active_db_name}.sqlite3"
            legacy_file = self.workspace_dir / "database.sqlite3"
            if active_file.exists():
                shutil.copy2(active_file, legacy_file)
        except Exception:
            pass

    def list_databases(self) -> List[str]:
        data = self._load_catalog()
        return sorted(list(data.get("databases", {}).keys()))

    def get_active_database_name(self) -> str:
        data = self._load_catalog()
        active = data.get("active_database", DEFAULT_DATABASE_NAME)
        if active in data.get("databases", {}):
            return active
        dbs = self.list_databases()
        return dbs[0] if dbs else DEFAULT_DATABASE_NAME

    def set_active_database(self, name: str) -> None:
        validated = validate_database_identifier(name)
        if not self.database_exists(validated):
            raise ValueError(f"Unknown database '{validated}'")
        data = self._load_catalog()
        data["active_database"] = validated
        self._save_catalog(data)
        self._sync_legacy_mirror(validated)

    def get_django_database(self) -> Optional[str]:
        """
        Returns the project-configured database for Django migrations & runtime.
        If no database is explicitly configured, returns None.
        """
        data = self._load_catalog()
        django_db = data.get("django_database")
        if django_db:
            return django_db

        if self.project_id:
            try:
                from .codelab_models import CodeProject
                proj = CodeProject.objects.filter(project_id=self.project_id).first()
                if proj and isinstance(proj.execution_settings, dict):
                    proj_db = proj.execution_settings.get("django_database")
                    if proj_db:
                        return proj_db
            except Exception:
                pass
        return None

    def set_django_database(self, name: Optional[str]) -> None:
        """
        Sets the project-configured database for Django migrations & runtime.
        Persists into catalog.json and CodeProject.execution_settings.
        """
        data = self._load_catalog()
        validated = None
        if name:
            validated = validate_database_identifier(name)
            if not self.database_exists(validated):
                raise ValueError(f"Can't select database '{validated}'; database doesn't exist")
            data["django_database"] = validated
        else:
            data["django_database"] = None

        self._save_catalog(data)

        if self.project_id:
            try:
                from .codelab_models import CodeProject
                proj = CodeProject.objects.filter(project_id=self.project_id).first()
                if proj:
                    if not isinstance(proj.execution_settings, dict):
                        proj.execution_settings = {}
                    if validated:
                        proj.execution_settings["django_database"] = validated
                    else:
                        proj.execution_settings.pop("django_database", None)
                    proj.save(update_fields=["execution_settings"])
            except Exception:
                pass

    def database_exists(self, name: str) -> bool:
        data = self._load_catalog()
        db_file = self.databases_dir / f"{name}.sqlite3"
        return name in data.get("databases", {}) and db_file.exists()

    def get_database_path(self, name: Optional[str] = None) -> Path:
        target = name or self.get_active_database_name()
        validated = validate_database_identifier(target)
        return self.databases_dir / f"{validated}.sqlite3"

    def create_database(self, name: str, if_not_exists: bool = False) -> Tuple[bool, str]:
        validated = validate_database_identifier(name)
        if self.database_exists(validated):
            if if_not_exists:
                return False, f"Query OK, 0 rows affected (Database '{validated}' already exists)."
            raise ValueError(f"Can't create database '{validated}'; database exists")

        db_file = self.databases_dir / f"{validated}.sqlite3"
        # Create empty SQLite database file
        conn = sqlite3.connect(str(db_file))
        conn.execute("PRAGMA user_version = 1;")
        conn.commit()
        conn.close()

        data = self._load_catalog()
        data["databases"][validated] = {
            "name": validated,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_default": False,
        }
        self._save_catalog(data)
        self._sync_django_workspace(validated, action="create")
        return True, f"Query OK, 1 row affected (Database '{validated}' created)."

    def drop_database(self, name: str, if_exists: bool = False) -> Tuple[bool, str]:
        validated = validate_database_identifier(name)
        if not self.database_exists(validated):
            if if_exists:
                return False, f"Query OK, 0 rows affected (Database '{validated}' does not exist)."
            raise ValueError(f"Can't drop database '{validated}'; database doesn't exist")

        db_file = self.databases_dir / f"{validated}.sqlite3"
        if db_file.exists():
            try:
                db_file.unlink()
            except Exception as e:
                raise RuntimeError(f"Failed to delete database file: {str(e)}")

        data = self._load_catalog()
        data["databases"].pop(validated, None)

        # If dropped database was the configured Django database, reset it to None
        if data.get("django_database") == validated:
            data["django_database"] = None
            if self.project_id:
                try:
                    from .codelab_models import CodeProject
                    proj = CodeProject.objects.filter(project_id=self.project_id).first()
                    if proj and isinstance(proj.execution_settings, dict):
                        proj.execution_settings.pop("django_database", None)
                        proj.save(update_fields=["execution_settings"])
                except Exception:
                    pass

        # If dropped database was the active one, fallback to default_db or first remaining
        if data.get("active_database") == validated:
            remaining = sorted(list(data["databases"].keys()))
            if remaining:
                data["active_database"] = remaining[0]
            else:
                # Re-provision default_db if all databases were deleted
                default_file = self.databases_dir / f"{DEFAULT_DATABASE_NAME}.sqlite3"
                self._provision_seed_database(default_file, "company_hr")
                data["databases"][DEFAULT_DATABASE_NAME] = {
                    "name": DEFAULT_DATABASE_NAME,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "is_default": True,
                }
                data["active_database"] = DEFAULT_DATABASE_NAME

        self._save_catalog(data)
        self._sync_legacy_mirror(data["active_database"])
        self._sync_django_workspace(validated, action="delete")
        return True, f"Query OK, 0 rows affected (Database '{validated}' dropped)."

    def _sync_django_workspace(self, db_name: str, action: str = "create", schema_json: str = "") -> None:
        """Optionally syncs catalog entry with Django's DatabaseWorkspace model."""
        if not self.project_id:
            return
        try:
            from .codelab_models import CodeProject, DatabaseWorkspace
            from sfs.models import AllUsers

            proj = CodeProject.objects.filter(project_id=self.project_id).first()
            if not proj:
                return
            user = proj.user or AllUsers.objects.first()
            db_id = f"db_{self.project_id}_{db_name}"

            if action == "create":
                DatabaseWorkspace.objects.update_or_create(
                    db_id=db_id,
                    defaults={
                        "user": user,
                        "project": proj,
                        "db_type": "sqlite",
                        "db_name": db_name,
                        "is_active": True,
                        "schema_snapshot": schema_json,
                    }
                )
            elif action == "delete":
                DatabaseWorkspace.objects.filter(db_id=db_id).delete()
        except Exception:
            pass

    def get_database_tables_meta(self, db_name: str) -> List[Dict[str, Any]]:
        """Inspects all tables and column metadata for a single database."""
        db_path = self.get_database_path(db_name)
        if not db_path.exists():
            return []

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        table_names = [row[0] for row in cursor.fetchall()]

        tables_meta = []
        for t_name in table_names:
            cursor.execute(f"PRAGMA table_info('{t_name}');")
            col_rows = cursor.fetchall()
            columns = []
            for c in col_rows:
                columns.append({
                    "cid": c[0],
                    "name": c[1],
                    "type": c[2] or "TEXT",
                    "notnull": bool(c[3]),
                    "default_value": c[4],
                    "pk": bool(c[5]),
                })

            try:
                cursor.execute(f"SELECT COUNT(*) FROM '{t_name}';")
                row_count = cursor.fetchone()[0]
            except Exception:
                row_count = 0

            cursor.execute(f"PRAGMA foreign_key_list('{t_name}');")
            fk_rows = cursor.fetchall()
            fks = []
            for fk in fk_rows:
                fks.append({
                    "id": fk[0],
                    "seq": fk[1],
                    "table": fk[2],
                    "from": fk[3],
                    "to": fk[4],
                })

            tables_meta.append({
                "name": t_name,
                "row_count": row_count,
                "columns": columns,
                "foreign_keys": fks,
            })

        conn.close()
        return tables_meta

    def get_catalog_summary(self) -> List[Dict[str, Any]]:
        """Returns structured metadata for all databases in the catalog."""
        catalog_data = self._load_catalog()
        active_db = self.get_active_database_name()
        django_db = self.get_django_database()
        result = []

        for name, meta in sorted(catalog_data.get("databases", {}).items()):
            tables = self.get_database_tables_meta(name)
            result.append({
                "name": name,
                "created_at": meta.get("created_at", ""),
                "is_active": (name == active_db),
                "is_default": meta.get("is_default", False),
                "is_django": (name == django_db),
                "tables_count": len(tables),
                "tables": tables,
            })

        return result


class SqlStatementDispatcher:
    """
    Routes SQL statements to database management handlers (CREATE DATABASE,
    DROP DATABASE, SHOW DATABASES, USE, SELECT DATABASE(), SHOW TABLES)
    or directly executes standard queries/DDL/DML on the active SQLite database.
    """

    RE_CREATE_DB = re.compile(
        r'^\s*CREATE\s+(?:DATABASE|SCHEMA)(?:\s+(IF\s+NOT\s+EXISTS))?\s+(.+?)\s*$',
        re.IGNORECASE
    )
    RE_CREATE_DB_PREFIX = re.compile(r'^\s*CREATE\s+(?:DATABASE|SCHEMA)\b', re.IGNORECASE)

    RE_DROP_DB = re.compile(
        r'^\s*DROP\s+(?:DATABASE|SCHEMA)(?:\s+(IF\s+EXISTS))?\s+(.+?)\s*$',
        re.IGNORECASE
    )
    RE_DROP_DB_PREFIX = re.compile(r'^\s*DROP\s+(?:DATABASE|SCHEMA)\b', re.IGNORECASE)

    RE_SHOW_DBS = re.compile(r'^\s*SHOW\s+(?:DATABASES|SCHEMAS)\s*$', re.IGNORECASE)
    RE_USE_DB = re.compile(r'^\s*USE\s+(.+?)\s*$', re.IGNORECASE)
    RE_USE_DB_PREFIX = re.compile(r'^\s*USE\b', re.IGNORECASE)

    RE_SELECT_DB = re.compile(
        r'^\s*SELECT\s+(?:DATABASE|CURRENT_DATABASE)\s*\(\s*\)(?:\s+AS\s+[`\'"]?([a-zA-Z0-9_]+)[`\'"]?)?\s*$',
        re.IGNORECASE
    )

    RE_SHOW_TABLES = re.compile(
        r'^\s*SHOW\s+TABLES(?:\s+(?:FROM|IN)\s+([`\'"]?[a-zA-Z0-9_]+[`\'"]?))?\s*$',
        re.IGNORECASE
    )

    def __init__(self, catalog: ProjectDatabaseCatalog, active_db: Optional[str] = None):
        self.catalog = catalog
        if active_db and self.catalog.database_exists(active_db):
            self.active_db = active_db
        else:
            self.active_db = self.catalog.get_active_database_name()

    def execute_script(self, script: str, timeout_seconds: float = 5.0) -> Dict[str, Any]:
        start_time = time.perf_counter()
        statements = split_sql_statements(script)

        if not statements:
            return {
                "status": False,
                "error": "No SQL statements found to execute.",
                "duration_ms": 0.0,
                "active_database": self.active_db,
                "databases": self.catalog.get_catalog_summary(),
            }

        results_list = []

        try:
            from .security import SqlSecurityGuard, SecurityPolicyViolation
            for stmt in statements:
                SqlSecurityGuard.validate_statement(stmt)

            for stmt in statements:
                # 1. CREATE DATABASE
                if self.RE_CREATE_DB_PREFIX.match(stmt):
                    match = self.RE_CREATE_DB.match(stmt)
                    if not match:
                        raise ValueError(
                            "You have an error in your SQL syntax; check the manual near "
                            f"'{stmt[:50]}' for valid CREATE DATABASE syntax."
                        )
                    if_not_exists = bool(match.group(1))
                    raw_name = match.group(2)
                    db_name = validate_database_identifier(raw_name)
                    created, msg = self.catalog.create_database(db_name, if_not_exists=if_not_exists)
                    results_list.append({
                        "is_query": False,
                        "affected_rows": 1 if created else 0,
                        "message": msg,
                        "statement": stmt,
                    })
                    continue

                # 2. DROP DATABASE
                if self.RE_DROP_DB_PREFIX.match(stmt):
                    match = self.RE_DROP_DB.match(stmt)
                    if not match:
                        raise ValueError(
                            "You have an error in your SQL syntax; check the manual near "
                            f"'{stmt[:50]}' for valid DROP DATABASE syntax."
                        )
                    if_exists = bool(match.group(1))
                    raw_name = match.group(2)
                    db_name = validate_database_identifier(raw_name)
                    dropped, msg = self.catalog.drop_database(db_name, if_exists=if_exists)
                    # Update active_db if dropped
                    self.active_db = self.catalog.get_active_database_name()
                    results_list.append({
                        "is_query": False,
                        "affected_rows": 0,
                        "message": msg,
                        "statement": stmt,
                    })
                    continue

                # 3. SHOW DATABASES / SHOW SCHEMAS
                if self.RE_SHOW_DBS.match(stmt):
                    dbs = self.catalog.list_databases()
                    results_list.append({
                        "is_query": True,
                        "columns": ["Database"],
                        "rows": [[d] for d in dbs],
                        "row_count": len(dbs),
                        "statement": stmt,
                    })
                    continue

                # 4. USE <name>
                if self.RE_USE_DB_PREFIX.match(stmt):
                    match = self.RE_USE_DB.match(stmt)
                    if not match:
                        raise ValueError(
                            "You have an error in your SQL syntax; check the manual near "
                            f"'{stmt[:50]}' for valid USE syntax."
                        )
                    raw_name = match.group(1)
                    db_name = validate_database_identifier(raw_name)
                    if not self.catalog.database_exists(db_name):
                        raise ValueError(f"Unknown database '{db_name}'")
                    self.active_db = db_name
                    self.catalog.set_active_database(db_name)
                    results_list.append({
                        "is_query": False,
                        "affected_rows": 0,
                        "message": f"Database changed to '{db_name}'.",
                        "statement": stmt,
                    })
                    continue

                # 5. SELECT DATABASE()
                if self.RE_SELECT_DB.match(stmt):
                    match = self.RE_SELECT_DB.match(stmt)
                    col_name = match.group(1) or "DATABASE()"
                    results_list.append({
                        "is_query": True,
                        "columns": [col_name],
                        "rows": [[self.active_db]],
                        "row_count": 1,
                        "statement": stmt,
                    })
                    continue

                # 6. SHOW TABLES
                if self.RE_SHOW_TABLES.match(stmt):
                    match = self.RE_SHOW_TABLES.match(stmt)
                    target_db = validate_database_identifier(match.group(1)) if match.group(1) else self.active_db
                    if not self.catalog.database_exists(target_db):
                        raise ValueError(f"Unknown database '{target_db}'")

                    tables_meta = self.catalog.get_database_tables_meta(target_db)
                    table_names = [t["name"] for t in tables_meta]
                    results_list.append({
                        "is_query": True,
                        "columns": [f"Tables_in_{target_db}"],
                        "rows": [[t] for t in table_names],
                        "row_count": len(table_names),
                        "statement": stmt,
                    })
                    continue

                # 7. Standard SQL query / DML / DDL against active database
                db_path = self.catalog.get_database_path(self.active_db)
                conn = sqlite3.connect(str(db_path), timeout=timeout_seconds)
                cursor = conn.cursor()

                try:
                    cursor.execute(stmt)
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        results_list.append({
                            "is_query": True,
                            "columns": columns,
                            "rows": rows,
                            "row_count": len(rows),
                            "statement": stmt,
                        })
                    else:
                        affected = cursor.rowcount
                        conn.commit()
                        results_list.append({
                            "is_query": False,
                            "affected_rows": affected if affected >= 0 else 0,
                            "message": f"Query OK, {affected if affected >= 0 else 0} row(s) affected.",
                            "statement": stmt,
                        })
                finally:
                    conn.close()

            # Ensure active db mirror is up to date
            self.catalog._sync_legacy_mirror(self.active_db)

            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            primary_result = results_list[-1] if results_list else {}

            return {
                "status": True,
                "active_database": self.active_db,
                "databases": self.catalog.get_catalog_summary(),
                "duration_ms": duration_ms,
                "results": results_list,
                "primary": primary_result,
            }

        except SecurityPolicyViolation as spv:
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return {
                "success": False,
                "status": False,
                "error_code": "SECURITY_POLICY_VIOLATION",
                "execution_status": "blocked",
                "message": spv.message,
                "error": spv.message,
                "rule_triggered": spv.rule_triggered,
                "active_database": self.active_db,
                "databases": self.catalog.get_catalog_summary(),
                "duration_ms": duration_ms,
            }
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return {
                "status": False,
                "active_database": self.active_db,
                "databases": self.catalog.get_catalog_summary(),
                "error": str(exc),
                "duration_ms": duration_ms,
            }


# ==============================================================================
# Public API Convenience Functions
# ==============================================================================

def get_project_db_path(project_id: str, db_name: Optional[str] = None) -> Path:
    """Returns absolute path to the project's active or specified database."""
    catalog = ProjectDatabaseCatalog(project_id=project_id)
    return catalog.get_database_path(db_name)


def initialize_project_db(
    project_id: str,
    template_key: str = "company_hr",
    db_name: Optional[str] = None
) -> Dict[str, Any]:
    """Provisions and seeds an isolated database for the project."""
    catalog = ProjectDatabaseCatalog(project_id=project_id)
    target_name = db_name or catalog.get_active_database_name()

    if not catalog.database_exists(target_name):
        catalog.create_database(target_name)

    db_path = catalog.get_database_path(target_name)
    catalog._provision_seed_database(db_path, template_key)
    catalog.set_active_database(target_name)

    template = SEED_TEMPLATES.get(template_key, SEED_TEMPLATES["company_hr"])
    return {
        "status": True,
        "message": f"Database '{target_name}' initialized with '{template['title']}' dataset.",
        "template": template_key,
        "active_database": target_name,
        "db_path": str(db_path),
    }


def get_database_schema(project_id: str, db_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Inspects catalog, databases, tables, columns, and foreign keys
    for the project. Returns current active database tables for backwards compatibility.
    """
    catalog = ProjectDatabaseCatalog(project_id=project_id)
    active_name = db_name or catalog.get_active_database_name()
    if not catalog.database_exists(active_name):
        active_name = catalog.get_active_database_name()

    current_tables = catalog.get_database_tables_meta(active_name)
    catalog_summary = catalog.get_catalog_summary()

    return {
        "active_database": active_name,
        "django_database": catalog.get_django_database(),
        "databases": catalog_summary,
        "tables": current_tables,
        "database_type": "SQLite 3",
        "total_tables": len(current_tables),
        "total_databases": len(catalog_summary),
    }


def execute_sql_query(
    project_id: str,
    query: str,
    active_db: Optional[str] = None,
    timeout_seconds: float = 5.0
) -> Dict[str, Any]:
    """
    Safely executes user SQL against the project's databases using SqlStatementDispatcher.
    Handles CREATE DATABASE, DROP DATABASE, USE, SHOW DATABASES, SELECT DATABASE(),
    and standard SQL table DDL/DML.
    """
    catalog = ProjectDatabaseCatalog(project_id=project_id)
    dispatcher = SqlStatementDispatcher(catalog, active_db=active_db)
    return dispatcher.execute_script(query, timeout_seconds=timeout_seconds)


def export_query_as_csv(
    project_id: str,
    query: str,
    active_db: Optional[str] = None
) -> io.StringIO:
    """Runs a query and formats output as a CSV stream."""
    res = execute_sql_query(project_id, query, active_db=active_db)
    output = io.StringIO()
    writer = csv.writer(output)

    if res.get("status") and res.get("primary", {}).get("is_query"):
        cols = res["primary"]["columns"]
        rows = res["primary"]["rows"]
        writer.writerow(cols)
        for r in rows:
            writer.writerow(r)
    else:
        writer.writerow(["Error"])
        writer.writerow([res.get("error", "Not a tabular query.")])

    output.seek(0)
    return output
