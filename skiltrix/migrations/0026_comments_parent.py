from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("skiltrix", "0025_codingproblems_django_project"),
    ]

    operations = [
        migrations.AddField(
            model_name="comments",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="replies",
                to="skiltrix.comments",
            ),
        ),
    ]
