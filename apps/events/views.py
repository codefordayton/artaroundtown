from django.contrib.auth.decorators import login_required
from django.core.mail import mail_admins
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import DetailView, TemplateView

from .forms import EventSubmissionForm
from .models import Event, EventStatus, SliderImage, SliderSettings


class LandingView(TemplateView):
    template_name = 'events/landing.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()

        approved = Event.objects.filter(status=EventStatus.APPROVED).select_related('venue')

        # Now showing: opened already and not yet closed (exhibitions mostly).
        # A single-day event with no end_date counts only on its day.
        ctx['current_events'] = approved.filter(
            Q(start_date__lte=today),
            Q(end_date__gte=today) | Q(end_date__isnull=True, start_date=today),
        ).order_by('end_date', 'start_date')[:4]

        upcoming = approved.filter(start_date__gt=today).order_by('start_date')
        ctx['featured_events'] = upcoming[:5]

        # Real artwork for the thumbnail strip: live (current or upcoming)
        # events that have an image, falling back to any approved event with
        # an image so the strip isn't empty early on.
        live = approved.filter(
            Q(start_date__gt=today) | Q(end_date__gte=today) | Q(start_date=today)
        ).order_by('start_date')
        artwork = list(live.exclude(image='')[:6])
        if len(artwork) < 6:
            seen = {e.pk for e in artwork}
            extra = (
                Event.objects.filter(status=EventStatus.APPROVED)
                .exclude(image='')
                .exclude(pk__in=seen)
                .order_by('-start_date')[: 6 - len(artwork)]
            )
            artwork.extend(extra)
        ctx['artwork_events'] = artwork

        ctx['slider_images'] = SliderImage.objects.filter(is_active=True)
        ctx['slider_interval_ms'] = SliderSettings.load().interval_seconds * 1000

        return ctx


class CalendarView(TemplateView):
    template_name = 'events/calendar.html'


@method_decorator(xframe_options_exempt, name='dispatch')
class CalendarEmbedView(TemplateView):
    template_name = 'events/calendar_embed.html'


class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'
    queryset = Event.objects.filter(status=EventStatus.APPROVED).select_related('venue')


def submit_event(request):
    anonymous = not request.user.is_authenticated

    if request.method == 'POST':
        form = EventSubmissionForm(
            request.POST, request.FILES,
            require_contact=anonymous,
        )
        if form.is_valid():
            event = form.save(commit=False)
            event.status = EventStatus.PENDING

            if anonymous:
                event.submitter_name = form.cleaned_data['submitter_name']
                event.submitter_email = form.cleaned_data['submitter_email']
            else:
                user = request.user
                event.submitted_by = user
                event.submitter_name = user.get_full_name() or user.username
                event.submitter_email = user.email

            event.save()

            mail_admins(
                subject=f'New event submission: {event.title}',
                message=(
                    f"A new event has been submitted and is awaiting your review.\n\n"
                    f"Title: {event.title}\n"
                    f"Submitted by: {event.submitter_name} ({event.submitter_email})\n"
                    f"Start date: {event.start_date}\n"
                    f"Location: {event.display_location}\n\n"
                    f"Review it in the admin panel.\n"
                ),
                fail_silently=True,
            )
            return redirect('submit-success')
    else:
        form = EventSubmissionForm(require_contact=anonymous)

    return render(request, 'events/submit.html', {
        'form': form,
        'anonymous': anonymous,
    })


def submit_success(request):
    return render(request, 'events/submit_success.html')
