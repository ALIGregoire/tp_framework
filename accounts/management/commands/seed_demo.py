from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tickets.models import Commentaire, HistoriqueStatut, Ticket


User = get_user_model()


@dataclass(frozen=True)
class DemoUserSpec:
    email: str
    username: str
    first_name: str
    last_name: str
    role: str
    is_staff: bool = False
    is_superuser: bool = False


class Command(BaseCommand):
    help = "Crée des données de démonstration (utilisateurs + tickets)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les données de démo existantes avant de recréer.",
        )
        parser.add_argument(
            "--password",
            default="DemoPass123!",
            help="Mot de passe à attribuer aux utilisateurs de démo.",
        )

    def handle(self, *args, **options):
        reset = bool(options["reset"])
        password = str(options["password"])

        domain = "demo.local"
        demo_email_suffix = f"@{domain}"
        demo_ticket_prefix = "[DEMO] "

        if reset:
            self._reset_demo_data(demo_email_suffix, demo_ticket_prefix)

        demo_users = [
            DemoUserSpec(
                email=f"admin@{domain}",
                username="admin",
                first_name="Admin",
                last_name="Démo",
                role="ADMIN",
                is_staff=True,
                is_superuser=True,
            ),
            DemoUserSpec(
                email=f"tech1@{domain}",
                username="tech1",
                first_name="Samir",
                last_name="Support",
                role="TECHNICIEN",
            ),
            DemoUserSpec(
                email=f"tech2@{domain}",
                username="tech2",
                first_name="Lina",
                last_name="Technicienne",
                role="TECHNICIEN",
            ),
            DemoUserSpec(
                email=f"citoyen1@{domain}",
                username="citoyen1",
                first_name="Yassine",
                last_name="Benali",
                role="CITOYEN",
            ),
            DemoUserSpec(
                email=f"citoyen2@{domain}",
                username="citoyen2",
                first_name="Sara",
                last_name="El Fassi",
                role="CITOYEN",
            ),
            DemoUserSpec(
                email=f"citoyen3@{domain}",
                username="citoyen3",
                first_name="Amine",
                last_name="Kacem",
                role="CITOYEN",
            ),
        ]

        with transaction.atomic():
            users = {spec.email: self._upsert_user(spec, password) for spec in demo_users}

            tech1 = users[f"tech1@{domain}"]
            tech2 = users[f"tech2@{domain}"]
            citoyen1 = users[f"citoyen1@{domain}"]
            citoyen2 = users[f"citoyen2@{domain}"]
            citoyen3 = users[f"citoyen3@{domain}"]

            tickets_specs = [
                (
                    citoyen1,
                    {
                        "titre": f"{demo_ticket_prefix}Internet en panne à la mairie",
                        "description": "Plus de connexion depuis ce matin. Besoin d'une intervention rapide.",
                        "type_ticket": Ticket.TypeTicket.INCIDENT,
                        "priorite": Ticket.Priorite.CRITIQUE,
                        "statut": Ticket.Statut.EN_COURS,
                        "assigne_a": tech1,
                    },
                ),
                (
                    citoyen2,
                    {
                        "titre": f"{demo_ticket_prefix}Réclamation : éclairage public",
                        "description": "Le lampadaire près de la rue principale ne fonctionne plus depuis 3 jours.",
                        "type_ticket": Ticket.TypeTicket.RECLAMATION,
                        "priorite": Ticket.Priorite.HAUTE,
                        "statut": Ticket.Statut.OUVERT,
                        "assigne_a": None,
                    },
                ),
                (
                    citoyen3,
                    {
                        "titre": f"{demo_ticket_prefix}Demande de service : attestation",
                        "description": "Je souhaite obtenir une attestation de résidence (urgent).",
                        "type_ticket": Ticket.TypeTicket.DEMANDE,
                        "priorite": Ticket.Priorite.NORMALE,
                        "statut": Ticket.Statut.RESOLU,
                        "assigne_a": tech2,
                    },
                ),
                (
                    citoyen1,
                    {
                        "titre": f"{demo_ticket_prefix}Incident : application mobile lente",
                        "description": "L'application met du temps à charger la liste des tickets.",
                        "type_ticket": Ticket.TypeTicket.INCIDENT,
                        "priorite": Ticket.Priorite.BASSE,
                        "statut": Ticket.Statut.CLOS,
                        "assigne_a": tech2,
                    },
                ),
            ]

            created = 0
            for auteur, payload in tickets_specs:
                ticket, was_created = Ticket.objects.get_or_create(
                    titre=payload["titre"],
                    defaults={
                        "description": payload["description"],
                        "type_ticket": payload["type_ticket"],
                        "statut": payload["statut"],
                        "priorite": payload["priorite"],
                        "auteur": auteur,
                        "assigne_a": payload["assigne_a"],
                        "date_resolution": timezone.now()
                        if payload["statut"] in (Ticket.Statut.RESOLU, Ticket.Statut.CLOS)
                        else None,
                    },
                )
                if was_created:
                    created += 1
                    self._add_demo_activity(ticket, auteur=auteur, technicien=payload["assigne_a"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Données de démo prêtes. Utilisateurs: {len(demo_users)} | Tickets créés: {created}"
            )
        )
        self.stdout.write(f"Mot de passe (démo): {password}")

    def _upsert_user(self, spec: DemoUserSpec, password: str):
        user, created = User.objects.get_or_create(
            email=spec.email,
            defaults={
                "username": self._unique_username(spec.username),
                "first_name": spec.first_name,
                "last_name": spec.last_name,
                "role": spec.role,
                "is_staff": spec.is_staff,
                "is_superuser": spec.is_superuser,
                "is_active": True,
            },
        )

        desired_username = spec.username
        if User.objects.exclude(pk=user.pk).filter(username=desired_username).exists():
            desired_username = self._unique_username(desired_username, exclude_pk=user.pk)

        changed = False
        for field, value in (
            ("username", desired_username),
            ("first_name", spec.first_name),
            ("last_name", spec.last_name),
            ("role", spec.role),
            ("is_staff", spec.is_staff),
            ("is_superuser", spec.is_superuser),
        ):
            if getattr(user, field) != value:
                setattr(user, field, value)
                changed = True

        if created or changed:
            user.set_password(password)
            user.save()

        return user

    def _unique_username(self, base: str, *, exclude_pk=None) -> str:
        base = (base or "user")[:150]
        candidate = base
        suffix = 1
        while User.objects.exclude(pk=exclude_pk).filter(username=candidate).exists():
            tail = str(suffix)
            candidate = f"{base[: max(0, 150 - len(tail))]}{tail}"
            suffix += 1
        return candidate

    def _add_demo_activity(self, ticket: Ticket, *, auteur, technicien):
        Commentaire.objects.create(
            ticket=ticket,
            auteur=auteur,
            contenu="Ticket créé automatiquement pour la démonstration.",
        )

        if technicien is not None:
            Commentaire.objects.create(
                ticket=ticket,
                auteur=technicien,
                contenu="Pris en charge. Je vous tiens informé de l'avancement.",
            )

        # Historique (simple) selon le statut final du ticket.
        if ticket.statut == Ticket.Statut.EN_COURS:
            HistoriqueStatut.objects.create(
                ticket=ticket,
                ancien_statut=Ticket.Statut.OUVERT,
                nouveau_statut=Ticket.Statut.EN_COURS,
                modifie_par=technicien,
            )
        elif ticket.statut in (Ticket.Statut.RESOLU, Ticket.Statut.CLOS):
            HistoriqueStatut.objects.create(
                ticket=ticket,
                ancien_statut=Ticket.Statut.OUVERT,
                nouveau_statut=Ticket.Statut.EN_COURS,
                modifie_par=technicien,
            )
            HistoriqueStatut.objects.create(
                ticket=ticket,
                ancien_statut=Ticket.Statut.EN_COURS,
                nouveau_statut=Ticket.Statut.RESOLU,
                modifie_par=technicien,
            )
            if ticket.statut == Ticket.Statut.CLOS:
                HistoriqueStatut.objects.create(
                    ticket=ticket,
                    ancien_statut=Ticket.Statut.RESOLU,
                    nouveau_statut=Ticket.Statut.CLOS,
                    modifie_par=technicien,
                )

    def _reset_demo_data(self, demo_email_suffix: str, demo_ticket_prefix: str):
        # Supprime d'abord les tickets (cascade pour commentaires/historique).
        Ticket.objects.filter(titre__startswith=demo_ticket_prefix).delete()
        User.objects.filter(email__endswith=demo_email_suffix).delete()
        self.stdout.write(self.style.WARNING("Données de démo supprimées (--reset)."))
