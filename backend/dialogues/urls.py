from django.urls import path
from .views import (
    SectionListView, SectionDetailView,
    InterlocutorListView,
    DialogueListView, DialogueDetailView, MyDialoguesView,
    DialogueReviewListView, DialogueModerateView, DialogueWithdrawView,
    CommentCreateView, CommentUpdateView, CommentReviewListView, CommentApproveView, CommentModerateView,
    LikeToggleView,
    DialogueOrderListView,
)

urlpatterns = [
    path('sections/', SectionListView.as_view(), name='section_list'),
    path('sections/<slug:slug>/', SectionDetailView.as_view(), name='section_detail'),
    path('interlocutors/', InterlocutorListView.as_view(), name='interlocutor_list'),
    path('dialogues/', DialogueListView.as_view(), name='dialogue_list'),
    path('dialogues/mine/', MyDialoguesView.as_view(), name='my_dialogues'),
    path('dialogues/review/', DialogueReviewListView.as_view(), name='dialogue_review_list'),
    path('dialogues/<int:pk>/', DialogueDetailView.as_view(), name='dialogue_detail'),
    path('dialogues/<int:pk>/moderate/', DialogueModerateView.as_view(), name='dialogue_moderate'),
    path('dialogues/<int:pk>/withdraw/', DialogueWithdrawView.as_view(), name='dialogue_withdraw'),
    path('dialogues/<int:dialogue_id>/comments/', CommentCreateView.as_view(), name='comment_create'),
    path('dialogues/<int:dialogue_id>/like/', LikeToggleView.as_view(), name='like_toggle'),
    path('comments/review/', CommentReviewListView.as_view(), name='comment_review_list'),
    path('comments/<int:pk>/', CommentUpdateView.as_view(), name='comment_update'),
    path('comments/<int:pk>/moderate/', CommentModerateView.as_view(), name='comment_moderate'),
    path('comments/<int:pk>/approve/', CommentApproveView.as_view(), name='comment_approve'),
    path('orders/', DialogueOrderListView.as_view(), name='dialogue_orders'),
]
