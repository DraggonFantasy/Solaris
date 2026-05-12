from django.db import migrations


SECTION_NAME_UPDATES = {
    'worldview-ai': 'Світогляд',
    'epistemology-ai': 'Теорія пізнання',
    'learning-ai': 'Навчання',
    'psychology-ai': 'Психологія',
    'language-logic-ai': 'Мова, логіка',
    'heuristics-ai': 'Евристика',
}


def remove_ai_suffix_from_section_names(apps, schema_editor):
    Section = apps.get_model('dialogues', 'Section')
    for slug, name in SECTION_NAME_UPDATES.items():
        Section.objects.filter(slug=slug).update(name=name)


def restore_ai_suffix_in_section_names(apps, schema_editor):
    Section = apps.get_model('dialogues', 'Section')
    for slug, name in SECTION_NAME_UPDATES.items():
        Section.objects.filter(slug=slug).update(name=f'{name} та ШІ')


class Migration(migrations.Migration):

    dependencies = [
        ('dialogues', '0005_comment_parent'),
    ]

    operations = [
        migrations.RunPython(
            remove_ai_suffix_from_section_names,
            restore_ai_suffix_in_section_names,
        ),
    ]
