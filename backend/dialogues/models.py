from django.db import models
from django.conf import settings


class Section(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    brief = models.TextField(blank=True)
    icon = models.ImageField(upload_to='section_icons/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Interlocutor(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(help_text='Worldview, education, historical period, etc.')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name='interlocutors'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Dialogue(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_CHANGES_REQUESTED = 'changes_requested'
    STATUS_REJECTED = 'rejected'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted for review'),
        (STATUS_CHANGES_REQUESTED, 'Changes requested'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    title = models.CharField(max_length=500)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='dialogues')
    source_url = models.URLField(max_length=2048, blank=True)
    text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    food_for_thought = models.TextField(blank=True)
    recommended_literature = models.TextField(blank=True)
    human_author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name='dialogues'
    )
    authors = models.JSONField(default=list, blank=True)
    llm_name = models.CharField(max_length=100, blank=True)
    llm_version = models.CharField(max_length=100, blank=True)
    interlocutors = models.ManyToManyField(Interlocutor, blank=True, related_name='dialogues')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    review_note = models.TextField(blank=True)
    moderation_note = models.TextField(blank=True)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.published = self.status == self.STATUS_PUBLISHED
        super().save(*args, **kwargs)

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.filter(approved=True).count()


class DialogueIllustration(models.Model):
    dialogue = models.ForeignKey(Dialogue, on_delete=models.CASCADE, related_name='illustrations')
    image = models.ImageField(upload_to='illustrations/')
    caption = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    source_key = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(
                fields=('dialogue', 'source_key'),
                condition=~models.Q(source_key=''),
                name='unique_dialogue_illustration_source',
            ),
        ]

    def __str__(self):
        return f'Illustration for "{self.dialogue.title}"'


class DialogueResourceProposal(models.Model):
    RESOURCE_AUTHOR = 'author'
    RESOURCE_LITERATURE = 'literature'
    RESOURCE_ILLUSTRATION = 'illustration'
    RESOURCE_AI_MODEL = 'ai_model'

    RESOURCE_TYPE_CHOICES = [
        (RESOURCE_AUTHOR, 'Author'),
        (RESOURCE_LITERATURE, 'Literature'),
        (RESOURCE_ILLUSTRATION, 'Illustration'),
        (RESOURCE_AI_MODEL, 'AI model'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    dialogue = models.ForeignKey(
        Dialogue,
        on_delete=models.CASCADE,
        related_name='resource_proposals',
    )
    resource_type = models.CharField(max_length=32, choices=RESOURCE_TYPE_CHOICES)
    payload = models.JSONField(default=dict, blank=True)
    image = models.ImageField(
        upload_to='resource_proposals/illustrations/',
        blank=True,
        null=True,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='dialogue_resource_proposals',
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_dialogue_resource_proposals',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.get_resource_type_display()} proposal for "{self.dialogue.title}"'


class DialogueInlineImage(models.Model):
    dialogue = models.ForeignKey(Dialogue, on_delete=models.CASCADE, related_name='inline_images')
    image = models.ImageField(upload_to='dialogue_inline_images/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Inline image for "{self.dialogue.title}"'


class Comment(models.Model):
    dialogue = models.ForeignKey(Dialogue, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    text = models.TextField()
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on "{self.dialogue.title}"'


class Like(models.Model):
    dialogue = models.ForeignKey(Dialogue, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('dialogue', 'user')


class DialogueOrder(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dialogue_orders'
    )
    topic = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    fulfilled = models.BooleanField(default=False)

    def __str__(self):
        return f'Order: {self.topic}'


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.user} — {self.action} at {self.timestamp}'
