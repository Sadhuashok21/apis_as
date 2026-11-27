from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skiltrix", "0026_comments_parent"),
    ]

    operations = [
        migrations.AddField(
            model_name="videos",
            name="chapters",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
