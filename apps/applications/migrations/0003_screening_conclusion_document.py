from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0002_jobapplication_organization_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="screening",
            name="conclusion_document",
            field=models.FileField(
                blank=True,
                upload_to="screenings/conclusions/%Y/%m/",
            ),
        ),
    ]
