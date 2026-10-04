"""
SkilTrix CodeLab - Django Project Execution & Management Service
Handles:
1. Isolated Django workspace initialization
2. Database migrations (makemigrations, migrate)
3. Unit test execution (manage.py test)
4. Development server process lifecycle (start, stop, restart, status, logs)
5. Live reverse-proxy preview (GET, POST, etc. streaming)
6. Postman-like API Tester panel execution
"""

import os
import sys
import time
import socket
import subprocess
import threading
import atexit
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import requests

from .codelab_runner import get_project_workspace_dir, sync_db_files_to_workspace, sync_workspace_files_to_db
from .execution.sandbox_policy import ExecutionPolicy
from .codelab_models import CodeProject, WorkspaceSession


def get_django_settings_module(workspace_dir: Path) -> str:
    """Detects active settings module name (config.settings or myproject.settings)."""
    if (workspace_dir / "config" / "settings.py").exists():
        return "config.settings"
    if (workspace_dir / "myproject" / "settings.py").exists():
        return "myproject.settings"
    for p in workspace_dir.glob("*/settings.py"):
        parent_name = p.parent.name
        if parent_name not in (".venv", "venv", "env"):
            return f"{parent_name}.settings"
    return "config.settings"


def find_free_port(start: int = 9100, end: int = 9999) -> int:
    """Finds an available TCP port for a local dev server."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    # Fallback to ephemeral port assigned by OS
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def is_port_in_use(port: int, host: str = '127.0.0.1') -> bool:
    """Checks if a port is currently listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def wait_for_server_ready(port: int, host: str = '127.0.0.1', timeout: float = 4.0) -> bool:
    """Waits until the server is listening on port."""
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.1)
    return False


def tail_file(file_path: Path, max_lines: int = 60) -> str:
    """Reads the last N lines of a file safely."""
    if not file_path.exists():
        return ""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return "".join(lines[-max_lines:])
    except Exception as e:
        return f"[Error reading logs: {str(e)}]"


class DjangoProcessManager:
    """
    Manages background Django development server processes.
    Enforces process isolation, log capture, and port lifecycle.
    """
    _servers: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()

    @classmethod
    def start(cls, project_id: str) -> Dict[str, Any]:
        with cls._lock:
            # Check if project exists
            try:
                project = CodeProject.objects.get(project_id=project_id)
            except CodeProject.DoesNotExist:
                return {"status": False, "error": f"Project {project_id} not found."}

            # Enforce per-user active server limit
            from .codelab_observability import check_user_server_limit
            user_id = project.user.user_id if project.user else None
            allowed, limit_err = check_user_server_limit(user_id, project_id)
            if not allowed:
                return {"status": False, "error": limit_err, "quota_exceeded": True}

            workspace_dir = sync_db_files_to_workspace(project)
            manage_py = workspace_dir / "manage.py"
            if not manage_py.exists():
                return {"status": False, "error": "No manage.py found in project root."}

            # Check if already running and responsive
            existing = cls._servers.get(project_id)
            if existing and existing["process"].poll() is None:
                return {
                    "status": True,
                    "server_status": "running",
                    "port": existing["port"],
                    "url": f"/apps/skiltrix/api/preview/{project_id}/",
                    "message": "Server is already active.",
                }

            # Allocate port
            port = find_free_port()
            log_path = workspace_dir / "django_server.log"
            log_file = open(log_path, "w", encoding="utf-8", errors="replace")

            # Clean environment without secret leaking
            settings_mod = get_django_settings_module(workspace_dir)
            env = ExecutionPolicy.sanitize_environment({
                "PYTHONUNBUFFERED": "1",
                "DJANGO_SETTINGS_MODULE": settings_mod,
            })

            # Resolve configured project database
            valid_db, db_msg, selected_db, db_path = resolve_project_django_database(project_id, workspace_dir)
            if valid_db and selected_db:
                ensure_project_django_settings_database(workspace_dir, selected_db, project)
                env["CODELAB_DJANGO_DATABASE"] = selected_db
                env["DJANGO_DATABASE_NAME"] = selected_db

            # Ensure workspace is on PYTHONPATH
            existing_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{str(workspace_dir)}{os.pathsep}{existing_pythonpath}"

            # Auto-apply migrations if selected database file does not exist yet or was corrupted
            ensure_valid_sqlite_db(workspace_dir)
            target_db_file = (workspace_dir / "databases" / f"{selected_db}.sqlite3") if (valid_db and selected_db) else (workspace_dir / "databases" / "default_db.sqlite3")
            if not target_db_file.exists():
                try:
                    subprocess.run(
                        [sys.executable, "manage.py", "migrate", "--noinput"],
                        cwd=workspace_dir,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=15.0
                    )
                except Exception:
                    pass

            cmd = [sys.executable, "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"]

            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=workspace_dir,
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            except Exception as e:
                log_file.close()
                return {"status": False, "error": f"Failed to launch Django process: {str(e)}"}

            # Wait for server to bind port and start accepting requests
            ready = wait_for_server_ready(port, timeout=8.0)
            poll_res = proc.poll()
            process_exited = poll_res is not None
            if poll_res is not None or not ready:
                if poll_res is None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=2.0)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                    poll_res = proc.poll()
                log_file.close()
                log_content = tail_file(log_path, 40)
                return {
                    "status": False,
                    "server_status": "failed",
                    "exit_code": poll_res,
                    "error": "Django server terminated during startup. Check the project settings and logs." if process_exited else "Django server did not open its port before the startup timeout. Check the project settings and logs.",
                    "logs": log_content
                }

            cls._servers[project_id] = {
                "process": proc,
                "port": port,
                "log_file": log_file,
                "log_path": log_path,
                "start_time": time.time(),
                "started_at": time.time(),
                "workspace_dir": workspace_dir,
            }

            # Update WorkspaceSession in database
            WorkspaceSession.objects.filter(project=project).update(
                status="running",
                container_id=f"django_proc_{proc.pid}",
                allocated_port=port,
                preview_url=f"/apps/skiltrix/api/preview/{project_id}/"
            )

            return {
                "status": True,
                "server_status": "running",
                "port": port,
                "url": f"/apps/skiltrix/api/preview/{project_id}/",
                "pid": proc.pid,
                "message": f"Django development server started on port {port}."
            }

    @classmethod
    def stop(cls, project_id: str) -> Dict[str, Any]:
        with cls._lock:
            server_info = cls._servers.pop(project_id, None)
            if not server_info:
                # Update DB state
                WorkspaceSession.objects.filter(project__project_id=project_id).update(status="stopped")
                return {"status": True, "message": "Server was not running."}

            proc: subprocess.Popen = server_info["process"]
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            except Exception:
                pass

            # Close log file descriptor
            try:
                log_f = server_info.get("log_file")
                if log_f and not log_f.closed:
                    log_f.close()
            except Exception:
                pass

            # Update DB state
            WorkspaceSession.objects.filter(project__project_id=project_id).update(status="stopped")

            return {"status": True, "message": "Django development server stopped."}

    @classmethod
    def restart(cls, project_id: str) -> Dict[str, Any]:
        cls.stop(project_id)
        time.sleep(0.3)
        return cls.start(project_id)

    @classmethod
    def get_status(cls, project_id: str) -> Dict[str, Any]:
        with cls._lock:
            server_info = cls._servers.get(project_id)
            if not server_info:
                # Check if log file exists anyway
                workspace_dir = get_project_workspace_dir(project_id)
                log_path = workspace_dir / "django_server.log"
                return {
                    "status": True,
                    "server_status": "stopped",
                    "port": None,
                    "uptime_seconds": 0,
                    "logs": tail_file(log_path, 40)
                }

            proc: subprocess.Popen = server_info["process"]
            poll = proc.poll()
            log_path = server_info["log_path"]
            logs = tail_file(log_path, 60)

            if poll is not None:
                # Server died
                return {
                    "status": True,
                    "server_status": "failed",
                    "port": server_info["port"],
                    "exit_code": poll,
                    "uptime_seconds": round(time.time() - server_info["start_time"], 1),
                    "logs": logs
                }

            return {
                "status": True,
                "server_status": "running",
                "port": server_info["port"],
                "url": f"/apps/skiltrix/api/preview/{project_id}/",
                "pid": proc.pid,
                "uptime_seconds": round(time.time() - server_info["start_time"], 1),
                "logs": logs
            }

    @classmethod
    def get_server_port(cls, project_id: str) -> Optional[int]:
        server_info = cls._servers.get(project_id)
        if server_info and server_info["process"].poll() is None:
            return server_info["port"]
        return None

    @classmethod
    def stop_all(cls):
        """Clean up all running processes upon application shutdown."""
        with cls._lock:
            for pid, info in list(cls._servers.items()):
                try:
                    p = info["process"]
                    if p.poll() is None:
                        p.terminate()
                except Exception:
                    pass


# Register graceful shutdown handler
atexit.register(DjangoProcessManager.stop_all)


def ensure_valid_sqlite_db(workspace_dir: Path) -> None:
    """
    Validates that SQLite databases in the workspace are not corrupted.
    If corrupted or zero-length, safely removes them so Django can cleanly regenerate.
    """
    import sqlite3
    db_candidates = list(workspace_dir.glob("*.sqlite*")) + list(workspace_dir.glob("*.db")) + list(workspace_dir.glob("databases/*.sqlite*"))
    for db_file in db_candidates:
        if not db_file.exists() or db_file.is_dir():
            continue
        # Check for empty file
        if db_file.stat().st_size == 0:
            try:
                db_file.unlink()
            except Exception:
                pass
            continue

        try:
            conn = sqlite3.connect(str(db_file), timeout=2.0)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            res = cursor.fetchone()
            conn.close()
            if not res or res[0] != "ok":
                db_file.unlink()
        except Exception:
            try:
                db_file.unlink()
            except Exception:
                pass


def resolve_project_django_database(project_id: str, workspace_dir: Path) -> Tuple[bool, str, Optional[str], Optional[Path]]:
    """
    Resolves the selected Django database for the project.
    Strictly enforces:
    1. A database must be explicitly selected in project configuration.
    2. The selected database must exist in the project catalog.
    3. Does NOT fall back silently to default_db or any other database.
    Returns (is_valid, message, db_name, db_path).
    """
    from .codelab_sql import ProjectDatabaseCatalog
    catalog = ProjectDatabaseCatalog(workspace_dir=workspace_dir, project_id=project_id)
    db_name = catalog.get_django_database()
    if not db_name:
        return False, "Error: No Django database selected for project. Please select or create a local database in Django Database settings.", None, None
    if not catalog.database_exists(db_name):
        return False, f"Error: Selected database '{db_name}' does not exist. Please create it or select an existing database.", None, None
    db_path = catalog.get_database_path(db_name)
    return True, "OK", db_name, db_path


def ensure_project_django_settings_database(workspace_dir: Path, selected_db: str, project: Optional[CodeProject] = None) -> None:
    """
    Ensures that the project's settings.py points DATABASES['default']['NAME']
    to the selected database in BASE_DIR / 'databases' / f'{selected_db}.sqlite3',
    respecting CODELAB_DJANGO_DATABASE environment override if present.
    """
    settings_file = None
    for cand in [workspace_dir / "config" / "settings.py", workspace_dir / "myproject" / "settings.py"]:
        if cand.exists():
            settings_file = cand
            break
    if not settings_file:
        for p in workspace_dir.glob("*/settings.py"):
            if p.parent.name not in (".venv", "venv", "env"):
                settings_file = p
                break

    if not settings_file or not settings_file.exists():
        return

    content = settings_file.read_text(encoding="utf-8", errors="replace")
    import re

    # Target replacement for DATABASES
    db_block = f"""# Database connected to CodeLab SQL Engine (Project-Local Database)
_configured_db = os.environ.get('CODELAB_DJANGO_DATABASE', '{selected_db}')
DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'databases' / f'{{_configured_db}}.sqlite3',
    }}
}}"""

    if re.search(r"DATABASES\s*=\s*\{[\s\S]*?\n\}", content):
        new_content = re.sub(r"DATABASES\s*=\s*\{[\s\S]*?\n\}", db_block, content, count=1)
    else:
        new_content = content + "\n\n" + db_block + "\n"

    if "import os" not in new_content:
        new_content = "import os\n" + new_content

    if new_content != content:
        settings_file.write_text(new_content, encoding="utf-8")
        if project:
            try:
                rel_path = settings_file.relative_to(workspace_dir).as_posix()
                pfile = ProjectFile.objects.filter(project=project, path=rel_path).first()
                if pfile:
                    pfile.content = new_content
                    pfile.size_bytes = len(new_content.encode("utf-8"))
                    pfile.save(update_fields=["content", "size_bytes"])
            except Exception:
                pass


def run_django_makemigrations(project_id: str, app_label: str = "") -> Dict[str, Any]:
    """
    Executes manage.py makemigrations [app_label] inside project workspace.
    Runs strictly against the project's selected database.
    """
    try:
        project = CodeProject.objects.get(project_id=project_id)
    except CodeProject.DoesNotExist:
        return {"status": False, "success": False, "exit_code": 1, "error": f"Project {project_id} not found.", "output": f"Project {project_id} not found."}

    workspace_dir = sync_db_files_to_workspace(project)
    manage_py = workspace_dir / "manage.py"
    if not manage_py.exists():
        return {"status": False, "success": False, "exit_code": 1, "error": "No manage.py found in project root.", "output": "No manage.py found in project root."}

    # Resolve selected database
    valid_db, db_msg, selected_db, db_path = resolve_project_django_database(project_id, workspace_dir)
    if not valid_db:
        return {
            "status": False,
            "success": False,
            "exit_code": 1,
            "error": db_msg,
            "output": db_msg,
            "duration_ms": 0,
        }

    ensure_project_django_settings_database(workspace_dir, selected_db, project)
    ensure_valid_sqlite_db(workspace_dir)

    settings_mod = get_django_settings_module(workspace_dir)
    env = ExecutionPolicy.sanitize_environment({
        "PYTHONUNBUFFERED": "1",
        "DJANGO_SETTINGS_MODULE": settings_mod,
        "CODELAB_DJANGO_DATABASE": selected_db,
        "DJANGO_DATABASE_NAME": selected_db,
    })
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{str(workspace_dir)}{os.pathsep}{existing_pythonpath}"

    cmd = [sys.executable, "manage.py", "makemigrations"]
    if app_label:
        cmd.append(app_label)

    start_time = time.time()
    res = subprocess.run(
        cmd,
        cwd=workspace_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=25.0
    )

    # Sync any newly generated migration files back to database
    sync_workspace_files_to_db(project)

    duration = round((time.time() - start_time) * 1000, 2)
    output = res.stdout
    if res.stderr:
        output += ("\n" if output else "") + res.stderr

    return {
        "status": res.returncode == 0,
        "success": res.returncode == 0,
        "exit_code": res.returncode,
        "output": output.strip() or "No changes detected",
        "database": selected_db,
        "duration_ms": duration
    }


def run_django_migrate(project_id: str, app_label: str = "", migration_name: str = "") -> Dict[str, Any]:
    """
    Executes manage.py migrate [app_label] [migration_name] --noinput inside project workspace.
    Runs strictly against the project's selected database.
    """
    try:
        project = CodeProject.objects.get(project_id=project_id)
    except CodeProject.DoesNotExist:
        return {"status": False, "success": False, "exit_code": 1, "error": f"Project {project_id} not found.", "output": f"Project {project_id} not found."}

    workspace_dir = sync_db_files_to_workspace(project)
    manage_py = workspace_dir / "manage.py"
    if not manage_py.exists():
        return {"status": False, "success": False, "exit_code": 1, "error": "No manage.py found in project root.", "output": "No manage.py found in project root."}

    # Resolve selected database
    valid_db, db_msg, selected_db, db_path = resolve_project_django_database(project_id, workspace_dir)
    if not valid_db:
        return {
            "status": False,
            "success": False,
            "exit_code": 1,
            "error": db_msg,
            "output": db_msg,
            "duration_ms": 0,
        }

    ensure_project_django_settings_database(workspace_dir, selected_db, project)
    ensure_valid_sqlite_db(workspace_dir)

    settings_mod = get_django_settings_module(workspace_dir)
    env = ExecutionPolicy.sanitize_environment({
        "PYTHONUNBUFFERED": "1",
        "DJANGO_SETTINGS_MODULE": settings_mod,
        "CODELAB_DJANGO_DATABASE": selected_db,
        "DJANGO_DATABASE_NAME": selected_db,
    })
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{str(workspace_dir)}{os.pathsep}{existing_pythonpath}"

    # Auto-generate migrations if app models are unmigrated
    myapp_mig = workspace_dir / "myapp" / "migrations"
    if myapp_mig.exists():
        py_files = [f for f in myapp_mig.glob("*.py") if f.name != "__init__.py"]
        if not py_files:
            run_django_makemigrations(project_id, app_label="myapp")

    cmd = [sys.executable, "manage.py", "migrate", "--noinput"]
    if app_label:
        cmd.append(app_label)
    if migration_name:
        cmd.append(migration_name)

    start_time = time.time()
    res = subprocess.run(
        cmd,
        cwd=workspace_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=30.0
    )

    # Sync workspace files back to database
    sync_workspace_files_to_db(project)

    duration = round((time.time() - start_time) * 1000, 2)
    output = res.stdout
    if res.stderr:
        output += ("\n" if output else "") + res.stderr

    return {
        "status": res.returncode == 0,
        "success": res.returncode == 0,
        "exit_code": res.returncode,
        "output": output.strip() or "Database migrated successfully.",
        "database": selected_db,
        "duration_ms": duration
    }


def run_django_showmigrations(project_id: str, app_label: str = "") -> Dict[str, Any]:
    """
    Executes manage.py showmigrations [app_label] inside project workspace.
    Runs strictly against the project's selected database.
    """
    try:
        project = CodeProject.objects.get(project_id=project_id)
    except CodeProject.DoesNotExist:
        return {"status": False, "success": False, "exit_code": 1, "error": f"Project {project_id} not found.", "output": f"Project {project_id} not found."}

    workspace_dir = sync_db_files_to_workspace(project)
    manage_py = workspace_dir / "manage.py"
    if not manage_py.exists():
        return {"status": False, "success": False, "exit_code": 1, "error": "No manage.py found in project root.", "output": "No manage.py found in project root."}

    valid_db, db_msg, selected_db, db_path = resolve_project_django_database(project_id, workspace_dir)
    if not valid_db:
        return {
            "status": False,
            "success": False,
            "exit_code": 1,
            "error": db_msg,
            "output": db_msg,
            "duration_ms": 0,
        }

    ensure_project_django_settings_database(workspace_dir, selected_db, project)
    ensure_valid_sqlite_db(workspace_dir)

    settings_mod = get_django_settings_module(workspace_dir)
    env = ExecutionPolicy.sanitize_environment({
        "PYTHONUNBUFFERED": "1",
        "DJANGO_SETTINGS_MODULE": settings_mod,
        "CODELAB_DJANGO_DATABASE": selected_db,
        "DJANGO_DATABASE_NAME": selected_db,
    })
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{str(workspace_dir)}{os.pathsep}{existing_pythonpath}"

    cmd = [sys.executable, "manage.py", "showmigrations"]
    if app_label:
        cmd.append(app_label)

    start_time = time.time()
    res = subprocess.run(
        cmd,
        cwd=workspace_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=25.0
    )

    duration = round((time.time() - start_time) * 1000, 2)
    output = res.stdout
    if res.stderr:
        output += ("\n" if output else "") + res.stderr

    # Parse migrations into structured list
    parsed_migrations = []
    current_app = ""
    for line in output.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if not line.startswith(" ") and not line.startswith("\t") and not line_stripped.startswith("["):
            current_app = line_stripped
        elif line_stripped.startswith("[X]") or line_stripped.startswith("[ ]"):
            applied = line_stripped.startswith("[X]")
            mig_name = line_stripped[3:].strip()
            parsed_migrations.append({
                "app": current_app,
                "name": mig_name,
                "applied": applied
            })

    return {
        "status": res.returncode == 0,
        "success": res.returncode == 0,
        "exit_code": res.returncode,
        "output": output.strip(),
        "database": selected_db,
        "migrations": parsed_migrations,
        "duration_ms": duration
    }


def run_django_sqlmigrate(project_id: str, app_label: str, migration_name: str) -> Dict[str, Any]:
    """
    Executes manage.py sqlmigrate <app_label> <migration_name> inside project workspace.
    Returns SQL generated for that migration.
    """
    if not app_label or not migration_name:
        return {
            "status": False,
            "success": False,
            "exit_code": 1,
            "error": "Both app_label and migration_name are required for sqlmigrate.",
            "output": "Both app_label and migration_name are required for sqlmigrate.",
            "duration_ms": 0,
        }

    try:
        project = CodeProject.objects.get(project_id=project_id)
    except CodeProject.DoesNotExist:
        return {"status": False, "success": False, "exit_code": 1, "error": f"Project {project_id} not found.", "output": f"Project {project_id} not found."}

    workspace_dir = sync_db_files_to_workspace(project)
    manage_py = workspace_dir / "manage.py"
    if not manage_py.exists():
        return {"status": False, "success": False, "exit_code": 1, "error": "No manage.py found in project root.", "output": "No manage.py found in project root."}

    valid_db, db_msg, selected_db, db_path = resolve_project_django_database(project_id, workspace_dir)
    if not valid_db:
        return {
            "status": False,
            "success": False,
            "exit_code": 1,
            "error": db_msg,
            "output": db_msg,
            "duration_ms": 0,
        }

    ensure_project_django_settings_database(workspace_dir, selected_db, project)
    ensure_valid_sqlite_db(workspace_dir)

    settings_mod = get_django_settings_module(workspace_dir)
    env = ExecutionPolicy.sanitize_environment({
        "PYTHONUNBUFFERED": "1",
        "DJANGO_SETTINGS_MODULE": settings_mod,
        "CODELAB_DJANGO_DATABASE": selected_db,
        "DJANGO_DATABASE_NAME": selected_db,
    })
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{str(workspace_dir)}{os.pathsep}{existing_pythonpath}"

    cmd = [sys.executable, "manage.py", "sqlmigrate", app_label, migration_name]

    start_time = time.time()
    res = subprocess.run(
        cmd,
        cwd=workspace_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=25.0
    )

    duration = round((time.time() - start_time) * 1000, 2)
    output = res.stdout
    if res.stderr:
        output += ("\n" if output else "") + res.stderr

    return {
        "status": res.returncode == 0,
        "success": res.returncode == 0,
        "exit_code": res.returncode,
        "output": output.strip(),
        "sql": output.strip(),
        "database": selected_db,
        "duration_ms": duration
    }


def run_django_migrations(project_id: str) -> Dict[str, Any]:
    """
    Executes makemigrations followed by migrate inside the project workspace.
    """
    make_res = run_django_makemigrations(project_id)
    if not make_res.get("status"):
        return make_res

    mig_res = run_django_migrate(project_id)

    combined_output = f"=== makemigrations ===\n{make_res.get('output', '')}\n\n=== migrate ===\n{mig_res.get('output', '')}"
    success = make_res.get("status", False) and mig_res.get("status", False)
    exit_code = 0 if success else (make_res.get("exit_code") or mig_res.get("exit_code") or 1)

    return {
        "status": success,
        "success": success,
        "exit_code": exit_code,
        "output": combined_output.strip(),
        "database": mig_res.get("database"),
        "duration_ms": (make_res.get("duration_ms", 0) + mig_res.get("duration_ms", 0))
    }


def run_django_tests(project_id: str) -> Dict[str, Any]:
    """
    Executes manage.py test inside the project workspace.
    """
    try:
        project = CodeProject.objects.get(project_id=project_id)
    except CodeProject.DoesNotExist:
        return {"status": False, "error": f"Project {project_id} not found."}

    workspace_dir = sync_db_files_to_workspace(project)
    manage_py = workspace_dir / "manage.py"
    if not manage_py.exists():
        return {"status": False, "error": "No manage.py found in project root."}

    valid_db, db_msg, selected_db, db_path = resolve_project_django_database(project_id, workspace_dir)
    if valid_db and selected_db:
        ensure_project_django_settings_database(workspace_dir, selected_db, project)

    settings_mod = get_django_settings_module(workspace_dir)
    env_vars = {
        "PYTHONUNBUFFERED": "1",
        "DJANGO_SETTINGS_MODULE": settings_mod,
    }
    if valid_db and selected_db:
        env_vars["CODELAB_DJANGO_DATABASE"] = selected_db
        env_vars["DJANGO_DATABASE_NAME"] = selected_db

    env = ExecutionPolicy.sanitize_environment(env_vars)
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{str(workspace_dir)}{os.pathsep}{existing_pythonpath}"

    start_time = time.time()
    res = subprocess.run(
        [sys.executable, "manage.py", "test", "--noinput"],
        cwd=workspace_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=25.0
    )
    duration = round((time.time() - start_time) * 1000, 2)

    return {
        "status": res.returncode == 0,
        "success": res.returncode == 0,
        "exit_code": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "output": (res.stdout + ("\n" + res.stderr if res.stderr else "")).strip(),
        "duration_ms": duration
    }


def run_django_check(project_id: str) -> Dict[str, Any]:
    """
    Executes python manage.py check inside the project workspace.
    """
    try:
        project = CodeProject.objects.get(project_id=project_id)
    except CodeProject.DoesNotExist:
        return {"status": False, "error": f"Project {project_id} not found."}

    workspace_dir = sync_db_files_to_workspace(project)
    manage_py = workspace_dir / "manage.py"
    if not manage_py.exists():
        return {"status": False, "error": "No manage.py found in project root."}

    settings_mod = get_django_settings_module(workspace_dir)
    env = ExecutionPolicy.sanitize_environment({
        "PYTHONUNBUFFERED": "1",
        "DJANGO_SETTINGS_MODULE": settings_mod,
    })
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{str(workspace_dir)}{os.pathsep}{existing_pythonpath}"

    start_time = time.time()
    res = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=workspace_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=15.0
    )
    duration = round((time.time() - start_time) * 1000, 2)
    output = (res.stdout + ("\n" + res.stderr if res.stderr else "")).strip()
    return {
        "status": res.returncode == 0,
        "success": res.returncode == 0,
        "exit_code": res.returncode,
        "output": output or "System check identified no issues (0 silenced).",
        "duration_ms": duration
    }


def create_django_app(project_id: str, app_name: str) -> Dict[str, Any]:
    """
    Creates a new Django app in the project:
    1. Runs manage.py startapp <app_name> (or creates the standard files)
    2. Adds urls.py in the app
    3. Updates settings.py INSTALLED_APPS to register the new app
    4. Syncs all files to ProjectFile database records
    """
    clean_app_name = "".join(c for c in app_name.strip().lower() if c.isalnum() or c == "_")
    if not clean_app_name or not clean_app_name[0].isalpha():
        return {"status": False, "error": f"Invalid app name '{app_name}'. Must start with a letter and contain only alphanumeric characters or underscores."}

    try:
        project = CodeProject.objects.get(project_id=project_id)
    except CodeProject.DoesNotExist:
        return {"status": False, "error": f"Project {project_id} not found."}

    workspace_dir = sync_db_files_to_workspace(project)
    app_dir = workspace_dir / clean_app_name
    if app_dir.exists():
        return {"status": False, "error": f"App or directory '{clean_app_name}' already exists."}

    app_dir.mkdir(parents=True, exist_ok=True)
    migrations_dir = app_dir / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)

    class_name = f"{clean_app_name.capitalize()}Config"

    # 1. Standard Django app files
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (migrations_dir / "__init__.py").write_text("", encoding="utf-8")

    (app_dir / "apps.py").write_text(f"""from django.apps import AppConfig

class {class_name}(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '{clean_app_name}'
""", encoding="utf-8")

    (app_dir / "admin.py").write_text(f"""from django.contrib import admin
# Register your models here.
""", encoding="utf-8")

    (app_dir / "models.py").write_text(f"""from django.db import models

# Create your models here.
class {clean_app_name.capitalize()}Item(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
""", encoding="utf-8")

    (app_dir / "views.py").write_text(f"""from django.shortcuts import render
from django.http import JsonResponse
from .models import {clean_app_name.capitalize()}Item

def index(request):
    items = {clean_app_name.capitalize()}Item.objects.all()
    return JsonResponse({{
        "app": "{clean_app_name}",
        "count": items.count(),
        "status": "active"
    }})
""", encoding="utf-8")

    (app_dir / "urls.py").write_text(f"""from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='{clean_app_name}_index'),
]
""", encoding="utf-8")

    (app_dir / "tests.py").write_text(f"""from django.test import TestCase
from .models import {clean_app_name.capitalize()}Item

class {clean_app_name.capitalize()}ModelTest(TestCase):
    def test_create_item(self):
        item = {clean_app_name.capitalize()}Item.objects.create(name="Test Item")
        self.assertEqual(item.name, "Test Item")
""", encoding="utf-8")

    # 2. Register in settings.py INSTALLED_APPS
    settings_file = None
    for candidate in [workspace_dir / "config" / "settings.py", workspace_dir / "myproject" / "settings.py"]:
        if candidate.exists():
            settings_file = candidate
            break
    if not settings_file:
        for p in workspace_dir.glob("*/settings.py"):
            settings_file = p
            break

    if settings_file and settings_file.exists():
        settings_text = settings_file.read_text(encoding="utf-8")
        if f"'{clean_app_name}'" not in settings_text and f'"{clean_app_name}"' not in settings_text:
            import re
            installed_apps_match = re.search(r"INSTALLED_APPS\s*=\s*\[([\s\S]*?)\]", settings_text)
            if installed_apps_match:
                apps_content = installed_apps_match.group(1)
                new_app_entry = f"    '{clean_app_name}.apps.{class_name}',\n"
                new_apps_content = apps_content.rstrip() + "\n" + new_app_entry
                updated_text = settings_text[:installed_apps_match.start(1)] + new_apps_content + settings_text[installed_apps_match.end(1):]
                settings_file.write_text(updated_text, encoding="utf-8")

    # 3. Register in root urls.py if not present
    urls_file = None
    for candidate in [workspace_dir / "config" / "urls.py", workspace_dir / "myproject" / "urls.py"]:
        if candidate.exists():
            urls_file = candidate
            break
    if urls_file and urls_file.exists():
        urls_text = urls_file.read_text(encoding="utf-8")
        if f"include('{clean_app_name}.urls')" not in urls_text:
            import re
            urlpatterns_match = re.search(r"urlpatterns\s*=\s*\[([\s\S]*?)\]", urls_text)
            if urlpatterns_match:
                url_content = urlpatterns_match.group(1)
                route_entry = f"    path('{clean_app_name}/', include('{clean_app_name}.urls')),\n"
                new_url_content = url_content.rstrip() + "\n" + route_entry
                updated_urls = urls_text[:urlpatterns_match.start(1)] + new_url_content + urls_text[urlpatterns_match.end(1):]
                urls_file.write_text(updated_urls, encoding="utf-8")

    # 4. Sync workspace back to ProjectFile records
    sync_workspace_files_to_db(project)

    return {
        "status": True,
        "message": f"Django app '{clean_app_name}' created and registered in INSTALLED_APPS.",
        "app_name": clean_app_name,
        "files_created": [
            f"{clean_app_name}/__init__.py",
            f"{clean_app_name}/apps.py",
            f"{clean_app_name}/models.py",
            f"{clean_app_name}/views.py",
            f"{clean_app_name}/urls.py",
            f"{clean_app_name}/admin.py",
            f"{clean_app_name}/tests.py",
            f"{clean_app_name}/migrations/__init__.py",
        ]
    }


def get_django_navigation(project_id: str) -> Dict[str, Any]:
    try:
        project = CodeProject.objects.get(project_id=project_id)
    except CodeProject.DoesNotExist:
        return {"status": False, "error": f"Project {project_id} not found."}

    workspace_dir = sync_db_files_to_workspace(project)
    settings_mod = get_django_settings_module(workspace_dir)

    # 1. Discover installed apps
    installed_apps = []
    settings_file = None
    for cand in [workspace_dir / "config" / "settings.py", workspace_dir / "myproject" / "settings.py"]:
        if cand.exists():
            settings_file = cand
            break
    if not settings_file:
        for p in workspace_dir.glob("*/settings.py"):
            settings_file = p
            break

    if settings_file and settings_file.exists():
        import re
        txt = settings_file.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"INSTALLED_APPS\s*=\s*\[([\s\S]*?)\]", txt)
        if m:
            raw_items = m.group(1).split(",")
            for item in raw_items:
                clean = item.strip().strip("'\"")
                if clean and not clean.startswith("#"):
                    is_contrib = clean.startswith("django.contrib")
                    installed_apps.append({
                        "name": clean,
                        "is_core": is_contrib,
                    })

    # 2. Discover routes from all urls.py
    routes = []
    for ufile in workspace_dir.glob("**/urls.py"):
        if ".venv" in ufile.parts or "venv" in ufile.parts:
            continue
        rel_path = ufile.relative_to(workspace_dir).as_posix()
        try:
            import re
            utxt = ufile.read_text(encoding="utf-8", errors="replace")
            for pm in re.finditer(r"path\(\s*['\"]([^'\"]*)['\"]\s*,\s*([^,\)]+)", utxt):
                routes.append({
                    "route": pm.group(1) or "/",
                    "handler": pm.group(2).strip(),
                    "file": rel_path
                })
        except Exception:
            pass

    # 3. Discover models
    models_list = []
    for mfile in workspace_dir.glob("**/models.py"):
        if ".venv" in mfile.parts or "venv" in mfile.parts:
            continue
        rel_path = mfile.relative_to(workspace_dir).as_posix()
        try:
            import re
            mtxt = mfile.read_text(encoding="utf-8", errors="replace")
            for mm in re.finditer(r"class\s+([A-Za-z0-9_]+)\s*\(\s*models\.Model\s*\):", mtxt):
                models_list.append({
                    "name": mm.group(1),
                    "file": rel_path
                })
        except Exception:
            pass

    # 4. Discover migrations
    migrations_list = []
    for mig in workspace_dir.glob("**/migrations/*.py"):
        if ".venv" in mig.parts or "venv" in mig.parts or mig.name == "__init__.py":
            continue
        rel_path = mig.relative_to(workspace_dir).as_posix()
        migrations_list.append({
            "name": mig.stem,
            "path": rel_path,
        })

    # 5. Templates & static
    templates_list = []
    for t in workspace_dir.glob("templates/**/*"):
        if t.is_file():
            templates_list.append(t.relative_to(workspace_dir).as_posix())

    static_list = []
    for s in workspace_dir.glob("static/**/*"):
        if s.is_file() and s.name != ".keep":
            static_list.append(s.relative_to(workspace_dir).as_posix())

    # 6. Shortcuts
    shortcuts = []
    if (workspace_dir / "manage.py").exists():
        shortcuts.append({"label": "manage.py", "path": "manage.py"})
    if settings_file:
        shortcuts.append({"label": "settings.py", "path": settings_file.relative_to(workspace_dir).as_posix()})
    for u in ["config/urls.py", "myproject/urls.py"]:
        if (workspace_dir / u).exists():
            shortcuts.append({"label": "urls.py", "path": u})
            break
    if (workspace_dir / "requirements.txt").exists():
        shortcuts.append({"label": "requirements.txt", "path": "requirements.txt"})

    status_info = DjangoProcessManager.get_status(project_id)

    from .codelab_sql import ProjectDatabaseCatalog
    catalog = ProjectDatabaseCatalog(workspace_dir=workspace_dir, project_id=project_id)
    selected_database = catalog.get_django_database()
    available_databases = catalog.list_databases()
    active_sql_database = catalog.get_active_database_name()

    return {
        "status": True,
        "project_id": project_id,
        "project_name": project.title,
        "root_dir": str(workspace_dir),
        "settings_module": settings_mod,
        "selected_database": selected_database,
        "available_databases": available_databases,
        "active_sql_database": active_sql_database,
        "installed_apps": installed_apps,
        "routes": routes,
        "models": models_list,
        "migrations": migrations_list,
        "templates": templates_list,
        "static": static_list,
        "shortcuts": shortcuts,
        "server_status": status_info.get("server_status", "stopped"),
        "port": status_info.get("port"),
        "url": status_info.get("url"),
    }


def test_django_api_endpoint(
    project_id: str,
    method: str,
    path: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Simulates a Postman / HTTP client request directly to the running Django development server.
    """
    port = DjangoProcessManager.get_server_port(project_id)
    if not port:
        return {
            "status": False,
            "error": "Django server is not running for this project. Start the server first."
        }

    clean_path = path if path.startswith("/") else f"/{path}"
    target_url = f"http://127.0.0.1:{port}{clean_path}"

    req_headers = {"User-Agent": "SkilTrix-CodeLab-ApiTester/1.0"}
    if headers:
        req_headers.update(headers)

    method = method.upper().strip()
    data_payload = body.encode("utf-8") if body else None

    start_time = time.time()
    resp = None
    for attempt in range(4):
        try:
            resp = requests.request(
                method=method,
                url=target_url,
                headers=req_headers,
                data=data_payload,
                timeout=10.0,
                allow_redirects=True
            )
            break
        except requests.exceptions.ConnectionError:
            if attempt < 3:
                time.sleep(0.5)
                continue
            return {
                "status": False,
                "error": "Connection refused. Server may be restarting or port not responding."
            }
        except requests.exceptions.Timeout:
            return {
                "status": False,
                "error": "Request timed out after 10.0 seconds."
            }
        except Exception as e:
            return {
                "status": False,
                "error": f"API Request failed: {str(e)}"
            }

    if resp is None:
        return {"status": False, "error": "No response received."}

    duration_ms = round((time.time() - start_time) * 1000, 2)
    is_json = False
    json_data = None
    try:
        json_data = resp.json()
        is_json = True
    except Exception:
        pass

    return {
        "status": True,
        "status_code": resp.status_code,
        "status_text": resp.reason,
        "duration_ms": duration_ms,
        "headers": dict(resp.headers),
        "content_type": resp.headers.get("Content-Type", "text/plain"),
        "body": resp.text,
        "is_json": is_json,
        "json_data": json_data
    }


from django.views.decorators.clickjacking import xframe_options_exempt

@xframe_options_exempt
def proxy_django_preview_request(request, project_id: str, subpath: str = ""):
    """
    Reverse proxies HTTP requests to the running isolated Django dev server.
    """
    from django.http import HttpResponse

    port = DjangoProcessManager.get_server_port(project_id)
    if not port:
        try:
            proj = CodeProject.objects.get(project_id=project_id)
            title = proj.title
        except CodeProject.DoesNotExist:
            resp = HttpResponse("<h3>Project not found</h3>", status=404, content_type="text/html")
            resp["X-Frame-Options"] = "ALLOWALL"
            resp["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self';"
            return resp

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SkilTrix Preview - Server Offline</title>
    <style>
        body {{
            background: #0f172a;
            color: #e2e8f0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }}
        .card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 32px;
            max-width: 480px;
            text-align: center;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5);
        }}
        h2 {{ color: #818cf8; margin-top: 0; font-size: 20px; }}
        p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 12px 0 20px; }}
        .badge {{ background: #312e81; color: #a5b4fc; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; display: inline-block; }}
    </style>
</head>
<body>
    <div class="card">
        <div style="font-size: 40px; margin-bottom: 12px;">🚀</div>
        <h2>Django Live Preview Offline</h2>
        <span class="badge">{title}</span>
        <p>Your development server is not currently running. Click <strong>Start Server</strong> in the top-right toolbar of the preview panel to launch your application.</p>
    </div>
</body>
</html>"""
        resp = HttpResponse(html, content_type="text/html")
        resp["X-Frame-Options"] = "ALLOWALL"
        resp["Access-Control-Allow-Origin"] = "*"
        resp["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self';"
        return resp

    clean_subpath = subpath if subpath.startswith("/") else f"/{subpath}"
    query = request.META.get('QUERY_STRING', '')
    target_url = f"http://127.0.0.1:{port}{clean_subpath}"
    if query:
        target_url = f"{target_url}?{query}"

    headers = {}
    for k, v in request.headers.items():
        if k.lower() not in ("host", "content-length"):
            headers[k] = v

    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.body,
            timeout=10.0,
            allow_redirects=False
        )

        content = resp.content
        content_type = resp.headers.get("Content-Type", "text/html")

        if "text/html" in content_type.lower():
            base_tag = f'<base href="/apps/skiltrix/api/preview/{project_id}/">'
            content_str = resp.text
            if "<head>" in content_str:
                content_str = content_str.replace("<head>", f"<head>\n    {base_tag}", 1)
            elif "<HEAD>" in content_str:
                content_str = content_str.replace("<HEAD>", f"<HEAD>\n    {base_tag}", 1)
            else:
                content_str = f"{base_tag}\n" + content_str
            content = content_str.encode("utf-8")

        response = HttpResponse(content, status=resp.status_code, content_type=content_type)
        if "location" in resp.headers:
            response["Location"] = resp.headers["location"]
        if "set-cookie" in resp.headers:
            response["Set-Cookie"] = resp.headers["set-cookie"]

        response["X-Frame-Options"] = "ALLOWALL"
        response["Access-Control-Allow-Origin"] = "*"
        response["Cross-Origin-Opener-Policy"] = "unsafe-none"
        response["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self';"
        return response
    except Exception as e:
        err_resp = HttpResponse(f"<h3>Gateway Error</h3><p>{str(e)}</p>", status=502, content_type="text/html")
        err_resp["X-Frame-Options"] = "ALLOWALL"
        return err_resp


