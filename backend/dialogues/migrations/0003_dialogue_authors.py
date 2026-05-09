# Generated for Solaris dialogue author metadata.

from django.db import migrations, models


def seed_authors_from_existing_fields(apps, schema_editor):
    Dialogue = apps.get_model('dialogues', 'Dialogue')
    for dialogue in Dialogue.objects.select_related('human_author'):
        authors = []
        if dialogue.human_author_id:
            user = dialogue.human_author
            display_name = ' '.join(
                part for part in (user.first_name, user.last_name) if part
            ) or user.username
            authors.append({
                'kind': 'person',
                'name': display_name,
                'description': getattr(user, 'bio', '') or '',
                'is_current_user': True,
            })
        if dialogue.llm_name:
            authors.append({
                'kind': 'ai_model',
                'name': dialogue.llm_name,
                'version': dialogue.llm_version,
                'description': '',
            })
        dialogue.authors = authors
        dialogue.save(update_fields=['authors', 'published'])


class Migration(migrations.Migration):

    dependencies = [
        ('dialogues', '0002_dialogue_status_moderation_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='dialogue',
            name='authors',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(seed_authors_from_existing_fields, migrations.RunPython.noop),
    ]
