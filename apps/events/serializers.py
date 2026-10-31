import datetime

from rest_framework import serializers
from .models import Event


class EventSerializer(serializers.ModelSerializer):
    display_location = serializers.ReadOnlyField()
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'category', 'category_display',
            'start_date', 'end_date',
            'opening_reception_date', 'opening_reception_time',
            'artist_talk_date', 'artist_talk_time',
            'closing_reception_date', 'closing_reception_time',
            'venue', 'venue_name', 'location_name', 'display_location',
            'url', 'description', 'image',
        ]


class EventCalendarSerializer(serializers.ModelSerializer):
    """FullCalendar-compatible format for the calendar feed endpoint."""
    start = serializers.DateField(source='start_date')
    end = serializers.SerializerMethodField()
    color = serializers.ReadOnlyField(source='category_color')
    extendedProps = serializers.SerializerMethodField()

    def get_end(self, obj):
        # FullCalendar treats all-day `end` as exclusive, so a show that
        # closes on the 23rd must be sent as the 24th or it drops a day.
        if obj.end_date:
            return (obj.end_date + datetime.timedelta(days=1)).isoformat()
        return None

    def get_extendedProps(self, obj):
        return {
            'slug': obj.slug,
            'location': obj.display_location,
            'category': obj.category,
            'category_display': obj.get_category_display() if obj.category else '',
        }

    class Meta:
        model = Event
        fields = ['id', 'title', 'start', 'end', 'color', 'extendedProps']
