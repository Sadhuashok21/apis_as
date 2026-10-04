"""
Django Management Command: cleanup_codelab_workspaces
Usage: python manage.py cleanup_codelab_workspaces [--max-idle-seconds 3600]
Housekeeps dead processes, terminates idle development servers, and deletes orphaned temp files.
"""

from django.core.management.base import BaseCommand
from skiltrix.codelab_observability import cleanup_stale_workspaces_and_processes


class Command(BaseCommand):
    help = "Terminates stale CodeLab development servers and purges temporary files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-idle-seconds",
            type=int,
            default=3600,
            help="Maximum seconds a server process is permitted to stay running (default: 3600s / 1hr)."
        )

    def handle(self, *args, **options):
        max_idle = options.get("max_idle_seconds", 3600)
        self.stdout.write(self.style.NOTICE(f"Starting CodeLab workspace cleanup (max_idle={max_idle}s)..."))

        result = cleanup_stale_workspaces_and_processes(max_idle_seconds=max_idle)

        stopped_django = result.get("stopped_django", [])
        stopped_php = result.get("stopped_php", [])
        deleted_temp = result.get("deleted_temp_files", 0)

        self.stdout.write(self.style.SUCCESS(
            f"Cleanup complete:\n"
            f" - Stopped Django servers: {len(stopped_django)}\n"
            f" - Stopped PHP servers: {len(stopped_php)}\n"
            f" - Deleted scratch temp files: {deleted_temp}"
        ))
