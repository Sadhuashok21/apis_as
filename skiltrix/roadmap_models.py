from django.db import models
from sfs.models import AllUsers


class LearningRoadmap(models.Model):
    """Stores admin-configurable career learning roadmaps and their stages."""

    key = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=80, default="Web Development")
    badge = models.CharField(max_length=80, default="INFOGRAPHICS TIMELINE")
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=40, default="code")
    accent_color = models.CharField(max_length=20, default="#3B82F6")
    estimated_weeks = models.CharField(max_length=40, default="12-16 Weeks")
    stages = models.JSONField(default=list, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "skiltrix_roadmaps"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.title} ({self.key})"


class LearningRoadmapProgress(models.Model):
    """
    Stores user completion of stages in the 7 career roadmaps
    (frontend_roadmap, backend_roadmap, fullstack_roadmap, python_fullstack_roadmap,
     java_roadmap, android_roadmap, cyber_security_roadmap)
    matching the Android app's RoadmapProgressEntity and ProgressManager.
    """
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="roadmap_progress"
    )
    roadmap_key = models.CharField(max_length=64, db_index=True)
    stage_number = models.IntegerField()
    completed = models.BooleanField(default=True)
    completed_subtopics = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "skiltrix_roadmap_progress"
        unique_together = ("user", "roadmap_key", "stage_number")
        indexes = [
            models.Index(fields=["user", "roadmap_key"]),
            models.Index(fields=["roadmap_key", "stage_number"]),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.roadmap_key} - Stage {self.stage_number} ({self.completed})"

