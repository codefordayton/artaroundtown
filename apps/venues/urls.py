from django.urls import path
from . import views

urlpatterns = [
    path('galleries/', views.VenueListView.as_view(), name='venue-list'),
    path('galleries/<slug:slug>/', views.VenueDetailView.as_view(), name='venue-detail'),
]
