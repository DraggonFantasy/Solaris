# Generated for Solaris moderation workflow.

from django.db import migrations, models


def copy_published_to_status(apps, schema_editor):
    Dialogue = apps.get_model('dialogues', 'Dialogue')
    Dialogue.objects.filter(published=True).update(status='published')
    Dialogue.objects.filter(published=False).update(status='draft')


class Migration(migrations.Migration):

    dependencies = [
        ('dialogues', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dialogue',
            name='moderation_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='dialogue',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('submitted', 'Submitted for review'),
                    ('changes_requested', 'Changes requested'),
                    ('rejected', 'Rejected'),
                    ('published', 'Published'),
                    ('archived', 'Archived'),
                ],
                default='draft',
                max_length=32,
            ),
        ),
        migrations.RunPython(copy_published_to_status, migrations.RunPython.noop),
    ]
