"""
SkilTrix Universal Security Firewall - Terminal & Shell Execution Firewall
Validates and confines terminal commands to prevent arbitrary shell breakouts,
administrative tool execution, command chaining injection, and path traversal.
"""

import re
import shlex
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .policies import (
    SecurityPolicyViolation,
    RULE_TERMINAL_VIOLATION,
    RULE_UNAUTHORIZED_SUBPROCESS,
    RULE_PATH_TRAVERSAL,
    RULE_DANGEROUS_FILESYSTEM,
)

# Prohibited administrative and dangerous tools
DANGEROUS_BINARIES = {
    "powershell", "powershell.exe", "pwsh", "pwsh.exe",
    "cmd", "cmd.exe", "bash", "sh", "zsh", "wscript", "cscript",
    "reg", "reg.exe", "regedit", "regedit.exe",
    "net", "net.exe", "net1", "net1.exe",
    "sc", "sc.exe", "taskkill", "taskkill.exe", "tasklist", "tasklist.exe",
    "rundll32", "rundll32.exe", "certutil", "certutil.exe", "bitsadmin",
    "attrib", "format", "format.exe", "chkdsk", "bcdedit", "shutdown",
    "curl", "curl.exe", "wget", "nc", "ncat", "netcat", "ssh", "telnet", "ftp",
    "sudo", "su", "chmod", "chown",
}

# Permitted base command tokens
ALLOWED_BASE_COMMANDS = {
    "python", "python3", "py",
    "manage.py", "makemigrations", "migrate", "showmigrations", "sqlmigrate",
    "ls", "dir", "pwd", "cd", "cat", "type", "head", "tail", "echo",
    "clear", "cls", "help", "whoami",
}

# Django management commands allowed
ALLOWED_DJANGO_ACTIONS = {
    "runserver", "check", "makemigrations", "migrate", "showmigrations",
    "sqlmigrate", "startapp", "test", "help", "collectstatic", "version",
}


class TerminalSecurityFirewall:
    """
    Validates terminal commands against an authorized whitelist specification,
    blocking shell meta-characters, subprocess breakouts, and parent traversal.
    """

    @classmethod
    def validate_command(cls, raw_command: str, workspace_dir: Path) -> List[str]:
        """
        Parses and validates the command string.
        Returns parsed list of argument tokens if safe.
        Raises SecurityPolicyViolation if unsafe.
        """
        cmd = raw_command.strip()
        if not cmd:
            return []

        # 1. Block command injection operators and shell chaining: &&, ;, ||, |, `, $(), >
        # Note: We permit simple string echo or standard flags, but block command chaining
        if re.search(r'([;&|`]|&&|\|\||\$\(|\b0x[0-9a-fA-F]+\b)', cmd):
            raise SecurityPolicyViolation(
                message="Command chaining, shell redirection, and backtick injection are forbidden.",
                rule_triggered=RULE_TERMINAL_VIOLATION,
                language="shell",
                entry_point="terminal",
            )

        # 2. Block path traversal in raw command string
        if "../" in cmd or "..\\" in cmd or "/.." in cmd or "\\.." in cmd:
            raise SecurityPolicyViolation(
                message="Directory traversal ('../') is forbidden in terminal commands.",
                rule_triggered=RULE_PATH_TRAVERSAL,
                language="shell",
                entry_point="terminal",
            )

        # 3. Tokenize command safely
        try:
            tokens = shlex.split(cmd, posix=False)
        except Exception:
            # Fallback simple split if shlex fails on Windows quotes
            tokens = cmd.split()

        if not tokens:
            return []

        base_cmd = tokens[0].lower().replace('"', '').replace("'", "")
        # Strip Windows .exe suffix for comparison
        base_name = base_cmd.split("\\")[-1].split("/")[-1].lower()
        if base_name.endswith(".exe"):
            base_name = base_name[:-4]

        # 4. Check against prohibited administrative utilities
        if base_name in DANGEROUS_BINARIES or base_cmd in DANGEROUS_BINARIES:
            raise SecurityPolicyViolation(
                message=f"Direct invocation of administrative utility '{base_name}' is forbidden.",
                rule_triggered=RULE_UNAUTHORIZED_SUBPROCESS,
                language="shell",
                entry_point="terminal",
                details={"binary": base_name},
            )

        # 5. Check destructive file deletions on system roots (rmdir /s /q C:, rm -rf /, etc.)
        if base_name in ("rmdir", "del", "erase", "rm"):
            # Check targets
            for t in tokens[1:]:
                clean_t = t.strip("'\"")
                if clean_t in ("/", "\\", "c:", "c:/", "c:\\", "C:", "C:/", "C:\\", "*", "*.*"):
                    raise SecurityPolicyViolation(
                        message=f"Destructive deletion on root path '{clean_t}' is strictly blocked.",
                        rule_triggered=RULE_DANGEROUS_FILESYSTEM,
                        language="shell",
                        entry_point="terminal",
                    )
                if clean_t.startswith("..") or is_dangerous_target(clean_t, workspace_dir):
                    raise SecurityPolicyViolation(
                        message=f"Destructive deletion outside project workspace '{clean_t}' is forbidden.",
                        rule_triggered=RULE_DANGEROUS_FILESYSTEM,
                        language="shell",
                        entry_point="terminal",
                    )

        # 6. Check base command against allowed specification
        if base_name not in ALLOWED_BASE_COMMANDS and base_cmd not in ALLOWED_BASE_COMMANDS:
            # Check if executing a local project script (e.g. ./manage.py or python script)
            if base_cmd.startswith("./") or base_cmd.startswith(".\\"):
                sub_target = base_cmd[2:]
                if sub_target not in ("manage.py",):
                    raise SecurityPolicyViolation(
                        message=f"Command '{tokens[0]}' is not permitted in sandbox.",
                        rule_triggered=RULE_TERMINAL_VIOLATION,
                        language="shell",
                        entry_point="terminal",
                    )
            else:
                raise SecurityPolicyViolation(
                    message=f"Command '{tokens[0]}' is not in the authorized terminal command whitelist.",
                    rule_triggered=RULE_TERMINAL_VIOLATION,
                    language="shell",
                    entry_point="terminal",
                    details={"command": tokens[0]},
                )

        # 7. Deep validation for Python invocations
        if base_name in ("python", "python3", "py"):
            cls._validate_python_invocation(tokens, workspace_dir)

        # 8. Deep validation for directory changing (cd)
        if base_name == "cd":
            if len(tokens) > 1:
                target_rel = tokens[1].strip("'\"")
                target_path = (workspace_dir / target_rel).resolve()
                try:
                    target_path.relative_to(workspace_dir.resolve())
                except ValueError:
                    raise SecurityPolicyViolation(
                        message="Cannot navigate outside the project workspace directory.",
                        rule_triggered=RULE_PATH_TRAVERSAL,
                        language="shell",
                        entry_point="terminal",
                    )

        return tokens

    @classmethod
    def _validate_python_invocation(cls, tokens: List[str], workspace_dir: Path) -> None:
        """Validates arguments passed to python."""
        if len(tokens) == 1:
            return

        second = tokens[1]
        # Python flags
        if second in ("-V", "--version", "-h", "--help"):
            return

        # python -c <code>
        if second == "-c":
            if len(tokens) < 3:
                raise SecurityPolicyViolation(
                    message="Incomplete python -c invocation.",
                    rule_triggered=RULE_TERMINAL_VIOLATION,
                    language="python",
                    entry_point="terminal",
                )
            inline_code = " ".join(tokens[2:]).strip()
            if (inline_code.startswith('"') and inline_code.endswith('"')) or (inline_code.startswith("'") and inline_code.endswith("'")):
                inline_code = inline_code[1:-1]
            from .static_analyzer import StaticCodeAnalyzer
            StaticCodeAnalyzer.analyze_python(inline_code)
            return

        # python -m <module>
        if second == "-m":
            if len(tokens) < 3:
                raise SecurityPolicyViolation(
                    message="Incomplete python -m command specification.",
                    rule_triggered=RULE_TERMINAL_VIOLATION,
                    language="python",
                    entry_point="terminal",
                )
            mod = tokens[2].lower()
            if mod not in ("venv", "pip"):
                raise SecurityPolicyViolation(
                    message=f"Module invocation 'python -m {mod}' is not authorized.",
                    rule_triggered=RULE_UNAUTHORIZED_SUBPROCESS,
                    language="python",
                    entry_point="terminal",
                )
            return

        # python manage.py <action>
        if second.lower().endswith("manage.py"):
            if len(tokens) > 2:
                action = tokens[2].lower()
                if action not in ALLOWED_DJANGO_ACTIONS:
                    raise SecurityPolicyViolation(
                        message=f"Django management action '{action}' is not in the authorized action list.",
                        rule_triggered=RULE_TERMINAL_VIOLATION,
                        language="django",
                        entry_point="terminal",
                    )
            return

        # python <script.py>
        target_script = (workspace_dir / second).resolve()
        try:
            target_script.relative_to(workspace_dir.resolve())
        except ValueError:
            raise SecurityPolicyViolation(
                message=f"Executing scripts outside workspace '{second}' is forbidden.",
                rule_triggered=RULE_PATH_TRAVERSAL,
                language="python",
                entry_point="terminal",
            )


def is_dangerous_target(target: str, workspace_dir: Path) -> bool:
    try:
        resolved = (workspace_dir / target).resolve()
        resolved.relative_to(workspace_dir.resolve())
        return False
    except Exception:
        return True

