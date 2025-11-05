from django.urls import path
from reports.views import GeneralStatsView, TechnicianPerformanceRankingView, ActiveClientsEvolutionView, ActivityHeatmapView, AverageResolutionTimeView, StateDistributionView

urlpatterns = [
    path('stats/general-stats/', GeneralStatsView.as_view(), name='general-stats'),
    path('stats/performance-ranking/', TechnicianPerformanceRankingView.as_view(), name='performance-ranking'),
    path('stats/clients-evolution/', ActiveClientsEvolutionView.as_view(), name='clients-evolution'),
    path('stats/activity-heatmap/', ActivityHeatmapView.as_view(), name='activity-heatmap'),
    path('stats/avg-resolution-time/', AverageResolutionTimeView.as_view(), name='avg-resolution-time'),
    path('stats/status-distribution/', StateDistributionView.as_view(), name='status-distribution'),
]

