import os
import sys
from pathlib import Path
from typing import Dict, Set

class ResourceLimitExceeded(Exception):
    """Raised when execution limits (time, memory, output) are exceeded."""
    pass


class ExecutionPolicy:
    """Security policies and resource quotas for untrusted code execution."""

    # Resource limits
    DEFAULT_TIMEOUT_SECONDS = 10.0
    PRACTICE_TIMEOUT_SECONDS = 5.0
    BUILD_TIMEOUT_SECONDS = 30.0
    MAX_OUTPUT_BYTES = 120_000  # 120 KB max stdout/stderr buffer
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per source file
    MAX_PROCESSES = 64
    MAX_MEMORY_MB = 512

    # Blacklisted environment variable names that must NEVER be passed to user processes
    SENSITIVE_ENV_KEYS: Set[str] = {
        "SESSION_SECRET_KEY",
        "SECRET_KEY",
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_NAME",
        "DB_PORT",
        "EMAIL_HOST_USER",
        "EMAIL_HOST_PASSWORD",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "aws_access_key_id",
        "aws_secret_access_key",
        "endpoint_url",
        "DATABASE_URL",
        "DOCKER_HOST",
        "DOCKER_AUTH",
    }

    # Safe environment variables permitted for execution environments
    SAFE_ENV_PASSTHROUGH: Set[str] = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "TEMP",
        "TMP",
        "LANG",
        "LC_ALL",
        "HOME",
        "USERPROFILE",
    }

    @classmethod
    def sanitize_environment(cls, custom_env: Dict[str, str] = None) -> Dict[str, str]:
        """
        Creates a stripped, secure environment dictionary.
        Prevents leaking host secrets, database passwords, or cloud credentials.
        """
        clean_env = {}
        for key in cls.SAFE_ENV_PASSTHROUGH:
            val = os.environ.get(key)
            if val is not None:
                clean_env[key] = val

        # Ensure Python/Node/Java output unbuffered UTF-8
        clean_env["PYTHONUNBUFFERED"] = "1"
        clean_env["PYTHONIOENCODING"] = "utf-8"
        clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
        clean_env["NODE_ENV"] = "production"

        if custom_env:
            for k, v in custom_env.items():
                if k.upper() not in cls.SENSITIVE_ENV_KEYS and not k.startswith("AWS_"):
                    clean_env[k] = str(v)

        return clean_env

    @classmethod
    def validate_path_safety(cls, base_dir: Path, target_path: Path) -> Path:
        """
        Guarantees target_path strictly resolves within base_dir.
        Blocks path traversal attacks (../../etc/passwd, ..\\windows\\system32).
        """
        try:
            resolved_base = base_dir.resolve()
            resolved_target = target_path.resolve()
            # Must be a subpath of base_dir
            resolved_target.relative_to(resolved_base)
            return resolved_target
        except (ValueError, RuntimeError) as err:
            raise PermissionError(f"Path traversal access violation: {target_path}") from err
