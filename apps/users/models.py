from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    is_approved_submitter = models.BooleanField(default=False)
    organization = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    website = models.URLField(blank=True)

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
