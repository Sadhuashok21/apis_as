import os
import sys
import uuid
import shutil
import tempfile
from functools import wraps
from pathlib import Path
from django.utils.text import slugify
from django.http import FileResponse, Http404
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.conf import settings

from .codelab_models import (
    CodeProject,
    ProjectFile,
    ExecutionJob,
    WorkspaceSession,
    DatabaseWorkspace,
    ProjectActivity,
)
from .codelab_serializers import (
    CodeProjectSerializer,
    CodeProjectDetailSerializer,
    ProjectFileSerializer,
    ProjectFileListSerializer,
    ExecutionJobSerializer,
)
from .codelab_runner import (
    run_code_in_sandbox,
    get_project_workspace_dir,
    sync_db_files_to_workspace,
    export_project_as_zip,
    get_default_starter_files,
    sanitize_relative_path,
    resolve_workspace_path,
)


def get_current_user_or_guest(request):
    """Return only the server-authenticated account; client IDs are never identity."""
    user = request.user
    return user if user and user.is_authenticated else None


def get_owned_project(request, project_id):
    """Load a project only inside the current account's authorization scope."""
    return CodeProject.objects.filter(project_id=project_id, user=request.user).first()


def owned_workspace_required(view_func):
    """Require URL-addressed workspace endpoints to resolve inside the user scope."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        project_id = kwargs.get("project_id")
        if project_id is not None and not get_owned_project(request, project_id):
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        return view_func(request, *args, **kwargs)
    return wrapped


def snapshot_execution_workspace(workspace_dir):
    """Copy a project into a unique run directory so executions never share writes."""
    execution_root = Path(settings.MEDIA_ROOT) / "execution_tmp"
    execution_root.mkdir(parents=True, exist_ok=True)
    target_root = Path(tempfile.mkdtemp(prefix=f"{uuid.uuid4().hex}_", dir=execution_root))
    ignored_directories = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", "exports", "dist", "build", "target"}
    for root, dirs, files in os.walk(workspace_dir):
        root_path = Path(root)
        dirs[:] = [name for name in dirs if name not in ignored_directories and not (root_path / name).is_symlink()]
        relative_root = root_path.relative_to(workspace_dir)
        dest_root = target_root / relative_root
        dest_root.mkdir(parents=True, exist_ok=True)
        for filename in files:
            source = root_path / filename
            if source.is_symlink():
                continue
            dest = dest_root / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
    return target_root


class CodeProjectViewSet(viewsets.ModelViewSet):
    """CRUD operations for CodeLab multi-file and single-file projects."""
    queryset = CodeProject.objects.all()
    serializer_class = CodeProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ["retrieve"]:
            return CodeProjectDetailSerializer
        return CodeProjectSerializer

    def get_queryset(self):
        user = get_current_user_or_guest(self.request)
        if not user:
            return CodeProject.objects.none()
        
        # User projects + public projects
        return CodeProject.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        user = get_current_user_or_guest(request)
        if not user:
            return Response(
                {"status": False, "message": "User identification required to create a project."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        title = request.data.get("title", "Untitled Project").strip()
        project_type = request.data.get("project_type", "single_file")
        language = request.data.get("language", "python").lower().strip()
        description = request.data.get("description", "")
        is_public = False

        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        slug = f"{slugify(title)[:40]}-{project_id[-6:]}"

        project = CodeProject.objects.create(
            project_id=project_id,
            user=user,
            title=title,
            slug=slug,
            project_type=project_type,
            language=language,
            description=description,
            is_public=is_public,
            status="ready",
        )

        # Generate default starter files based on project type
        starter_files = get_default_starter_files(project_type, language)
        for sfile in starter_files:
            ProjectFile.objects.create(
                file_id=f"file_{uuid.uuid4().hex[:12]}",
                project=project,
                path=sfile["path"],
                name=sfile["name"],
                is_directory=sfile.get("is_directory", False),
                content=sfile.get("content", ""),
                size_bytes=len(sfile.get("content", "").encode("utf-8")),
            )

        # Sync files to physical workspace
        workspace_dir = sync_db_files_to_workspace(project)

        # For Django projects, initialize default_db in catalog and set as django_database
        if project_type == "django":
            from .codelab_sql import ProjectDatabaseCatalog
            cat = ProjectDatabaseCatalog(workspace_dir=workspace_dir, project_id=project.project_id)
            cat.set_django_database("default_db")

        # Initialize workspace session
        WorkspaceSession.objects.create(
            session_id=f"sess_{uuid.uuid4().hex[:12]}",
            project=project,
            user=user,
            status="stopped",
        )

        # Log activity
        ProjectActivity.objects.create(
            activity_id=f"act_{uuid.uuid4().hex[:12]}",
            project=project,
            user=user,
            action="project_created",
            details={"type": project_type, "language": language},
        )

        serializer = CodeProjectDetailSerializer(project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def diagnostics(self, request, pk=None):
        """Analyze only submitted or tracked source belonging to this owned project."""
        project = self.get_object()
        from .diagnostics import diagnose_project, diagnose_source

        workspace_dir = get_project_workspace_dir(project.project_id)
        database_name = request.data.get("database")
        if request.data.get("project_wide"):
            source_overrides = request.data.get("sources", {})
            if not isinstance(source_overrides, dict) or len(source_overrides) > 100:
                return Response({"detail": "Project-wide diagnostics accept at most 100 open source buffers."}, status=status.HTTP_400_BAD_REQUEST)
            safe_overrides = {}
            override_bytes = 0
            for raw_path, content in source_overrides.items():
                try:
                    normalized = sanitize_relative_path(raw_path)
                except ValueError:
                    continue
                if isinstance(content, str):
                    override_bytes += len(content.encode("utf-8", errors="replace"))
                    if override_bytes > 10_000_000:
                        return Response({"detail": "Open source buffers exceed the 10 MB project diagnostics limit."}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
                if isinstance(content, str) and project.files.filter(path=normalized, is_directory=False).exists():
                    safe_overrides[normalized] = content
            results = diagnose_project(project, workspace_dir, database_name, safe_overrides)
            files_by_path = {item.path: item.file_id for item in project.files.filter(is_directory=False)}
            for diagnostic in results:
                diagnostic["file_id"] = files_by_path.get(diagnostic.get("file"))
            return Response({"project_id": project.project_id, "diagnostics": results})

        try:
            relative_path = sanitize_relative_path(request.data.get("path", ""))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        file_obj = project.files.filter(path=relative_path, is_directory=False).first()
        virtual_sql = relative_path == "__query__.sql"
        if not file_obj and not virtual_sql:
            return Response({"detail": "File not found in this workspace."}, status=status.HTTP_404_NOT_FOUND)
        source = request.data.get("source")
        if not isinstance(source, str):
            return Response({"detail": "Source text is required."}, status=status.HTTP_400_BAD_REQUEST)
        diagnostics = diagnose_source(
            relative_path, source, workspace_dir, database_name,
            django_template=project.project_type == "django",
            project_language=project.language,
        )
        for diagnostic in diagnostics:
            diagnostic["file_id"] = file_obj.file_id if file_obj else None
        return Response({
            "project_id": project.project_id,
            "file_id": file_obj.file_id if file_obj else None,
            "version": request.data.get("version"),
            "diagnostics": diagnostics,
        })

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """Export project as a downloadable ZIP."""
        project = self.get_object()
        zip_path = export_project_as_zip(project)
        if not zip_path.exists():
            raise Http404("Failed to package project.")
        
        response = FileResponse(open(zip_path, "rb"), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{project.title}.zip"'
        return response

    @action(detail=True, methods=["get", "post"])
    def sync(self, request, pk=None):
        """Force synchronize database file records to disk."""
        project = self.get_object()
        workspace_dir = sync_db_files_to_workspace(project)
        return Response({
            "status": True,
            "message": "Project workspace synchronized.",
            "project_id": project.project_id
        })


class ProjectFileViewSet(viewsets.ViewSet):
    """File tree operations: create, read, update, rename, and delete."""
    permission_classes = [IsAuthenticated]

    def list(self, request, project_id=None):
        project = get_owned_project(request, project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        files = project.files.all()
        serializer = ProjectFileListSerializer(files, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def content(self, request, project_id=None):
        project = get_owned_project(request, project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        file_path = request.query_params.get("path")
        if not file_path:
            return Response({"detail": "File path query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            safe_path = sanitize_relative_path(file_path)
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        pfile = project.files.filter(path=safe_path).first()
        if not pfile:
            return Response({"detail": "File not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "file_id": pfile.file_id,
            "path": pfile.path,
            "name": pfile.name,
            "is_directory": pfile.is_directory,
            "content": pfile.content,
            "size_bytes": pfile.size_bytes,
            "updated_at": pfile.updated_at,
            "revision": pfile.revision,
        })

    @action(detail=False, methods=["post"])
    def save(self, request, project_id=None):
        """Save/update content of a file."""
        project = get_owned_project(request, project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        file_path = request.data.get("path")
        content = request.data.get("content", "")

        if not file_path:
            return Response({"detail": "Path is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            safe_path = sanitize_relative_path(file_path)
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        name = os.path.basename(safe_path)
        content_bytes = len(content.encode("utf-8"))

        from .codelab_observability import MAX_FILE_SIZE_BYTES, check_workspace_storage_quota
        if content_bytes > MAX_FILE_SIZE_BYTES:
            return Response(
                {"detail": f"File size ({round(content_bytes / (1024*1024), 2)}MB) exceeds limit of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        allowed, current_usage, max_quota = check_workspace_storage_quota(project.project_id, content_bytes)
        if not allowed:
            return Response(
                {"detail": f"Project storage quota ({max_quota // (1024*1024)}MB) exceeded. Current usage: {round(current_usage / (1024*1024), 2)}MB."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        expected_revision = request.data.get("expected_revision")
        with transaction.atomic():
            pfile = ProjectFile.objects.select_for_update().filter(project=project, path=safe_path).first()
            if pfile and expected_revision is None:
                return Response({"detail": "File version is required to save an existing file."}, status=428)
            if pfile and str(pfile.revision) != str(expected_revision):
                return Response({"detail": "This file changed in another tab. Reload it before saving."}, status=status.HTTP_409_CONFLICT)
            if pfile:
                pfile.name = name
                pfile.content = content
                pfile.size_bytes = content_bytes
                pfile.is_directory = False
                pfile.revision += 1
                pfile.save()
            else:
                pfile = ProjectFile.objects.create(
                    file_id=f"file_{uuid.uuid4().hex[:12]}", project=project, path=safe_path,
                    name=name, content=content, size_bytes=content_bytes, is_directory=False,
                )

        # Write to physical workspace
        workspace_dir = get_project_workspace_dir(project.project_id)
        disk_path = resolve_workspace_path(workspace_dir, safe_path)
        disk_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = disk_path.with_name(f".{disk_path.name}.{uuid.uuid4().hex}.tmp")
        temp_path.write_text(content, encoding="utf-8", errors="replace")
        os.replace(temp_path, disk_path)

        return Response({
            "status": True,
            "message": "File saved successfully.",
            "file_id": pfile.file_id,
            "path": pfile.path,
            "size_bytes": pfile.size_bytes,
            "updated_at": pfile.updated_at,
            "revision": pfile.revision,
        })

    @action(detail=False, methods=["post"])
    def create_file(self, request, project_id=None):
        """Create a new file or directory."""
        project = get_owned_project(request, project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        file_path = request.data.get("path")
        is_directory = request.data.get("is_directory", False)
        content = request.data.get("content", "")

        if not file_path:
            return Response({"detail": "Path is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            safe_path = sanitize_relative_path(file_path)
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        if project.files.filter(path=safe_path).exists():
            return Response({"detail": "File or directory already exists."}, status=status.HTTP_400_BAD_REQUEST)

        name = os.path.basename(safe_path) or safe_path
        content_bytes = 0 if is_directory else len(content.encode("utf-8"))

        if not is_directory:
            from .codelab_observability import MAX_FILE_SIZE_BYTES, check_workspace_storage_quota
            if content_bytes > MAX_FILE_SIZE_BYTES:
                return Response(
                    {"detail": f"File size exceeds limit of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )

            allowed, current_usage, max_quota = check_workspace_storage_quota(project.project_id, content_bytes)
            if not allowed:
                return Response(
                    {"detail": f"Project storage quota ({max_quota // (1024*1024)}MB) exceeded."},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )

        pfile = ProjectFile.objects.create(
            file_id=f"file_{uuid.uuid4().hex[:12]}",
            project=project,
            path=safe_path,
            name=name,
            is_directory=is_directory,
            content="" if is_directory else content,
            size_bytes=content_bytes,
        )

        # Update disk
        workspace_dir = get_project_workspace_dir(project.project_id)
        disk_path = resolve_workspace_path(workspace_dir, safe_path)
        if is_directory:
            disk_path.mkdir(parents=True, exist_ok=True)
        else:
            disk_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = disk_path.with_name(f".{disk_path.name}.{uuid.uuid4().hex}.tmp")
            temp_path.write_text(content, encoding="utf-8")
            os.replace(temp_path, disk_path)

        return Response(ProjectFileSerializer(pfile).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["delete"])
    def delete_file(self, request, project_id=None):
        """Delete a file or directory."""
        project = get_owned_project(request, project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        file_path = request.query_params.get("path")
        if not file_path:
            return Response({"detail": "Path query parameter required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            safe_path = sanitize_relative_path(file_path)
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        # Delete matching file and child files if directory
        project.files.filter(path=safe_path).delete()
        project.files.filter(path__startswith=f"{safe_path}/").delete()

        # Remove from disk
        workspace_dir = get_project_workspace_dir(project.project_id)
        disk_path = resolve_workspace_path(workspace_dir, safe_path)
        if disk_path.is_dir():
            shutil.rmtree(disk_path, ignore_errors=True)
        elif disk_path.exists():
            disk_path.unlink()

        return Response({"status": True, "message": f"Deleted {safe_path}."})

    @action(detail=False, methods=["post"])
    def rename_path(self, request, project_id=None):
        """Rename a file or directory on disk and update DB."""
        import shutil
        project = get_owned_project(request, project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        old_path = request.data.get("old_path", "").strip()
        new_path = request.data.get("new_path", "").strip()

        if not old_path or not new_path:
            return Response({"detail": "Both old_path and new_path are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            safe_old = sanitize_relative_path(old_path)
            safe_new = sanitize_relative_path(new_path)
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        if safe_old == safe_new:
            return Response({"status": True, "message": "Paths are identical."})

        if project.files.filter(path=safe_new).exists():
            return Response({"detail": f"Target path '{safe_new}' already exists."}, status=status.HTTP_400_BAD_REQUEST)

        workspace_dir = get_project_workspace_dir(project.project_id)
        old_disk = resolve_workspace_path(workspace_dir, safe_old)
        new_disk = resolve_workspace_path(workspace_dir, safe_new)

        if old_disk.exists():
            new_disk.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_disk), str(new_disk))

        # Update in database
        exact_file = project.files.filter(path=safe_old).first()
        if exact_file:
            exact_file.path = safe_new
            exact_file.name = os.path.basename(safe_new)
            exact_file.save()

        # Update children if folder
        prefix = f"{safe_old}/"
        children = project.files.filter(path__startswith=prefix)
        for child in children:
            rel_child = child.path[len(safe_old):]
            child.path = f"{safe_new}{rel_child}"
            child.save()

        return Response({
            "status": True,
            "message": f"Renamed '{safe_old}' to '{safe_new}'.",
            "old_path": safe_old,
            "new_path": safe_new,
        })

    @action(detail=False, methods=["post"])
    def move_path(self, request, project_id=None):
        """Move a file or folder into a destination folder."""
        import shutil
        project = get_owned_project(request, project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        source_path = request.data.get("source_path", "").strip()
        target_folder = request.data.get("target_folder", "").strip()

        if not source_path:
            return Response({"detail": "source_path is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            safe_source = sanitize_relative_path(source_path)
            safe_target = sanitize_relative_path(target_folder) if target_folder else ""
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        base_name = os.path.basename(safe_source)
        new_path = f"{safe_target}/{base_name}" if safe_target else base_name

        if safe_source == new_path:
            return Response({"status": True, "message": "Source and destination are identical."})

        if safe_target == safe_source or safe_target.startswith(f"{safe_source}/"):
            return Response({"detail": "Cannot move a folder into itself or one of its descendants."}, status=status.HTTP_400_BAD_REQUEST)

        if project.files.filter(path=new_path).exists():
            return Response({"detail": f"An item named '{base_name}' already exists in destination."}, status=status.HTTP_400_BAD_REQUEST)

        workspace_dir = get_project_workspace_dir(project.project_id)
        old_disk = resolve_workspace_path(workspace_dir, safe_source)
        new_disk = resolve_workspace_path(workspace_dir, new_path)

        if old_disk.exists():
            new_disk.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_disk), str(new_disk))

        exact_file = project.files.filter(path=safe_source).first()
        if exact_file:
            exact_file.path = new_path
            exact_file.name = base_name
            exact_file.save()

        prefix = f"{safe_source}/"
        children = project.files.filter(path__startswith=prefix)
        for child in children:
            rel_child = child.path[len(safe_source):]
            child.path = f"{new_path}{rel_child}"
            child.save()

        return Response({
            "status": True,
            "message": f"Moved '{safe_source}' to '{new_path}'.",
            "source_path": safe_source,
            "new_path": new_path,
        })

    @action(detail=False, methods=["post"])
    def duplicate_file(self, request, project_id=None):
        """Duplicate a file."""
        project = get_owned_project(request, project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        source_path = request.data.get("source_path", "").strip()
        if not source_path:
            return Response({"detail": "source_path is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            safe_source = sanitize_relative_path(source_path)
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        pfile = project.files.filter(path=safe_source).first()
        if not pfile:
            return Response({"detail": f"File '{safe_source}' not found."}, status=status.HTTP_404_NOT_FOUND)

        parent = os.path.dirname(safe_source)
        name, ext = os.path.splitext(pfile.name)
        new_name = f"{name}_copy{ext}"
        new_path = f"{parent}/{new_name}" if parent else new_name

        idx = 2
        while project.files.filter(path=new_path).exists():
            new_name = f"{name}_copy_{idx}{ext}"
            new_path = f"{parent}/{new_name}" if parent else new_name
            idx += 1

        new_pfile = ProjectFile.objects.create(
            file_id=f"file_{uuid.uuid4().hex[:12]}",
            project=project,
            path=new_path,
            name=new_name,
            is_directory=pfile.is_directory,
            content=pfile.content,
            size_bytes=pfile.size_bytes,
        )

        workspace_dir = get_project_workspace_dir(project.project_id)
        disk_path = resolve_workspace_path(workspace_dir, new_path)
        disk_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = disk_path.with_name(f".{disk_path.name}.{uuid.uuid4().hex}.tmp")
        temp_path.write_text(pfile.content, encoding="utf-8", errors="replace")
        os.replace(temp_path, disk_path)

        return Response({
            "status": True,
            "message": f"Duplicated '{safe_source}' to '{new_path}'.",
            "file": ProjectFileSerializer(new_pfile).data
        })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def execute_project_or_code(request):
    """
    Real code execution API.
    Can execute standalone snippet or project file in its workspace.
    """
    user = get_current_user_or_guest(request)
    if not user:
        return Response({"detail": "User required for execution."}, status=status.HTTP_401_UNAUTHORIZED)

    code = request.data.get("code", "")
    language = request.data.get("language", "python").lower().strip()
    stdin = request.data.get("stdin", "")
    project_id = request.data.get("project_id")
    file_path = request.data.get("file_path")

    project = None
    workspace_dir = None
    execution_dir = None
    entry_filename = None

    if project_id:
        project = get_owned_project(request, project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        workspace_dir = sync_db_files_to_workspace(project)
        execution_dir = snapshot_execution_workspace(workspace_dir)
        if file_path:
            entry_filename = os.path.basename(file_path)

    # Perform real execution in sandbox
    try:
        result = run_code_in_sandbox(
            language=language,
            code=code,
            stdin=stdin,
            workspace_dir=execution_dir,
            entry_filename=entry_filename
        )
    finally:
        if execution_dir:
            shutil.rmtree(execution_dir, ignore_errors=True)

    # Check if execution was blocked by Universal Security Firewall
    if result.get("error_code") == "SECURITY_POLICY_VIOLATION" or result.get("execution_status") == "blocked":
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    # Record job in database
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = ExecutionJob.objects.create(
        job_id=job_id,
        user=user,
        project=project,
        language=language,
        execution_type="run",
        status=result["status"],
        stdin=stdin,
        stdout=result["stdout"],
        stderr=result["stderr"],
        exit_code=result["exit_code"],
        duration_ms=result["duration_ms"],
        memory_kb=result["memory_kb"],
    )

    return Response({
        "status": True,
        "job_id": job.job_id,
        "execution_status": result["status"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "exit_code": result["exit_code"],
        "duration_ms": result["duration_ms"],
        "memory_kb": result["memory_kb"],
    })


# ==============================================================================
# SQL PLAYGROUND API ENDPOINTS
# ==============================================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def get_sql_schema(request, project_id):
    """Inspect schema (databases, tables, columns, types, keys) of the project's databases."""
    from .codelab_sql import get_database_schema
    db_name = request.query_params.get("database")
    schema = get_database_schema(project_id, db_name=db_name)
    return Response(schema)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def execute_sql(request, project_id):
    """Execute SQL query against the project's isolated SQLite sandbox."""
    from .codelab_sql import execute_sql_query
    from .security import UniversalSecurityEngine

    query = request.data.get("query") or request.data.get("sql", "")
    active_db = request.data.get("database") or request.data.get("active_database")
    if not query.strip():
        return Response({"status": False, "error": "Query string is required."}, status=status.HTTP_400_BAD_REQUEST)

    sec_violation = UniversalSecurityEngine.evaluate_sql(query, project_id=project_id)
    if sec_violation:
        return Response(sec_violation, status=status.HTTP_400_BAD_REQUEST)

    result = execute_sql_query(project_id, query, active_db=active_db)
    if result.get("error_code") == "SECURITY_POLICY_VIOLATION" or result.get("execution_status") == "blocked":
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def reset_sql_database(request, project_id):
    """Reset the database to a fresh state with chosen seed template."""
    from .codelab_sql import initialize_project_db
    template_key = request.data.get("template", "company_hr")
    active_db = request.data.get("database") or request.data.get("active_database")
    res = initialize_project_db(project_id, template_key, db_name=active_db)
    return Response(res)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def export_sql_csv(request, project_id):
    """Export query output as downloadable CSV."""
    from django.http import HttpResponse
    from .codelab_sql import export_query_as_csv

    query = request.query_params.get("query", "SELECT 1;")
    active_db = request.query_params.get("database")
    csv_stream = export_query_as_csv(project_id, query, active_db=active_db)

    response = HttpResponse(csv_stream.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="query_export_{project_id}.csv"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def list_sql_templates(request):
    """List available seed datasets for practice."""
    from .codelab_sql import SEED_TEMPLATES
    templates_list = [
        {"key": k, "title": v["title"], "description": v["description"]}
        for k, v in SEED_TEMPLATES.items()
    ]
    return Response({"templates": templates_list})


# --- CodeLab Django Environment Endpoints ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def start_django_server(request, project_id):
    """Start isolated Django dev server."""
    from .codelab_django import DjangoProcessManager
    res = DjangoProcessManager.start(project_id)
    return Response(res, status=status.HTTP_200_OK if res.get("status") else status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def stop_django_server(request, project_id):
    """Stop running Django dev server."""
    from .codelab_django import DjangoProcessManager
    res = DjangoProcessManager.stop(project_id)
    return Response(res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def restart_django_server(request, project_id):
    """Restart Django dev server."""
    from .codelab_django import DjangoProcessManager
    res = DjangoProcessManager.restart(project_id)
    return Response(res)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def get_django_server_status(request, project_id):
    """Get status and logs for running Django dev server."""
    from .codelab_django import DjangoProcessManager
    res = DjangoProcessManager.get_status(project_id)
    return Response(res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def run_django_migrations_endpoint(request, project_id):
    """Run makemigrations and migrate against project database."""
    from .codelab_django import run_django_migrations
    res = run_django_migrations(project_id)
    return Response(res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def run_django_makemigrations_endpoint(request, project_id):
    """Run makemigrations against project models."""
    from .codelab_django import run_django_makemigrations
    app_label = request.data.get("app_label", "")
    res = run_django_makemigrations(project_id, app_label=app_label)
    return Response(res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def run_django_migrate_endpoint(request, project_id):
    """Run migrate against project database."""
    from .codelab_django import run_django_migrate
    app_label = request.data.get("app_label", "")
    migration_name = request.data.get("migration_name", "")
    res = run_django_migrate(project_id, app_label=app_label, migration_name=migration_name)
    return Response(res)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def project_django_database_endpoint(request, project_id):
    """Get or set the configured Django database for the project."""
    from .codelab_sql import ProjectDatabaseCatalog
    catalog = ProjectDatabaseCatalog(project_id=project_id)

    if request.method == "POST":
        db_name = request.data.get("database") or request.data.get("database_name")
        try:
            catalog.set_django_database(db_name)
            return Response({
                "status": True,
                "message": f"Django database configured to '{db_name}'.",
                "django_database": catalog.get_django_database(),
                "available_databases": catalog.list_databases(),
                "active_sql_database": catalog.get_active_database_name(),
            })
        except Exception as e:
            return Response({"status": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "status": True,
        "django_database": catalog.get_django_database(),
        "available_databases": catalog.list_databases(),
        "active_sql_database": catalog.get_active_database_name(),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def run_django_showmigrations_endpoint(request, project_id):
    """Run showmigrations against project database."""
    from .codelab_django import run_django_showmigrations
    app_label = request.data.get("app_label", "")
    res = run_django_showmigrations(project_id, app_label=app_label)
    return Response(res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def run_django_sqlmigrate_endpoint(request, project_id):
    """Run sqlmigrate to preview generated SQL for a migration."""
    from .codelab_django import run_django_sqlmigrate
    app_label = request.data.get("app_label", "")
    migration_name = request.data.get("migration_name", "")
    res = run_django_sqlmigrate(project_id, app_label=app_label, migration_name=migration_name)
    return Response(res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def run_django_tests_endpoint(request, project_id):
    """Run Django unit tests against project database."""
    from .codelab_django import run_django_tests
    res = run_django_tests(project_id)
    return Response(res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def test_django_api_endpoint_view(request, project_id):
    """Postman-like API Tester runner."""
    from .codelab_django import test_django_api_endpoint
    method = request.data.get("method", "GET")
    path = request.data.get("path", "/")
    headers = request.data.get("headers", {})
    body = request.data.get("body", "")

    res = test_django_api_endpoint(project_id, method=method, path=path, headers=headers, body=body)
    return Response(res)


from django.views.decorators.clickjacking import xframe_options_exempt

@xframe_options_exempt
def preview_proxy(request, project_id, subpath=""):
    """Unified reverse proxy preview endpoint supporting both Django and PHP."""
    from .codelab_django import DjangoProcessManager, proxy_django_preview_request
    from .codelab_php import PhpProcessManager
    from django.http import HttpResponse

    if not getattr(request.user, "is_authenticated", False):
        return HttpResponse(status=401)
    if not get_owned_project(request, project_id):
        return HttpResponse(status=404)

    django_port = DjangoProcessManager.get_server_port(project_id)
    if django_port:
        return proxy_django_preview_request(request, project_id, subpath=subpath)

    php_port = PhpProcessManager.get_server_port(project_id)
    if php_port:
        clean_subpath = subpath if subpath.startswith("/") else f"/{subpath}"
        query = request.META.get('QUERY_STRING', '')
        target_url = f"http://127.0.0.1:{php_port}{clean_subpath}"
        if query:
            target_url = f"{target_url}?{query}"

        headers = {}
        for k, v in request.headers.items():
            if k.lower() not in ("host", "content-length"):
                headers[k] = v

        try:
            import requests
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.body,
                timeout=10.0,
                allow_redirects=False
            )
            content = resp.content
            content_type = resp.headers.get("Content-Type", "text/html")

            if "text/html" in content_type.lower():
                base_tag = f'<base href="/apps/skiltrix/api/preview/{project_id}/">'
                content_str = resp.text
                if "<head>" in content_str:
                    content_str = content_str.replace("<head>", f"<head>\n    {base_tag}", 1)
                elif "<HEAD>" in content_str:
                    content_str = content_str.replace("<HEAD>", f"<HEAD>\n    {base_tag}", 1)
                else:
                    content_str = f"{base_tag}\n" + content_str
                content = content_str.encode("utf-8")

            response = HttpResponse(content, status=resp.status_code, content_type=content_type)
            if "location" in resp.headers:
                response["Location"] = resp.headers["location"]
            if "set-cookie" in resp.headers:
                response["Set-Cookie"] = resp.headers["set-cookie"]

            response["X-Frame-Options"] = "ALLOWALL"
            response["Access-Control-Allow-Origin"] = "*"
            response["Cross-Origin-Opener-Policy"] = "unsafe-none"
            response["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self';"
            return response
        except Exception as e:
            err_resp = HttpResponse(f"<h3>PHP Gateway Error</h3><p>{str(e)}</p>", status=502, content_type="text/html")
            err_resp["X-Frame-Options"] = "ALLOWALL"
            return err_resp

    return proxy_django_preview_request(request, project_id, subpath=subpath)



# --- CodeLab PHP Environment Endpoints ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def start_php_server(request, project_id):
    """Start isolated PHP development server."""
    from .codelab_php import PhpProcessManager
    res = PhpProcessManager.start(project_id)
    return Response(res, status=status.HTTP_200_OK if res.get("status") else status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def stop_php_server(request, project_id):
    """Stop running PHP development server."""
    from .codelab_php import PhpProcessManager
    res = PhpProcessManager.stop(project_id)
    return Response(res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def restart_php_server(request, project_id):
    """Restart PHP development server."""
    from .codelab_php import PhpProcessManager
    res = PhpProcessManager.restart(project_id)
    return Response(res)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def get_php_server_status(request, project_id):
    """Get status and logs for running PHP development server."""
    from .codelab_php import PhpProcessManager
    res = PhpProcessManager.get_status(project_id)
    return Response(res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def test_php_api_endpoint_view(request, project_id):
    """API Tester runner for PHP."""
    from .codelab_php import test_php_api_endpoint
    method = request.data.get("method", "GET")
    path = request.data.get("path", "/api.php")
    headers = request.data.get("headers", {})
    body = request.data.get("body", "")

    res = test_php_api_endpoint(project_id, method=method, path=path, headers=headers, body=body)
    return Response(res)


# --- CodeLab Django Project Navigation & Management Endpoints ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def run_django_check_endpoint(request, project_id):
    """Run python manage.py check for project."""
    from .codelab_django import run_django_check
    res = run_django_check(project_id)
    return Response(res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def create_django_app_endpoint(request, project_id):
    """Create a new Django app and register it in settings."""
    from .codelab_django import create_django_app
    app_name = request.data.get("app_name", "").strip()
    res = create_django_app(project_id, app_name)
    return Response(res, status=status.HTTP_201_CREATED if res.get("status") else status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def get_django_navigation_endpoint(request, project_id):
    """Get project navigation data (apps, routes, models, migrations, etc.)."""
    from .codelab_django import get_django_navigation
    res = get_django_navigation(project_id)
    return Response(res)


# --- CodeLab Interactive Terminal Command Bridge ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def execute_terminal_command(request, project_id):
    """
    Executes a shell command directly inside the project workspace directory.
    Provides an interactive command execution bridge for the browser terminal.
    """
    command = request.data.get("command", "").strip()
    if not command:
        return Response({"status": False, "error": "Command is required."}, status=status.HTTP_400_BAD_REQUEST)

    import subprocess
    from .codelab_runner import get_project_workspace_dir, sync_workspace_files_to_db
    from .execution.sandbox_policy import ExecutionPolicy
    from .codelab_django import (
        DjangoProcessManager,
        run_django_check,
        create_django_app,
        run_django_makemigrations,
        run_django_migrate,
        run_django_showmigrations,
        run_django_sqlmigrate,
        run_django_migrations,
        get_django_settings_module,
    )

    project = get_owned_project(request, project_id)
    if not project:
        return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
    workspace_dir = get_project_workspace_dir(project_id)

    # Universal Terminal Security Firewall evaluation
    from .security import UniversalSecurityEngine
    is_safe, sec_error, tokens = UniversalSecurityEngine.evaluate_terminal_command(
        command=command,
        workspace_dir=workspace_dir,
        project_id=project_id,
    )
    if not is_safe:
        return Response(sec_error, status=status.HTTP_400_BAD_REQUEST)

    env = ExecutionPolicy.sanitize_environment()
    settings_mod = get_django_settings_module(workspace_dir)
    env["DJANGO_SETTINGS_MODULE"] = settings_mod
    env["PYTHONPATH"] = f"{str(workspace_dir)}{os.pathsep}{env.get('PYTHONPATH', '')}"

    cmd_lower = command.lower().strip()

    if cmd_lower in ("cls", "clear"):
        return Response({"status": True, "output": "\x1b[2J\x1b[H", "exit_code": 0})

    if cmd_lower == "help":
        help_text = (
            "Available Commands:\n"
            "  python manage.py runserver          Start Django development server\n"
            "  python manage.py check              Validate Django models and settings\n"
            "  python manage.py makemigrations     Create model migrations\n"
            "  python manage.py migrate            Apply database migrations\n"
            "  python manage.py startapp <name>    Create a new Django app and register it\n"
            "  python -m venv .venv                Initialize virtual environment\n"
            "  python -m pip install <package>     Install package in workspace\n"
            "  ls / dir                            List workspace files\n"
            "  clear                               Clear terminal output\n"
        )
        return Response({"status": True, "output": help_text, "exit_code": 0})

    # Interceptor 1: python manage.py runserver
    if cmd_lower.startswith("python manage.py runserver"):
        start_res = DjangoProcessManager.start(project_id)
        if start_res.get("status"):
            port = start_res.get("port")
            url = start_res.get("url")
            output = (
                f"Watching for file changes with StatReloader\n"
                f"Performing system checks...\n\n"
                f"System check identified no issues (0 silenced).\n"
                f"Django development server running at http://127.0.0.1:{port}/\n"
                f"Live Preview URL: {url}\n"
                f"Quit the server with Stop Server or Control-C."
            )
            return Response({
                "status": True,
                "exit_code": 0,
                "output": output,
                "cwd": "/",
                "is_server": True,
                "server_port": port,
                "preview_url": url,
            })
        else:
            return Response({
                "status": False,
                "exit_code": 1,
                "output": f"Failed to start server: {start_res.get('error', 'Unknown error')}",
                "cwd": "/"
            })

    # Interceptor 2: python manage.py startapp <app_name>
    if cmd_lower.startswith("python manage.py startapp"):
        parts = command.split()
        if len(parts) >= 4:
            app_name = parts[3]
            app_res = create_django_app(project_id, app_name)
            if app_res.get("status"):
                return Response({
                    "status": True,
                    "exit_code": 0,
                    "output": f"App '{app_name}' created successfully and registered in settings.py.",
                    "cwd": "/"
                })
            else:
                return Response({
                    "status": False,
                    "exit_code": 1,
                    "output": f"Error creating app: {app_res.get('error')}",
                    "cwd": "/"
                })

    # Interceptor 3: python manage.py check
    if cmd_lower in ("python manage.py check", "python manage.py check --deploy"):
        check_res = run_django_check(project_id)
        return Response({
            "status": check_res.get("status", False),
            "exit_code": check_res.get("exit_code", 0),
            "output": check_res.get("output", ""),
            "cwd": "/"
        })

    # Interceptor 4: makemigrations
    if cmd_lower.startswith("python manage.py makemigrations") or cmd_lower.startswith("manage.py makemigrations") or cmd_lower.startswith("makemigrations"):
        parts = command.split()
        app_label = ""
        if "makemigrations" in parts:
            idx = parts.index("makemigrations")
            if idx + 1 < len(parts) and not parts[idx + 1].startswith("-"):
                app_label = parts[idx + 1]
        make_res = run_django_makemigrations(project_id, app_label=app_label)
        if project:
            sync_workspace_files_to_db(project)
        return Response({
            "status": make_res.get("status", False),
            "exit_code": make_res.get("exit_code", 0),
            "output": make_res.get("output", ""),
            "cwd": "/"
        })

    # Interceptor 5: migrate
    if cmd_lower.startswith("python manage.py migrate") or cmd_lower.startswith("manage.py migrate") or cmd_lower.startswith("migrate"):
        parts = command.split()
        app_label = ""
        migration_name = ""
        if "migrate" in parts:
            idx = parts.index("migrate")
            if idx + 1 < len(parts) and not parts[idx + 1].startswith("-"):
                app_label = parts[idx + 1]
            if idx + 2 < len(parts) and not parts[idx + 2].startswith("-"):
                migration_name = parts[idx + 2]
        mig_res = run_django_migrate(project_id, app_label=app_label, migration_name=migration_name)
        if project:
            sync_workspace_files_to_db(project)
        return Response({
            "status": mig_res.get("status", False),
            "exit_code": mig_res.get("exit_code", 0),
            "output": mig_res.get("output", ""),
            "cwd": "/"
        })

    # Interceptor 5b: showmigrations
    if cmd_lower.startswith("python manage.py showmigrations") or cmd_lower.startswith("manage.py showmigrations") or cmd_lower.startswith("showmigrations"):
        parts = command.split()
        app_label = ""
        if "showmigrations" in parts:
            idx = parts.index("showmigrations")
            if idx + 1 < len(parts) and not parts[idx + 1].startswith("-"):
                app_label = parts[idx + 1]
        show_res = run_django_showmigrations(project_id, app_label=app_label)
        return Response({
            "status": show_res.get("status", False),
            "exit_code": show_res.get("exit_code", 0),
            "output": show_res.get("output", ""),
            "cwd": "/"
        })

    # Interceptor 5c: sqlmigrate
    if cmd_lower.startswith("python manage.py sqlmigrate") or cmd_lower.startswith("manage.py sqlmigrate") or cmd_lower.startswith("sqlmigrate"):
        parts = command.split()
        app_label = ""
        migration_name = ""
        if "sqlmigrate" in parts:
            idx = parts.index("sqlmigrate")
            if idx + 1 < len(parts) and not parts[idx + 1].startswith("-"):
                app_label = parts[idx + 1]
            if idx + 2 < len(parts) and not parts[idx + 2].startswith("-"):
                migration_name = parts[idx + 2]
        sql_res = run_django_sqlmigrate(project_id, app_label=app_label, migration_name=migration_name)
        return Response({
            "status": sql_res.get("status", False),
            "exit_code": sql_res.get("exit_code", 0),
            "output": sql_res.get("output", ""),
            "cwd": "/"
        })

    # Interceptor 5: python -m venv .venv
    if cmd_lower.startswith("python -m venv"):
        venv_target = (workspace_dir / ".venv")
        venv_target.mkdir(parents=True, exist_ok=True)
        (venv_target / "pyvenv.cfg").write_text(f"home = {sys.prefix}\ninclude-system-site-packages = true\nversion = {sys.version.split()[0]}\n", encoding="utf-8")
        (venv_target / "Scripts").mkdir(parents=True, exist_ok=True)
        return Response({
            "status": True,
            "exit_code": 0,
            "output": f"Virtual environment initialized at {venv_target}\nActivate with source .venv/bin/activate (or .venv\\Scripts\\activate)",
            "cwd": "/"
        })

    # Interceptor 6: python -m pip install ...
    if cmd_lower.startswith("python -m pip install"):
        pkg = command.split()[-1] if len(command.split()) > 4 else "package"
        # Check if django or requirement
        if "django" in cmd_lower:
            return Response({
                "status": True,
                "exit_code": 0,
                "output": f"Requirement already satisfied: django in {sys.prefix}\\lib\\site-packages\nRequirement already satisfied: asgiref in {sys.prefix}\\lib\\site-packages\nRequirement already satisfied: sqlparse in {sys.prefix}\\lib\\site-packages",
                "cwd": "/"
            })

    base_cmd = tokens[0].lower() if tokens else ""
    if base_cmd in ("dir", "ls"):
        target = workspace_dir
        if len(tokens) > 1:
            clean_sub = tokens[1].strip("'\"")
            target = (workspace_dir / clean_sub).resolve()
        if target.is_dir():
            entries = []
            for item in sorted(target.iterdir()):
                prefix = "<DIR> " if item.is_dir() else f"{item.stat().st_size:>8} "
                entries.append(f"{prefix} {item.name}")
            output = f" Directory of {target.name or '.'}\n\n" + "\n".join(entries)
            return Response({"status": True, "exit_code": 0, "output": output, "cwd": "/"})
        else:
            return Response({"status": False, "exit_code": 1, "output": f"Directory not found: {tokens[1]}", "cwd": "/"})

    if base_cmd in ("cat", "type"):
        if len(tokens) > 1:
            clean_sub = tokens[1].strip("'\"")
            target = (workspace_dir / clean_sub).resolve()
            if target.is_file():
                try:
                    content = target.read_text(encoding="utf-8", errors="replace")
                    return Response({"status": True, "exit_code": 0, "output": content, "cwd": "/"})
                except Exception as ex:
                    return Response({"status": False, "exit_code": 1, "output": str(ex), "cwd": "/"})
            return Response({"status": False, "exit_code": 1, "output": f"File not found: {clean_sub}", "cwd": "/"})

    if base_cmd == "pwd":
        return Response({"status": True, "exit_code": 0, "output": f"/{project_id}", "cwd": "/"})

    if base_cmd == "echo":
        return Response({"status": True, "exit_code": 0, "output": " ".join(tokens[1:]), "cwd": "/"})

    if base_cmd == "whoami":
        return Response({"status": True, "exit_code": 0, "output": "skiltrix-sandbox-user", "cwd": "/"})

    exec_tokens = []
    for t in tokens:
        clean_t = t.strip()
        if (clean_t.startswith('"') and clean_t.endswith('"')) or (clean_t.startswith("'") and clean_t.endswith("'")):
            clean_t = clean_t[1:-1]
        exec_tokens.append(clean_t)
    exec_cmd = [sys.executable] + exec_tokens[1:] if base_cmd in ("python", "python3", "py") else exec_tokens
    try:
        res = subprocess.run(
            exec_cmd,
            shell=False,
            cwd=workspace_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=15.0
        )
        output = res.stdout
        if res.stderr:
            output += ("\n" if output else "") + res.stderr

        # Sync disk changes back to DB
        if project:
            sync_workspace_files_to_db(project)

        return Response({
            "status": True,
            "exit_code": res.returncode,
            "output": output,
            "cwd": "/"
        })
    except subprocess.TimeoutExpired:
        return Response({
            "status": False,
            "exit_code": 124,
            "output": "[Process timed out after 15 seconds]"
        })
    except Exception as e:
        return Response({
            "status": False,
            "exit_code": 1,
            "output": f"[Execution failed: {str(e)}]"
        })


# --- CodeLab Observability & Health Check ---

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@owned_workspace_required
def codelab_health_check(request):
    """
    Returns comprehensive system health, runtime availability, running servers,
    and quota metrics for SkilTrix CodeLab.
    """
    from .codelab_observability import get_system_health_report
    report = get_system_health_report()
    return Response(report, status=status.HTTP_200_OK)





