from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuteurOrReadOnly(BasePermission):
    """Seul l'auteur peut modifier son ticket."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.auteur == request.user


class IsTechnicienOrAdmin(BasePermission):
    """Seuls les techniciens et admins peuvent changer le statut."""

    def has_permission(self, request, view):
        return request.user.role in ('TECHNICIEN', 'ADMIN')


class TicketWritePermission(BasePermission):
    """Règles d'écriture sur un ticket (hors actions dédiées)."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        role = getattr(user, "role", None)
        if role == "ADMIN":
            return True
        if role == "CITOYEN":
            return obj.auteur_id == user.id

        # TECHNICIEN: modifications via actions dédiées (statut/commentaires).
        return False
