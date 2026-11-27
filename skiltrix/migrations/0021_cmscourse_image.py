from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skiltrix", "0020_coding_assessment_module"),
    ]

    operations = [
        migrations.AddField(
            model_name="cmscourse",
            name="image",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
