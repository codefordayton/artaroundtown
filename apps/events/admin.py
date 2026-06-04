from django.contrib import admin
from .models import Event, EventStatus


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'display_location', 'status', 'submitted_by', 'created_at']
    list_filter = ['status', 'start_date']
    search_fields = ['title', 'description', 'submitter_name', 'submitter_email']
    readonly_fields = ['created_at', 'updated_at', 'submitted_by', 'submitter_name', 'submitter_email']
    actions = ['approve_events', 'reject_events']

    fieldsets = (
        (None, {'fields': ('title', 'slug', 'status')}),
        ('Submitter', {'fields': ('submitted_by', 'submitter_name', 'submitter_email')}),
        ('Dates', {'fields': (
            'start_date', 'end_date',
            'opening_reception_date', 'opening_reception_time',
            'artist_talk_date', 'artist_talk_time',
            'closing_reception_date', 'closing_reception_time',
        )}),
        ('Location', {'fields': ('venue', 'location_name')}),
        ('Content', {'fields': ('description', 'url', 'image')}),
        ('Metadata', {'fields': ('created_at', 'updated_at')}),
    )

    def approve_events(self, request, queryset):
        queryset.update(status=EventStatus.APPROVED)
    approve_events.short_description = 'Approve selected events'

    def reject_events(self, request, queryset):
        queryset.update(status=EventStatus.REJECTED)
    reject_events.short_description = 'Reject selected events'
