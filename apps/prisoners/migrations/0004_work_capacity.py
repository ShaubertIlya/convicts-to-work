from django.db import migrations, models


def label_demo_prisoners(apps, schema_editor):
    Prisoner = apps.get_model("prisoners", "Prisoner")
    demo_iins = [f"900101{index:06d}" for index in range(1, 21)]
    demo = Prisoner.objects.filter(
        iin__in=demo_iins, criminal_article__endswith="(тестовые данные)"
    )
    demo.filter(iin__in=["900101000006", "900101000011"]).update(work_capacity="UNABLE")
    demo.exclude(iin__in=["900101000006", "900101000011"]).update(work_capacity="CAPABLE")


class Migration(migrations.Migration):
    dependencies = [
        ("prisoners", "0003_local_reference_photos"),
    ]

    operations = [
        migrations.AddField(
            model_name="prisoner",
            name="work_capacity",
            field=models.CharField(
                choices=[
                    ("UNKNOWN", "Не установлено"),
                    ("CAPABLE", "Трудоспособен"),
                    ("UNABLE", "Нетрудоспособен"),
                ],
                default="UNKNOWN",
                max_length=16,
            ),
        ),
        migrations.RunPython(label_demo_prisoners, migrations.RunPython.noop),
    ]
