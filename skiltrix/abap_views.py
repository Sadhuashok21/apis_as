"""
SkilTrix SAP ABAP Lab - REST API Views & ViewSets
"""

import os
import uuid
import zipfile
import shutil
from pathlib import Path
from django.conf import settings
from django.utils.text import slugify
from django.http import FileResponse, HttpResponse, Http404
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .abap_access import HasABAPEntitlement

from sfs.models import AllUsers
from .abap_models import (
    ABAPProject,
    ABAPSourceFile,
    ABAPExercise,
    ABAPTestCase,
    ABAPSubmission,
    SAPSystemConnection,
    ABAPDictionaryTable,
    ABAPLearningProgress,
)
from .abap_serializers import (
    ABAPProjectListSerializer,
    ABAPProjectDetailSerializer,
    ABAPSourceFileSerializer,
    ABAPExerciseListSerializer,
    ABAPExerciseDetailSerializer,
    ABAPSubmissionSerializer,
    SAPSystemConnectionSerializer,
    ABAPDictionaryTableSerializer,
    ABAPLearningProgressSerializer,
)


ABAP_WORKSPACE_BASE_DIR = Path(settings.MEDIA_ROOT) / "abap_workspaces"
ABAP_WORKSPACE_BASE_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_workspace_relpath(relpath: str) -> str:
    """Normalizes and validates relative paths within an ABAP workspace."""
    clean = (relpath or "").strip().replace("\\", "/")
    if clean.startswith("/") or (len(clean) >= 2 and clean[1] == ":"):
        raise ValueError("Absolute workspace paths are prohibited.")
    parts = [p for p in clean.split("/") if p and p != "."]
    if any(p == ".." for p in parts):
        raise ValueError("Invalid relative path: directory traversal is prohibited.")
    return "/".join(parts)


def get_abap_workspace_dir(project_id: str) -> Path:
    safe_id = "".join(c for c in project_id if c.isalnum() or c in ("-", "_"))
    project = ABAPProject.objects.filter(project_id=project_id).select_related("user").first()
    if not project:
        raise Http404("Project not found.")
    owner = "".join(c for c in project.user.user_id if c.isalnum() or c in ("-", "_"))
    pdir = ABAP_WORKSPACE_BASE_DIR / "users" / owner / safe_id
    legacy = ABAP_WORKSPACE_BASE_DIR / safe_id
    if not pdir.exists() and legacy.exists() and not legacy.is_symlink():
        pdir.parent.mkdir(parents=True, exist_ok=True)
        pdir.mkdir(parents=True, exist_ok=True)
        for source in legacy.rglob("*"):
            if source.is_symlink():
                continue
            target = pdir / source.relative_to(legacy)
            if source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    pdir.mkdir(parents=True, exist_ok=True)
    return pdir


def resolve_abap_workspace_path(workspace_dir: Path, relative_path: str) -> Path:
    root = workspace_dir.resolve()
    target = (root / sanitize_workspace_relpath(relative_path)).resolve()
    if target != root and root not in target.parents:
        raise ValueError("Workspace path escapes the project directory.")
    return target


class ABAPProjectViewSet(viewsets.ModelViewSet):
    """CRUD operations for student & enterprise ABAP project workspaces."""
    queryset = ABAPProject.objects.all()
    permission_classes = [IsAuthenticated, HasABAPEntitlement]

    def get_serializer_class(self):
        if self.action in ["retrieve", "create"]:
            return ABAPProjectDetailSerializer
        return ABAPProjectListSerializer

    def get_queryset(self):
        qs = ABAPProject.objects.filter(user=self.request.user)
        mode = self.request.query_params.get("mode")
        if mode:
            qs = qs.filter(execution_mode=mode)
        return qs

    def create(self, request, *args, **kwargs):
        user = request.user

        title = request.data.get("title", "Z_MY_ABAP_REPORT").strip().upper()
        # Ensure title follows SAP naming convention (Z or Y prefix)
        if not title.startswith("Z") and not title.startswith("Y"):
            title = f"Z{title}"

        package_name = request.data.get("package_name", "$TMP").strip().upper()
        execution_mode = request.data.get("execution_mode", "simulator")
        sap_system_id = request.data.get("sap_system_id", "")
        description = request.data.get("description", "")

        project_id = f"abap_{uuid.uuid4().hex[:12]}"
        slug = f"{slugify(title)[:40]}-{project_id[-6:]}"

        project = ABAPProject.objects.create(
            project_id=project_id,
            user=user,
            title=title,
            slug=slug,
            package_name=package_name,
            execution_mode=execution_mode,
            sap_system_id=sap_system_id,
            description=description,
            status="ready",
        )

        # Create default starter report
        main_report_name = f"{title.lower()}.prog.abap"
        starter_code = f"""*&---------------------------------------------------------------------*
*& Report {title}
*& Description: {description or 'SkilTrix ABAP Development Program'}
*& Package: {package_name}
*&---------------------------------------------------------------------*
REPORT {title.lower()}.

* Data Declarations
DATA: lv_message TYPE string VALUE 'Welcome to SkilTrix SAP ABAP Studio!'.

* Main Processing Block
START-OF-SELECTION.
  WRITE: / '==================================================',
         / lv_message,
         / 'Current System Date:', sy-datum,
         / 'Current System Time:', sy-uzeit,
         / '=================================================='.
  ULINE.
"""
        ABAPSourceFile.objects.create(
            file_id=f"afile_{uuid.uuid4().hex[:12]}",
            project=project,
            name=main_report_name,
            object_type="report",
            content=starter_code,
            size_bytes=len(starter_code.encode("utf-8")),
            is_active=True,
        )

        # Write to workspace disk
        ws_dir = get_abap_workspace_dir(project_id)
        resolve_abap_workspace_path(ws_dir, main_report_name).write_text(starter_code, encoding="utf-8")

        serializer = ABAPProjectDetailSerializer(project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """Export project files as an ABAP ZIP archive."""
        project = self.get_object()
        ws_dir = get_abap_workspace_dir(project.project_id)
        zip_path = ws_dir / "exports" / f"{uuid.uuid4().hex}.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for sfile in project.source_files.all():
                zf.writestr(sfile.name, sfile.content)

        with open(zip_path, "rb") as fh:
            zip_data = fh.read()
        response = HttpResponse(zip_data, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{project.title}.zip"'
        return response


class ABAPSourceFileViewSet(viewsets.ViewSet):
    """File operations for individual ABAP objects in a project."""
    permission_classes = [IsAuthenticated, HasABAPEntitlement]

    def list(self, request, project_id=None):
        project = ABAPProject.objects.filter(project_id=project_id, user=request.user).first()
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ABAPSourceFileSerializer(project.source_files.all(), many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def content(self, request, project_id=None):
        project = ABAPProject.objects.filter(project_id=project_id, user=request.user).first()
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            file_name = sanitize_workspace_relpath(request.query_params.get("name") or request.query_params.get("path") or "")
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        if not file_name:
            return Response({"detail": "Object name is required."}, status=status.HTTP_400_BAD_REQUEST)

        sfile = project.source_files.filter(name=file_name).first()
        if not sfile:
            # Fallback to reading from disk workspace if available
            ws_file = resolve_abap_workspace_path(get_abap_workspace_dir(project.project_id), file_name)
            if ws_file.exists() and ws_file.is_file():
                content = ws_file.read_text(encoding="utf-8", errors="replace")
                sfile = ABAPSourceFile.objects.create(
                    file_id=f"afile_{uuid.uuid4().hex[:12]}",
                    project=project,
                    name=file_name,
                    object_type="report" if file_name.endswith(".abap") else "other",
                    content=content,
                    size_bytes=len(content.encode("utf-8")),
                    is_active=True,
                )
            else:
                return Response({"detail": "File not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ABAPSourceFileSerializer(sfile)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def save(self, request, project_id=None):
        project = ABAPProject.objects.filter(project_id=project_id, user=request.user).first()
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            file_name = sanitize_workspace_relpath(request.data.get("name", ""))
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        content = request.data.get("content", "")
        object_type = request.data.get("object_type", "report")

        if not file_name:
            return Response({"detail": "Object name is required."}, status=status.HTTP_400_BAD_REQUEST)

        content_bytes = len(content.encode("utf-8"))
        existing = project.source_files.filter(name=file_name).first()
        sfile, _ = ABAPSourceFile.objects.update_or_create(
            project=project,
            name=file_name,
            defaults={
                "file_id": existing.file_id if existing else f"afile_{uuid.uuid4().hex[:12]}",
                "object_type": object_type,
                "content": content,
                "size_bytes": content_bytes,
                "is_active": True,
            }
        )

        # Write to disk workspace
        ws_dir = get_abap_workspace_dir(project.project_id)
        target_disk = resolve_abap_workspace_path(ws_dir, file_name)
        target_disk.parent.mkdir(parents=True, exist_ok=True)
        target_disk.write_text(content, encoding="utf-8", errors="replace")

        return Response({
            "status": True,
            "message": f"ABAP object {file_name} saved successfully.",
            "file_id": sfile.file_id,
            "name": sfile.name,
            "size_bytes": sfile.size_bytes,
        })

    @action(detail=False, methods=["post"])
    def create_file(self, request, project_id=None):
        project = ABAPProject.objects.filter(project_id=project_id, user=request.user).first()
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        raw_name = request.data.get("name", "").strip()
        try:
            file_name = sanitize_workspace_relpath(raw_name)
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        object_type = request.data.get("object_type", "report")
        content = request.data.get("content", "")

        if not file_name:
            return Response({"detail": "Object name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Auto-append proper ABAP extension if absent
        if not any(file_name.lower().endswith(ext) for ext in [".abap", ".prog.abap", ".clas.abap", ".incl.abap", ".intf.abap", ".json", ".txt", ".md"]):
            if object_type == "class":
                file_name += ".clas.abap"
            elif object_type == "include":
                file_name += ".incl.abap"
            elif object_type == "interface":
                file_name += ".intf.abap"
            else:
                file_name += ".prog.abap"

        if project.source_files.filter(name=file_name).exists():
            return Response({"detail": f"File '{file_name}' already exists."}, status=status.HTTP_400_BAD_REQUEST)

        sfile = ABAPSourceFile.objects.create(
            file_id=f"afile_{uuid.uuid4().hex[:12]}",
            project=project,
            name=file_name,
            object_type=object_type,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            is_active=True,
        )

        ws_dir = get_abap_workspace_dir(project.project_id)
        target_disk = resolve_abap_workspace_path(ws_dir, file_name)
        target_disk.parent.mkdir(parents=True, exist_ok=True)
        target_disk.write_text(content, encoding="utf-8", errors="replace")

        return Response(ABAPSourceFileSerializer(sfile).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def create_folder(self, request, project_id=None):
        project = ABAPProject.objects.filter(project_id=project_id, user=request.user).first()
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            folder_path = sanitize_workspace_relpath(request.data.get("folder_path", "") or request.data.get("path", ""))
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        if not folder_path:
            return Response({"detail": "folder_path is required."}, status=status.HTTP_400_BAD_REQUEST)

        ws_dir = get_abap_workspace_dir(project.project_id)
        resolve_abap_workspace_path(ws_dir, folder_path).mkdir(parents=True, exist_ok=True)

        keep_file = f"{folder_path}/.keep"
        existing = project.source_files.filter(name=keep_file).first()
        sfile, _ = ABAPSourceFile.objects.get_or_create(
            project=project,
            name=keep_file,
            defaults={
                "file_id": existing.file_id if existing else f"afold_{uuid.uuid4().hex[:12]}",
                "object_type": "folder",
                "content": "",
                "size_bytes": 0,
                "is_active": True,
            }
        )
        resolve_abap_workspace_path(ws_dir, keep_file).write_text("", encoding="utf-8")

        return Response({
            "status": True,
            "message": f"Folder '{folder_path}' created successfully.",
            "folder_path": folder_path,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def rename(self, request, project_id=None):
        project = ABAPProject.objects.filter(project_id=project_id, user=request.user).first()
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            old_path = sanitize_workspace_relpath(request.data.get("old_path", ""))
            new_path = sanitize_workspace_relpath(request.data.get("new_path", ""))
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        if not old_path or not new_path:
            return Response({"detail": "Both old_path and new_path are required."}, status=status.HTTP_400_BAD_REQUEST)

        if old_path == new_path:
            return Response({"status": True, "message": "Paths are identical, no change."})

        ws_dir = get_abap_workspace_dir(project.project_id)
        updated_count = 0

        # Case 1: Exact single file
        sfile = project.source_files.filter(name=old_path).first()
        if sfile:
            sfile.name = new_path
            sfile.save()
            updated_count += 1
            src_disk = resolve_abap_workspace_path(ws_dir, old_path)
            dest_disk = resolve_abap_workspace_path(ws_dir, new_path)
            dest_disk.parent.mkdir(parents=True, exist_ok=True)
            if src_disk.exists() and src_disk != dest_disk:
                shutil.move(str(src_disk), str(dest_disk))

        # Case 2: Folder rename (all files with prefix old_path + "/")
        prefix = old_path + "/"
        folder_files = project.source_files.filter(name__startswith=prefix)
        for ff in folder_files:
            rel_suffix = ff.name[len(prefix):]
            ff.name = f"{new_path}/{rel_suffix}"
            ff.save()
            updated_count += 1

        src_folder = resolve_abap_workspace_path(ws_dir, old_path)
        dest_folder = resolve_abap_workspace_path(ws_dir, new_path)
        if src_folder.exists() and src_folder.is_dir() and src_folder != dest_folder:
            dest_folder.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_folder), str(dest_folder))

        if updated_count == 0 and not resolve_abap_workspace_path(ws_dir, new_path).exists():
            return Response({"detail": f"Item '{old_path}' not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ABAPSourceFileSerializer(project.source_files.all(), many=True)
        return Response({
            "status": True,
            "message": f"Renamed '{old_path}' to '{new_path}'.",
            "old_path": old_path,
            "new_path": new_path,
            "files": serializer.data,
        })

    @action(detail=False, methods=["post"])
    def move(self, request, project_id=None):
        project = ABAPProject.objects.filter(project_id=project_id, user=request.user).first()
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            source_path = sanitize_workspace_relpath(request.data.get("source_path", ""))
            target_folder = sanitize_workspace_relpath(request.data.get("target_folder", ""))
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        if not source_path:
            return Response({"detail": "source_path is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Prevent moving folder into itself or its descendants
        if target_folder == source_path or target_folder.startswith(source_path + "/"):
            return Response({"detail": "Cannot move a folder into itself or one of its descendants."}, status=status.HTTP_400_BAD_REQUEST)

        base_name = source_path.split("/")[-1]
        dest_path = f"{target_folder}/{base_name}" if target_folder else base_name
        if dest_path == source_path:
            return Response({"status": True, "message": "Item is already at destination location."})

        request.data["old_path"] = source_path
        request.data["new_path"] = dest_path
        return self.rename(request, project_id=project_id)

    @action(detail=False, methods=["post"])
    def duplicate(self, request, project_id=None):
        project = ABAPProject.objects.filter(project_id=project_id, user=request.user).first()
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            source_path = sanitize_workspace_relpath(request.data.get("source_path", ""))
            new_path = sanitize_workspace_relpath(request.data.get("new_path", ""))
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        if not source_path:
            return Response({"detail": "source_path is required."}, status=status.HTTP_400_BAD_REQUEST)

        sfile = project.source_files.filter(name=source_path).first()
        if not sfile:
            return Response({"detail": "Source file not found."}, status=status.HTTP_404_NOT_FOUND)

        if not new_path:
            if "." in source_path:
                idx = source_path.find(".")
                prefix = source_path[:idx]
                ext = source_path[idx:]
                new_path = f"{prefix}_copy{ext}"
            else:
                new_path = f"{source_path}_copy"

        existing = project.source_files.filter(name=new_path).first()
        dup_file, _ = ABAPSourceFile.objects.update_or_create(
            project=project,
            name=new_path,
            defaults={
                "file_id": existing.file_id if existing else f"afile_{uuid.uuid4().hex[:12]}",
                "object_type": sfile.object_type,
                "content": sfile.content,
                "size_bytes": sfile.size_bytes,
                "is_active": True,
            }
        )

        ws_dir = get_abap_workspace_dir(project.project_id)
        target_disk = resolve_abap_workspace_path(ws_dir, new_path)
        target_disk.parent.mkdir(parents=True, exist_ok=True)
        target_disk.write_text(sfile.content, encoding="utf-8", errors="replace")

        return Response(ABAPSourceFileSerializer(dup_file).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["delete"])
    def delete_file(self, request, project_id=None):
        project = ABAPProject.objects.filter(project_id=project_id, user=request.user).first()
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            target_path = sanitize_workspace_relpath(request.query_params.get("name") or request.query_params.get("path") or "")
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        if not target_path:
            return Response({"detail": "Object path is required."}, status=status.HTTP_400_BAD_REQUEST)

        ws_dir = get_abap_workspace_dir(project.project_id)
        deleted_count = 0

        # Exact match
        sfile = project.source_files.filter(name=target_path).first()
        if sfile:
            sfile.delete()
            deleted_count += 1

        # Prefix match for directory
        prefix = target_path + "/"
        folder_files = project.source_files.filter(name__startswith=prefix)
        deleted_count += folder_files.count()
        folder_files.delete()

        # Disk deletion
        disk_target = resolve_abap_workspace_path(ws_dir, target_path)
        if disk_target.exists():
            if disk_target.is_dir():
                shutil.rmtree(str(disk_target), ignore_errors=True)
            else:
                disk_target.unlink(missing_ok=True)

        if deleted_count > 0 or not disk_target.exists():
            return Response({"status": True, "message": f"Deleted {target_path}", "deleted_count": deleted_count})

        return Response({"detail": "File or folder not found."}, status=status.HTTP_404_NOT_FOUND)


class ABAPExerciseViewSet(viewsets.ReadOnlyModelViewSet):
    """Searchable ABAP learning repository and question bank."""
    queryset = ABAPExercise.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, HasABAPEntitlement]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ABAPExerciseDetailSerializer
        return ABAPExerciseListSerializer

    def get_queryset(self):
        qs = ABAPExercise.objects.filter(is_active=True)
        category = self.request.query_params.get("category")
        difficulty = self.request.query_params.get("difficulty")
        search = self.request.query_params.get("search")

        if category:
            qs = qs.filter(category__iexact=category)
        if difficulty:
            qs = qs.filter(difficulty__iexact=difficulty)
        if search:
            qs = qs.filter(title__icontains=search)
        return qs

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Evaluates a student's solution against sample and hidden evaluation test cases.
        Updates user learning progress and saves an ABAPSubmission record.
        """
        exercise = self.get_object()
        code = request.data.get("code", "")
        user = request.user

        from .abap_engine import execute_abap_code
        result = execute_abap_code(code)

        test_cases = exercise.test_cases.all()
        total_tests = test_cases.count()
        passed_tests = 0
        test_results = []

        actual_output = result.get("output", "").strip()

        for tc in test_cases:
            expected = tc.expected_output.strip()
            passed = expected in actual_output or actual_output == expected
            if passed:
                passed_tests += 1

            test_results.append({
                "test_case_id": tc.test_case_id,
                "order": tc.order,
                "passed": passed,
                "is_sample": tc.is_sample,
                "expected": expected if tc.is_sample else "[HIDDEN TEST CASE]",
                "actual": actual_output if tc.is_sample else ("[PASSED]" if passed else "[FAILED]"),
            })

        if not result.get("status"):
            verdict = "Runtime Error"
        elif total_tests > 0 and passed_tests == total_tests:
            verdict = "Accepted"
        elif total_tests == 0 and result.get("status"):
            verdict = "Accepted"
            passed_tests = 1
            total_tests = 1
        else:
            verdict = "Wrong Answer"

        sub = ABAPSubmission.objects.create(
            submission_id=f"asub_{uuid.uuid4().hex[:12]}",
            user=user,
            exercise=exercise,
            source_code=code,
            execution_mode="simulator",
            verdict=verdict,
            passed_tests=passed_tests,
            total_tests=total_tests,
            execution_time_ms=result.get("execution_time_ms", 0.0),
            diagnostics=result.get("diagnostics", []),
        )

        if verdict == "Accepted" and user:
            progress, _ = ABAPLearningProgress.objects.get_or_create(
                user=user,
                defaults={"progress_id": f"prog_{uuid.uuid4().hex[:12]}"}
            )
            progress.completed_exercises += 1
            progress.total_points += exercise.points
            progress.save()

        return Response({
            "submission_id": sub.submission_id,
            "verdict": verdict,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "execution_time_ms": sub.execution_time_ms,
            "test_results": test_results,
            "output": actual_output,
            "points_earned": exercise.points if verdict == "Accepted" else 0,
        })


class SAPSystemConnectionViewSet(viewsets.ModelViewSet):
    """Configures enterprise SAP connection profiles with server-side credential security."""
    queryset = SAPSystemConnection.objects.all()
    serializer_class = SAPSystemConnectionSerializer
    permission_classes = [IsAuthenticated, HasABAPEntitlement]

    def get_queryset(self):
        return SAPSystemConnection.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user

        system_name = request.data.get("system_name", "SAP S/4HANA System").strip()
        system_id = request.data.get("system_id", "S4H").strip().upper()
        client = request.data.get("client", "100").strip()
        host = request.data.get("host", "").strip()
        port = int(request.data.get("port", 443))
        auth_type = request.data.get("auth_type", "basic")
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")
        btp_key = request.data.get("btp_service_key_json", "")

        conn = SAPSystemConnection.objects.create(
            connection_id=f"sapconn_{uuid.uuid4().hex[:12]}",
            user=user,
            system_name=system_name,
            system_id=system_id,
            client=client,
            host=host,
            port=port,
            auth_type=auth_type,
            username=username,
            encrypted_password=password, # Server-side stored
            btp_service_key_json=btp_key,
            is_active=True,
        )

        serializer = SAPSystemConnectionSerializer(conn)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        """Attempts an authorized ping/discovery handshake with the configured SAP host."""
        conn = self.get_object()
        from .abap_sap_connector import test_sap_connection
        result = test_sap_connection(conn)
        return Response(result)


class ABAPDictionaryViewSet(viewsets.ModelViewSet):
    """SE11 ABAP Dictionary transparent tables and structure modeling."""
    queryset = ABAPDictionaryTable.objects.all()
    serializer_class = ABAPDictionaryTableSerializer
    permission_classes = [IsAuthenticated, HasABAPEntitlement]
    lookup_field = "table_id"

    def get_queryset(self):
        from django.db.models import Q
        project_id = self.request.query_params.get("project_id")
        if project_id:
            return ABAPDictionaryTable.objects.filter(
                Q(project__project_id=project_id, project__user=self.request.user) |
                Q(user=self.request.user)
            ).order_by("-updated_at")
        return ABAPDictionaryTable.objects.filter(user=self.request.user).order_by("-updated_at")

    def create(self, request, *args, **kwargs):
        project_id = request.data.get("project_id")
        project = ABAPProject.objects.filter(project_id=project_id, user=request.user).first() if project_id else None
        if project_id and project is None:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        user = request.user

        table_name = request.data.get("table_name", "ZMY_TABLE").strip().upper()
        if not table_name.startswith("Z") and not table_name.startswith("Y"):
            table_name = f"Z{table_name}"

        description = request.data.get("description", "Transparent Application Table")
        fields_schema = request.data.get("fields_schema", [])

        # Only add MANDT client field if client_dependent is explicitly set to True
        client_dependent = request.data.get("client_dependent", False)
        if isinstance(client_dependent, str):
            client_dependent = client_dependent.lower() in ("true", "1", "yes")

        if client_dependent and not any(f.get("field") == "MANDT" for f in fields_schema):
            fields_schema.insert(0, {
                "field": "MANDT",
                "key": True,
                "data_element": "MANDT",
                "type": "CLNT",
                "length": 3,
                "description": "Client Number",
            })

        # Validate that at least one primary key field is defined
        if not any(bool(f.get("key")) for f in fields_schema):
            return Response(
                {"detail": "At least one key field is required to define a primary key.", "error": "At least one key field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicate table creation: reject if table already exists
        existing = ABAPDictionaryTable.objects.filter(table_name__iexact=table_name, user=user).first()
        if not existing and project:
            existing = ABAPDictionaryTable.objects.filter(table_name__iexact=table_name, project=project).first()
        if existing:
            return Response(
                {"detail": "Database table already exists", "error": "Database table already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .abap_engine.datasets import STANDARD_DATASETS
        if table_name in STANDARD_DATASETS:
            return Response(
                {"detail": "Database table already exists", "error": "Database table already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        table = ABAPDictionaryTable.objects.create(
            table_id=f"tabl_{uuid.uuid4().hex[:12]}",
            project=project,
            user=user,
            table_name=table_name,
            description=description,
            delivery_class=request.data.get("delivery_class", "A"),
            fields_schema=fields_schema,
            sample_records=request.data.get("sample_records", []),
        )

        serializer = ABAPDictionaryTableSerializer(table)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def add_record(self, request, table_id=None):
        table = self.get_object()
        record = request.data.get("record", {})
        if not isinstance(record, dict) or not record:
            return Response({"error": "Invalid record format."}, status=status.HTTP_400_BAD_REQUEST)

        current_data = list(table.sample_records or [])
        current_data.append(record)
        table.sample_records = current_data
        table.save(update_fields=["sample_records"])

        return Response({
            "status": True,
            "message": "Record inserted successfully.",
            "row_count": len(current_data),
            "table_name": table.table_name,
            "record": record,
        })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def abap_health_check(request):
    """Health check & status telemetry for SkilTrix SAP ABAP Lab."""
    return Response({
        "status": "healthy",
        "service": "SkilTrix SAP ABAP Lab Engine",
        "version": "1.0.0",
        "modes": {
            "simulator": {"enabled": True, "parser": "AST-based Python ABAP Subset Engine"},
            "sap_connected": {"enabled": True, "protocols": ["SAP ADT REST", "SAP BTP OAuth2"]},
        },
        "total_exercises": ABAPExercise.objects.count(),
        "total_projects": ABAPProject.objects.filter(user=request.user).count(),
        "total_connections": SAPSystemConnection.objects.filter(user=request.user).count(),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasABAPEntitlement])
def execute_abap_view(request):
    """
    Executes ABAP source code using either:
    - Mode B: Educational ABAP Simulator (AST Parser + Interpreter)
    - Mode A: Real SAP Environment (via authorized ADT REST connector)
    """
    code = request.data.get("code", "")
    mode = request.data.get("execution_mode", "simulator")
    sap_system_id = request.data.get("sap_system_id")
    project_id = request.data.get("project_id")
    file_name = request.data.get("file_name")
    if project_id and not ABAPProject.objects.filter(project_id=project_id, user=request.user).exists():
        return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

    # Universal Security Firewall evaluation for ABAP
    from .security import UniversalSecurityEngine
    abap_violation = UniversalSecurityEngine.evaluate_abap(code, project_id=project_id)
    if abap_violation:
        return Response(abap_violation, status=status.HTTP_400_BAD_REQUEST)

    if mode == "sap_connected":
        conn = None
        if sap_system_id:
            conn = SAPSystemConnection.objects.filter(connection_id=sap_system_id, user=request.user).first()
        if not conn:
            conn = SAPSystemConnection.objects.filter(is_active=True, user=request.user).first()

        if not conn:
            return Response({
                "status": False,
                "output": "[SAP CONNECTION ERROR]: No active SAP system connection profile configured.\nPlease configure your SAP S/4HANA or BTP system credentials in System Connections.",
                "execution_time_ms": 0,
                "diagnostics": [{"line": 1, "severity": "error", "message": "No SAP connection configured"}],
                "execution_mode": "sap_connected",
            }, status=status.HTTP_200_OK)

        from .abap_sap_connector import execute_on_sap_adt
        result = execute_on_sap_adt(conn, code, object_name=file_name or "Z_SKILTRIX_REPORT")
        return Response(result)

    # Simulator execution (Mode B)
    from .abap_engine import execute_abap_code
    result = execute_abap_code(code, user_id=request.user.user_id, project_id=project_id)
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasABAPEntitlement])
def syntax_check_view(request):
    """Checks ABAP syntax and returns compiler/parser diagnostics."""
    code = request.data.get("code", "")
    from .abap_engine import check_abap_syntax
    result = check_abap_syntax(code)
    return Response(result)


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasABAPEntitlement])
def dictionary_preview_view(request):
    """Returns metadata and records for standard or custom transparent tables."""
    table_name = request.query_params.get("table", "KNA1").strip().upper()
    from .abap_engine.datasets import STANDARD_DATASETS
    # Read standard fixtures directly. The engine's convenience cache can
    # contain a custom table snapshot, which must never override a user's DB row.
    std_data = STANDARD_DATASETS.get(table_name)
    if std_data:
        return Response({
            "table_name": table_name,
            "description": std_data["description"],
            "row_count": len(std_data["rows"]),
            "columns": std_data["columns"],
            "rows": std_data["rows"],
        })

    # Check custom ABAPDictionaryTable
    project_id = request.query_params.get("project_id")
    custom = None
    if project_id:
        custom = ABAPDictionaryTable.objects.filter(
            table_name__iexact=table_name, project__project_id=project_id, project__user=request.user,
        ).first()
    if not custom:
        custom = ABAPDictionaryTable.objects.filter(
            table_name__iexact=table_name, user=request.user,
        ).first()
    if custom:
        return Response({
            "table_name": custom.table_name,
            "description": custom.description,
            "row_count": len(custom.sample_records or []),
            "columns": [
                {
                    "name": f.get("field"),
                    "type": f.get("type", "CHAR"),
                    "length": f.get("length", 10),
                    "key": f.get("key", False),
                    "description": f.get("description", ""),
                }
                for f in (custom.fields_schema or [])
            ],
            "rows": custom.sample_records or [],
        })

    return Response({
        "table_name": table_name,
        "description": "Unknown Table",
        "row_count": 0,
        "columns": [],
        "rows": [],
    }, status=status.HTTP_404_NOT_FOUND)
