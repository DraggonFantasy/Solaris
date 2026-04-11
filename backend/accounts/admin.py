from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff',
                    'token_budget', 'tokens_used', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Solaris', {'fields': ('bio', 'preferred_language', 'token_budget', 'tokens_used')}),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
