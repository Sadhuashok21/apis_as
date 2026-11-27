from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skiltrix", "0021_cmscourse_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="cmspage",
            name="draft_html",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="cmspage",
            name="draft_css",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="cmspage",
            name="draft_js",
            field=models.TextField(blank=True, default=""),
        ),
    ]
