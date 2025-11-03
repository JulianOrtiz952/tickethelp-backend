from django.urls import path
from reports.views import GeneralStatsView, TechnicianPerformanceRankingView, ActiveClientsEvolutionView

urlpatterns = [
    path('stats/general-stats/', GeneralStatsView.as_view(), name='general-stats'),
    path('stats/performance-ranking/', TechnicianPerformanceRankingView.as_view(), name='performance-ranking'),
    path('stats/clients-evolution/', ActiveClientsEvolutionView.as_view(), name='clients-evolution'),
]

