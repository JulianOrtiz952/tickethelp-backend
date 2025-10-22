from django.urls import path
from tickets.views import TicketAV, EstadoAV, LeastBusyTechnicianAV, ChangeTechnicianAV, ActiveTechniciansAV, StateChangeAV, StateApprovalAV, PendingApprovalsAV, TicketListView

urlpatterns = [
    # Listar tickets y crear tickets
    path('tickets/', TicketAV.as_view(), name="ticket-list"),
    # Obtener el correo del técnico menos ocupado
    path('tickets/least-busy-technician/', LeastBusyTechnicianAV.as_view(), name="least-busy-technician"),
    # Cambiar el técnico de un ticket
    path('tickets/change-technician/<int:ticket_id>/', ChangeTechnicianAV.as_view(), name="change-technician"),
    # Listar todos los técnicos activos para reasignación
    path('tickets/active-technicians/', ActiveTechniciansAV.as_view(), name="active-technicians"),
    # Cambio de estado de tickets
    path('tickets/change-state/<int:ticket_id>/', StateChangeAV.as_view(), name="change-state"),
    # Aprobar/rechazar cambio de estado
    path('tickets/approve-state/<int:request_id>/', StateApprovalAV.as_view(), name="approve-state"),
    # Listar solicitudes pendientes de aprobación
    path('tickets/pending-approvals/', PendingApprovalsAV.as_view(), name="pending-approvals"),
    # Listar estados de tickets
    path('estados/', EstadoAV.as_view(), name="estado_list"),
    # Consultar los tickets asignados al técnico
    path('tickets/consulta/', TicketListView.as_view(), name="ticket-consulta"),
]