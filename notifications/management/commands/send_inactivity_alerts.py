from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import Notification, NotificationType
from tickets.models import Ticket
from users.models import User


class Command(BaseCommand):
    help = "Genera alertas para tickets inactivos por mas de 24 horas."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        inactivity_type, _ = NotificationType.objects.get_or_create(
            codigo="ticket_inactivo",
            defaults={
                "nombre": "Alerta de inactividad",
                "descripcion": "Ticket sin cambios por mas de 24 horas",
                "enviar_a_tecnico": True,
                "enviar_a_admin": True,
                "enviar_a_cliente": False,
            },
        )

        inactive_tickets = Ticket.objects.select_related(
            "tecnico", "administrador", "estado"
        ).filter(actualizado_en__lte=cutoff, estado__es_final=False)

        created_count = 0

        for ticket in inactive_tickets:
            recipients = []
            if ticket.tecnico and ticket.tecnico.is_active:
                recipients.append(ticket.tecnico)
            admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
            recipients.extend(admins)

            seen_documents = set()
            for user in recipients:
                if not user or user.document in seen_documents:
                    continue
                seen_documents.add(user.document)

                already_exists = Notification.objects.filter(
                    usuario=user,
                    ticket=ticket,
                    tipo=inactivity_type,
                    datos_adicionales__alert_type="inactivity_24h",
                ).exists()
                if already_exists:
                    continue

                Notification.objects.create(
                    usuario=user,
                    ticket=ticket,
                    tipo=inactivity_type,
                    titulo="Ticket inactivo por mas de 24 horas",
                    mensaje=(
                        f"El ticket #{ticket.pk} ({ticket.titulo}) no tiene cambios "
                        "de estado en mas de 24 horas."
                    ),
                    estado=Notification.Estado.ENVIADA,
                    fecha_envio=timezone.now(),
                    datos_adicionales={
                        "alert_type": "inactivity_24h",
                        "last_update": ticket.actualizado_en.isoformat(),
                    },
                )
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Alertas de inactividad creadas: {created_count}")
        )
