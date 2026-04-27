from django.urls import path
from .views import SystemOverviewView, UserStatsView, DailySnapshotsView

urlpatterns = [
    path("overview/", SystemOverviewView.as_view(), name="analytics-overview"),
    path("users/", UserStatsView.as_view(), name="analytics-users"),
    path("snapshots/", DailySnapshotsView.as_view(), name="analytics-snapshots"),
]
