from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skiltrix", "0022_cmspage_draft_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="courses",
            name="compare_price",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="courses",
            name="discount_percent",
            field=models.FloatField(default=0),
        ),
    ]
