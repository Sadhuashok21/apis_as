from django.db import models
from sfs.models import AllUsers


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

