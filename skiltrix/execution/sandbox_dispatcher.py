"""Isolated multi-backend code execution dispatcher for SkilTrix assessments.

Supports three execution backends configured via ``settings.EXECUTION_BACKEND``
or the ``EXECUTION_BACKEND`` environment variable:
- ``docker``: Ephemeral rootless container with ``--network=none``, dropped capabilities,
  read-only root filesystem, PID cap, CPU/memory limits, and wall timeout.
- ``judge0``: Remote/self-hosted Judge0 sandbox API (``JUDGE0_API_URL``).
- ``sandboxed_local``: Ephemeral temp-directory subprocess with sanitized environment,
  compiler-error classification, wall-clock timeout, output truncation, and OS-level
  peak RSS/WorkingSet memory measurement (NEVER runs code inside Django's process).
- ``auto`` (default): Uses Docker when the ``docker`` daemon is reachable, else Judge0
  if ``JUDGE0_API_URL`` is explicitly configured, else ``sandboxed_local`` (falling back
  to configured Judge0 when a required native compiler such as ``gcc``/``g++`` is absent).
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
import requests

from .sandbox_policy import ExecutionPolicy

# Normalize user-facing or legacy language aliases into canonical keys
LANGUAGE_ALIASES: Dict[str, str] = {
    "py": "python",
    "python": "python",
    "python3": "python",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    "javascript": "javascript",
}

LANGUAGE_SPECS: Dict[str, Dict[str, Any]] = {
    "python": {
        "display_name": "Python 3",
        "filename": "main.py",
        "judge0_id": 71,
        "docker_image": "skiltrix-sandbox-python:latest",
    },
    "java": {
        "display_name": "Java",
        "filename": "Main.java",
        "judge0_id": 62,
        "docker_image": "skiltrix-sandbox-java:latest",
    },
    "c": {
        "display_name": "C",
        "filename": "main.c",
        "judge0_id": 50,
        "docker_image": "skiltrix-sandbox-c:latest",
    },
    "cpp": {
        "display_name": "C++",
        "filename": "main.cpp",
        "judge0_id": 54,
        "docker_image": "skiltrix-sandbox-cpp:latest",
    },
    "javascript": {
        "display_name": "JavaScript",
        "filename": "main.js",
        "judge0_id": 63,
        "docker_image": "skiltrix-sandbox-node:latest",
    },
}


@dataclass
class SandboxExecutionResult:
    status: str  # OK | Compilation Error | Runtime Error | Time Limit Exceeded | Memory Limit Exceeded
    stdout: str
    stderr: str
    compile_output: str
    exit_code: Optional[int]
    execution_time_ms: float
    memory_kb: float
    backend_used: str


def canonicalize_language(language: str) -> str:
    key = (language or "").strip().lower()
    if key not in LANGUAGE_ALIASES:
        raise ValueError(f"Unsupported programming language: {language}")
    return LANGUAGE_ALIASES[key]


def _truncate_output(text: str, limit_bytes: int = ExecutionPolicy.MAX_OUTPUT_BYTES) -> str:
    if not text:
        return ""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit_bytes:
        return text
    truncated = encoded[:limit_bytes].decode("utf-8", errors="ignore")
    return truncated + "\n... [output truncated]"


def _docker_available() -> bool:
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False
    try:
        probe = subprocess.run(
            [docker_bin, "info", "--format", "{{.ServerVersion}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2.5,
            check=False,
        )
        return probe.returncode == 0
    except Exception:
        return False


def _measure_windows_peak_working_set_kb(handle: int) -> float:
    """Query PROCESS_MEMORY_COUNTERS.PeakWorkingSetSize via Win32 psapi/kernel32."""
    if os.name != "nt" or not handle:
        return 0.0
    try:
        class _ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        psapi = ctypes.windll.psapi  # type: ignore[attr-defined]
        ok = psapi.GetProcessMemoryInfo(
            ctypes.c_void_p(int(handle)),
            ctypes.byref(counters),
            counters.cb,
        )
        if not ok:
            ok = kernel32.K32GetProcessMemoryInfo(
                ctypes.c_void_p(int(handle)),
                ctypes.byref(counters),
                counters.cb,
            )
        if ok and counters.PeakWorkingSetSize:
            return round(counters.PeakWorkingSetSize / 1024.0, 2)
    except Exception:
        return 0.0
    return 0.0


def _measure_posix_vmhwm_kb(pid: int) -> float:
    if os.name == "nt" or pid <= 0:
        return 0.0
    status_path = f"/proc/{pid}/status"
    try:
        with open(status_path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if line.startswith("VmHWM:") or line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        return float(parts[1])
    except Exception:
        return 0.0
    return 0.0


def _build_preexec_limits(memory_limit_mb: int, timeout_seconds: float):
    """POSIX resource limits applied inside the forked child process."""
    if os.name == "nt":
        return None
    import resource

    def _apply_limits() -> None:
        mem_bytes = max(64, int(memory_limit_mb)) * 1024 * 1024
        cpu_seconds = max(1, int(timeout_seconds) + 1)
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        except Exception:
            pass
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except Exception:
            pass
        try:
            resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
        except Exception:
            pass

    return _apply_limits


def _run_subprocess_monitored(
    cmd: List[str],
    cwd: str,
    stdin_data: str,
    timeout_seconds: float,
    memory_limit_mb: int,
    env: Dict[str, str],
) -> Tuple[Optional[int], str, str, float, float, bool, bool]:
    """Run an external subprocess with timeout & RSS polling.

    Returns ``(returncode, stdout, stderr, elapsed_ms, peak_kb, timed_out, mle)``.
    """
    popen_kwargs: Dict[str, Any] = {
        "cwd": cwd,
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "env": env,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    else:
        popen_kwargs["preexec_fn"] = _build_preexec_limits(memory_limit_mb, timeout_seconds)

    start = time.perf_counter()
    proc = subprocess.Popen(cmd, **popen_kwargs)

    peak_kb = 0.0
    mle_flag = False
    stop_event = threading.Event()
    mem_limit_kb = max(16, int(memory_limit_mb)) * 1024.0

    def _poll_memory() -> None:
        nonlocal peak_kb, mle_flag
        while not stop_event.is_set() and proc.poll() is None:
            rss_kb = (
                _measure_windows_peak_working_set_kb(getattr(proc, "_handle", 0))
                if os.name == "nt"
                else _measure_posix_vmhwm_kb(proc.pid)
            )
            if rss_kb > peak_kb:
                peak_kb = rss_kb
            if rss_kb > mem_limit_kb:
                mle_flag = True
                try:
                    proc.kill()
                except Exception:
                    pass
                break
            stop_event.wait(0.03)

    monitor = threading.Thread(target=_poll_memory, daemon=True)
    monitor.start()

    timed_out = False
    stdout = ""
    stderr = ""
    try:
        stdout, stderr = proc.communicate(input=stdin_data or "", timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            proc.kill()
        except Exception:
            pass
        stdout, stderr = proc.communicate()
    finally:
        # Take one final reading before handle cleanup where possible
        final_rss = (
            _measure_windows_peak_working_set_kb(getattr(proc, "_handle", 0))
            if os.name == "nt"
            else _measure_posix_vmhwm_kb(proc.pid)
        )
        if final_rss > peak_kb:
            peak_kb = final_rss
        stop_event.set()
        monitor.join(timeout=0.5)

    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
    return (
        proc.returncode,
        _truncate_output(stdout),
        _truncate_output(stderr),
        elapsed_ms,
        round(peak_kb, 2),
        timed_out,
        mle_flag,
    )


def _find_binary(name: str, extra_dirs: Optional[List[str]] = None) -> Optional[str]:
    found = shutil.which(name)
    if found:
        return found
    for directory in extra_dirs or []:
        candidate = os.path.join(directory, f"{name}.exe" if os.name == "nt" else name)
        if os.path.isfile(candidate):
            return candidate
    return None


def _execute_local_sandbox(
    language: str,
    source_code: str,
    stdin_data: str,
    timeout_seconds: float,
    memory_limit_mb: int,
) -> SandboxExecutionResult:
    """Compile (if needed) and execute in an ephemeral workspace outside Django."""
    env = ExecutionPolicy.sanitize_environment()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    if os.name == "nt":
        # Preserve minimal runtime library lookup dirs for Windows interpreters/compilers
        for var in ("SystemRoot", "WINDIR", "COMSPEC"):
            if var in os.environ:
                env[var] = os.environ[var]

    with tempfile.TemporaryDirectory(prefix="st_sandbox_") as workdir:
        filename = LANGUAGE_SPECS[language]["filename"]
        source_path = os.path.join(workdir, filename)
        with open(source_path, "w", encoding="utf-8") as handle:
            handle.write(source_code)

        compile_cmd: Optional[List[str]] = None
        run_cmd: List[str]

        if language == "python":
            py_bin = _find_binary("python") or sys.executable
            run_cmd = [py_bin, "-I", "-u", source_path]
        elif language == "javascript":
            node_bin = _find_binary("node")
            if not node_bin:
                raise FileNotFoundError("Node.js runtime not installed on host.")
            run_cmd = [
                node_bin,
                f"--max-old-space-size={max(64, int(memory_limit_mb))}",
                source_path,
            ]
        elif language == "java":
            javac_bin = _find_binary("javac")
            java_bin = _find_binary("java")
            if not javac_bin or not java_bin:
                raise FileNotFoundError("Java JDK (javac/java) not installed on host.")
            compile_cmd = [javac_bin, "-J-Xmx256m", source_path]
            run_cmd = [java_bin, f"-Xmx{max(64, int(memory_limit_mb))}m", "-cp", workdir, "Main"]
        elif language == "c":
            gcc_bin = _find_binary(
                "gcc",
                [r"C:\msys64\mingw64\bin", r"C:\mingw64\bin", r"C:\MinGW\bin"],
            )
            if not gcc_bin:
                raise FileNotFoundError("GCC C compiler (gcc) not installed on host.")
            exe_name = "main.exe" if os.name == "nt" else "main.out"
            exe_path = os.path.join(workdir, exe_name)
            compile_cmd = [gcc_bin, "-O2", "-std=c11", source_path, "-o", exe_path, "-lm"]
            run_cmd = [exe_path]
        elif language == "cpp":
            gpp_bin = _find_binary(
                "g++",
                [r"C:\msys64\mingw64\bin", r"C:\mingw64\bin", r"C:\MinGW\bin"],
            )
            if not gpp_bin:
                raise FileNotFoundError("GCC C++ compiler (g++) not installed on host.")
            exe_name = "main.exe" if os.name == "nt" else "main.out"
            exe_path = os.path.join(workdir, exe_name)
            compile_cmd = [gpp_bin, "-O2", "-std=c++17", source_path, "-o", exe_path]
            run_cmd = [exe_path]
        else:
            raise ValueError(f"Unsupported language: {language}")

        if compile_cmd is not None:
            rc, c_out, c_err, c_ms, _, c_tle, _ = _run_subprocess_monitored(
                compile_cmd,
                workdir,
                "",
                max(10.0, timeout_seconds * 2),
                max(512, int(memory_limit_mb)),
                env,
            )
            if c_tle:
                return SandboxExecutionResult(
                    status="Compilation Error",
                    stdout="",
                    stderr="Compilation timed out.",
                    compile_output=c_err or "Compilation timed out.",
                    exit_code=rc,
                    execution_time_ms=c_ms,
                    memory_kb=0.0,
                    backend_used="sandboxed_local",
                )
            if rc != 0:
                compile_msg = (c_err or c_out or "Compilation failed.").strip()
                return SandboxExecutionResult(
                    status="Compilation Error",
                    stdout="",
                    stderr=compile_msg,
                    compile_output=compile_msg,
                    exit_code=rc,
                    execution_time_ms=c_ms,
                    memory_kb=0.0,
                    backend_used="sandboxed_local",
                )

        rc, out, err, elapsed_ms, peak_kb, timed_out, mle = _run_subprocess_monitored(
            run_cmd,
            workdir,
            stdin_data,
            timeout_seconds,
            memory_limit_mb,
            env,
        )

        if mle:
            return SandboxExecutionResult(
                status="Memory Limit Exceeded",
                stdout=out,
                stderr=err or f"Process exceeded memory limit of {memory_limit_mb} MB.",
                compile_output="",
                exit_code=rc,
                execution_time_ms=elapsed_ms,
                memory_kb=peak_kb,
                backend_used="sandboxed_local",
            )
        if timed_out:
            return SandboxExecutionResult(
                status="Time Limit Exceeded",
                stdout=out,
                stderr=err or f"Execution timed out after {timeout_seconds}s.",
                compile_output="",
                exit_code=rc,
                execution_time_ms=elapsed_ms,
                memory_kb=peak_kb,
                backend_used="sandboxed_local",
            )
        if rc != 0:
            # Classify POSIX SIGKILL/MemoryError or Java OutOfMemoryError cleanly
            err_lower = (err or "").lower()
            if "outofmemoryerror" in err_lower or "memoryerror" in err_lower or rc in (-9, 137):
                return SandboxExecutionResult(
                    status="Memory Limit Exceeded",
                    stdout=out,
                    stderr=err or "Memory Limit Exceeded",
                    compile_output="",
                    exit_code=rc,
                    execution_time_ms=elapsed_ms,
                    memory_kb=peak_kb,
                    backend_used="sandboxed_local",
                )
            return SandboxExecutionResult(
                status="Runtime Error",
                stdout=out,
                stderr=err or f"Exited with status {rc}",
                compile_output="",
                exit_code=rc,
                execution_time_ms=elapsed_ms,
                memory_kb=peak_kb,
                backend_used="sandboxed_local",
            )

        return SandboxExecutionResult(
            status="OK",
            stdout=out,
            stderr=err,
            compile_output="",
            exit_code=0,
            execution_time_ms=elapsed_ms,
            memory_kb=peak_kb,
            backend_used="sandboxed_local",
        )


def _execute_docker_sandbox(
    language: str,
    source_code: str,
    stdin_data: str,
    timeout_seconds: float,
    memory_limit_mb: int,
) -> SandboxExecutionResult:
    """Execute inside an ephemeral rootless Docker container with strict cgroups."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        raise FileNotFoundError("Docker CLI not installed.")

    spec = LANGUAGE_SPECS[language]
    image = spec["docker_image"]
    filename = spec["filename"]
    mem_mb = max(64, int(memory_limit_mb))
    mem_flag = f"{mem_mb}m"

    with tempfile.TemporaryDirectory(prefix="st_docker_") as workdir:
        source_path = os.path.join(workdir, filename)
        with open(source_path, "w", encoding="utf-8") as handle:
            handle.write(source_code)

        # Build compile + run script inside isolated container /tmp directory
        if language == "python":
            inner_cmd = "python -I -u /workspace/main.py"
        elif language == "javascript":
            inner_cmd = f"node --max-old-space-size={mem_mb} /workspace/main.js"
        elif language == "java":
            inner_cmd = (
                "javac -d /tmp /workspace/Main.java 2>/tmp/compile.err || "
                "{ cat /tmp/compile.err >&2; exit 97; }; "
                f"java -Xmx{mem_mb}m -cp /tmp Main"
            )
        elif language == "c":
            inner_cmd = (
                "gcc -O2 -std=c11 /workspace/main.c -o /tmp/a.out -lm 2>/tmp/compile.err || "
                "{ cat /tmp/compile.err >&2; exit 97; }; "
                "/tmp/a.out"
            )
        elif language == "cpp":
            inner_cmd = (
                "g++ -O2 -std=c++17 /workspace/main.cpp -o /tmp/a.out 2>/tmp/compile.err || "
                "{ cat /tmp/compile.err >&2; exit 97; }; "
                "/tmp/a.out"
            )
        else:
            raise ValueError(f"Unsupported language: {language}")

        cmd = [
            docker_bin,
            "run",
            "--rm",
            "-i",
            "--network=none",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,exec,nosuid,size=64m",
            "--pids-limit=64",
            "--cpus=1.0",
            f"--memory={mem_flag}",
            f"--memory-swap={mem_flag}",
            "-v",
            f"{os.path.abspath(workdir)}:/workspace:ro",
            "--entrypoint",
            "/bin/sh",
            image,
            "-c",
            inner_cmd,
        ]

        start = time.perf_counter()
        timed_out = False
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_data or "",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds + 2.0,
                check=False,
            )
            rc = proc.returncode
            out = _truncate_output(proc.stdout)
            err = _truncate_output(proc.stderr)
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            rc = None
            out = _truncate_output((exc.stdout or "") if isinstance(exc.stdout, str) else "")
            err = _truncate_output((exc.stderr or "") if isinstance(exc.stderr, str) else "")

        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
        if timed_out:
            return SandboxExecutionResult(
                status="Time Limit Exceeded",
                stdout=out,
                stderr=err or f"Container timed out after {timeout_seconds}s.",
                compile_output="",
                exit_code=None,
                execution_time_ms=elapsed_ms,
                memory_kb=0.0,
                backend_used="docker",
            )
        if rc == 97:
            return SandboxExecutionResult(
                status="Compilation Error",
                stdout="",
                stderr=err,
                compile_output=err,
                exit_code=rc,
                execution_time_ms=elapsed_ms,
                memory_kb=0.0,
                backend_used="docker",
            )
        if rc == 137:
            return SandboxExecutionResult(
                status="Memory Limit Exceeded",
                stdout=out,
                stderr=err or "Container killed (OOM / Memory Limit Exceeded).",
                compile_output="",
                exit_code=rc,
                execution_time_ms=elapsed_ms,
                memory_kb=float(mem_mb * 1024),
                backend_used="docker",
            )
        if rc != 0:
            return SandboxExecutionResult(
                status="Runtime Error",
                stdout=out,
                stderr=err or f"Exited with status {rc}",
                compile_output="",
                exit_code=rc,
                execution_time_ms=elapsed_ms,
                memory_kb=0.0,
                backend_used="docker",
            )

        return SandboxExecutionResult(
            status="OK",
            stdout=out,
            stderr=err,
            compile_output="",
            exit_code=0,
            execution_time_ms=elapsed_ms,
            memory_kb=0.0,
            backend_used="docker",
        )


def _execute_judge0_sandbox(
    language: str,
    source_code: str,
    stdin_data: str,
    timeout_seconds: float,
    memory_limit_mb: int,
) -> SandboxExecutionResult:
    """Execute via configured Judge0 API (self-hosted or CE worker)."""
    base_url = (
        getattr(settings, "JUDGE0_API_URL", None)
        or os.environ.get("JUDGE0_API_URL")
        or "https://ce.judge0.com"
    ).rstrip("/")
    api_key = getattr(settings, "JUDGE0_API_KEY", None) or os.environ.get("JUDGE0_API_KEY")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Auth-Token"] = api_key
        headers["X-RapidAPI-Key"] = api_key

    language_id = LANGUAGE_SPECS[language]["judge0_id"]
    payload = {
        "source_code": source_code,
        "language_id": language_id,
        "stdin": stdin_data or "",
        "cpu_time_limit": max(1.0, float(timeout_seconds)),
        "wall_time_limit": max(2.0, float(timeout_seconds) + 2.0),
        "memory_limit": max(32768, int(memory_limit_mb) * 1024),
    }

    resp = requests.post(
        f"{base_url}/submissions?base64_encoded=false&wait=true",
        json=payload,
        headers=headers,
        timeout=max(15.0, float(timeout_seconds) + 10.0),
    )
    resp.raise_for_status()
    data = resp.json()

    status_id = int((data.get("status") or {}).get("id") or 0)
    status_desc = (data.get("status") or {}).get("description") or ""
    stdout = _truncate_output(data.get("stdout") or "")
    stderr = _truncate_output(data.get("stderr") or "")
    compile_out = _truncate_output(data.get("compile_output") or "")
    exec_ms = round(float(data.get("time") or 0.0) * 1000.0, 2)
    memory_kb = float(data.get("memory") or 0.0)

    if status_id == 6:
        mapped_status = "Compilation Error"
    elif status_id == 5:
        mapped_status = "Time Limit Exceeded"
    elif memory_kb > float(memory_limit_mb) * 1024.0 or "memory" in status_desc.lower():
        mapped_status = "Memory Limit Exceeded"
    elif status_id in (7, 8, 9, 10, 11, 12, 13, 14):
        mapped_status = "Runtime Error"
    else:
        mapped_status = "OK"

    return SandboxExecutionResult(
        status=mapped_status,
        stdout=stdout,
        stderr=stderr or (status_desc if mapped_status != "OK" and not compile_out else ""),
        compile_output=compile_out,
        exit_code=data.get("exit_code"),
        execution_time_ms=exec_ms,
        memory_kb=memory_kb,
        backend_used="judge0",
    )


def execute_in_sandbox(
    language: str,
    source_code: str,
    stdin_data: str = "",
    timeout_seconds: float = 2.0,
    memory_limit_mb: int = 256,
) -> SandboxExecutionResult:
    """Dispatch code execution cleanly using the configured sandbox backend."""
    canonical = canonicalize_language(language)
    backend = (
        getattr(settings, "EXECUTION_BACKEND", None)
        or os.environ.get("EXECUTION_BACKEND")
        or "auto"
    ).strip().lower()

    if backend == "docker":
        return _execute_docker_sandbox(
            canonical, source_code, stdin_data, timeout_seconds, memory_limit_mb
        )
    if backend == "judge0":
        return _execute_judge0_sandbox(
            canonical, source_code, stdin_data, timeout_seconds, memory_limit_mb
        )

    if backend == "auto":
        if _docker_available():
            try:
                return _execute_docker_sandbox(
                    canonical, source_code, stdin_data, timeout_seconds, memory_limit_mb
                )
            except Exception:
                pass
        configured_judge0 = getattr(settings, "JUDGE0_API_URL", None) or os.environ.get(
            "JUDGE0_API_URL"
        )
        if configured_judge0:
            try:
                return _execute_judge0_sandbox(
                    canonical, source_code, stdin_data, timeout_seconds, memory_limit_mb
                )
            except Exception:
                pass

    try:
        return _execute_local_sandbox(
            canonical, source_code, stdin_data, timeout_seconds, memory_limit_mb
        )
    except FileNotFoundError as missing_exc:
        allow_fallback = getattr(settings, "ALLOW_JUDGE0_FALLBACK", True)
        if allow_fallback:
            try:
                return _execute_judge0_sandbox(
                    canonical, source_code, stdin_data, timeout_seconds, memory_limit_mb
                )
            except Exception as j0_exc:
                return SandboxExecutionResult(
                    status="Runtime Error",
                    stdout="",
                    stderr=f"{missing_exc} (Judge0 fallback unavailable: {j0_exc})",
                    compile_output="",
                    exit_code=None,
                    execution_time_ms=0.0,
                    memory_kb=0.0,
                    backend_used="unavailable",
                )
        return SandboxExecutionResult(
            status="Runtime Error",
            stdout="",
            stderr=str(missing_exc),
            compile_output="",
            exit_code=None,
            execution_time_ms=0.0,
            memory_kb=0.0,
            backend_used="unavailable",
        )
