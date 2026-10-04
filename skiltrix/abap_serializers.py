"""
SkilTrix SAP ABAP Lab - REST API Serializers
"""

from rest_framework import serializers
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


class ABAPSourceFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ABAPSourceFile
        fields = [
            "file_id",
            "name",
            "object_type",
            "content",
            "size_bytes",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ABAPProjectListSerializer(serializers.ModelSerializer):
    files_count = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ABAPProject
        fields = [
            "project_id",
            "title",
            "slug",
            "package_name",
            "execution_mode",
            "sap_system_id",
            "description",
            "status",
            "files_count",
            "owner_username",
            "last_opened_at",
            "created_at",
            "updated_at",
        ]

    def get_files_count(self, obj):
        return obj.source_files.count()


class ABAPProjectDetailSerializer(serializers.ModelSerializer):
    source_files = ABAPSourceFileSerializer(many=True, read_only=True)
    owner_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ABAPProject
        fields = [
            "project_id",
            "title",
            "slug",
            "package_name",
            "execution_mode",
            "sap_system_id",
            "description",
            "status",
            "owner_username",
            "source_files",
            "last_opened_at",
            "created_at",
            "updated_at",
        ]


class ABAPTestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ABAPTestCase
        fields = [
            "test_case_id",
            "input_data",
            "expected_output",
            "is_sample",
            "order",
        ]
        # Notice: is_hidden test cases must NEVER expose expected_output to public clients!


class ABAPExerciseListSerializer(serializers.ModelSerializer):
    submissions_count = serializers.SerializerMethodField()

    class Meta:
        model = ABAPExercise
        fields = [
            "exercise_id",
            "title",
            "slug",
            "category",
            "difficulty",
            "topic",
            "supported_mode",
            "points",
            "order",
            "submissions_count",
            "created_at",
        ]

    def get_submissions_count(self, obj):
        return obj.submissions.count()


class ABAPExerciseDetailSerializer(serializers.ModelSerializer):
    sample_test_cases = serializers.SerializerMethodField()

    class Meta:
        model = ABAPExercise
        fields = [
            "exercise_id",
            "title",
            "slug",
            "category",
            "difficulty",
            "topic",
            "problem_statement",
            "starter_code",
            "solution_hint",
            "supported_mode",
            "points",
            "order",
            "sample_test_cases",
            "created_at",
        ]

    def get_sample_test_cases(self, obj):
        samples = obj.test_cases.filter(is_sample=True).order_by("order")
        return ABAPTestCaseSerializer(samples, many=True).data


class ABAPSubmissionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    exercise_title = serializers.CharField(source="exercise.title", read_only=True)

    class Meta:
        model = ABAPSubmission
        fields = [
            "submission_id",
            "username",
            "exercise",
            "exercise_title",
            "source_code",
            "execution_mode",
            "verdict",
            "passed_tests",
            "total_tests",
            "execution_time_ms",
            "diagnostics",
            "created_at",
        ]


class SAPSystemConnectionSerializer(serializers.ModelSerializer):
    """Safely serializes connection metadata while strictly masking passwords/keys."""
    has_credentials = serializers.SerializerMethodField()

    class Meta:
        model = SAPSystemConnection
        fields = [
            "connection_id",
            "system_name",
            "system_id",
            "client",
            "host",
            "port",
            "auth_type",
            "username",
            "has_credentials",
            "is_active",
            "last_connection_test",
            "last_status_message",
            "created_at",
        ]
        read_only_fields = ["last_connection_test", "last_status_message", "created_at"]

    def get_has_credentials(self, obj):
        return bool(obj.encrypted_password or obj.btp_service_key_json)


class ABAPDictionaryTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = ABAPDictionaryTable
        fields = [
            "table_id",
            "project",
            "table_name",
            "description",
            "delivery_class",
            "fields_schema",
            "sample_records",
            "created_at",
            "updated_at",
        ]


class ABAPLearningProgressSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ABAPLearningProgress
        fields = [
            "progress_id",
            "username",
            "completed_exercises",
            "total_points",
            "current_streak_days",
            "last_active_at",
        ]

