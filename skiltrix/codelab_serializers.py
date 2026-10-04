from rest_framework import serializers
from .codelab_models import (
    CodeProject,
    ProjectFile,
    ExecutionJob,
    SubmissionResult,
    WorkspaceSession,
    DatabaseWorkspace,
    ProjectDependency,
    ProjectActivity,
)


class ProjectFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFile
        fields = [
            "file_id",
            "project",
            "path",
            "name",
            "is_directory",
            "content",
            "size_bytes",
            "mime_type",
            "updated_at",
            "revision",
        ]
        read_only_fields = ["file_id", "size_bytes", "updated_at", "revision"]


class ProjectFileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFile
        fields = [
            "file_id",
            "path",
            "name",
            "is_directory",
            "size_bytes",
            "mime_type",
            "updated_at",
            "revision",
        ]


class CodeProjectSerializer(serializers.ModelSerializer):
    files_count = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = CodeProject
        fields = [
            "project_id",
            "title",
            "slug",
            "project_type",
            "language",
            "description",
            "is_public",
            "status",
            "execution_settings",
            "files_count",
            "owner_username",
            "last_opened_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["project_id", "slug", "created_at", "updated_at", "last_opened_at"]

    def get_files_count(self, obj):
        return obj.files.filter(is_directory=False).count()


class CodeProjectDetailSerializer(serializers.ModelSerializer):
    files = ProjectFileListSerializer(many=True, read_only=True)
    owner_username = serializers.CharField(source="user.username", read_only=True)
    preview_url = serializers.CharField(source="session.preview_url", read_only=True, default="")
    session_status = serializers.CharField(source="session.status", read_only=True, default="stopped")

    class Meta:
        model = CodeProject
        fields = [
            "project_id",
            "title",
            "slug",
            "project_type",
            "language",
            "description",
            "is_public",
            "execution_settings",
            "status",
            "owner_username",
            "preview_url",
            "session_status",
            "files",
            "last_opened_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["project_id", "slug", "created_at", "updated_at", "last_opened_at"]


class ExecutionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionJob
        fields = [
            "job_id",
            "user",
            "project",
            "language",
            "execution_type",
            "status",
            "stdin",
            "stdout",
            "stderr",
            "exit_code",
            "duration_ms",
            "memory_kb",
            "error_message",
            "created_at",
        ]
        read_only_fields = [
            "job_id",
            "user",
            "status",
            "stdout",
            "stderr",
            "exit_code",
            "duration_ms",
            "memory_kb",
            "error_message",
            "created_at",
        ]


class SubmissionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionResult
        fields = [
            "result_id",
            "submission_id",
            "test_case_id",
            "verdict",
            "execution_time_ms",
            "memory_kb",
            "actual_output",
            "error_message",
        ]


class WorkspaceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceSession
        fields = [
            "session_id",
            "project",
            "status",
            "allocated_port",
            "preview_url",
            "started_at",
            "last_heartbeat",
            "expires_at",
        ]


class DatabaseWorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatabaseWorkspace
        fields = [
            "db_id",
            "user",
            "project",
            "db_type",
            "db_name",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["db_id", "created_at"]
