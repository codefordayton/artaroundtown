from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'is_approved_submitter', 'organization', 'is_staff']
    list_filter = ['is_approved_submitter', 'is_staff', 'is_superuser']
    fieldsets = UserAdmin.fieldsets + (
        ('Art Around Town', {'fields': ('is_approved_submitter', 'organization', 'bio', 'website')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Art Around Town', {'fields': ('is_approved_submitter', 'organization')}),
    )
