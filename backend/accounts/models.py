from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    bio = models.TextField(blank=True)
    preferred_language = models.CharField(max_length=10, default='uk')
    token_budget = models.IntegerField(default=0, help_text='Max tokens allowed (0 = unlimited)')
    tokens_used = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    @property
    def is_over_budget(self):
        if self.token_budget == 0:
            return False
        return self.tokens_used >= self.token_budget
