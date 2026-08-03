import logging
import re
from urllib.parse import urlparse

from django.db import models
from rest_framework import exceptions, generics, parsers, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import (
    Section, Interlocutor, Dialogue, DialogueIllustration, DialogueInlineImage,
    Comment, Like, DialogueOrder, AuditLog,
)
from .serializers import (
    SectionSerializer, InterlocutorSerializer,
    DialogueListSerializer, DialogueDetailSerializer, DialogueWriteSerializer,
    DialogueModerationSerializer, CommentSerializer, CommentEditSerializer,
    CommentReviewSerializer, DialogueIllustrationSerializer, DialogueInlineImageSerializer,
    DialogueOrderSerializer,
)
from .gemini_illustrations import (
    canonical_gemini_share_url,
    import_gemini_illustrations,
    is_gemini_share_url,
)


logger = logging.getLogger(__name__)


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


def maybe_import_gemini_illustrations(
    dialogue,
    user,
    *,
    previous_status=None,
    previous_source_url=None,
):
    import_statuses = {
        Dialogue.STATUS_SUBMITTED,
        Dialogue.STATUS_PUBLISHED,
    }
    if (
        dialogue.status not in import_statuses
        or not is_gemini_share_url(dialogue.source_url)
    ):
        return

    source_changed = (
        previous_source_url is not None
        and previous_source_url != dialogue.source_url
    )
    entered_import_status = previous_status not in import_statuses
    retry_before_publication = (
        previous_status == Dialogue.STATUS_SUBMITTED
        and dialogue.status == Dialogue.STATUS_PUBLISHED
        and not dialogue.illustrations.exists()
    )
    if not (source_changed or entered_import_status or retry_before_publication):
        return

    try:
        result = import_gemini_illustrations(dialogue)
    except Exception as exc:
        logger.exception(
            "Automatic Gemini illustration import failed for dialogue %s.",
            dialogue.pk,
        )
        AuditLog.objects.create(
            user=user,
            action="import_gemini_illustrations_failed",
            object_type="Dialogue",
            object_id=str(dialogue.id),
            details=str(exc)[:1000],
        )
        return

    action = (
        "import_gemini_illustrations_failed"
        if result.failed and not result.imported
        else "import_gemini_illustrations"
    )
    AuditLog.objects.create(
        user=user,
        action=action,
        object_type="Dialogue",
        object_id=str(dialogue.id),
        details=(
            f"Found: {result.found}; imported: {result.imported}; "
            f"duplicates: {result.skipped_duplicates}; failed: {result.failed}"
        ),
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


class SectionResourcesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        section = generics.get_object_or_404(Section, slug=slug)
        dialogues = (
            Dialogue.objects
            .filter(section=section, status=Dialogue.STATUS_PUBLISHED)
            .select_related('human_author')
            .prefetch_related('illustrations')
        )
        literature = []
        authors = []
        illustrations = []

        for dialogue in dialogues:
            if dialogue.recommended_literature.strip():
                literature.append({
                    'dialogue_id': dialogue.id,
                    'dialogue_title': dialogue.title,
                    'text': dialogue.recommended_literature,
                })

            dialogue_authors = dialogue.authors if isinstance(dialogue.authors, list) else []
            if dialogue_authors:
                for author in dialogue_authors:
                    if not isinstance(author, dict) or not author.get('name'):
                        continue
                    authors.append({
                        'dialogue_id': dialogue.id,
                        'dialogue_title': dialogue.title,
                        'name': author.get('name', ''),
                        'kind': author.get('kind', ''),
                        'version': author.get('version', ''),
                        'description': author.get('description', ''),
                    })
            elif dialogue.human_author:
                authors.append({
                    'dialogue_id': dialogue.id,
                    'dialogue_title': dialogue.title,
                    'name': dialogue.human_author.username,
                    'kind': 'person',
                    'version': '',
                    'description': '',
                })

            for illustration in dialogue.illustrations.all():
                image_url = ''
                if illustration.image:
                    image_url = request.build_absolute_uri(illustration.image.url)
                illustrations.append({
                    'id': illustration.id,
                    'dialogue_id': dialogue.id,
                    'dialogue_title': dialogue.title,
                    'image': image_url,
                    'caption': illustration.caption,
                    'order': illustration.order,
                })

        return Response({
            'section': SectionSerializer(section, context={'request': request}).data,
            'literature': literature,
            'authors': authors,
            'illustrations': illustrations,
        })


class SolarisDialogueContextView(APIView):
    """Public, provider-neutral context that authors can give to any LLM."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        dialogues = (
            Dialogue.objects
            .filter(status=Dialogue.STATUS_PUBLISHED)
            .select_related('section', 'human_author')
            .order_by('section__order', 'created_at')
        )
        entries = []
        markdown_parts = [
            '# Контекст платформи «Соляріс»',
            '',
            'Нижче наведені опубліковані діалоги різних авторів. '
            'Враховуйте їх як спільний контекст нового діалогу.',
        ]
        for dialogue in dialogues:
            author_names = [
                author.get('name', '')
                for author in dialogue.authors if isinstance(author, dict) and author.get('name')
            ] if isinstance(dialogue.authors, list) else []
            entry = {
                'id': dialogue.id,
                'title': dialogue.title,
                'section': dialogue.section.name,
                'summary': dialogue.summary,
                'authors': author_names,
                'model': dialogue.llm_name,
                'literature': dialogue.recommended_literature,
                'source_url': dialogue.source_url,
                'text': dialogue.text,
            }
            entries.append(entry)
            markdown_parts.extend([
                '',
                f'## {dialogue.section.name}: {dialogue.title}',
                f'Автори: {", ".join(author_names)}' if author_names else '',
                f'Модель ШІ: {dialogue.llm_name}' if dialogue.llm_name else '',
                f'Посилання: {dialogue.source_url}' if dialogue.source_url else '',
                '',
                dialogue.summary.strip(),
                '',
                dialogue.text.strip(),
                '',
                f'Рекомендована література: {dialogue.recommended_literature.strip()}'
                if dialogue.recommended_literature.strip() else '',
            ])

        markdown = '\n'.join(part for part in markdown_parts if part is not None).strip()
        return Response({
            'dialogue_count': len(entries),
            'markdown': markdown,
            'dialogues': entries,
        })


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
        qs = Dialogue.objects.select_related('section', 'human_author').prefetch_related('illustrations')
        section_slug = self.request.query_params.get('section')
        if section_slug:
            return qs.filter(section__slug=section_slug, status=Dialogue.STATUS_PUBLISHED)
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
        maybe_import_gemini_illustrations(dialogue, self.request.user)


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
        previous_status = serializer.instance.status
        previous_source_url = serializer.instance.source_url
        dialogue = serializer.save()
        AuditLog.objects.create(
            user=self.request.user, action='update_dialogue',
            object_type='Dialogue', object_id=str(dialogue.id)
        )
        maybe_import_gemini_illustrations(
            dialogue,
            self.request.user,
            previous_status=previous_status,
            previous_source_url=previous_source_url,
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
        previous_status = serializer.instance.status
        previous_source_url = serializer.instance.source_url
        dialogue = serializer.save()
        AuditLog.objects.create(
            user=self.request.user,
            action='moderate_dialogue',
            object_type='Dialogue',
            object_id=str(dialogue.id),
            details=f'Status changed to {dialogue.status}'
        )
        maybe_import_gemini_illustrations(
            dialogue,
            self.request.user,
            previous_status=previous_status,
            previous_source_url=previous_source_url,
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
        'chat.openai.com',
        'claude.ai',
        'gemini.google.com',
        'share.gemini.google',
        'share.google',
        'g.co',
    }

    def host_is_allowed(self, hostname):
        hostname = (hostname or '').lower().rstrip('.')
        return any(
            hostname == allowed or hostname.endswith(f'.{allowed}')
            for allowed in self.allowed_hosts
        )

    def post(self, request):
        url = (request.data.get('url') or '').strip()
        if not url:
            return Response({'detail': 'Share URL is required.'}, status=status.HTTP_400_BAD_REQUEST)

        parsed = urlparse(url)
        if parsed.scheme not in {'http', 'https'} or not self.host_is_allowed(parsed.hostname):
            return Response({'detail': 'Unsupported share URL.'}, status=status.HTTP_400_BAD_REQUEST)
        if (parsed.hostname or '').lower().rstrip('.') == 'g.co' and not is_gemini_share_url(url):
            return Response({'detail': 'Unsupported share URL.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from llm_shared_chat import extract_share
        except ImportError:
            return Response(
                {'detail': 'Shared chat extractor is not installed.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            extract_url = canonical_gemini_share_url(url) if is_gemini_share_url(url) else url
            conversation = extract_share(extract_url)
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
            raise exceptions.PermissionDenied('You cannot edit illustrations for this dialogue.')
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
            raise exceptions.PermissionDenied('You cannot edit this illustration.')

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


class DialogueInlineImageCreateView(generics.CreateAPIView):
    serializer_class = DialogueInlineImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def perform_create(self, serializer):
        dialogue = generics.get_object_or_404(Dialogue, pk=self.kwargs['dialogue_id'])
        if not can_edit_dialogue(self.request.user, dialogue):
            raise exceptions.PermissionDenied('You cannot add inline images to this dialogue.')
        inline_image = serializer.save(dialogue=dialogue)
        AuditLog.objects.create(
            user=self.request.user,
            action='create_inline_image',
            object_type='DialogueInlineImage',
            object_id=str(inline_image.id),
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
