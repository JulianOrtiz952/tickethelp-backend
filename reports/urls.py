from django.urls import path
from reports.views import GeneralStatsView

urlpatterns = [
    path('stats/general-stats/', GeneralStatsView.as_view(), name='general-stats'),
]

