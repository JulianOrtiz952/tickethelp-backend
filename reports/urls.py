from django.urls import path
from reports.views import GeneralStatsView, TechnicianPerformanceRankingView

urlpatterns = [
    path('stats/general-stats/', GeneralStatsView.as_view(), name='general-stats'),
    path('stats/performance-ranking/', TechnicianPerformanceRankingView.as_view(), name='performance-ranking'),
]

