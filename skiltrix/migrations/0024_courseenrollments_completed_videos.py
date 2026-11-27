from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skiltrix", "0023_courses_compare_price_discount"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseenrollments",
            name="completed_videos",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
