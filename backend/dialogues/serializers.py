import ipaddress
from urllib.parse import urlparse

from django.db import models
from rest_framework import serializers
from .models import (
    Section, Interlocutor, Dialogue, DialogueIllustration, DialogueInlineImage,
    Comment, Like, DialogueOrder,
)


AI_PROVIDERS = (
    ('gemini.google.com', 'Gemini'),
    ('share.gemini.google', 'Gemini'),
    ('share.google', 'Gemini'),
    ('chatgpt.com', 'ChatGPT'),
    ('chat.openai.com', 'ChatGPT'),
    ('claude.ai', 'Claude'),
    ('grok.com', 'Grok'),
    ('copilot.microsoft.com', 'Microsoft Copilot'),
    ('perplexity.ai', 'Perplexity'),
)


def infer_ai_provider(url):
    parsed = urlparse(url or '')
    hostname = (parsed.hostname or '').lower().rstrip('.')
    path_parts = [part for part in parsed.path.split('/') if part]
    if hostname == 'g.co' and len(path_parts) >= 3 and path_parts[:2] == ['gemini', 'share']:
        return 'Gemini'
    for domain, provider in AI_PROVIDERS:
        if hostname == domain or hostname.endswith(f'.{domain}'):
            return provider
    return hostname.removeprefix('www.')


def validate_external_url(value):
    value = (value or '').strip()
    if not value:
        return value
    parsed = urlparse(value)
    hostname = (parsed.hostname or '').lower().rstrip('.')
    if parsed.scheme not in {'http', 'https'} or not hostname:
        raise serializers.ValidationError('Enter a valid public HTTP(S) URL.')
    if parsed.username or parsed.password:
        raise serializers.ValidationError('Credentials are not allowed in a dialogue URL.')
    if hostname == 'localhost' or hostname.endswith('.local'):
        raise serializers.ValidationError('The dialogue URL must point to a public external resource.')
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise serializers.ValidationError('The dialogue URL must point to a public external resource.')
    return value


def normalize_dialogue_authors(authors, human_author, source_url):
    normalized = []
    human_name = ''
    if human_author:
        human_name = ' '.join(
            part for part in (human_author.first_name, human_author.last_name) if part
        ).strip() or human_author.username

    for author in authors if isinstance(authors, list) else []:
        if not isinstance(author, dict) or not str(author.get('name', '')).strip():
            continue
        if author.get('is_current_user') or author.get('is_source_model'):
            continue
        if human_name and author.get('kind') == 'person' and author.get('name') == human_name:
            continue
        normalized.append(author)

    if human_author:
        normalized.insert(0, {
            'kind': 'person',
            'name': human_name,
            'version': '',
            'description': human_author.bio or '',
            'is_current_user': True,
        })

    provider = infer_ai_provider(source_url)
    if provider:
        normalized.append({
            'kind': 'ai_model',
            'name': provider,
            'version': '',
            'description': '',
            'is_source_model': True,
        })
    return normalized


class SectionSerializer(serializers.ModelSerializer):
    dialogue_count = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = ('id', 'name', 'slug', 'brief', 'icon', 'order', 'dialogue_count')

    def get_dialogue_count(self, obj):
        return obj.dialogues.filter(published=True).count()


class InterlocutorSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Interlocutor
        fields = ('id', 'name', 'description', 'created_by_username', 'created_at')
        read_only_fields = ('created_at',)


class DialogueIllustrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DialogueIllustration
        fields = ('id', 'image', 'caption', 'order')


class DialogueInlineImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DialogueInlineImage
        fields = ('id', 'image')


class CommentSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    author_username = serializers.CharField(source='author.username', read_only=True)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Comment.objects.all(), required=False, allow_null=True
    )
    parent_author_username = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            'id', 'parent', 'parent_author_username', 'author_id', 'author_username',
            'text', 'approved', 'created_at',
        )
        read_only_fields = ('approved', 'created_at')

    def get_parent_author_username(self, obj):
        if not obj.parent_id:
            return ''
        return obj.parent.author.username


class CommentEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('text',)


class CommentReviewSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    dialogue_id = serializers.IntegerField(source='dialogue.id', read_only=True)
    dialogue_title = serializers.CharField(source='dialogue.title', read_only=True)
    parent = serializers.SerializerMethodField()
    parent_author_username = serializers.SerializerMethodField()
    parent_text = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            'id', 'author_username', 'dialogue_id', 'dialogue_title',
            'parent', 'parent_author_username', 'parent_text',
            'text', 'approved', 'created_at',
        )
        read_only_fields = fields

    def get_parent(self, obj):
        return obj.parent_id

    def get_parent_author_username(self, obj):
        if not obj.parent_id:
            return ''
        return obj.parent.author.username

    def get_parent_text(self, obj):
        if not obj.parent_id:
            return ''
        return obj.parent.text


class DialogueListSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.name', read_only=True)
    section_slug = serializers.CharField(source='section.slug', read_only=True)
    human_author_username = serializers.CharField(source='human_author.username', read_only=True)
    review_note = serializers.SerializerMethodField()
    illustrations = DialogueIllustrationSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dialogue
        fields = ('id', 'title', 'section', 'section_name', 'section_slug', 'source_url', 'summary',
                  'recommended_literature', 'illustrations',
                  'human_author_username', 'authors', 'llm_name', 'llm_version',
                  'status', 'review_note', 'moderation_note', 'published', 'created_at',
                  'likes_count', 'comments_count')

    def get_review_note(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return ''
        if request.user.is_staff or obj.human_author_id == request.user.id:
            return obj.review_note
        return ''


class DialogueDetailSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.name', read_only=True)
    section_slug = serializers.CharField(source='section.slug', read_only=True)
    human_author_username = serializers.CharField(source='human_author.username', read_only=True)
    human_author_bio = serializers.CharField(source='human_author.bio', read_only=True)
    interlocutors = InterlocutorSerializer(many=True, read_only=True)
    illustrations = DialogueIllustrationSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    user_has_liked = serializers.SerializerMethodField()
    review_note = serializers.SerializerMethodField()

    class Meta:
        model = Dialogue
        fields = ('id', 'title', 'section', 'section_name', 'section_slug', 'source_url', 'text', 'summary',
                  'food_for_thought', 'recommended_literature',
                  'human_author_username', 'human_author_bio',
                  'authors', 'llm_name', 'llm_version', 'interlocutors', 'illustrations',
                  'status', 'review_note', 'moderation_note', 'published', 'created_at', 'updated_at',
                  'likes_count', 'user_has_liked', 'comments')

    def get_comments(self, obj):
        if obj.status != Dialogue.STATUS_PUBLISHED:
            return []
        qs = obj.comments.select_related('author', 'parent', 'parent__author').filter(approved=True)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if request.user.is_staff:
                qs = obj.comments.select_related('author', 'parent', 'parent__author').all()
            else:
                qs = obj.comments.select_related('author', 'parent', 'parent__author').filter(
                    models.Q(approved=True) | models.Q(author=request.user)
                )
        visible = list(qs)
        visible.sort(key=lambda comment: comment.created_at)
        return CommentSerializer(visible, many=True).data

    def get_user_has_liked(self, obj):
        if obj.status != Dialogue.STATUS_PUBLISHED:
            return False
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_review_note(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return ''
        if request.user.is_staff or obj.human_author_id == request.user.id:
            return obj.review_note
        return ''


class DialogueWriteSerializer(serializers.ModelSerializer):
    source_url = serializers.URLField(
        max_length=2048, required=False, allow_blank=True,
        validators=[validate_external_url],
    )
    interlocutor_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Interlocutor.objects.all(),
        source='interlocutors', required=False
    )

    class Meta:
        model = Dialogue
        fields = ('id', 'title', 'section', 'source_url', 'text', 'summary', 'food_for_thought',
                  'recommended_literature', 'llm_name', 'llm_version',
                  'authors', 'review_note', 'interlocutor_ids', 'status', 'published')
        read_only_fields = ('id', 'published')

    def validate_status(self, value):
        request = self.context.get('request')
        if request and request.user.is_staff:
            return value
        allowed = {Dialogue.STATUS_DRAFT, Dialogue.STATUS_SUBMITTED}
        if value not in allowed:
            raise serializers.ValidationError('Only draft or submitted status is allowed.')
        return value

    def validate(self, attrs):
        if attrs.get('published') and not attrs.get('status'):
            attrs['status'] = Dialogue.STATUS_SUBMITTED
        request = self.context.get('request')
        if (
            request
            and request.user.is_staff
            and attrs.get('status') == Dialogue.STATUS_SUBMITTED
        ):
            attrs['status'] = Dialogue.STATUS_PUBLISHED
        authors = attrs.get('authors')
        if authors is not None and not isinstance(authors, list):
            raise serializers.ValidationError({'authors': 'Authors must be a list.'})
        next_status = attrs.get('status', getattr(self.instance, 'status', Dialogue.STATUS_DRAFT))
        source_url = attrs.get('source_url', getattr(self.instance, 'source_url', ''))
        text = attrs.get('text', getattr(self.instance, 'text', ''))
        has_source = bool((source_url or '').strip() or (text or '').strip())
        if next_status in {Dialogue.STATUS_SUBMITTED, Dialogue.STATUS_PUBLISHED} and not has_source:
            raise serializers.ValidationError(
                'Provide either a public link to the external dialogue or paste the dialogue text.'
            )
        return attrs

    def create(self, validated_data):
        validated_data['authors'] = normalize_dialogue_authors(
            validated_data.get('authors', []),
            validated_data.get('human_author'),
            validated_data.get('source_url', ''),
        )
        provider = infer_ai_provider(validated_data.get('source_url', ''))
        if provider:
            validated_data['llm_name'] = provider
        return super().create(validated_data)

    def update(self, instance, validated_data):
        source_url = validated_data.get('source_url', instance.source_url)
        validated_data['authors'] = normalize_dialogue_authors(
            validated_data.get('authors', instance.authors),
            instance.human_author,
            source_url,
        )
        provider = infer_ai_provider(source_url)
        if provider:
            validated_data['llm_name'] = provider
        return super().update(instance, validated_data)


class DialogueModerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dialogue
        fields = ('status', 'moderation_note')

    def validate_status(self, value):
        allowed = {
            Dialogue.STATUS_SUBMITTED,
            Dialogue.STATUS_CHANGES_REQUESTED,
            Dialogue.STATUS_REJECTED,
            Dialogue.STATUS_PUBLISHED,
            Dialogue.STATUS_ARCHIVED,
        }
        if value not in allowed:
            raise serializers.ValidationError('Unsupported moderation status.')
        has_source = bool(
            (self.instance.source_url or '').strip() or (self.instance.text or '').strip()
        )
        if value == Dialogue.STATUS_PUBLISHED and not has_source:
            raise serializers.ValidationError(
                'A dialogue link or pasted dialogue text is required before publication.'
            )
        return value


class DialogueOrderSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    section_name = serializers.CharField(source='section.name', read_only=True)

    class Meta:
        model = DialogueOrder
        fields = ('id', 'author_username', 'topic', 'description', 'section',
                  'section_name', 'created_at', 'fulfilled')
        read_only_fields = ('created_at', 'fulfilled')
