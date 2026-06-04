from django.contrib import admin
from .models import Venue


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'is_active']
    list_filter = ['city', 'state', 'is_active']
    search_fields = ['name', 'city', 'address']
    prepopulated_fields = {'slug': ('name',)}
