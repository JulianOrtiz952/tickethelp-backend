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
    ResolutionsByWeekdayView
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
    path('stats/resolutions-by-weekday/', ResolutionsByWeekdayView.as_view(), name='resolutions-by-weekday'),
]

