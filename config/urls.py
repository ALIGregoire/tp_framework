"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from tickets.views import NotificationViewSet, PlatformConfigViewSet, TicketViewSet
from accounts.views import (
    AdminUserDetailView,
    ProfileView,
    RegisterView,
    TechnicianListView,
    UserListView,
)

# Création du routeur DRF
router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'configurations', PlatformConfigViewSet, basename='configuration')

# URL patterns
urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentification JWT
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/profil/', ProfileView.as_view(), name='profil'),
    path('api/auth/utilisateurs/', UserListView.as_view(), name='utilisateurs'),
    path('api/auth/utilisateurs/<int:pk>/', AdminUserDetailView.as_view(), name='utilisateur_detail'),
    path('api/auth/techniciens/', TechnicianListView.as_view(), name='techniciens'),

    # API tickets
    path('api/', include(router.urls)),
]
