from django.db import migrations, models


def seed_initial_roadmaps(apps, schema_editor):
    LearningRoadmap = apps.get_model("skiltrix", "LearningRoadmap")
    from skiltrix.roadmap_views import OFFICIAL_ROADMAPS

    for idx, rm in enumerate(OFFICIAL_ROADMAPS, start=1):
        LearningRoadmap.objects.update_or_create(
            key=rm["key"],
            defaults={
                "title": rm["title"],
                "category": rm.get("category", "Web Development"),
                "badge": rm.get("badge", "INFOGRAPHICS TIMELINE"),
                "description": rm.get("description", ""),
                "icon": rm.get("icon", "code"),
                "accent_color": rm.get("accent_color", "#3B82F6"),
                "estimated_weeks": rm.get("estimated_weeks", "12-16 Weeks"),
                "stages": rm.get("stages", []),
                "order": idx,
                "is_active": True,
            },
        )


def unseed_initial_roadmaps(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("skiltrix", "0028_videos_lesson_content"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningRoadmap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=64, unique=True)),
                ("title", models.CharField(max_length=150)),
                ("category", models.CharField(default="Web Development", max_length=80)),
                ("badge", models.CharField(default="INFOGRAPHICS TIMELINE", max_length=80)),
                ("description", models.TextField(blank=True, default="")),
                ("icon", models.CharField(default="code", max_length=40)),
                ("accent_color", models.CharField(default="#3B82F6", max_length=20)),
                ("estimated_weeks", models.CharField(default="12-16 Weeks", max_length=40)),
                ("stages", models.JSONField(blank=True, default=list)),
                ("order", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "skiltrix_roadmaps",
                "ordering": ["order", "id"],
                "managed": True,
            },
        ),
        migrations.RunPython(seed_initial_roadmaps, unseed_initial_roadmaps),
    ]
