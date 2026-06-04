from django.urls import path
from . import views

urlpatterns = [
    path('artists/', views.ArtistListView.as_view(), name='artist-list'),
    path('artists/<slug:slug>/', views.ArtistDetailView.as_view(), name='artist-detail'),
]
