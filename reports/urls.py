from django.urls import path
from reports.views import (
    GeneralStatsView,
    TechnicianPerformanceRankingView,
    ActiveClientsEvolutionView,
    ActivityHeatmapView,
    AverageResolutionTimeView,
    TTRPromedioView,
    FlowFunnelView,
    StateDistributionView,
    TicketAgingTopView,
    WeekdayResolutionCountView,
    TTAByStateView,
    TTATotalView,
    ActiveClientsMonthlyComparisonView,
    TechnicianPerformanceView
)

urlpatterns = [
    # ============================================================================
    # Estadísticas generales del sistema (solo administradores)
    # ============================================================================
    path('stats/general-stats/', GeneralStatsView.as_view(), name='general-stats'),
    
    # Ranking de desempeño de técnicos (solo administradores)
    path('stats/performance-ranking/', TechnicianPerformanceRankingView.as_view(), name='performance-ranking'),
    
    # Evolución anual de clientes activos (solo administradores)
    path('stats/clients-evolution/', ActiveClientsEvolutionView.as_view(), name='clients-evolution'),
    
    # Mapa de calor de actividad de cambios de estado (solo administradores)
    path('stats/activity-heatmap/', ActivityHeatmapView.as_view(), name='activity-heatmap'),
    
    # Tiempo promedio de resolución global (solo administradores)
    path('stats/avg-resolution-time/', AverageResolutionTimeView.as_view(), name='avg-resolution-time'),
    
    # Tiempo Total de Resolución (TTR) promedio global y por técnico (solo administradores)
    path('stats/ttr-promedio/', TTRPromedioView.as_view(), name='ttr-promedio'),
    
    # Embudo de flujo: distribución porcentual por estados intermedios (solo administradores)
    path('stats/flow-funnel/', FlowFunnelView.as_view(), name='flow-funnel'),
    
    # Distribución porcentual de tickets por estado en un rango de fechas (solo administradores)
    path('stats/status-distribution/', StateDistributionView.as_view(), name='status-distribution'),
    
    # Top 10 de tickets más antiguos no finalizados (solo administradores)
    path('stats/aging-top/', TicketAgingTopView.as_view(), name='aging-top'),
    
    # Conteo de tickets finalizados por día de la semana (solo administradores)
    path('stats/resolutions-by-weekday/', WeekdayResolutionCountView.as_view(), name='resolutions-by-weekday'),
    
    # Tiempo promedio por estado (TTA) (solo administradores)
    path('stats/tta/by-state/', TTAByStateView.as_view(), name='tta-by-state'),
    
    # TTA total global (solo administradores)
    path('stats/tta/total/', TTATotalView.as_view(), name='tta-total'),
    
    # Comparación mensual de clientes activos (solo administradores)
    path("stats/clientes-activos-mes/", ActiveClientsMonthlyComparisonView.as_view(), name="clientes-activos-mes"),
    
    # ============================================================================
    # Panel de rendimiento del técnico (solo técnicos)
    # ============================================================================
    # HU: Como técnico, quiero visualizar estadísticas de mi rendimiento
    # Endpoint: GET /reports/stats/performance/
    # Retorna:
    #   - Tiempos promedio entre estados relevantes (excluyendo fase de pruebas)
    #   - Duración promedio de resolución desde estado inicial hasta Finalizado
    #   - Total de tickets asignados y resueltos
    #   - Top 3 tickets resueltos en menor tiempo
    # Permisos: Requiere autenticación y rol técnico (403 si no es técnico, 401 si no autenticado)
    path('stats/performance/', TechnicianPerformanceView.as_view(), name='technician-performance')
]

