from django.db import models
from rest_framework import serializers
from .models import Section, Interlocutor, Dialogue, DialogueIllustration, Comment, Like, DialogueOrder


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


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'author_username', 'text', 'approved', 'created_at')
        read_only_fields = ('approved', 'created_at')


class CommentReviewSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    dialogue_id = serializers.IntegerField(source='dialogue.id', read_only=True)
    dialogue_title = serializers.CharField(source='dialogue.title', read_only=True)

    class Meta:
        model = Comment
        fields = (
            'id', 'author_username', 'dialogue_id', 'dialogue_title',
            'text', 'approved', 'created_at',
        )
        read_only_fields = fields


class DialogueListSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.name', read_only=True)
    section_slug = serializers.CharField(source='section.slug', read_only=True)
    human_author_username = serializers.CharField(source='human_author.username', read_only=True)
    review_note = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dialogue
        fields = ('id', 'title', 'section', 'section_name', 'section_slug', 'summary', 'style',
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
        fields = ('id', 'title', 'section', 'section_name', 'section_slug', 'text', 'summary',
                  'food_for_thought', 'recommended_literature', 'style',
                  'human_author_username', 'human_author_bio',
                  'authors', 'llm_name', 'llm_version', 'interlocutors', 'illustrations',
                  'status', 'review_note', 'moderation_note', 'published', 'created_at', 'updated_at',
                  'likes_count', 'user_has_liked', 'comments')

    def get_comments(self, obj):
        if obj.status != Dialogue.STATUS_PUBLISHED:
            return []
        qs = obj.comments.filter(approved=True)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if request.user.is_staff:
                qs = obj.comments.all()
            else:
                qs = obj.comments.filter(models.Q(approved=True) | models.Q(author=request.user))
        return CommentSerializer(qs, many=True).data

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
    interlocutor_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Interlocutor.objects.all(),
        source='interlocutors', required=False
    )

    class Meta:
        model = Dialogue
        fields = ('id', 'title', 'section', 'text', 'summary', 'food_for_thought',
                  'recommended_literature', 'style', 'llm_name', 'llm_version',
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
        authors = attrs.get('authors')
        if authors is not None and not isinstance(authors, list):
            raise serializers.ValidationError({'authors': 'Authors must be a list.'})
        return attrs


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
        return value


class DialogueOrderSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    section_name = serializers.CharField(source='section.name', read_only=True)

    class Meta:
        model = DialogueOrder
        fields = ('id', 'author_username', 'topic', 'description', 'section',
                  'section_name', 'created_at', 'fulfilled')
        read_only_fields = ('created_at', 'fulfilled')
