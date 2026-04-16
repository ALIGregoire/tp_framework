from django.contrib import admin

from .models import (
    Commentaire,
    HistoriqueStatut,
    Notification,
    PlatformSettings,
    PriorityConfig,
    Ticket,
    TicketTypeConfig,
)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'titre',
        'type_ticket',
        'statut',
        'priorite',
        'auteur',
        'assigne_a',
        'est_archive',
        'date_creation',
    )
    list_filter = ('type_ticket', 'statut', 'priorite', 'est_archive')
    search_fields = ('titre', 'description', 'auteur__email', 'assigne_a__email')
    autocomplete_fields = ('auteur', 'assigne_a')
    readonly_fields = (
        'date_creation',
        'date_modification',
        'date_resolution',
        'date_cloture',
        'date_archivage',
    )


@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'auteur', 'date')
    search_fields = ('contenu', 'auteur__email', 'ticket__titre')
    autocomplete_fields = ('ticket', 'auteur')
    readonly_fields = ('date',)


@admin.register(HistoriqueStatut)
class HistoriqueStatutAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'ticket',
        'ancien_statut',
        'nouveau_statut',
        'modifie_par',
        'date_changement',
    )
    list_filter = ('ancien_statut', 'nouveau_statut')
    autocomplete_fields = ('ticket', 'modifie_par')
    readonly_fields = ('date_changement',)


@admin.register(TicketTypeConfig)
class TicketTypeConfigAdmin(admin.ModelAdmin):
    list_display = ('code', 'label', 'actif', 'ordre')
    list_editable = ('label', 'actif', 'ordre')


@admin.register(PriorityConfig)
class PriorityConfigAdmin(admin.ModelAdmin):
    list_display = ('code', 'label', 'delai_heures', 'actif', 'ordre')
    list_editable = ('label', 'delai_heures', 'actif', 'ordre')


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ('nom', 'archive_after_days')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'utilisateur', 'type_notification', 'titre', 'lue', 'date_creation')
    list_filter = ('type_notification', 'lue')
    search_fields = ('titre', 'message', 'utilisateur__email', 'ticket__titre')
    autocomplete_fields = ('utilisateur', 'ticket')
    readonly_fields = ('date_creation',)
