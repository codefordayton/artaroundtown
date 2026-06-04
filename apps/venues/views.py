import datetime

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
        ctx['upcoming_events'] = (
            Event.objects.filter(
                venue=self.object,
                status=EventStatus.APPROVED,
                start_date__gte=datetime.date.today(),
            )
            .order_by('start_date')[:10]
        )
        return ctx
