from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dialogues', '0006_backfill_section_names'),
    ]

    operations = [
        migrations.CreateModel(
            name='DialogueInlineImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='dialogue_inline_images/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('dialogue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inline_images', to='dialogues.dialogue')),
            ],
        ),
    ]
