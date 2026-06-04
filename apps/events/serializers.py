from rest_framework import serializers
from .models import Event


class EventSerializer(serializers.ModelSerializer):
    display_location = serializers.ReadOnlyField()
    venue_name = serializers.CharField(source='venue.name', read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug',
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
    end = serializers.DateField(source='end_date', allow_null=True)
    extendedProps = serializers.SerializerMethodField()

    def get_extendedProps(self, obj):
        return {
            'slug': obj.slug,
            'location': obj.display_location,
        }

    class Meta:
        model = Event
        fields = ['id', 'title', 'start', 'end', 'extendedProps']
