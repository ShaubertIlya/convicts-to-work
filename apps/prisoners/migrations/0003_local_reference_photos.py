from django.db import migrations, models

import apps.prisoners.storage


class Migration(migrations.Migration):
    dependencies = [
        ("prisoners", "0002_prisoner_criminal_article_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="prisoner",
            name="photo",
            field=models.ImageField(
                blank=True,
                storage=apps.prisoners.storage.prisoner_photo_storage,
                upload_to="prisoners/reference/",
            ),
        ),
    ]
