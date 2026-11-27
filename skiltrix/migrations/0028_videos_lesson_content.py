from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skiltrix", "0027_videos_chapters"),
    ]

    operations = [
        migrations.AddField(
            model_name="videos",
            name="code_language",
            field=models.CharField(blank=True, default="python", max_length=30),
        ),
        migrations.AddField(
            model_name="videos",
            name="code_snippet",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="videos",
            name="lesson_notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="videos",
            name="transcript",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
