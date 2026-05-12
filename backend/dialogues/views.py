from django.db import models
import re
from urllib.parse import urlparse
from rest_framework import generics, parsers, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Section, Interlocutor, Dialogue, DialogueIllustration, Comment, Like, DialogueOrder, AuditLog
from .serializers import (
    SectionSerializer, InterlocutorSerializer,
    DialogueListSerializer, DialogueDetailSerializer, DialogueWriteSerializer,
    DialogueModerationSerializer, CommentSerializer, CommentEditSerializer,
    CommentReviewSerializer, DialogueIllustrationSerializer, DialogueOrderSerializer
)


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.human_author == request.user or request.user.is_staff


class IsAuthorEditableOrStaff(permissions.BasePermission):
    editable_statuses = {
        Dialogue.STATUS_DRAFT,
        Dialogue.STATUS_CHANGES_REQUESTED,
        Dialogue.STATUS_REJECTED,
    }

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.human_author == request.user and obj.status in self.editable_statuses


def can_edit_dialogue(user, dialogue):
    if user.is_staff:
        return True
    return (
        dialogue.human_author == user
        and dialogue.status in IsAuthorEditableOrStaff.editable_statuses
    )


class SectionListView(generics.ListCreateAPIView):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class SectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


class InterlocutorListView(generics.ListCreateAPIView):
    queryset = Interlocutor.objects.all().order_by('name')
    serializer_class = InterlocutorSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        interlocutor = serializer.save(created_by=self.request.user)
        AuditLog.objects.create(
            user=self.request.user, action='create_interlocutor',
            object_type='Interlocutor', object_id=str(interlocutor.id)
        )


class DialogueListView(generics.ListCreateAPIView):
    serializer_class = DialogueListSerializer

    def get_queryset(self):
        qs = Dialogue.objects.select_related('section', 'human_author')
        section_slug = self.request.query_params.get('section')
        if section_slug:
            qs = qs.filter(section__slug=section_slug)
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(status=Dialogue.STATUS_PUBLISHED)
        return qs

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DialogueWriteSerializer
        return DialogueListSerializer

    def perform_create(self, serializer):
        dialogue = serializer.save(human_author=self.request.user)
        AuditLog.objects.create(
            user=self.request.user, action='create_dialogue',
            object_type='Dialogue', object_id=str(dialogue.id),
            details=f'Created dialogue: {dialogue.title}'
        )


class DialogueDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        qs = Dialogue.objects.all()
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(models.Q(status=Dialogue.STATUS_PUBLISHED) | models.Q(human_author=user))
        return qs.filter(status=Dialogue.STATUS_PUBLISHED)

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return DialogueDetailSerializer
        return DialogueWriteSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsAuthorEditableOrStaff()]

    def perform_update(self, serializer):
        dialogue = serializer.save()
        AuditLog.objects.create(
            user=self.request.user, action='update_dialogue',
            object_type='Dialogue', object_id=str(dialogue.id)
        )

    def perform_destroy(self, instance):
        AuditLog.objects.create(
            user=self.request.user, action='delete_dialogue',
            object_type='Dialogue', object_id=str(instance.id),
            details=f'Deleted: {instance.title}'
        )
        instance.delete()


class MyDialoguesView(generics.ListAPIView):
    serializer_class = DialogueListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Dialogue.objects.filter(
            human_author=self.request.user
        ).select_related('section', 'human_author')


class DialogueReviewListView(generics.ListAPIView):
    serializer_class = DialogueListSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        status_filter = self.request.query_params.get('status')
        qs = Dialogue.objects.select_related('section', 'human_author')
        if status_filter:
            return qs.filter(status=status_filter)
        return qs.exclude(status=Dialogue.STATUS_DRAFT)


class DialogueModerateView(generics.UpdateAPIView):
    queryset = Dialogue.objects.all()
    serializer_class = DialogueModerationSerializer
    permission_classes = [permissions.IsAdminUser]
    http_method_names = ['patch', 'post', 'options']

    def post(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        dialogue = serializer.save()
        AuditLog.objects.create(
            user=self.request.user,
            action='moderate_dialogue',
            object_type='Dialogue',
            object_id=str(dialogue.id),
            details=f'Status changed to {dialogue.status}'
        )


class DialogueWithdrawView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        dialogue = generics.get_object_or_404(Dialogue, pk=pk)
        is_author = dialogue.human_author == request.user
        if not (is_author or request.user.is_staff):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if dialogue.status != Dialogue.STATUS_SUBMITTED:
            return Response(
                {'detail': 'Only submitted dialogues can be withdrawn.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dialogue.status = Dialogue.STATUS_DRAFT
        dialogue.save(update_fields=['status', 'published', 'updated_at'])
        AuditLog.objects.create(
            user=request.user,
            action='withdraw_dialogue',
            object_type='Dialogue',
            object_id=str(dialogue.id),
            details='Withdrawn from review'
        )
        return Response(DialogueDetailSerializer(dialogue, context={'request': request}).data)


class DialogueImportShareView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    allowed_hosts = {
        'chatgpt.com',
        'claude.ai',
        'gemini.google.com',
    }

    def post(self, request):
        url = (request.data.get('url') or '').strip()
        if not url:
            return Response({'detail': 'Share URL is required.'}, status=status.HTTP_400_BAD_REQUEST)

        parsed = urlparse(url)
        if parsed.scheme not in {'http', 'https'} or parsed.netloc not in self.allowed_hosts:
            return Response({'detail': 'Unsupported share URL.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from llm_shared_chat import extract_share
        except ImportError:
            return Response(
                {'detail': 'Shared chat extractor is not installed.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            conversation = extract_share(url)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        messages = conversation.get('messages') or []
        markdown = self.to_markdown(messages, conversation.get('service'))
        if not markdown.strip():
            return Response({'detail': 'No visible messages found.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'service': conversation.get('service') or '',
            'title': conversation.get('title') or '',
            'markdown': markdown,
            'message_count': len(messages),
        })

    def to_markdown(self, messages, service):
        service_name = {
            'chatgpt': 'ChatGPT',
            'claude': 'Claude',
            'gemini': 'Gemini',
        }.get(service, 'ШІ')
        speaker_names = {
            'user': 'Користувач',
            'assistant': service_name,
            'model': service_name,
        }
        parts = []
        for message in messages:
            content = (message.get('content') or '').strip()
            if not content:
                continue
            content = self.demote_markdown_headings(content)
            role = (message.get('role') or '').lower()
            speaker = speaker_names.get(role, role.title() or service_name)
            parts.append(f'## {speaker}\n\n{content}')
        return '\n\n'.join(parts)

    def demote_markdown_headings(self, content):
        return re.sub(
            r'^(#{1,6})(\s+)',
            lambda match: f'{"#" * min(len(match.group(1)) + 1, 6)}{match.group(2)}',
            content,
            flags=re.MULTILINE,
        )


class DialogueIllustrationCreateView(generics.CreateAPIView):
    serializer_class = DialogueIllustrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def perform_create(self, serializer):
        dialogue = generics.get_object_or_404(Dialogue, pk=self.kwargs['dialogue_id'])
        if not can_edit_dialogue(self.request.user, dialogue):
            raise permissions.PermissionDenied('You cannot edit illustrations for this dialogue.')
        illustration = serializer.save(dialogue=dialogue)
        AuditLog.objects.create(
            user=self.request.user,
            action='create_illustration',
            object_type='DialogueIllustration',
            object_id=str(illustration.id),
        )


class DialogueIllustrationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DialogueIllustrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    http_method_names = ['patch', 'delete', 'options']

    def get_queryset(self):
        return DialogueIllustration.objects.select_related('dialogue', 'dialogue__human_author')

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if not can_edit_dialogue(request.user, obj.dialogue):
            raise permissions.PermissionDenied('You cannot edit this illustration.')

    def perform_update(self, serializer):
        illustration = serializer.save()
        AuditLog.objects.create(
            user=self.request.user,
            action='update_illustration',
            object_type='DialogueIllustration',
            object_id=str(illustration.id),
        )

    def perform_destroy(self, instance):
        illustration_id = instance.id
        instance.delete()
        AuditLog.objects.create(
            user=self.request.user,
            action='delete_illustration',
            object_type='DialogueIllustration',
            object_id=str(illustration_id),
        )


class CommentCreateView(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        dialogue = generics.get_object_or_404(
            Dialogue,
            pk=self.kwargs['dialogue_id'],
            status=Dialogue.STATUS_PUBLISHED,
        )
        parent = serializer.validated_data.get('parent')
        if parent and parent.dialogue_id != dialogue.id:
            raise serializers.ValidationError({'parent': 'Parent comment belongs to another dialogue.'})
        if parent and not parent.approved:
            raise serializers.ValidationError({'parent': 'Replies to unpublished comments are not allowed.'})
        comment = serializer.save(
            author=self.request.user,
            dialogue=dialogue,
            approved=self.request.user.is_staff,
        )
        AuditLog.objects.create(
            user=self.request.user, action='create_comment',
            object_type='Comment', object_id=str(comment.id)
        )


class CommentUpdateView(generics.UpdateAPIView):
    serializer_class = CommentEditSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch', 'put', 'options']

    def get_queryset(self):
        return Comment.objects.filter(author=self.request.user, approved=False)

    def perform_update(self, serializer):
        comment = serializer.save()
        AuditLog.objects.create(
            user=self.request.user, action='update_comment',
            object_type='Comment', object_id=str(comment.id)
        )


class CommentReviewListView(generics.ListAPIView):
    serializer_class = CommentReviewSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = Comment.objects.select_related('author', 'dialogue', 'parent', 'parent__author')
        approved = self.request.query_params.get('approved')
        if approved == 'true':
            return qs.filter(approved=True)
        if approved == 'all':
            return qs
        return qs.filter(approved=False)


class CommentApproveView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        comment = generics.get_object_or_404(Comment, pk=pk)
        comment.approved = True
        comment.save()
        AuditLog.objects.create(
            user=request.user, action='approve_comment',
            object_type='Comment', object_id=str(comment.id)
        )
        return Response({'status': 'approved'})


class CommentModerateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        comment = generics.get_object_or_404(Comment, pk=pk)
        action = request.data.get('action')
        if action == 'approve':
            comment.approved = True
            comment.save(update_fields=['approved'])
            AuditLog.objects.create(
                user=request.user, action='approve_comment',
                object_type='Comment', object_id=str(comment.id)
            )
            return Response(CommentReviewSerializer(comment).data)
        if action == 'reject':
            comment_id = comment.id
            comment.delete()
            AuditLog.objects.create(
                user=request.user, action='reject_comment',
                object_type='Comment', object_id=str(comment_id)
            )
            return Response({'status': 'rejected'})
        return Response(
            {'detail': 'Unsupported moderation action.'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LikeToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, dialogue_id):
        dialogue = generics.get_object_or_404(Dialogue, pk=dialogue_id, status=Dialogue.STATUS_PUBLISHED)
        like, created = Like.objects.get_or_create(dialogue=dialogue, user=request.user)
        if not created:
            like.delete()
            return Response({'liked': False, 'likes_count': dialogue.likes_count})
        return Response({'liked': True, 'likes_count': dialogue.likes_count})


class DialogueOrderListView(generics.ListCreateAPIView):
    serializer_class = DialogueOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return DialogueOrder.objects.all()
        return DialogueOrder.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
