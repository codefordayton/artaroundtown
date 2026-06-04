from django.contrib.auth.decorators import login_required
from django.core.mail import mail_admins
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import DetailView, TemplateView

from .forms import EventSubmissionForm
from .models import Event, EventStatus


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
