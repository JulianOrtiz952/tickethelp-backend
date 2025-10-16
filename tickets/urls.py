from django.urls import path
from tickets.views import (
    TicketAV, EstadoAV, ticket_detail, 
    request_ticket_completion, approve_ticket_completion
)

urlpatterns = [
    # Lista y creación de tickets
    path('tickets/', TicketAV.as_view(), name="ticket-list"),
    
    # Detalle y modificación de tickets
    path('tickets/<int:ticket_id>/', ticket_detail, name="ticket-detail"),
    
    # Solicitud de finalización
    path('tickets/<int:ticket_id>/request-completion/', 
         request_ticket_completion, name="request-completion"),
    
    # Aprobación de finalización
    path('tickets/<int:ticket_id>/approve-completion/', 
         approve_ticket_completion, name="approve-completion"),
    
    # Estados
    path('estados/', EstadoAV.as_view(), name="estado_list"),
]