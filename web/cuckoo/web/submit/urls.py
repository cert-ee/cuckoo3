# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path, register_converter

from cuckoo.web import converters
from . import views

register_converter(converters.AnalysisId, "analysis_id")

urlpatterns = [
    path("", views.Submit.as_view(), name="Submit/index"),
    path(
        "waitidentify/<analysis_id:analysis_id>",
        views.WaitIdentify.as_view(), name="Submit/waitidentify"),
    path(
        "settings/<analysis_id:analysis_id>/", views.Settings.as_view(),
        name="Submit/settings"
    ),
    path(
        "re/<analysis_id:analysis_id>/", views.Resubmit.as_view(),
        name="Submit/resubmit"
    ),
]
