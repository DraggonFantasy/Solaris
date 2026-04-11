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


class DialogueListSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.name', read_only=True)
    human_author_username = serializers.CharField(source='human_author.username', read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dialogue
        fields = ('id', 'title', 'section', 'section_name', 'summary', 'style',
                  'human_author_username', 'llm_name', 'llm_version',
                  'published', 'created_at', 'likes_count', 'comments_count')


class DialogueDetailSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.name', read_only=True)
    human_author_username = serializers.CharField(source='human_author.username', read_only=True)
    human_author_bio = serializers.CharField(source='human_author.bio', read_only=True)
    interlocutors = InterlocutorSerializer(many=True, read_only=True)
    illustrations = DialogueIllustrationSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    user_has_liked = serializers.SerializerMethodField()

    class Meta:
        model = Dialogue
        fields = ('id', 'title', 'section', 'section_name', 'text', 'summary',
                  'food_for_thought', 'recommended_literature', 'style',
                  'human_author_username', 'human_author_bio',
                  'llm_name', 'llm_version', 'interlocutors', 'illustrations',
                  'published', 'created_at', 'updated_at',
                  'likes_count', 'user_has_liked', 'comments')

    def get_comments(self, obj):
        approved = obj.comments.filter(approved=True)
        return CommentSerializer(approved, many=True).data

    def get_user_has_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False


class DialogueWriteSerializer(serializers.ModelSerializer):
    interlocutor_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Interlocutor.objects.all(),
        source='interlocutors', required=False
    )

    class Meta:
        model = Dialogue
        fields = ('title', 'section', 'text', 'summary', 'food_for_thought',
                  'recommended_literature', 'style', 'llm_name', 'llm_version',
                  'interlocutor_ids', 'published')


class DialogueOrderSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    section_name = serializers.CharField(source='section.name', read_only=True)

    class Meta:
        model = DialogueOrder
        fields = ('id', 'author_username', 'topic', 'description', 'section',
                  'section_name', 'created_at', 'fulfilled')
        read_only_fields = ('created_at', 'fulfilled')
