"""
SkilTrix CodeLab - Observability, Quotas & Lifecycle Management
Provides:
1. System health check & runtime telemetry endpoint logic.
2. Per-user concurrent server limit enforcement (max 2 active servers).
3. Workspace storage quota enforcement (max 50 MB per project).
4. Automatic idle workspace and orphaned process cleanup routines.
"""

import os
import sys
import time
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from django.conf import settings
from .codelab_models import CodeProject
from .codelab_runner import WORKSPACE_BASE_DIR, get_project_workspace_dir


# Quota definitions
MAX_CONCURRENT_SERVERS_PER_USER = 2
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024          # 5 MB per single file
MAX_WORKSPACE_STORAGE_BYTES = 50 * 1024 * 1024  # 50 MB per workspace
MAX_SERVER_UPTIME_SECONDS = 3600                # 1 hour max server lifespan
MAX_EXECUTION_TIMEOUT_SECONDS = 15.0


def get_runtime_telemetry() -> Dict[str, Any]:
    """Detects available language compilers and runtimes with versions."""
    runtimes = {}

    # 1. Python
    runtimes["python"] = {
        "available": True,
        "version": sys.version.split()[0],
        "path": sys.executable,
    }

    # 2. SQLite
    runtimes["sqlite"] = {
        "available": True,
        "version": sqlite3.sqlite_version,
        "path": "embedded-c-driver",
    }

    # 3. PHP
    try:
        from .codelab_php import find_php_executable
        php_bin = find_php_executable()
        if php_bin:
            res = subprocess.run([php_bin, "-v"], capture_output=True, text=True, timeout=3.0)
            first_line = res.stdout.splitlines()[0] if res.stdout else "PHP installed"
            runtimes["php"] = {
                "available": True,
                "version": first_line.split()[1] if len(first_line.split()) > 1 else first_line,
                "path": php_bin,
            }
        else:
            runtimes["php"] = {"available": False, "version": None, "path": None}
    except Exception:
        runtimes["php"] = {"available": False, "version": None, "path": None}

    # 4. Node.js
    try:
        node_bin = shutil.which("node")
        if node_bin:
            res = subprocess.run([node_bin, "--version"], capture_output=True, text=True, timeout=3.0)
            runtimes["node"] = {
                "available": True,
                "version": res.stdout.strip(),
                "path": node_bin,
            }
        else:
            runtimes["node"] = {"available": False, "version": None, "path": None}
    except Exception:
        runtimes["node"] = {"available": False, "version": None, "path": None}

    # 5. Java / javac
    try:
        javac_bin = shutil.which("javac")
        if javac_bin:
            res = subprocess.run([javac_bin, "-version"], capture_output=True, text=True, timeout=3.0)
            ver = res.stdout.strip() or res.stderr.strip()
            runtimes["java"] = {
                "available": True,
                "version": ver.replace("javac ", ""),
                "path": javac_bin,
            }
        else:
            runtimes["java"] = {"available": False, "version": None, "path": None}
    except Exception:
        runtimes["java"] = {"available": False, "version": None, "path": None}

    # 6. GCC / G++
    try:
        gcc_bin = shutil.which("gcc") or shutil.which("g++")
        if gcc_bin:
            res = subprocess.run([gcc_bin, "--version"], capture_output=True, text=True, timeout=3.0)
            first_line = res.stdout.splitlines()[0] if res.stdout else "GCC"
            runtimes["gcc"] = {
                "available": True,
                "version": first_line,
                "path": gcc_bin,
            }
        else:
            runtimes["gcc"] = {"available": False, "version": None, "path": None}
    except Exception:
        runtimes["gcc"] = {"available": False, "version": None, "path": None}

    return runtimes


def get_active_servers_summary() -> Dict[str, Any]:
    """Returns currently running Django and PHP servers across the instance."""
    from .codelab_django import DjangoProcessManager
    from .codelab_php import PhpProcessManager

    django_servers = []
    for pid, sinfo in DjangoProcessManager._servers.items():
        proc = sinfo.get("process")
        if proc and proc.poll() is None:
            django_servers.append({
                "project_id": pid,
                "port": sinfo.get("port"),
                "started_at": sinfo.get("started_at", 0),
                "type": "django",
            })

    php_servers = []
    for pid, sinfo in PhpProcessManager._servers.items():
        proc = sinfo.get("process")
        if proc and proc.poll() is None:
            php_servers.append({
                "project_id": pid,
                "port": sinfo.get("port"),
                "started_at": sinfo.get("started_at", 0),
                "type": "php",
            })

    return {
        "django_active": len(django_servers),
        "php_active": len(php_servers),
        "total_active": len(django_servers) + len(php_servers),
        "django_servers": django_servers,
        "php_servers": php_servers,
    }


def check_user_server_limit(user_id: str, new_project_id: str, limit: int = MAX_CONCURRENT_SERVERS_PER_USER) -> Tuple[bool, Optional[str]]:
    """
    Ensures a single user does not exceed the allowed concurrent server processes.
    Returns (True, None) if permitted, or (False, error_msg) if quota exceeded.
    """
    if not user_id:
        return True, None

    from .codelab_django import DjangoProcessManager
    from .codelab_php import PhpProcessManager

    # Find all project IDs owned by this user
    user_project_ids = set(
        CodeProject.objects.filter(user__user_id=user_id).values_list("project_id", flat=True)
    )

    active_user_servers = 0
    # Check Django servers
    for pid, sinfo in DjangoProcessManager._servers.items():
        if pid in user_project_ids and pid != new_project_id:
            proc = sinfo.get("process")
            if proc and proc.poll() is None:
                active_user_servers += 1

    # Check PHP servers
    for pid, sinfo in PhpProcessManager._servers.items():
        if pid in user_project_ids and pid != new_project_id:
            proc = sinfo.get("process")
            if proc and proc.poll() is None:
                active_user_servers += 1

    if active_user_servers >= limit:
        return False, (
            f"Active server quota exceeded. You currently have {active_user_servers} "
            f"running servers (maximum allowed: {limit}). Please stop an active server first."
        )

    return True, None


def get_workspace_disk_usage(project_id: str) -> int:
    """Calculates total disk usage in bytes for a project's workspace directory."""
    workspace_dir = get_project_workspace_dir(project_id)
    total_bytes = 0
    if not workspace_dir.exists():
        return 0

    for root, _, files in os.walk(workspace_dir):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_bytes += os.path.getsize(fp)
            except (OSError, FileNotFoundError):
                pass
    return total_bytes


def check_workspace_storage_quota(project_id: str, additional_bytes: int = 0) -> Tuple[bool, int, int]:
    """
    Checks if adding additional_bytes will exceed the workspace storage quota.
    Returns (allowed, current_usage_bytes, max_quota_bytes).
    """
    current_usage = get_workspace_disk_usage(project_id)
    allowed = (current_usage + additional_bytes) <= MAX_WORKSPACE_STORAGE_BYTES
    return allowed, current_usage, MAX_WORKSPACE_STORAGE_BYTES


def cleanup_stale_workspaces_and_processes(max_idle_seconds: int = MAX_SERVER_UPTIME_SECONDS) -> Dict[str, Any]:
    """
    Terminates dead or over-age server processes, cleans orphaned log/temp files,
    and returns a summary of cleaned resources.
    """
    from .codelab_django import DjangoProcessManager
    from .codelab_php import PhpProcessManager

    now = time.time()
    stopped_django = []
    stopped_php = []

    # 1. Inspect Django processes
    with DjangoProcessManager._lock:
        for pid in list(DjangoProcessManager._servers.keys()):
            sinfo = DjangoProcessManager._servers.get(pid, {})
            proc = sinfo.get("process")
            started = sinfo.get("started_at", now)
            # Check if terminated or expired
            if proc is None or proc.poll() is not None:
                DjangoProcessManager.stop(pid)
                stopped_django.append({"project_id": pid, "reason": "process_terminated"})
            elif (now - started) > max_idle_seconds:
                DjangoProcessManager.stop(pid)
                stopped_django.append({"project_id": pid, "reason": "uptime_exceeded"})

    # 2. Inspect PHP processes
    with PhpProcessManager._lock:
        for pid in list(PhpProcessManager._servers.keys()):
            sinfo = PhpProcessManager._servers.get(pid, {})
            proc = sinfo.get("process")
            started = sinfo.get("started_at", now)
            if proc is None or proc.poll() is not None:
                PhpProcessManager.stop(pid)
                stopped_php.append({"project_id": pid, "reason": "process_terminated"})
            elif (now - started) > max_idle_seconds:
                PhpProcessManager.stop(pid)
                stopped_php.append({"project_id": pid, "reason": "uptime_exceeded"})

    # 3. Clean up scratch temporary files in WORKSPACE_BASE_DIR older than 1 day
    deleted_temp_files = 0
    one_day_ago = now - 86400
    if WORKSPACE_BASE_DIR.exists():
        for item in WORKSPACE_BASE_DIR.iterdir():
            if item.is_file() and item.suffix in (".zip", ".tmp", ".log"):
                try:
                    if item.stat().st_mtime < one_day_ago:
                        item.unlink()
                        deleted_temp_files += 1
                except Exception:
                    pass

    return {
        "status": True,
        "stopped_django": stopped_django,
        "stopped_php": stopped_php,
        "deleted_temp_files": deleted_temp_files,
        "timestamp": now,
    }


def get_system_health_report() -> Dict[str, Any]:
    """Generates a complete telemetry and health check status for SkilTrix CodeLab."""
    runtimes = get_runtime_telemetry()
    servers = get_active_servers_summary()

    # Determine execution engine mode
    is_docker = os.path.exists("/.dockerenv") or os.environ.get("CODELAB_EXECUTION_MODE") == "docker"
    sandbox_mode = "docker_rootless_worker" if is_docker else "local_restricted_process"

    # Disk usage of workspaces
    total_workspace_bytes = 0
    if WORKSPACE_BASE_DIR.exists():
        for root, _, files in os.walk(WORKSPACE_BASE_DIR):
            for f in files:
                try:
                    total_workspace_bytes += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass

    return {
        "status": "healthy",
        "service": "SkilTrix CodeLab Engine",
        "version": "1.0.0",
        "platform": sys.platform,
        "sandbox_mode": sandbox_mode,
        "runtimes": runtimes,
        "active_servers": servers,
        "quotas": {
            "max_file_size_bytes": MAX_FILE_SIZE_BYTES,
            "max_file_size_mb": MAX_FILE_SIZE_BYTES // (1024 * 1024),
            "max_workspace_storage_bytes": MAX_WORKSPACE_STORAGE_BYTES,
            "max_workspace_storage_mb": MAX_WORKSPACE_STORAGE_BYTES // (1024 * 1024),
            "max_concurrent_servers_per_user": MAX_CONCURRENT_SERVERS_PER_USER,
            "max_execution_timeout_seconds": MAX_EXECUTION_TIMEOUT_SECONDS,
            "max_server_uptime_seconds": MAX_SERVER_UPTIME_SECONDS,
        },
        "storage": {
            "workspaces_base_dir": str(WORKSPACE_BASE_DIR),
            "total_workspaces_disk_usage_mb": round(total_workspace_bytes / (1024 * 1024), 2),
        },
        "channels": {
            "status": "active",
            "layer": "InMemoryChannelLayer",
            "endpoints": [
                "/ws/codelab/terminal/<project_id>/",
                "/ws/codelab/logs/<project_id>/",
            ]
        }
    }
