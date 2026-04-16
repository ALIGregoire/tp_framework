from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class TicketTypeConfig(models.Model):
    code = models.CharField(max_length=20, unique=True)
    label = models.CharField(max_length=100)
    actif = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'label']
        verbose_name = 'Type de ticket'
        verbose_name_plural = 'Types de ticket'

    def __str__(self):
        return self.label


class PriorityConfig(models.Model):
    code = models.CharField(max_length=20, unique=True)
    label = models.CharField(max_length=100)
    actif = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)
    delai_heures = models.PositiveIntegerField(default=24)

    class Meta:
        ordering = ['ordre', 'label']
        verbose_name = 'Priorite'
        verbose_name_plural = 'Priorites'

    def __str__(self):
        return self.label


class PlatformSettings(models.Model):
    nom = models.CharField(max_length=50, default='default', unique=True)
    archive_after_days = models.PositiveIntegerField(default=30)

    class Meta:
        verbose_name = 'Parametre plateforme'
        verbose_name_plural = 'Parametres plateforme'

    def __str__(self):
        return f'Configuration {self.nom}'

    @classmethod
    def get_solo(cls):
        settings_obj, _ = cls.objects.get_or_create(nom='default')
        return settings_obj


class Ticket(models.Model):
    class TypeTicket(models.TextChoices):
        INCIDENT = 'INCIDENT', 'Incident technique'
        RECLAMATION = 'RECLAMATION', 'Reclamation'
        DEMANDE = 'DEMANDE', 'Demande de service'

    class Statut(models.TextChoices):
        OUVERT = 'OUVERT', 'Ouvert'
        EN_COURS = 'EN_COURS', 'En cours de traitement'
        RESOLU = 'RESOLU', 'Resolu'
        CLOS = 'CLOS', 'Clos'

    class Priorite(models.TextChoices):
        BASSE = 'BASSE', 'Basse'
        NORMALE = 'NORMALE', 'Normale'
        HAUTE = 'HAUTE', 'Haute'
        CRITIQUE = 'CRITIQUE', 'Critique'

    titre = models.CharField(max_length=200)
    description = models.TextField()

    type_ticket = models.CharField(
        max_length=15,
        choices=TypeTicket.choices,
        default=TypeTicket.INCIDENT,
    )

    statut = models.CharField(
        max_length=10,
        choices=Statut.choices,
        default=Statut.OUVERT,
    )

    priorite = models.CharField(
        max_length=10,
        choices=Priorite.choices,
        default=Priorite.NORMALE,
    )

    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets_crees',
    )

    assigne_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_assignes',
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_resolution = models.DateTimeField(null=True, blank=True)
    date_cloture = models.DateTimeField(null=True, blank=True)
    est_archive = models.BooleanField(default=False)
    date_archivage = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'

    def __str__(self):
        return f'[{self.statut}] {self.titre}'

    @classmethod
    def archive_expired(cls):
        delay_days = PlatformSettings.get_solo().archive_after_days
        cutoff = timezone.now() - timedelta(days=delay_days)
        return cls.objects.filter(
            statut=cls.Statut.CLOS,
            est_archive=False,
            date_cloture__isnull=False,
            date_cloture__lte=cutoff,
        ).update(est_archive=True, date_archivage=timezone.now())


class Commentaire(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='commentaires',
    )

    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contenu = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'Commentaire de {self.auteur} sur #{self.ticket.id}'


class HistoriqueStatut(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='historique',
    )

    ancien_statut = models.CharField(max_length=10)
    nouveau_statut = models.CharField(max_length=10)
    date_changement = models.DateTimeField(auto_now_add=True)

    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )

    class Meta:
        ordering = ['-date_changement']


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        INFO = 'INFO', 'Information'
        STATUT = 'STATUT', 'Changement de statut'
        ASSIGNATION = 'ASSIGNATION', 'Assignation'
        COMMENTAIRE = 'COMMENTAIRE', 'Commentaire'
        ARCHIVAGE = 'ARCHIVAGE', 'Archivage'

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
    )
    type_notification = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
    )
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f'{self.utilisateur} - {self.titre}'
