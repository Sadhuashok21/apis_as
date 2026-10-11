from django.db import models
from django.utils import timezone
from sfs.models import AllUsers
import uuid


class TutorialTrack(models.Model):
    """
    Main technology/language learning track (e.g. Java, Python, React, SQL).
    """
    CATEGORY_CHOICES = (
        ("languages", "Programming Languages"),
        ("web", "Web Development"),
        ("backend", "Backend Development"),
        ("databases", "Databases"),
        ("computer_science", "Computer Science"),
        ("cloud_devops", "Cloud & DevOps"),
        ("other_tech", "Other Technology"),
    )

    track_id = models.CharField(max_length=60, primary_key=True, help_text="Slug identifier (e.g. java, python, react)")
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default="languages")
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=60, default="code", help_text="Tech icon name")
    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "st_tutorial_tracks"
        ordering = ["order", "title"]

    def __str__(self):
        return f"{self.title} ({self.track_id})"


class TutorialModule(models.Model):
    """
    Module/Chapter within a tutorial track (e.g. Java Basics, Java OOP).
    """
    LEVEL_CHOICES = (
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
        ("expert", "Expert"),
    )

    module_id = models.CharField(max_length=100, primary_key=True)
    track = models.ForeignKey(TutorialTrack, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="beginner")
    description = models.TextField(blank=True, default="")
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "st_tutorial_modules"
        ordering = ["order", "title"]

    def __str__(self):
        return f"{self.track.title} - {self.title}"


class TutorialLesson(models.Model):
    """
    Individual step-by-step tutorial lesson with explanation, syntax, examples,
    try-it-yourself sandbox, quiz, and coding challenge.
    """
    lesson_id = models.CharField(max_length=120, primary_key=True)
    module = models.ForeignKey(TutorialModule, on_delete=models.CASCADE, related_name="lessons")
    track = models.ForeignKey(TutorialTrack, on_delete=models.CASCADE, related_name="lessons")
    slug = models.SlugField(max_length=100)
    title = models.CharField(max_length=255)
    reading_time_minutes = models.PositiveIntegerField(default=5)
    learning_objectives = models.JSONField(default=list, blank=True)
    explanation = models.TextField(help_text="Detailed educational explanation with markdown/html formatting")
    syntax_code = models.TextField(blank=True, default="")
    code_examples = models.JSONField(default=list, blank=True, help_text="List of runnable code examples with explanation")
    try_it_yourself = models.JSONField(default=dict, blank=True, help_text="Interactive exercise: task, initial_code, expected_output, hints")
    quiz = models.JSONField(default=dict, blank=True, help_text="End-of-lesson quiz: question, options, correct_index, explanation")
    challenge = models.JSONField(default=dict, blank=True, help_text="Coding challenge: title, description, initial_code, test_cases")
    order = models.IntegerField(default=1)
    meta_title = models.CharField(max_length=200, blank=True, default="")
    meta_description = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "st_tutorial_lessons"
        ordering = ["order"]
        unique_together = (("track", "slug"),)

    def __str__(self):
        return f"{self.track.title}: {self.title}"


class TutorialProgress(models.Model):
    """
    Tracks learner completion of lessons, quizzes, challenges, and awarded XP.
    """
    user = models.ForeignKey(AllUsers, on_delete=models.CASCADE, to_field="user_id", db_column="user_id", related_name="tutorial_progress")
    lesson = models.ForeignKey(TutorialLesson, on_delete=models.CASCADE, related_name="user_progress")
    track = models.ForeignKey(TutorialTrack, on_delete=models.CASCADE, related_name="user_progress")
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    quiz_completed = models.BooleanField(default=False)
    quiz_score = models.IntegerField(default=0)
    challenge_completed = models.BooleanField(default=False)
    xp_earned = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "st_tutorial_progress"
        unique_together = (("user", "lesson"),)
        indexes = [
            models.Index(fields=["user", "track", "completed"]),
        ]


class TutorialBookmark(models.Model):
    """
    User bookmarked lessons.
    """
    user = models.ForeignKey(AllUsers, on_delete=models.CASCADE, to_field="user_id", db_column="user_id", related_name="tutorial_bookmarks")
    lesson = models.ForeignKey(TutorialLesson, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "st_tutorial_bookmarks"
        unique_together = (("user", "lesson"),)


class TutorialNote(models.Model):
    """
    Personal notes written by a learner on a specific lesson.
    """
    user = models.ForeignKey(AllUsers, on_delete=models.CASCADE, to_field="user_id", db_column="user_id", related_name="tutorial_notes")
    lesson = models.ForeignKey(TutorialLesson, on_delete=models.CASCADE, related_name="notes")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "st_tutorial_notes"
        unique_together = (("user", "lesson"),)


class TutorialCertificate(models.Model):
    """
    Verifiable Certificate of Course Completion issued by SkilTrix.
    """
    certificate_id = models.CharField(max_length=64, unique=True, primary_key=True)
    user = models.ForeignKey(AllUsers, on_delete=models.CASCADE, to_field="user_id", db_column="user_id", related_name="tutorial_certificates")
    track = models.ForeignKey(TutorialTrack, on_delete=models.CASCADE, related_name="certificates")
    student_name = models.CharField(max_length=150)
    course_name = models.CharField(max_length=200)
    score_percent = models.IntegerField(default=95)
    issued_at = models.DateTimeField(default=timezone.now)
    verification_hash = models.CharField(max_length=128, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "st_tutorial_certificates"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.certificate_id} - {self.student_name} ({self.course_name})"

