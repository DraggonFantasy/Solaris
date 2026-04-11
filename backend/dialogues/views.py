from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Section, Interlocutor, Dialogue, Comment, Like, DialogueOrder, AuditLog
from .serializers import (
    SectionSerializer, InterlocutorSerializer,
    DialogueListSerializer, DialogueDetailSerializer, DialogueWriteSerializer,
    CommentSerializer, DialogueOrderSerializer
)


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.human_author == request.user or request.user.is_staff


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
            qs = qs.filter(published=True)
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
    queryset = Dialogue.objects.all()

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return DialogueDetailSerializer
        return DialogueWriteSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsAuthorOrReadOnly()]

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


class CommentCreateView(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        dialogue = generics.get_object_or_404(Dialogue, pk=self.kwargs['dialogue_id'])
        comment = serializer.save(author=self.request.user, dialogue=dialogue)
        AuditLog.objects.create(
            user=self.request.user, action='create_comment',
            object_type='Comment', object_id=str(comment.id)
        )


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


class LikeToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, dialogue_id):
        dialogue = generics.get_object_or_404(Dialogue, pk=dialogue_id, published=True)
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
