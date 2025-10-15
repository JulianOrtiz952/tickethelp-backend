from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
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
            'description': 'Define a qué tipos de usuarios se envía este tipo de notificación'
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
        'fecha_creacion', 'fecha_envio', 'fecha_lectura', 'datos_adicionales_display'
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
        ('Datos Adicionales', {
            'fields': ('datos_adicionales_display',),
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
    
    def datos_adicionales_display(self, obj):
        """Muestra los datos adicionales de forma legible."""
        if obj.datos_adicionales:
            import json
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 4px;">{}</pre>',
                json.dumps(obj.datos_adicionales, indent=2, ensure_ascii=False)
            )
        return 'Sin datos adicionales'
    datos_adicionales_display.short_description = 'Datos Adicionales'
    
    def get_queryset(self, request):
        """Optimiza las consultas con select_related."""
        return super().get_queryset(request).select_related(
            'usuario', 'tipo', 'ticket'
        )
    
    actions = ['marcar_como_enviadas', 'marcar_como_leidas']
    
    def marcar_como_enviadas(self, request, queryset):
        """Acción para marcar notificaciones como enviadas."""
        from django.utils import timezone
        updated = queryset.filter(estado='PENDIENTE').update(
            estado='ENVIADA',
            fecha_envio=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} notificaciones marcadas como enviadas.'
        )
    marcar_como_enviadas.short_description = "Marcar como enviadas"
    
    def marcar_como_leidas(self, request, queryset):
        """Acción para marcar notificaciones como leídas."""
        from django.utils import timezone
        updated = queryset.filter(estado='ENVIADA').update(
            estado='LEIDA',
            fecha_lectura=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} notificaciones marcadas como leídas.'
        )
    marcar_como_leidas.short_description = "Marcar como leídas"