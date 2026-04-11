from django.contrib import admin
from .models import Section, Interlocutor, Dialogue, DialogueIllustration, Comment, Like, DialogueOrder, AuditLog


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order',)


@admin.register(Interlocutor)
class InterlocutorAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    search_fields = ('name', 'description')


class IllustrationInline(admin.TabularInline):
    model = DialogueIllustration
    extra = 1


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('author', 'text', 'created_at')


@admin.register(Dialogue)
class DialogueAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'human_author', 'llm_name', 'published', 'created_at')
    list_filter = ('published', 'section', 'style')
    search_fields = ('title', 'text', 'summary')
    list_editable = ('published',)
    filter_horizontal = ('interlocutors',)
    inlines = [IllustrationInline, CommentInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'dialogue', 'approved', 'created_at')
    list_filter = ('approved',)
    list_editable = ('approved',)
    actions = ['approve_comments']

    @admin.action(description='Approve selected comments')
    def approve_comments(self, request, queryset):
        queryset.update(approved=True)


@admin.register(DialogueOrder)
class DialogueOrderAdmin(admin.ModelAdmin):
    list_display = ('topic', 'author', 'section', 'fulfilled', 'created_at')
    list_editable = ('fulfilled',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'object_type', 'object_id', 'timestamp')
    list_filter = ('action',)
    readonly_fields = ('user', 'action', 'object_type', 'object_id', 'details', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
