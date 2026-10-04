"""
SkilTrix SAP ABAP Lab - Data Models
Defines all entities for:
1. ABAP Projects and Source Files (Reports, Classes, Includes, DDIC)
2. Question Repository & Test Cases (Beginner, Intermediate, Advanced)
3. Submissions and Verdict History
4. Enterprise SAP System Connection Profiles (server-side secure credentials)
5. SE11 ABAP Dictionary Table Definitions
6. User Progress and Workspace Sessions
"""

from django.db import models
from sfs.models import AllUsers


class ABAPProject(models.Model):
    """Represents a student or developer's ABAP project workspace."""
    EXECUTION_MODES = [
        ("simulator", "Educational ABAP Simulator"),
        ("sap_connected", "Real SAP ABAP System"),
    ]

    project_id = models.CharField(max_length=50, primary_key=True)
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        db_column="user_id",
        to_field="user_id",
        related_name="abap_projects"
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    package_name = models.CharField(max_length=30, default="$TMP")
    execution_mode = models.CharField(max_length=20, choices=EXECUTION_MODES, default="simulator")
    sap_system_id = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="ready")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_opened_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "abap_projects"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.package_name})"


class ABAPSourceFile(models.Model):
    """An individual ABAP development object within an ABAPProject."""
    OBJECT_TYPES = [
        ("report", "Executable Report (PROG)"),
        ("include", "ABAP Include (INCL)"),
        ("class", "ABAP Class (CLAS)"),
        ("interface", "ABAP Interface (INTF)"),
        ("function_module", "Function Module (FUNC)"),
        ("ddic_table", "Dictionary Table (TABL)"),
        ("structure", "Dictionary Structure (STRU)"),
        ("folder", "Folder Directory"),
        ("other", "General File"),
    ]

    file_id = models.CharField(max_length=50, primary_key=True)
    project = models.ForeignKey(
        ABAPProject,
        on_delete=models.CASCADE,
        related_name="source_files"
    )
    name = models.CharField(max_length=255)
    object_type = models.CharField(max_length=30, choices=OBJECT_TYPES, default="report")
    content = models.TextField(blank=True)
    size_bytes = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "abap_source_files"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} [{self.object_type}]"


class ABAPExercise(models.Model):
    """An educational ABAP coding challenge in the question repository."""
    CATEGORIES = [
        ("Beginner", "Beginner: Syntax, Types, Control Flow"),
        ("Intermediate", "Intermediate: Internal Tables, SQL, Modularization"),
        ("Advanced", "Advanced: OO ABAP, CDS, RAP, OData"),
    ]
    DIFFICULTIES = [
        ("Easy", "Easy"),
        ("Medium", "Medium"),
        ("Hard", "Hard"),
    ]
    SUPPORTED_MODES = [
        ("simulator", "Simulator Only"),
        ("sap_only", "SAP System Only"),
        ("both", "Simulator & Real SAP"),
    ]

    exercise_id = models.CharField(max_length=50, primary_key=True)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORIES, default="Beginner")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTIES, default="Easy")
    topic = models.CharField(max_length=100, default="Basic Syntax")
    problem_statement = models.TextField()
    starter_code = models.TextField()
    solution_hint = models.TextField(blank=True)
    supported_mode = models.CharField(max_length=20, choices=SUPPORTED_MODES, default="simulator")
    points = models.IntegerField(default=10)
    order = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "abap_exercises"
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"[{self.difficulty}] {self.title}"


class ABAPTestCase(models.Model):
    """Sample and hidden evaluation test cases for ABAP exercises."""
    test_case_id = models.CharField(max_length=50, primary_key=True)
    exercise = models.ForeignKey(
        ABAPExercise,
        on_delete=models.CASCADE,
        related_name="test_cases"
    )
    input_data = models.TextField(blank=True)
    expected_output = models.TextField()
    is_sample = models.BooleanField(default=True)
    is_hidden = models.BooleanField(default=False)
    order = models.IntegerField(default=1)

    class Meta:
        managed = True
        db_table = "abap_test_cases"
        ordering = ["order"]

    def __str__(self):
        return f"Test #{self.order} for {self.exercise.title} (Hidden: {self.is_hidden})"


class ABAPSubmission(models.Model):
    """Tracks a student's solution submission and evaluation verdict."""
    VERDICTS = [
        ("Accepted", "Accepted"),
        ("Wrong Answer", "Wrong Answer"),
        ("Syntax Error", "Syntax Error"),
        ("Runtime Error", "Runtime Error"),
        ("Time Limit Exceeded", "Time Limit Exceeded"),
    ]

    submission_id = models.CharField(max_length=50, primary_key=True)
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        db_column="user_id",
        to_field="user_id"
    )
    exercise = models.ForeignKey(
        ABAPExercise,
        on_delete=models.CASCADE,
        related_name="submissions"
    )
    source_code = models.TextField()
    execution_mode = models.CharField(max_length=20, default="simulator")
    verdict = models.CharField(max_length=30, choices=VERDICTS)
    passed_tests = models.IntegerField(default=0)
    total_tests = models.IntegerField(default=0)
    execution_time_ms = models.FloatField(default=0.0)
    diagnostics = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "abap_submissions"
        ordering = ["-created_at"]


class SAPSystemConnection(models.Model):
    """
    Secure server-side storage of authorized SAP development system connections.
    Supports S/4HANA On-Premise, NetWeaver AS ABAP, and SAP BTP Steampunk tenants.
    Credentials are NEVER transmitted to frontend clients.
    """
    AUTH_TYPES = [
        ("basic", "Basic Authentication (User/Password)"),
        ("oauth2_btp", "SAP BTP OAuth 2.0 (Service Key)"),
        ("jwt_token", "JWT Bearer Token"),
    ]

    connection_id = models.CharField(max_length=50, primary_key=True)
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        db_column="user_id",
        to_field="user_id",
        related_name="sap_connections"
    )
    system_name = models.CharField(max_length=100)
    system_id = models.CharField(max_length=10) # e.g. S4H, NPL, TRL
    client = models.CharField(max_length=5, default="100")
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=443)
    auth_type = models.CharField(max_length=30, choices=AUTH_TYPES, default="basic")
    username = models.CharField(max_length=100, blank=True)
    encrypted_password = models.TextField(blank=True) # Server-side encrypted
    btp_service_key_json = models.TextField(blank=True) # Encrypted BTP OAuth JSON
    is_active = models.BooleanField(default=True)
    last_connection_test = models.DateTimeField(null=True, blank=True)
    last_status_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "sap_system_connections"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.system_name} ({self.system_id}/{self.client})"


class ABAPDictionaryTable(models.Model):
    """Represents a simulated SE11 Dictionary transparent table design."""
    table_id = models.CharField(max_length=50, primary_key=True)
    project = models.ForeignKey(
        ABAPProject,
        on_delete=models.CASCADE,
        related_name="dictionary_tables",
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        db_column="user_id",
        to_field="user_id",
        null=True,
        blank=True
    )
    table_name = models.CharField(max_length=30)
    description = models.CharField(max_length=200)
    delivery_class = models.CharField(max_length=1, default="A")
    fields_schema = models.JSONField(default=list) # [{field, key, type, length, desc}]
    sample_records = models.JSONField(default=list, blank=True) # [{col: val}]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "abap_dictionary_tables"
        ordering = ["table_name"]

    def __str__(self):
        return self.table_name


class ABAPLearningProgress(models.Model):
    """Tracks student progress, points, and streaks in the ABAP curriculum."""
    progress_id = models.CharField(max_length=50, primary_key=True)
    user = models.OneToOneField(
        AllUsers,
        on_delete=models.CASCADE,
        db_column="user_id",
        to_field="user_id",
        related_name="abap_progress"
    )
    completed_exercises = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    current_streak_days = models.IntegerField(default=0)
    last_active_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "abap_learning_progress"

    def __str__(self):
        return f"Progress for {self.user.username}: {self.completed_exercises} completed"

