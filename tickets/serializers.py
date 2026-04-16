from rest_framework import serializers

from accounts.models import CustomUser

from .models import (
    Commentaire,
    HistoriqueStatut,
    Notification,
    PlatformSettings,
    PriorityConfig,
    Ticket,
    TicketTypeConfig,
)


class UserLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email', 'role']


class CommentaireSerializer(serializers.ModelSerializer):
    auteur = UserLightSerializer(read_only=True)

    class Meta:
        model = Commentaire
        fields = ['id', 'auteur', 'contenu', 'date']
        read_only_fields = ['auteur', 'date']


class HistoriqueStatutSerializer(serializers.ModelSerializer):
    modifie_par = UserLightSerializer(read_only=True)

    class Meta:
        model = HistoriqueStatut
        fields = ['id', 'ancien_statut', 'nouveau_statut', 'date_changement', 'modifie_par']


class TicketTypeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketTypeConfig
        fields = ['id', 'code', 'label', 'actif', 'ordre']


class PriorityConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorityConfig
        fields = ['id', 'code', 'label', 'actif', 'ordre', 'delai_heures']


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = ['archive_after_days']


class PlatformConfigSerializer(serializers.Serializer):
    types_ticket = TicketTypeConfigSerializer(many=True)
    priorites = PriorityConfigSerializer(many=True)
    settings = PlatformSettingsSerializer()


class NotificationSerializer(serializers.ModelSerializer):
    ticket_titre = serializers.CharField(source='ticket.titre', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'type_notification',
            'titre',
            'message',
            'lue',
            'date_creation',
            'ticket',
            'ticket_titre',
        ]
        read_only_fields = ['date_creation', 'ticket_titre']


class TicketSerializer(serializers.ModelSerializer):
    auteur = UserLightSerializer(read_only=True)
    assigne_a = UserLightSerializer(read_only=True)
    commentaires = CommentaireSerializer(many=True, read_only=True)
    historique = HistoriqueStatutSerializer(many=True, read_only=True)
    assigne_a_id = serializers.PrimaryKeyRelatedField(
        source='assigne_a',
        queryset=CustomUser.objects.filter(role='TECHNICIEN'),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Ticket
        fields = [
            'id',
            'titre',
            'description',
            'type_ticket',
            'statut',
            'priorite',
            'auteur',
            'assigne_a',
            'assigne_a_id',
            'date_creation',
            'date_modification',
            'date_resolution',
            'date_cloture',
            'est_archive',
            'date_archivage',
            'commentaires',
            'historique',
        ]
        read_only_fields = [
            'auteur',
            'statut',
            'date_creation',
            'date_modification',
            'date_resolution',
            'date_cloture',
            'est_archive',
            'date_archivage',
        ]

    def validate_type_ticket(self, value):
        if not TicketTypeConfig.objects.filter(code=value, actif=True).exists():
            raise serializers.ValidationError('Type de ticket indisponible.')
        return value

    def validate_priorite(self, value):
        if not PriorityConfig.objects.filter(code=value, actif=True).exists():
            raise serializers.ValidationError('Priorite indisponible.')
        return value

    def create(self, validated_data):
        validated_data['auteur'] = self.context['request'].user
        if validated_data['auteur'].role != 'ADMIN':
            validated_data.pop('assigne_a', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request is None or getattr(request.user, 'role', None) != 'ADMIN':
            validated_data.pop('assigne_a', None)
        return super().update(instance, validated_data)


class TicketListSerializer(serializers.ModelSerializer):
    auteur = UserLightSerializer(read_only=True)
    assigne_a = UserLightSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id',
            'titre',
            'description',
            'type_ticket',
            'statut',
            'priorite',
            'auteur',
            'assigne_a',
            'date_creation',
            'est_archive',
        ]
