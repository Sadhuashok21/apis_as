"""
SkilTrix CodeLab - Django Channels WebSocket Consumers
Provides:
1. CodeLabTerminalConsumer: Bidirectional xterm.js terminal sessions with workspace execution.
2. CodeLabLogStreamConsumer: Real-time server log streaming over WebSockets.
"""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from .codelab_runner import get_project_workspace_dir
from .codelab_models import CodeProject
from .execution.sandbox_policy import ExecutionPolicy


class CodeLabTerminalConsumer(AsyncJsonWebsocketConsumer):
    """
    Bidirectional WebSocket consumer for xterm.js browser terminal.
    Interacts with the project's sandboxed workspace.
    """
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs'].get('project_id')
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not await self._owns_project(user, self.project_id):
            await self.close(code=4404)
            return
        self.workspace_dir = await self._get_workspace_dir(self.project_id)
        self.current_dir = self.workspace_dir
        self.input_buffer = ""

        await self.accept()

        banner = (
            "\r\n\x1b[1;36m=== SkilTrix CodeLab Cloud Terminal ===\x1b[0m\r\n"
            "\x1b[90mConnected to workspace session. Type standard commands or 'help'.\x1b[0m\r\n"
            f"\x1b[32mworkspace:\x1b[0m {self.project_id}\r\n\r\n$ "
        )
        await self.send_json({
            "type": "output",
            "data": banner
        })

    @database_sync_to_async
    def _owns_project(self, user, project_id):
        return CodeProject.objects.filter(project_id=project_id, user=user).exists()

    @database_sync_to_async
    def _get_workspace_dir(self, project_id):
        return get_project_workspace_dir(project_id)

    async def disconnect(self, close_code):
        pass

    async def receive_json(self, content, **kwargs):
        action = content.get("action", "")
        data = content.get("data", "")
        cmd_text = content.get("command", "")

        if action == "resize":
            # Terminal dimension change from xterm FitAddon
            return

        if action == "command" or cmd_text:
            command_to_run = (cmd_text or data).strip()
            if command_to_run:
                await self.execute_command(command_to_run)
            return

        if action == "input" or "data" in content:
            # Interactive keystroke streaming from xterm.js
            char = data
            if char in ("\r", "\n"):
                await self.send_json({"type": "output", "data": "\r\n"})
                command_to_run = self.input_buffer.strip()
                self.input_buffer = ""
                if command_to_run:
                    await self.execute_command(command_to_run)
                else:
                    await self.send_json({"type": "output", "data": "$ "})
            elif char == "\u007F" or char == "\b":
                # Backspace
                if len(self.input_buffer) > 0:
                    self.input_buffer = self.input_buffer[:-1]
                    await self.send_json({"type": "output", "data": "\b \b"})
            elif char == "\u0003":
                # Ctrl+C
                self.input_buffer = ""
                await self.send_json({"type": "output", "data": "^C\r\n$ "})
            else:
                self.input_buffer += char
                await self.send_json({"type": "output", "data": char})

    async def execute_command(self, cmd: str):
        from .security import UniversalSecurityEngine

        is_safe, security_error, _ = UniversalSecurityEngine.evaluate_terminal_command(
            command=cmd,
            workspace_dir=self.workspace_dir,
            project_id=self.project_id,
            user_id=getattr(self.scope.get("user"), "user_id", None),
        )
        if not is_safe:
            message = security_error.get("message", "Command blocked by workspace security policy.")
            await self.send_json({"type": "output", "data": f"\x1b[31m{message}\x1b[0m\r\n$ "})
            return

        # Handle built-in shell helper commands
        lower_cmd = cmd.lower()
        if lower_cmd == "clear" or lower_cmd == "cls":
            await self.send_json({"type": "output", "data": "\x1b[2J\x1b[H$ "})
            return

        if lower_cmd == "help":
            help_text = (
                "\r\n\x1b[1mAvailable Commands:\x1b[0m\r\n"
                "  ls / dir              List workspace files\r\n"
                "  python [script.py]    Run Python scripts or manage.py\r\n"
                "  php [script.php]       Run PHP scripts or built-in server\r\n"
                "  node [script.js]       Execute JavaScript files\r\n"
                "  git status            View git status\r\n"
                "  clear                 Clear terminal screen\r\n\r\n$ "
            )
            await self.send_json({"type": "output", "data": help_text})
            return

        # Execute in sandbox subprocess asynchronously
        env = ExecutionPolicy.sanitize_environment()
        clean_pythonpath = f"{str(self.workspace_dir)}{os.pathsep}{env.get('PYTHONPATH', '')}"
        env["PYTHONPATH"] = clean_pythonpath

        try:
            loop = asyncio.get_event_loop()
            proc_output = await loop.run_in_executor(
                None,
                self._run_process_sync,
                cmd,
                self.workspace_dir,
                env
            )
            formatted = proc_output.replace("\n", "\r\n")
            if not formatted.endswith("\r\n") and formatted:
                formatted += "\r\n"
            await self.send_json({"type": "output", "data": formatted + "$ "})
        except Exception as e:
            await self.send_json({"type": "output", "data": f"\x1b[31mError: {str(e)}\x1b[0m\r\n$ "})

    def _run_process_sync(self, cmd: str, cwd: Path, env: dict) -> str:
        try:
            shell_cmd = cmd
            # Normalize commands across platforms
            is_win = sys.platform == "win32"
            res = subprocess.run(
                shell_cmd,
                shell=True,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=12.0
            )
            out = res.stdout
            err = res.stderr
            combined = ""
            if out:
                combined += out
            if err:
                combined += f"\x1b[31m{err}\x1b[0m"
            return combined if combined else ""
        except subprocess.TimeoutExpired:
            return "\x1b[31m[Process timed out after 12 seconds]\x1b[0m"
        except Exception as err:
            return f"\x1b[31m[Execution error: {str(err)}]\x1b[0m"


class CodeLabLogStreamConsumer(AsyncJsonWebsocketConsumer):
    """
    Streams server logs (django_server.log or php_server.log) in real time over WebSockets.
    """
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs'].get('project_id')
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not await self._owns_project(user, self.project_id):
            await self.close(code=4404)
            return
        self.workspace_dir = await self._get_workspace_dir(self.project_id)
        self.is_active = True
        await self.accept()

        asyncio.create_task(self.stream_logs())

    @database_sync_to_async
    def _owns_project(self, user, project_id):
        return CodeProject.objects.filter(project_id=project_id, user=user).exists()

    @database_sync_to_async
    def _get_workspace_dir(self, project_id):
        return get_project_workspace_dir(project_id)

    async def disconnect(self, close_code):
        self.is_active = False

    async def stream_logs(self):
        last_size = 0
        while self.is_active:
            # Check both django_server.log and php_server.log
            for log_name in ("django_server.log", "php_server.log"):
                log_file = self.workspace_dir / log_name
                if log_file.exists():
                    try:
                        curr_size = log_file.stat().st_size
                        if curr_size > last_size:
                            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                                f.seek(last_size)
                                new_chunk = f.read()
                                last_size = curr_size
                                if new_chunk:
                                    await self.send_json({
                                        "type": "log_chunk",
                                        "data": new_chunk
                                    })
                    except Exception:
                        pass
            await asyncio.sleep(1.0)
