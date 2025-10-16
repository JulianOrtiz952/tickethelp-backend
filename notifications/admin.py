from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Notification, NotificationType


@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'enviar_a_cliente', 'enviar_a_tecnico', 'enviar_a_admin', 'es_activo']
    list_filter = ['es_activo', 'enviar_a_cliente', 'enviar_a_tecnico', 'enviar_a_admin']
    search_fields = ['codigo', 'nombre', 'descripcion']
    readonly_fields = ['codigo']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'descripcion', 'es_activo')
        }),
        ('Configuración de Destinatarios', {
            'fields': ('enviar_a_cliente', 'enviar_a_tecnico', 'enviar_a_admin'),
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'usuario', 'tipo', 'titulo', 'estado', 
        'fecha_creacion', 'fecha_envio', 'fecha_lectura', 'ticket_link'
    ]
    list_filter = [
        'estado', 'tipo', 'fecha_creacion', 'fecha_envio', 'fecha_lectura'
    ]
    search_fields = [
        'usuario__email', 'usuario__document', 'titulo', 'mensaje', 'ticket__titulo'
    ]
    readonly_fields = [
        'fecha_creacion', 'fecha_envio', 'fecha_lectura'
    ]
    date_hierarchy = 'fecha_creacion'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('usuario', 'tipo', 'ticket', 'estado')
        }),
        ('Contenido', {
            'fields': ('titulo', 'mensaje')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_envio', 'fecha_lectura'),
            'classes': ('collapse',)
        }),
    )
    
    def ticket_link(self, obj):
        """Muestra un enlace al ticket relacionado."""
        if obj.ticket:
            url = reverse('admin:tickets_ticket_change', args=[obj.ticket.pk])
            return format_html('<a href="{}">#{}</a>', url, obj.ticket.pk)
        return '-'
    ticket_link.short_description = 'Ticket'
    ticket_link.admin_order_field = 'ticket__pk'
    
    def get_queryset(self, request):
        """Optimiza las consultas con select_related."""
        return super().get_queryset(request).select_related(
            'usuario', 'tipo', 'ticket'
        )