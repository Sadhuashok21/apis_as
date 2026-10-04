import uuid
from django.db import models
from sfs.models import AllUsers


class CodeProject(models.Model):
    PROJECT_TYPES = (
        ("single_file", "Single File Program"),
        ("django", "Django Project"),
        ("react", "React Application"),
        ("php", "PHP Application"),
        ("sql", "SQL Workspace"),
        ("fullstack", "Full-Stack Project"),
    )

    STATUS_CHOICES = (
        ("ready", "Ready"),
        ("building", "Building"),
        ("running", "Running"),
        ("stopped", "Stopped"),
        ("error", "Error"),
    )

    project_id = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        related_name="codelab_projects",
        db_column="user_id",
        to_field="user_id",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    project_type = models.CharField(max_length=30, choices=PROJECT_TYPES, default="single_file")
    language = models.CharField(max_length=50, default="python")
    description = models.TextField(blank=True, default="")
    is_public = models.BooleanField(default=False)
    workspace_path = models.CharField(max_length=500, blank=True, default="")
    execution_settings = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ready")
    last_opened_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "st_codelab_projects"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.project_id}) - {self.language}"


class ProjectFile(models.Model):
    file_id = models.CharField(max_length=64, primary_key=True)
    project = models.ForeignKey(
        CodeProject,
        on_delete=models.CASCADE,
        related_name="files",
        db_column="project_id",
    )
    path = models.CharField(max_length=500)
    name = models.CharField(max_length=255)
    is_directory = models.BooleanField(default=False)
    content = models.TextField(blank=True, default="")
    size_bytes = models.IntegerField(default=0)
    mime_type = models.CharField(max_length=100, default="text/plain")
    revision = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "st_codelab_project_files"
        unique_together = ("project", "path")
        ordering = ["path"]

    def __str__(self):
        return f"{self.project_id}:{self.path}"


class ExecutionJob(models.Model):
    EXECUTION_TYPES = (
        ("run", "Run Code"),
        ("test", "Test Evaluation"),
        ("build", "Build Application"),
        ("migration", "Database Migration"),
    )

    STATUS_CHOICES = (
        ("queued", "Queued"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("timeout", "Timeout"),
    )

    job_id = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        related_name="codelab_executions",
        db_column="user_id",
        to_field="user_id",
    )
    project = models.ForeignKey(
        CodeProject,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="execution_jobs",
        db_column="project_id",
    )
    language = models.CharField(max_length=50)
    execution_type = models.CharField(max_length=20, choices=EXECUTION_TYPES, default="run")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    stdin = models.TextField(blank=True, default="")
    stdout = models.TextField(blank=True, default="")
    stderr = models.TextField(blank=True, default="")
    exit_code = models.IntegerField(null=True, blank=True)
    duration_ms = models.FloatField(default=0.0)
    memory_kb = models.FloatField(default=0.0)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_codelab_execution_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.job_id} ({self.language}) - {self.status}"


class SubmissionResult(models.Model):
    VERDICT_CHOICES = (
        ("Accepted", "Accepted"),
        ("Wrong Answer", "Wrong Answer"),
        ("Time Limit Exceeded", "Time Limit Exceeded"),
        ("Memory Limit Exceeded", "Memory Limit Exceeded"),
        ("Runtime Error", "Runtime Error"),
        ("Compile Error", "Compile Error"),
    )

    result_id = models.CharField(max_length=64, primary_key=True)
    submission_id = models.CharField(max_length=50)
    test_case_id = models.CharField(max_length=50)
    verdict = models.CharField(max_length=30, choices=VERDICT_CHOICES)
    execution_time_ms = models.FloatField(default=0.0)
    memory_kb = models.FloatField(default=0.0)
    actual_output = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    class Meta:
        managed = True
        db_table = "st_codelab_submission_results"

    def __str__(self):
        return f"Sub {self.submission_id} - Case {self.test_case_id}: {self.verdict}"


class WorkspaceSession(models.Model):
    STATUS_CHOICES = (
        ("starting", "Starting"),
        ("running", "Running"),
        ("stopped", "Stopped"),
        ("failed", "Failed"),
    )

    session_id = models.CharField(max_length=64, primary_key=True)
    project = models.OneToOneField(
        CodeProject,
        on_delete=models.CASCADE,
        related_name="session",
        db_column="project_id",
    )
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        db_column="user_id",
        to_field="user_id",
    )
    container_id = models.CharField(max_length=128, blank=True, default="")
    allocated_port = models.IntegerField(null=True, blank=True)
    preview_url = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="stopped")
    started_at = models.DateTimeField(null=True, blank=True)
    last_heartbeat = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "st_codelab_workspace_sessions"

    def __str__(self):
        return f"Session {self.session_id} - {self.project_id} ({self.status})"


class DatabaseWorkspace(models.Model):
    DB_TYPES = (
        ("sqlite", "SQLite"),
        ("mysql", "MySQL"),
        ("postgresql", "PostgreSQL"),
    )

    db_id = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        related_name="database_workspaces",
        db_column="user_id",
        to_field="user_id",
    )
    project = models.ForeignKey(
        CodeProject,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="database_workspaces",
        db_column="project_id",
    )
    db_type = models.CharField(max_length=20, choices=DB_TYPES, default="sqlite")
    db_name = models.CharField(max_length=100)
    db_user = models.CharField(max_length=100, blank=True, default="")
    db_password = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    schema_snapshot = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_codelab_database_workspaces"

    def __str__(self):
        return f"{self.db_type} DB: {self.db_name} ({self.user.username})"


class ProjectDependency(models.Model):
    dependency_id = models.CharField(max_length=64, primary_key=True)
    project = models.ForeignKey(
        CodeProject,
        on_delete=models.CASCADE,
        related_name="dependencies",
        db_column="project_id",
    )
    package_name = models.CharField(max_length=150)
    version = models.CharField(max_length=50, blank=True, default="")
    package_manager = models.CharField(max_length=50, default="pip")
    status = models.CharField(max_length=30, default="installed")

    class Meta:
        managed = True
        db_table = "st_codelab_project_dependencies"

    def __str__(self):
        return f"{self.project_id}: {self.package_name}=={self.version}"


class ProjectActivity(models.Model):
    activity_id = models.CharField(max_length=64, primary_key=True)
    project = models.ForeignKey(
        CodeProject,
        on_delete=models.CASCADE,
        related_name="activities",
        db_column="project_id",
    )
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        db_column="user_id",
        to_field="user_id",
    )
    action = models.CharField(max_length=50)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_codelab_project_activities"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.project_id}: {self.action} at {self.timestamp}"
