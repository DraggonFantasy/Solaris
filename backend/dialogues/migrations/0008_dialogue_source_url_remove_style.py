from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dialogues', '0007_dialogueinlineimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='dialogue',
            name='source_url',
            field=models.URLField(blank=True, max_length=2048),
        ),
        migrations.AlterField(
            model_name='dialogue',
            name='text',
            field=models.TextField(blank=True),
        ),
        migrations.RemoveField(
            model_name='dialogue',
            name='style',
        ),
    ]
