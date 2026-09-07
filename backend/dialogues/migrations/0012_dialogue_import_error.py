from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('dialogues', '0011_dialogue_published_at_dialogueillustration_origin_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dialogue',
            name='import_error',
            field=models.TextField(blank=True, max_length=2000),
        ),
    ]
