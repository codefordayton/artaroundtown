from django.contrib.auth.decorators import login_required
from django.core.mail import mail_admins
from django.shortcuts import render, redirect

from apps.events.models import Event
from .forms import RegistrationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            name = user.get_full_name() or user.username
            org = f" ({user.organization})" if user.organization else ""
            mail_admins(
                subject=f'New submitter request: {name}{org}',
                message=(
                    f"A new user has registered and is requesting event submission access.\n\n"
                    f"Name: {name}\n"
                    f"Username: {user.username}\n"
                    f"Email: {user.email}\n"
                    f"Organization: {user.organization or '—'}\n\n"
                    f"To approve them, go to the admin panel and set "
                    f"'Is approved submitter' to checked on their account.\n"
                ),
                fail_silently=True,
            )
            return redirect('pending-approval')
    else:
        form = RegistrationForm()
    return render(request, 'users/register.html', {'form': form})


def pending_approval_view(request):
    return render(request, 'users/pending_approval.html')


@login_required
def my_events_view(request):
    events = (
        Event.objects.filter(submitted_by=request.user)
        .order_by('-created_at')
    )
    return render(request, 'users/my_events.html', {'events': events})
