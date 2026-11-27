from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skiltrix", "0024_courseenrollments_completed_videos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="codingproblems",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("algorithmic", "Algorithmic Problem"),
                    ("debugging", "Backend & Code Debugging"),
                    ("django_debug", "Django Project Debugging"),
                    ("sql", "SQL Query Assessment"),
                ],
                default="algorithmic",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="codingproblems",
            name="project_files",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Starter multi-file workspace {rel_path: content} for Django debugging problems",
            ),
        ),
        migrations.AddField(
            model_name="codingproblems",
            name="hidden_test_files",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Hidden grading test files {rel_path: content} overlaid on submit",
            ),
        ),
    ]
