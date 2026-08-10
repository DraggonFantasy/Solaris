from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dialogues', '0009_dialogueillustration_source_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='DialogueResourceProposal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resource_type', models.CharField(choices=[('author', 'Author'), ('literature', 'Literature'), ('illustration', 'Illustration'), ('ai_model', 'AI model')], max_length=32)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('image', models.ImageField(blank=True, null=True, upload_to='resource_proposals/illustrations/')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], db_index=True, default='pending', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('dialogue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resource_proposals', to='dialogues.dialogue')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_dialogue_resource_proposals', to=settings.AUTH_USER_MODEL)),
                ('submitted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dialogue_resource_proposals', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
