from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("skiltrix", "0004_alter_abapsourcefile_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectfile",
            name="revision",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
