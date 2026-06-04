from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('pending-approval/', views.pending_approval_view, name='pending-approval'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('my-events/', views.my_events_view, name='my-events'),
]
