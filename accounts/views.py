from rest_framework import generics, permissions
from django.contrib.auth import get_user_model

from .serializers import AdminUserSerializer, RegisterSerializer, UserSerializer
from .permissions import IsAdminRole


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by("-date_joined")


class TechnicianListView(generics.ListAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = UserSerializer
    queryset = User.objects.filter(role="TECHNICIEN").order_by("first_name", "last_name", "id")


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()
