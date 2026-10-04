"""Audit and copy legacy CodeLab/ABAP workspace folders to owner scoped storage."""

import json
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Audit legacy workspace folders; pass --apply to copy verified projects into owner scoped storage."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Copy verified workspaces. Originals remain as backups.")
        parser.add_argument("--report", help="Write the JSON audit report to this path.")

    def handle(self, *args, **options):
        from skiltrix.codelab_models import CodeProject
        from skiltrix.abap_models import ABAPProject

        media_root = Path(settings.MEDIA_ROOT)
        entries = []
        mappings = (
            ("codelab", media_root / "codelab_workspaces", CodeProject, "project_id"),
            ("abap", media_root / "abap_workspaces", ABAPProject, "project_id"),
        )
        for workspace_type, source_root, model, id_field in mappings:
            known = {str(value): owner for value, owner in model.objects.values_list(id_field, "user__user_id")}
            for source in sorted(source_root.iterdir()) if source_root.exists() else []:
                if source.name in {"temp", "users"} or not source.is_dir() or source.is_symlink():
                    continue
                owner_id = known.get(source.name)
                if not owner_id:
                    entries.append({"type": workspace_type, "workspace": source.name, "status": "unresolved", "detail": "No verified owner record; retained for administrative review."})
                    continue

                target_root = source_root / "users" / "".join(c for c in owner_id if c.isalnum() or c in "-_")
                target = target_root / "".join(c for c in source.name if c.isalnum() or c in "-_")
                if target.exists():
                    state = "already_migrated"
                elif options["apply"]:
                    target.mkdir(parents=True, exist_ok=True)
                    for candidate in source.rglob("*"):
                        if candidate.is_symlink():
                            continue
                        relative = candidate.relative_to(source)
                        destination = target / relative
                        if candidate.is_dir():
                            destination.mkdir(parents=True, exist_ok=True)
                        elif candidate.is_file():
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(candidate, destination)
                    state = "copied"
                else:
                    state = "ready_to_copy"
                entries.append({
                    "type": workspace_type, "workspace": source.name, "owner_id": owner_id,
                    "status": state, "backup": "original retained",
                })

        report = {"mode": "apply" if options["apply"] else "dry_run", "entries": entries}
        serialized = json.dumps(report, indent=2)
        if options["report"]:
            report_path = Path(options["report"]).resolve()
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(serialized, encoding="utf-8")
        self.stdout.write(serialized)
