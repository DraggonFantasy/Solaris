from django.urls import path
from .views import (
    SectionListView, SectionDetailView,
    InterlocutorListView,
    DialogueListView, DialogueDetailView, MyDialoguesView,
    CommentCreateView, CommentApproveView,
    LikeToggleView,
    DialogueOrderListView,
)

urlpatterns = [
    path('sections/', SectionListView.as_view(), name='section_list'),
    path('sections/<slug:slug>/', SectionDetailView.as_view(), name='section_detail'),
    path('interlocutors/', InterlocutorListView.as_view(), name='interlocutor_list'),
    path('dialogues/', DialogueListView.as_view(), name='dialogue_list'),
    path('dialogues/mine/', MyDialoguesView.as_view(), name='my_dialogues'),
    path('dialogues/<int:pk>/', DialogueDetailView.as_view(), name='dialogue_detail'),
    path('dialogues/<int:dialogue_id>/comments/', CommentCreateView.as_view(), name='comment_create'),
    path('dialogues/<int:dialogue_id>/like/', LikeToggleView.as_view(), name='like_toggle'),
    path('comments/<int:pk>/approve/', CommentApproveView.as_view(), name='comment_approve'),
    path('orders/', DialogueOrderListView.as_view(), name='dialogue_orders'),
]
