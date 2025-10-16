from django.urls import path
from tickets.views import TicketAV, EstadoAV

urlpatterns = [
    path('tickets/', TicketAV.as_view(), name="ticket-list"),
    path('estados/', EstadoAV.as_view(), name="estado_list"),
]