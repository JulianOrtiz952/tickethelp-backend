from django.urls import path
from tickets.views import TicketAV, EstadoAV, LeastBusyTechnicianAV

urlpatterns = [
    # Listar tickets y crear tickets
    path('tickets/', TicketAV.as_view(), name="ticket-list"),
    # Obtener el correo del técnico menos ocupado
    path('tickets/least-busy-technician/', LeastBusyTechnicianAV.as_view(), name="least-busy-technician"),
    # Listar estados de tickets
    path('estados/', EstadoAV.as_view(), name="estado_list"),
]