from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dialogues', '0008_dialogue_source_url_remove_style'),
    ]

    operations = [
        migrations.AddField(
            model_name='dialogueillustration',
            name='source_key',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddConstraint(
            model_name='dialogueillustration',
            constraint=models.UniqueConstraint(
                condition=~models.Q(source_key=''),
                fields=('dialogue', 'source_key'),
                name='unique_dialogue_illustration_source',
            ),
        ),
    ]
