"""
SkilTrix CodeLab - PHP Project Execution & Management Service
Handles:
1. Multi-file PHP project runtime execution (built-in PHP web server)
2. Process lifecycle (start, stop, restart, status, logs)
3. SQLite and MySQL database connectivity via PDO
4. HTTP request proxying, sessions, cookies, and live web preview
5. REST API / Form submission testing
"""

import os
import sys
import time
import socket
import subprocess
import threading
import atexit
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from .codelab_runner import get_project_workspace_dir, sync_db_files_to_workspace
from .execution.sandbox_policy import ExecutionPolicy
from .execution.runtimes.php_runtime import find_php_executable
from .codelab_models import CodeProject, WorkspaceSession


def find_free_port(start: int = 9200, end: int = 9999) -> int:
    """Finds an available TCP port for a local PHP server."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


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


class PhpProcessManager:
    """
    Manages background PHP development server processes (php -S 127.0.0.1:<port>).
    """
    _servers: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()

    @classmethod
    def start(cls, project_id: str) -> Dict[str, Any]:
        with cls._lock:
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

            php_bin = find_php_executable()
            if not php_bin:
                return {
                    "status": False,
                    "error": "PHP CLI executable not found on host system."
                }

            workspace_dir = sync_db_files_to_workspace(project)
            index_php = workspace_dir / "index.php"
            if not index_php.exists():
                # Create default index.php if absent
                index_php.write_text("<?php echo '<h1>PHP Workspace Active</h1>'; ?>", encoding="utf-8")

            # Check if already running and responsive
            existing = cls._servers.get(project_id)
            if existing and existing["process"].poll() is None:
                return {
                    "status": True,
                    "server_status": "running",
                    "port": existing["port"],
                    "url": f"/apps/skiltrix/api/preview/{project_id}/",
                    "message": "PHP server is already running.",
                }

            port = find_free_port()
            log_path = workspace_dir / "php_server.log"
            log_file = open(log_path, "w", encoding="utf-8", errors="replace")

            # Sanitized environment
            env = ExecutionPolicy.sanitize_environment()

            # Command: php -S 127.0.0.1:<port> -t <workspace_dir>
            cmd = [
                php_bin,
                "-S", f"127.0.0.1:{port}",
                "-t", str(workspace_dir),
                "-d", "display_errors=1",
                "-d", "error_reporting=E_ALL",
                "-d", "memory_limit=128M"
            ]

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
                return {"status": False, "error": f"Failed to launch PHP process: {str(e)}"}

            # Wait for server port to bind
            ready = wait_for_server_ready(port, timeout=4.0)
            poll_res = proc.poll()
            if poll_res is not None or not ready:
                if poll_res is not None:
                    log_file.close()
                    log_content = tail_file(log_path, 40)
                    return {
                        "status": False,
                        "server_status": "failed",
                        "exit_code": poll_res,
                        "error": "PHP server terminated immediately.",
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
                container_id=f"php_proc_{proc.pid}",
                allocated_port=port,
                preview_url=f"/apps/skiltrix/api/preview/{project_id}/"
            )

            return {
                "status": True,
                "server_status": "running",
                "port": port,
                "url": f"/apps/skiltrix/api/preview/{project_id}/",
                "pid": proc.pid,
                "message": f"PHP server running on port {port}."
            }

    @classmethod
    def stop(cls, project_id: str) -> Dict[str, Any]:
        with cls._lock:
            server_info = cls._servers.pop(project_id, None)
            if not server_info:
                WorkspaceSession.objects.filter(project__project_id=project_id).update(status="stopped")
                return {"status": True, "message": "PHP server was not running."}

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

            try:
                log_f = server_info.get("log_file")
                if log_f and not log_f.closed:
                    log_f.close()
            except Exception:
                pass

            WorkspaceSession.objects.filter(project__project_id=project_id).update(status="stopped")
            return {"status": True, "message": "PHP server stopped."}

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
                workspace_dir = get_project_workspace_dir(project_id)
                log_path = workspace_dir / "php_server.log"
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
        with cls._lock:
            for pid, info in list(cls._servers.items()):
                try:
                    p = info["process"]
                    if p.poll() is None:
                        p.terminate()
                except Exception:
                    pass


# Graceful shutdown handler
atexit.register(PhpProcessManager.stop_all)


def test_php_api_endpoint(
    project_id: str,
    method: str,
    path: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends an HTTP request directly to the running PHP server.
    """
    port = PhpProcessManager.get_server_port(project_id)
    if not port:
        return {
            "status": False,
            "error": "PHP development server is not running. Start the server first."
        }

    clean_path = path if path.startswith("/") else f"/{path}"
    target_url = f"http://127.0.0.1:{port}{clean_path}"

    req_headers = {"User-Agent": "SkilTrix-CodeLab-PhpTester/1.0"}
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
                time.sleep(0.4)
                continue
            return {
                "status": False,
                "error": "Connection refused. PHP server not responding."
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
