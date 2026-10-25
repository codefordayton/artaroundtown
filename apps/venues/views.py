from django.db.models import Q
from django.utils import timezone
from django.views.generic import ListView, DetailView

from apps.events.models import Event, EventStatus
from .models import Venue


class VenueListView(ListView):
    model = Venue
    template_name = 'venues/venue_list.html'
    context_object_name = 'venues'
    queryset = Venue.objects.filter(is_active=True)


class VenueDetailView(DetailView):
    model = Venue
    template_name = 'venues/venue_detail.html'
    context_object_name = 'venue'
    queryset = Venue.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        events = Event.objects.filter(venue=self.object, status=EventStatus.APPROVED)
        # Current: already open and not yet closed. A single-day event with
        # no end_date counts as current only on its day.
        ctx['current_events'] = events.filter(
            Q(start_date__lte=today),
            Q(end_date__gte=today) | Q(end_date__isnull=True, start_date=today),
        ).order_by('end_date', 'start_date')
        ctx['upcoming_events'] = events.filter(
            start_date__gt=today,
        ).order_by('start_date')[:20]
        return ctx
