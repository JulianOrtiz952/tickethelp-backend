from django.urls import path
from tickets.views import TicketAV, EstadoAV, LeastBusyTechnicianAV, ChangeTechnicianAV, ActiveTechniciansAV

urlpatterns = [
    # Listar tickets y crear tickets
    path('tickets/', TicketAV.as_view(), name="ticket-list"),
    # Obtener el correo del técnico menos ocupado
    path('tickets/least-busy-technician/', LeastBusyTechnicianAV.as_view(), name="least-busy-technician"),
    # Cambiar el técnico de un ticket
    path('tickets/change-technician/<int:ticket_id>/', ChangeTechnicianAV.as_view(), name="change-technician"),
    # Listar todos los técnicos activos para reasignación
    path('tickets/active-technicians/', ActiveTechniciansAV.as_view(), name="active-technicians"),
    # Listar estados de tickets
    path('estados/', EstadoAV.as_view(), name="estado_list"),
]