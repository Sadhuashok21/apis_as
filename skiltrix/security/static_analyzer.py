"""
SkilTrix Universal Security Firewall - Language-Aware Static Code Analyzer
Inspects source code for Python, JavaScript/TypeScript, Java, PHP, C/C++, and ABAP
to detect dangerous OS operations, unauthorized subprocess spawning, network attempts,
path traversal, reflection obfuscation, and destructive file actions.
"""

import ast
import re
from typing import Dict, Any, List, Optional, Tuple

from .policies import (
    SecurityPolicyViolation,
    RULE_DANGEROUS_FILESYSTEM,
    RULE_PATH_TRAVERSAL,
    RULE_UNAUTHORIZED_SUBPROCESS,
    RULE_NETWORK_VIOLATION,
    RULE_REFLECTION_OBFUSCATION,
    RULE_ABAP_VIOLATION,
)


# Common root wipe / dangerous path patterns in string literals
DANGEROUS_PATH_PATTERNS = [
    re.compile(r'^\s*([a-zA-Z]:[/\\]|\.{2}[/\\]|[/\\](?:etc|root|windows|boot|sys|var|proc|bin|sbin)\b)', re.IGNORECASE),
    re.compile(r'^[/\\]+$'),  # '/' or '\' alone
    re.compile(r'^[a-zA-Z]:[/\\]*$', re.IGNORECASE),  # 'C:/' or 'C:\' alone
]


def is_dangerous_target_path(path_str: str) -> bool:
    """Checks if a string represents root, drive root, parent traversal, or host system folder."""
    clean = path_str.strip().strip("'\"")
    if not clean:
        return False
    if clean in ("/", "\\", "C:", "C:/", "C:\\", "c:", "c:/", "c:\\"):
        return True
    if clean.startswith("../") or clean.startswith("..\\") or "/../" in clean or "\\..\\" in clean:
        return True
    for pat in DANGEROUS_PATH_PATTERNS:
        if pat.search(clean):
            return True
    return False


class PythonSecurityVisitor(ast.NodeVisitor):
    """
    AST Visitor analyzing Python code for:
    - Dangerous OS/filesystem operations (os.remove, os.rmdir, shutil.rmtree)
    - Unauthorized subprocess execution (subprocess, os.system, os.popen)
    - Network socket / HTTP requests (socket, urllib, requests)
    - Path traversal in string arguments
    - Obfuscated reflection attempts (__import__, getattr on builtins/os)
    """

    def __init__(self):
        self.violations: List[Tuple[str, str, int]] = []
        self.imported_modules: set = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name.split(".")[0]
            self.imported_modules.add(name)
            if name in ("subprocess", "pty", "winreg", "posix", "nt"):
                self.violations.append((
                    RULE_UNAUTHORIZED_SUBPROCESS,
                    f"Direct import of unauthorized process module '{name}' is forbidden.",
                    node.lineno,
                ))
            elif name in ("socket", "urllib", "requests", "http", "ftplib", "telnetlib", "smtplib"):
                self.violations.append((
                    RULE_NETWORK_VIOLATION,
                    f"Unauthorized network module import '{name}' is blocked by sandbox policy.",
                    node.lineno,
                ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        root_mod = mod.split(".")[0]
        self.imported_modules.add(root_mod)

        if root_mod in ("subprocess", "pty", "winreg"):
            self.violations.append((
                RULE_UNAUTHORIZED_SUBPROCESS,
                f"Unauthorized import from process module '{mod}' is forbidden.",
                node.lineno,
            ))
        elif root_mod in ("socket", "urllib", "requests", "http", "ftplib"):
            self.violations.append((
                RULE_NETWORK_VIOLATION,
                f"Unauthorized import from network module '{mod}' is forbidden.",
                node.lineno,
            ))
        elif root_mod == "shutil":
            for alias in node.names:
                if alias.name in ("rmtree", "move"):
                    # We will inspect call arguments, but mark module
                    pass
        elif root_mod == "os":
            for alias in node.names:
                if alias.name in ("system", "popen", "spawn", "execl", "execv"):
                    self.violations.append((
                        RULE_UNAUTHORIZED_SUBPROCESS,
                        f"Unauthorized process execution function 'os.{alias.name}' is forbidden.",
                        node.lineno,
                    ))

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = self._resolve_call_name(node.func)

        # 1. Process / Shell execution
        if func_name in (
            "os.system", "os.popen", "os.spawnl", "os.spawnv", "os.spawnle", "os.spawnve",
            "subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_call",
            "subprocess.check_output", "pty.spawn",
        ):
            self.violations.append((
                RULE_UNAUTHORIZED_SUBPROCESS,
                f"Unauthorized subprocess call '{func_name}' is forbidden.",
                node.lineno,
            ))

        # 2. Network calls
        elif func_name in (
            "socket.socket", "socket.connect", "socket.create_connection",
            "requests.get", "requests.post", "requests.put", "requests.delete", "requests.request",
            "urllib.request.urlopen", "http.client.HTTPConnection", "http.client.HTTPSConnection",
        ):
            self.violations.append((
                RULE_NETWORK_VIOLATION,
                f"Unauthorized outbound network request '{func_name}' is forbidden.",
                node.lineno,
            ))

        # 3. Dynamic reflection / obfuscation
        elif func_name in ("eval", "exec", "__import__"):
            # Check arguments for os, subprocess, or dangerous calls
            arg_str = self._extract_first_arg_str(node)
            if arg_str and any(b in arg_str.lower() for b in ("os", "subprocess", "system", "shutil", "socket", "rmtree")):
                self.violations.append((
                    RULE_REFLECTION_OBFUSCATION,
                    f"Dynamic execution / import of restricted primitive '{arg_str}' is forbidden.",
                    node.lineno,
                ))

        # 4. Destructive filesystem operations
        elif func_name in (
            "os.remove", "os.unlink", "os.rmdir", "os.removedirs",
            "shutil.rmtree", "pathlib.Path.unlink", "pathlib.Path.rmdir",
        ):
            arg_str = self._extract_first_arg_str(node)
            if arg_str and is_dangerous_target_path(arg_str):
                self.violations.append((
                    RULE_DANGEROUS_FILESYSTEM,
                    f"Destructive filesystem operation '{func_name}' on protected target '{arg_str}' is forbidden.",
                    node.lineno,
                ))
            elif not arg_str and func_name == "shutil.rmtree":
                # shutil.rmtree with dynamic target is high risk
                self.violations.append((
                    RULE_DANGEROUS_FILESYSTEM,
                    f"Destructive recursive deletion via '{func_name}' is blocked by sandbox policy.",
                    node.lineno,
                ))

        # Check for path traversal in open() or Path()
        if func_name in ("open", "Path", "pathlib.Path"):
            arg_str = self._extract_first_arg_str(node)
            if arg_str and is_dangerous_target_path(arg_str):
                self.violations.append((
                    RULE_PATH_TRAVERSAL,
                    f"Path traversal or host path access in '{func_name}' ('{arg_str}') is forbidden.",
                    node.lineno,
                ))

        self.generic_visit(node)

    def _resolve_call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._resolve_call_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return ""

    def _extract_first_arg_str(self, call_node: ast.Call) -> Optional[str]:
        if call_node.args:
            first = call_node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                return first.value
        return None


class StaticCodeAnalyzer:
    """Central static code analysis coordinator across all supported languages."""

    @classmethod
    def analyze_python(cls, code: str) -> None:
        """Parses Python AST and verifies security policy."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Let standard Python compiler handle user syntax errors
            return

        visitor = PythonSecurityVisitor()
        visitor.visit(tree)

        if visitor.violations:
            rule, msg, lineno = visitor.violations[0]
            raise SecurityPolicyViolation(
                message=f"Line {lineno}: {msg}",
                rule_triggered=rule,
                language="python",
                entry_point="static_analyzer",
                details={"line": lineno, "rule": rule},
            )

    @classmethod
    def analyze_javascript(cls, code: str) -> None:
        """Analyzes JS/TS code for dangerous Node/OS primitives."""
        # Check for child_process
        if re.search(r'require\s*\(\s*[\'"]child_process[\'"]\s*\)|from\s+[\'"]child_process[\'"]', code):
            raise SecurityPolicyViolation(
                message="Unauthorized process module 'child_process' is forbidden.",
                rule_triggered=RULE_UNAUTHORIZED_SUBPROCESS,
                language="javascript",
                entry_point="static_analyzer",
            )

        # Check for destructive fs operations targeting root/parent
        rm_match = re.search(r'(?:require\s*\(\s*[\'"]fs[\'"]\s*\)\s*\.|fs\.)\s*(?:rmSync|rmdirSync|unlinkSync|promises\.rm(?:dir)?|rm(?:dir)?|unlink)\s*\(\s*([\'"][^\'"]+[\'"])', code)
        if rm_match:
            path_target = rm_match.group(1).strip("'\"")
            if is_dangerous_target_path(path_target):
                raise SecurityPolicyViolation(
                    message=f"Destructive file operation on protected path '{path_target}' is forbidden.",
                    rule_triggered=RULE_DANGEROUS_FILESYSTEM,
                    language="javascript",
                    entry_point="static_analyzer",
                )

        # Check process.exit / process.kill
        if re.search(r'\bprocess\.(?:exit|kill)\s*\(', code):
            raise SecurityPolicyViolation(
                message="Invoking process termination 'process.exit/kill' is blocked by security policy.",
                rule_triggered=RULE_UNAUTHORIZED_SUBPROCESS,
                language="javascript",
                entry_point="static_analyzer",
            )

        # Check socket primitives
        if re.search(r'require\s*\(\s*[\'"](?:net|dgram|dns)[\'"]\s*\)', code):
            raise SecurityPolicyViolation(
                message="Unauthorized low-level network module is blocked by security policy.",
                rule_triggered=RULE_NETWORK_VIOLATION,
                language="javascript",
                entry_point="static_analyzer",
            )

    @classmethod
    def analyze_java(cls, code: str) -> None:
        """Analyzes Java code for process spawning and dangerous file wiping."""
        if re.search(r'Runtime\.getRuntime\(\)\.exec\s*\(|ProcessBuilder\b', code):
            raise SecurityPolicyViolation(
                message="Unauthorized process invocation (Runtime.exec / ProcessBuilder) is forbidden.",
                rule_triggered=RULE_UNAUTHORIZED_SUBPROCESS,
                language="java",
                entry_point="static_analyzer",
            )

        if re.search(r'System\.exit\s*\(', code):
            raise SecurityPolicyViolation(
                message="JVM termination call 'System.exit' is blocked by sandbox policy.",
                rule_triggered=RULE_UNAUTHORIZED_SUBPROCESS,
                language="java",
                entry_point="static_analyzer",
            )

        if re.search(r'Files\.(?:delete|deleteIfExists|walkFileTree)\b', code):
            if any(p in code for p in ("C:/", "C:\\", "../", "/etc", "/root", "/var", "/windows")):
                raise SecurityPolicyViolation(
                    message="Destructive file operation targeting protected host path is forbidden.",
                    rule_triggered=RULE_DANGEROUS_FILESYSTEM,
                    language="java",
                    entry_point="static_analyzer",
                )

        if re.search(r'java\.net\.(?:Socket|ServerSocket|URL|HttpURLConnection)\b', code):
            raise SecurityPolicyViolation(
                message="Direct network socket creation is blocked by sandbox policy.",
                rule_triggered=RULE_NETWORK_VIOLATION,
                language="java",
                entry_point="static_analyzer",
            )

    @classmethod
    def analyze_php(cls, code: str) -> None:
        """Analyzes PHP code for shell execution and dangerous file calls."""
        # Dangerous execution functions
        shell_match = re.search(r'\b(exec|shell_exec|system|passthru|proc_open|popen)\s*\(', code, re.IGNORECASE)
        if shell_match:
            func = shell_match.group(1)
            raise SecurityPolicyViolation(
                message=f"Unauthorized OS shell execution function '{func}()' is forbidden in PHP environment.",
                rule_triggered=RULE_UNAUTHORIZED_SUBPROCESS,
                language="php",
                entry_point="static_analyzer",
            )

        # Destructive file unlinking on root or traversal
        unlink_match = re.search(r'\b(unlink|rmdir)\s*\(\s*([\'"][^\'"]+[\'"])', code, re.IGNORECASE)
        if unlink_match:
            target = unlink_match.group(2).strip("'\"")
            if is_dangerous_target_path(target):
                raise SecurityPolicyViolation(
                    message=f"Destructive file operation on protected path '{target}' is forbidden.",
                    rule_triggered=RULE_DANGEROUS_FILESYSTEM,
                    language="php",
                    entry_point="static_analyzer",
                )

        # Sockets
        if re.search(r'\b(fsockopen|pfsockopen|curl_init|curl_exec)\s*\(', code, re.IGNORECASE):
            raise SecurityPolicyViolation(
                message="Unauthorized network socket / curl connection is forbidden in PHP sandbox.",
                rule_triggered=RULE_NETWORK_VIOLATION,
                language="php",
                entry_point="static_analyzer",
            )

    @classmethod
    def analyze_cpp(cls, code: str) -> None:
        """Analyzes C/C++ code for system() calls and process spawning."""
        if re.search(r'\b(system|popen|fork|execl|execv|execvp|execve)\s*\(', code):
            raise SecurityPolicyViolation(
                message="Unauthorized process invocation (system/popen/fork/exec) is forbidden in C/C++.",
                rule_triggered=RULE_UNAUTHORIZED_SUBPROCESS,
                language="cpp",
                entry_point="static_analyzer",
            )

        # Destructive file remove on root
        rm_match = re.search(r'\b(remove|unlink|rmdir)\s*\(\s*([\'"][^\'"]+[\'"])', code)
        if rm_match:
            target = rm_match.group(2).strip("'\"")
            if is_dangerous_target_path(target):
                raise SecurityPolicyViolation(
                    message=f"Destructive file deletion on protected path '{target}' is forbidden.",
                    rule_triggered=RULE_DANGEROUS_FILESYSTEM,
                    language="cpp",
                    entry_point="static_analyzer",
                )

        if re.search(r'#include\s*<sys/socket\.h>|#include\s*<winsock2\.h>', code):
            raise SecurityPolicyViolation(
                message="Network socket header inclusions are forbidden in sandboxed C/C++.",
                rule_triggered=RULE_NETWORK_VIOLATION,
                language="cpp",
                entry_point="static_analyzer",
            )

    @classmethod
    def analyze_abap(cls, code: str) -> None:
        """Analyzes ABAP source code for unauthorized OS execution and dataset manipulations."""
        upper = code.upper()

        # CALL 'SYSTEM'
        if re.search(r"CALL\s+['\"]SYSTEM['\"]", upper):
            raise SecurityPolicyViolation(
                message="Unauthorized operating system command execution (CALL 'SYSTEM') is forbidden in ABAP.",
                rule_triggered=RULE_ABAP_VIOLATION,
                language="abap",
                entry_point="static_analyzer",
            )

        # SUBMIT ... VIA JOB
        if re.search(r"SUBMIT\s+[a-zA-Z0-9_/]+\s+VIA\s+JOB", upper):
            raise SecurityPolicyViolation(
                message="Unauthorized background job submission (SUBMIT ... VIA JOB) is restricted.",
                rule_triggered=RULE_ABAP_VIOLATION,
                language="abap",
                entry_point="static_analyzer",
            )

        # DELETE DATASET / OPEN DATASET on sensitive paths
        if re.search(r"DELETE\s+DATASET\b", upper):
            raise SecurityPolicyViolation(
                message="Destructive dataset deletion (DELETE DATASET) is forbidden in ABAP simulator.",
                rule_triggered=RULE_DANGEROUS_FILESYSTEM,
                language="abap",
                entry_point="static_analyzer",
            )

    @classmethod
    def analyze(cls, language: str, code: str) -> None:
        """Dispatches code analysis based on language identifier."""
        if not code or not code.strip():
            return

        lang = language.lower().strip()
        if lang in ("python", "py", "python3"):
            cls.analyze_python(code)
        elif lang in ("javascript", "js", "node", "nodejs", "typescript", "ts"):
            cls.analyze_javascript(code)
        elif lang in ("java",):
            cls.analyze_java(code)
        elif lang in ("php",):
            cls.analyze_php(code)
        elif lang in ("cpp", "c++", "c"):
            cls.analyze_cpp(code)
        elif lang in ("abap",):
            cls.analyze_abap(code)
