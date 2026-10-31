import datetime
from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import mail_admins
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import Truncator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import DetailView, TemplateView

from apps.venues.models import Venue
from . import newsletter
from .forms import EventSubmissionForm
from .models import (
    CATEGORY_COLORS, Event, EventCategory, EventStatus, SliderImage, SliderSettings,
)


def category_choices():
    """[{value, label, color}, ...] for filter pills and legends."""
    return [
        {'value': value, 'label': label, 'color': CATEGORY_COLORS[value]}
        for value, label in EventCategory.choices
    ]


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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = category_choices()
        return ctx


@method_decorator(xframe_options_exempt, name='dispatch')
class CalendarEmbedView(TemplateView):
    template_name = 'events/calendar_embed.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = category_choices()
        return ctx


def _event_date_span(event):
    """(start, end) with an exclusive end, in the shapes iCalendar and Google
    Calendar expect: dates for all-day events, naive local datetimes for
    single-day timed events."""
    if event.start_time and not event.end_date:
        start = datetime.datetime.combine(event.start_date, event.start_time)
        if event.end_time:
            end = datetime.datetime.combine(event.start_date, event.end_time)
            if end <= start:
                end += datetime.timedelta(days=1)
        else:
            end = start + datetime.timedelta(hours=2)
        return start, end, False
    end_date = (event.end_date or event.start_date) + datetime.timedelta(days=1)
    return event.start_date, end_date, True


def _event_plain_description(event):
    parts = []
    if event.opening_reception_date:
        when = event.opening_reception_date.strftime('%b %-d')
        if event.opening_reception_time:
            when += ' at ' + event.opening_reception_time.strftime('%-I:%M %p')
        parts.append(f'Opening reception: {when}')
    if event.description:
        parts.append(event.description)
    if event.url:
        parts.append(event.url)
    return '\n\n'.join(parts)


def _event_location_line(event):
    if event.venue:
        v = event.venue
        bits = [v.name, v.address, f'{v.city}, {v.state} {v.zip_code}'.strip()]
        return ', '.join(b for b in bits if b)
    return event.location_name


def google_calendar_url(event):
    start, end, all_day = _event_date_span(event)
    fmt = '%Y%m%d' if all_day else '%Y%m%dT%H%M%S'
    params = {
        'action': 'TEMPLATE',
        'text': event.title,
        'dates': f'{start.strftime(fmt)}/{end.strftime(fmt)}',
        'details': _event_plain_description(event),
        'location': _event_location_line(event),
    }
    if not all_day:
        params['ctz'] = 'America/New_York'
    return 'https://calendar.google.com/calendar/render?' + urlencode(params)


class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'
    queryset = Event.objects.filter(status=EventStatus.APPROVED).select_related('venue')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object
        # Link-preview metadata (Open Graph / Twitter cards), see base.html
        ctx['page_title'] = f'{event.title} — Art Around Town Dayton'
        summary = Truncator(event.description).chars(200) if event.description else ''
        when = event.start_date.strftime('%B %-d, %Y')
        if event.end_date:
            when += ' – ' + event.end_date.strftime('%B %-d, %Y')
        ctx['meta_description'] = f'{when} · {event.display_location}. {summary}'.strip()
        if event.image:
            ctx['og_image'] = self.request.build_absolute_uri(event.image.url)
        ctx['og_type'] = 'article'
        ctx['google_calendar_url'] = google_calendar_url(event)
        return ctx


def _ics_escape(value):
    return (
        str(value or '')
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\r\n', '\\n')
        .replace('\n', '\\n')
    )


def _ics_fold(line):
    """RFC 5545 folds lines longer than 75 octets with CRLF + space."""
    out, raw = [], line.encode('utf-8')
    while len(raw) > 75:
        cut = 75
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:   # don't split a UTF-8 char
            cut -= 1
        out.append(raw[:cut].decode('utf-8'))
        raw = b' ' + raw[cut:]
    out.append(raw.decode('utf-8'))
    return '\r\n'.join(out)


def event_ics(request, slug):
    """Download a single event as an .ics file ("Add to my calendar")."""
    event = get_object_or_404(
        Event.objects.select_related('venue'), slug=slug, status=EventStatus.APPROVED,
    )
    start, end, all_day = _event_date_span(event)
    if all_day:
        dt_lines = [
            f'DTSTART;VALUE=DATE:{start.strftime("%Y%m%d")}',
            f'DTEND;VALUE=DATE:{end.strftime("%Y%m%d")}',
        ]
    else:
        dt_lines = [
            f'DTSTART;TZID=America/New_York:{start.strftime("%Y%m%dT%H%M%S")}',
            f'DTEND;TZID=America/New_York:{end.strftime("%Y%m%dT%H%M%S")}',
        ]
    detail_url = request.build_absolute_uri(event.get_absolute_url())
    stamp = timezone.now().strftime('%Y%m%dT%H%M%SZ')
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Art Around Town Dayton//Events//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'BEGIN:VEVENT',
        f'UID:event-{event.pk}@artaroundtowndayton.org',
        f'DTSTAMP:{stamp}',
        *dt_lines,
        f'SUMMARY:{_ics_escape(event.title)}',
        f'DESCRIPTION:{_ics_escape(_event_plain_description(event))}',
        f'LOCATION:{_ics_escape(_event_location_line(event))}',
        f'URL:{detail_url}',
        'END:VEVENT',
        'END:VCALENDAR',
    ]
    body = '\r\n'.join(_ics_fold(line) for line in lines) + '\r\n'
    response = HttpResponse(body, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{event.slug}.ics"'
    return response


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


# ── Search ──────────────────────────────────────────────────────────

def _terms(q):
    return [t for t in q.split() if len(t) > 1][:8]


class SearchView(TemplateView):
    template_name = 'events/search.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()[:100]
        ctx['q'] = q
        ctx['page_title'] = f'Search: {q} — Art Around Town Dayton' if q else 'Search — Art Around Town Dayton'
        terms = _terms(q)
        if not terms:
            ctx.update(current_events=[], past_events=[], venues=[], searched=bool(q))
            return ctx

        events = Event.objects.filter(status=EventStatus.APPROVED).select_related('venue')
        venues = Venue.objects.filter(is_active=True)
        for t in terms:   # every term must match somewhere
            events = events.filter(
                Q(title__icontains=t) | Q(description__icontains=t)
                | Q(venue__name__icontains=t) | Q(location_name__icontains=t)
            )
            venues = venues.filter(
                Q(name__icontains=t) | Q(city__icontains=t) | Q(description__icontains=t)
            )

        today = timezone.localdate()
        live = Q(start_date__gte=today) | Q(end_date__gte=today)
        ctx['current_events'] = events.filter(live).order_by('start_date')[:50]
        ctx['past_events'] = events.exclude(live).order_by('-start_date')[:20]
        ctx['venues'] = venues[:30]
        ctx['searched'] = True
        return ctx


# ── Newsletter signup ──────────────────────────────────────────────

class NewsletterForm(forms.Form):
    email = forms.EmailField(max_length=254)
    name = forms.CharField(max_length=120, required=False)
    website = forms.CharField(required=False)   # honeypot: humans leave it blank


def newsletter_signup(request):
    if request.method != 'POST':
        return redirect('home')

    back = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        back = '/'

    form = NewsletterForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Please enter a valid email address.')
        return redirect(back)
    if form.cleaned_data['website']:        # bot filled the hidden field
        messages.success(request, "You're on the list. Thanks!")
        return redirect(back)

    try:
        newsletter.subscribe(form.cleaned_data['email'], form.cleaned_data['name'])
    except newsletter.NewsletterError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "You're on the list. Thanks!")
    return redirect(back)
