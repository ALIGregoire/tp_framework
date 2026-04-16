from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminRole

from .models import (
    Commentaire,
    HistoriqueStatut,
    Notification,
    PlatformSettings,
    PriorityConfig,
    Ticket,
    TicketTypeConfig,
)
from .permissions import IsTechnicienOrAdmin, TicketWritePermission
from .serializers import (
    CommentaireSerializer,
    NotificationSerializer,
    PlatformConfigSerializer,
    PlatformSettingsSerializer,
    PriorityConfigSerializer,
    TicketListSerializer,
    TicketSerializer,
    TicketTypeConfigSerializer,
)


def create_notifications(users, *, ticket, title, message, notification_type, exclude_user_ids=None):
    exclude_ids = set(exclude_user_ids or [])
    notifications = []
    seen_ids = set()
    for user in users:
        if user is None or user.id in exclude_ids or user.id in seen_ids:
            continue
        seen_ids.add(user.id)
        notifications.append(
            Notification(
                utilisateur=user,
                ticket=ticket,
                titre=title,
                message=message,
                type_notification=notification_type,
            )
        )
    if notifications:
        Notification.objects.bulk_create(notifications)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    permission_classes = [IsAuthenticated, TicketWritePermission]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ['statut', 'priorite', 'type_ticket', 'assigne_a', 'est_archive']
    search_fields = ['titre', 'description']
    ordering_fields = ['date_creation', 'priorite', 'statut']

    def get_serializer_class(self):
        if self.action == 'list':
            return TicketListSerializer
        return TicketSerializer

    def _archive_expired_tickets(self):
        archived_count = Ticket.archive_expired()
        if archived_count:
            archived_tickets = Ticket.objects.filter(
                est_archive=True,
                date_archivage__gte=timezone.now() - timedelta(minutes=1),
            ).select_related('auteur', 'assigne_a')
            for ticket in archived_tickets:
                create_notifications(
                    [ticket.auteur, ticket.assigne_a],
                    ticket=ticket,
                    title='Ticket archive',
                    message=f'Le ticket "{ticket.titre}" a ete archive automatiquement.',
                    notification_type=Notification.NotificationType.ARCHIVAGE,
                )

    def get_queryset(self):
        self._archive_expired_tickets()

        user = self.request.user
        include_archived = self.request.query_params.get('include_archived') == '1'
        qs = Ticket.objects.select_related('auteur', 'assigne_a')

        if self.action != 'list':
            commentaires_qs = Commentaire.objects.select_related('auteur')
            historique_qs = HistoriqueStatut.objects.select_related('modifie_par')
            qs = qs.prefetch_related(
                Prefetch('commentaires', queryset=commentaires_qs),
                Prefetch('historique', queryset=historique_qs),
            )

        if not include_archived:
            qs = qs.filter(est_archive=False)

        if user.role == 'CITOYEN':
            return qs.filter(auteur=user)
        if user.role == 'TECHNICIEN':
            return qs.filter(assigne_a=user)
        return qs

    def perform_create(self, serializer):
        ticket = serializer.save()
        create_notifications(
            [ticket.auteur],
            ticket=ticket,
            title='Ticket cree',
            message=f'Votre ticket "{ticket.titre}" a ete cree avec succes.',
            notification_type=Notification.NotificationType.INFO,
        )

    def _pick_technicien_auto(self):
        from accounts.models import CustomUser

        return (
            CustomUser.objects.filter(role='TECHNICIEN', is_active=True)
            .annotate(
                open_ticket_count=Count(
                    'tickets_assignes',
                    filter=~Q(tickets_assignes__statut__in=[Ticket.Statut.RESOLU, Ticket.Statut.CLOS]),
                )
            )
            .order_by('open_ticket_count', 'first_name', 'last_name', 'id')
            .first()
        )

    @action(detail=True, methods=['patch'], permission_classes=[IsTechnicienOrAdmin])
    def changer_statut(self, request, pk=None):
        ticket = self.get_object()
        nouveau_statut = request.data.get('statut')

        if nouveau_statut not in dict(Ticket.Statut.choices):
            return Response({'erreur': 'Statut invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        allowed_transitions = {
            Ticket.Statut.OUVERT: {Ticket.Statut.EN_COURS},
            Ticket.Statut.EN_COURS: {Ticket.Statut.RESOLU},
            Ticket.Statut.RESOLU: {Ticket.Statut.CLOS},
            Ticket.Statut.CLOS: set(),
        }
        if nouveau_statut not in allowed_transitions.get(ticket.statut, set()):
            return Response(
                {
                    'erreur': 'Transition de statut invalide.',
                    'statut_actuel': ticket.statut,
                    'statuts_autorises': sorted(allowed_transitions.get(ticket.statut, set())),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ancien_statut = ticket.statut
        ticket.statut = nouveau_statut
        if nouveau_statut == Ticket.Statut.RESOLU:
            ticket.date_resolution = timezone.now()
        if nouveau_statut == Ticket.Statut.CLOS:
            ticket.date_cloture = timezone.now()

        with transaction.atomic():
            ticket.save()
            HistoriqueStatut.objects.create(
                ticket=ticket,
                ancien_statut=ancien_statut,
                nouveau_statut=nouveau_statut,
                modifie_par=request.user,
            )

        create_notifications(
            [ticket.auteur, ticket.assigne_a],
            ticket=ticket,
            title='Statut mis a jour',
            message=f'Le ticket "{ticket.titre}" est passe de {ancien_statut} a {nouveau_statut}.',
            notification_type=Notification.NotificationType.STATUT,
            exclude_user_ids=[request.user.id],
        )

        return Response(TicketSerializer(ticket, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def commenter(self, request, pk=None):
        ticket = self.get_object()
        serializer = CommentaireSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(ticket=ticket, auteur=request.user)
            create_notifications(
                [ticket.auteur, ticket.assigne_a],
                ticket=ticket,
                title='Nouveau commentaire',
                message=f'Un nouveau commentaire a ete ajoute sur "{ticket.titre}".',
                notification_type=Notification.NotificationType.COMMENTAIRE,
                exclude_user_ids=[request.user.id],
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminRole])
    def assigner(self, request, pk=None):
        ticket = self.get_object()
        technicien_id = request.data.get('technicien_id')

        if ticket.statut in (Ticket.Statut.RESOLU, Ticket.Statut.CLOS):
            return Response(
                {'erreur': 'Impossible d assigner un ticket resolu ou clos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from accounts.models import CustomUser

        try:
            ancien_statut = ticket.statut
            ancien_assigne = ticket.assigne_a
            if technicien_id in (None, ''):
                ticket.assigne_a = None
            else:
                tech = CustomUser.objects.get(id=technicien_id, role='TECHNICIEN')
                ticket.assigne_a = tech
                if ticket.statut == Ticket.Statut.OUVERT:
                    ticket.statut = Ticket.Statut.EN_COURS

            with transaction.atomic():
                ticket.save()
                if ancien_statut != ticket.statut:
                    HistoriqueStatut.objects.create(
                        ticket=ticket,
                        ancien_statut=ancien_statut,
                        nouveau_statut=ticket.statut,
                        modifie_par=request.user,
                    )

            if ticket.assigne_a is not None:
                create_notifications(
                    [ticket.auteur, ticket.assigne_a],
                    ticket=ticket,
                    title='Ticket assigne',
                    message=f'Le ticket "{ticket.titre}" a ete assigne a {ticket.assigne_a.get_full_name() or ticket.assigne_a.email}.',
                    notification_type=Notification.NotificationType.ASSIGNATION,
                    exclude_user_ids=[request.user.id],
                )
            elif ancien_assigne is not None:
                create_notifications(
                    [ticket.auteur, ancien_assigne],
                    ticket=ticket,
                    title='Ticket desassigne',
                    message=f'Le ticket "{ticket.titre}" n est plus assigne.',
                    notification_type=Notification.NotificationType.ASSIGNATION,
                    exclude_user_ids=[request.user.id],
                )

            return Response(TicketSerializer(ticket, context={'request': request}).data)
        except CustomUser.DoesNotExist:
            return Response({'erreur': 'Technicien introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminRole])
    def assigner_auto(self, request, pk=None):
        ticket = self.get_object()

        if ticket.statut in (Ticket.Statut.RESOLU, Ticket.Statut.CLOS):
            return Response(
                {'erreur': 'Impossible d assigner un ticket resolu ou clos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tech = self._pick_technicien_auto()
        if tech is None:
            return Response(
                {'erreur': 'Aucun technicien actif disponible.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ancien_statut = ticket.statut
        ticket.assigne_a = tech
        if ticket.statut == Ticket.Statut.OUVERT:
            ticket.statut = Ticket.Statut.EN_COURS

        with transaction.atomic():
            ticket.save()
            if ancien_statut != ticket.statut:
                HistoriqueStatut.objects.create(
                    ticket=ticket,
                    ancien_statut=ancien_statut,
                    nouveau_statut=ticket.statut,
                    modifie_par=request.user,
                )

        create_notifications(
            [ticket.auteur, ticket.assigne_a],
            ticket=ticket,
            title='Attribution automatique',
            message=f'Le ticket "{ticket.titre}" a ete attribue automatiquement.',
            notification_type=Notification.NotificationType.ASSIGNATION,
            exclude_user_ids=[request.user.id],
        )

        return Response(TicketSerializer(ticket, context={'request': request}).data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminRole])
    def stats(self, request):
        self._archive_expired_tickets()
        qs = Ticket.objects.filter(est_archive=False)

        by_statut = dict(qs.values('statut').annotate(c=Count('id')).values_list('statut', 'c'))
        by_type = dict(qs.values('type_ticket').annotate(c=Count('id')).values_list('type_ticket', 'c'))
        by_priorite = dict(qs.values('priorite').annotate(c=Count('id')).values_list('priorite', 'c'))

        by_technicien = list(
            qs.exclude(assigne_a=None)
            .values('assigne_a_id', 'assigne_a__first_name', 'assigne_a__last_name', 'assigne_a__email')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return Response(
            {
                'total': qs.count(),
                'by_statut': by_statut,
                'by_type': by_type,
                'by_priorite': by_priorite,
                'by_technicien': by_technicien,
            }
        )


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(utilisateur=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(lue=False).update(lue=True)
        return Response({'detail': 'Notifications marquees comme lues.'})


class PlatformConfigViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        payload = {
            'types_ticket': TicketTypeConfig.objects.filter(actif=True),
            'priorites': PriorityConfig.objects.filter(actif=True),
            'settings': PlatformSettings.get_solo(),
        }
        serializer = PlatformConfigSerializer(payload)
        return Response(serializer.data)

    @action(detail=False, methods=['patch'], permission_classes=[IsAdminRole])
    def settings(self, request):
        serializer = PlatformSettingsSerializer(
            PlatformSettings.get_solo(),
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminRole])
    def types(self, request):
        return Response(TicketTypeConfigSerializer(TicketTypeConfig.objects.all(), many=True).data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminRole])
    def priorites(self, request):
        return Response(PriorityConfigSerializer(PriorityConfig.objects.all(), many=True).data)
