from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dialogues', '0003_dialogue_authors'),
    ]

    operations = [
        migrations.AddField(
            model_name='dialogue',
            name='review_note',
            field=models.TextField(blank=True),
        ),
    ]
