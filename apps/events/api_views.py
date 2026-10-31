from django.db.models import Q
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from .models import Event, EventStatus
from .serializers import EventSerializer, EventCalendarSerializer


def filter_common(qs, params):
    """Filters shared by the list and calendar-feed endpoints."""
    if params.get('venue'):
        qs = qs.filter(venue__slug=params['venue'])
    if params.get('category'):
        # Accepts one value or a comma-separated list: ?category=music,dance
        cats = [c.strip() for c in params['category'].split(',') if c.strip()]
        qs = qs.filter(category__in=cats)
    return qs


class EventListAPIView(ListAPIView):
    serializer_class = EventSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Event.objects.filter(status=EventStatus.APPROVED).select_related('venue')
        params = self.request.query_params
        if params.get('start'):
            qs = qs.filter(start_date__gte=params['start'])
        if params.get('end'):
            qs = qs.filter(start_date__lte=params['end'])
        return filter_common(qs, params)


class EventCalendarFeedView(ListAPIView):
    """Returns events in FullCalendar's expected JSON format. No pagination."""
    serializer_class = EventCalendarSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = Event.objects.filter(status=EventStatus.APPROVED).select_related('venue')
        params = self.request.query_params
        # FullCalendar sends ISO datetimes for the visible range; slice to
        # the date portion. An event overlaps the range if it starts before
        # the range ends and (its end, or its start for single-day events)
        # is on/after the range start, so multi-month shows keep appearing.
        if params.get('end'):
            qs = qs.filter(start_date__lt=params['end'][:10])
        if params.get('start'):
            start = params['start'][:10]
            qs = qs.filter(Q(end_date__gte=start) | Q(end_date__isnull=True, start_date__gte=start))
        return filter_common(qs, params)


class EventDetailAPIView(RetrieveAPIView):
    serializer_class = EventSerializer
    permission_classes = [AllowAny]
    queryset = Event.objects.filter(status=EventStatus.APPROVED).select_related('venue')
