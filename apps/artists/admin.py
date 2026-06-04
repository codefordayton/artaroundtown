from django.contrib import admin
from .models import Artist, Medium


@admin.register(Medium)
class MediumAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['name', 'primary_venue', 'is_active']
    list_filter = ['mediums', 'is_active']
    search_fields = ['name', 'bio']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['mediums']
