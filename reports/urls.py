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
    ActiveClientsMonthlyComparisonView
)

urlpatterns = [
    path('stats/general-stats/', GeneralStatsView.as_view(), name='general-stats'),
    path('stats/performance-ranking/', TechnicianPerformanceRankingView.as_view(), name='performance-ranking'),
    path('stats/clients-evolution/', ActiveClientsEvolutionView.as_view(), name='clients-evolution'),
    path('stats/activity-heatmap/', ActivityHeatmapView.as_view(), name='activity-heatmap'),
    path('stats/avg-resolution-time/', AverageResolutionTimeView.as_view(), name='avg-resolution-time'),
    path('stats/ttr-promedio/', TTRPromedioView.as_view(), name='ttr-promedio'),
    path('stats/flow-funnel/', FlowFunnelView.as_view(), name='flow-funnel'),
    path('stats/status-distribution/', StateDistributionView.as_view(), name='status-distribution'),
    path('stats/aging-top/', TicketAgingTopView.as_view(), name='aging-top'),
    path('stats/resolutions-by-weekday/', WeekdayResolutionCountView.as_view(), name='resolutions-by-weekday'),
    path('stats/tta/by-state/', TTAByStateView.as_view(), name='tta-by-state'),
    path('stats/tta/total/', TTATotalView.as_view(), name='tta-total'),
    path("stats/clientes-activos-mes/", ActiveClientsMonthlyComparisonView.as_view(), name="clientes-activos-mes"),
]

