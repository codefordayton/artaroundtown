from django.urls import path
from . import views

urlpatterns = [
    path('', views.LandingView.as_view(), name='home'),
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('embed/calendar/', views.CalendarEmbedView.as_view(), name='calendar-embed'),
    path('submit/', views.submit_event, name='submit-event'),
    path('submit/success/', views.submit_success, name='submit-success'),
    path('events/<slug:slug>/', views.EventDetailView.as_view(), name='event-detail'),
]
