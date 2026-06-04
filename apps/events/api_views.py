from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from .models import Event, EventStatus
from .serializers import EventSerializer, EventCalendarSerializer


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
        if params.get('venue'):
            qs = qs.filter(venue__slug=params['venue'])
        return qs


class EventCalendarFeedView(ListAPIView):
    """Returns events in FullCalendar's expected JSON format. No pagination."""
    serializer_class = EventCalendarSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = Event.objects.filter(status=EventStatus.APPROVED).select_related('venue')
        params = self.request.query_params
        # FullCalendar sends ISO datetimes; slice to date portion
        if params.get('start'):
            qs = qs.filter(start_date__gte=params['start'][:10])
        if params.get('end'):
            qs = qs.filter(start_date__lte=params['end'][:10])
        if params.get('venue'):
            qs = qs.filter(venue__slug=params['venue'])
        return qs


class EventDetailAPIView(RetrieveAPIView):
    serializer_class = EventSerializer
    permission_classes = [AllowAny]
    queryset = Event.objects.filter(status=EventStatus.APPROVED).select_related('venue')
