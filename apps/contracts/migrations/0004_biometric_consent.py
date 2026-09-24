from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contracts", "0003_employmentcontract_organization_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="biometricsignatureattempt",
            name="consent_acknowledged_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
