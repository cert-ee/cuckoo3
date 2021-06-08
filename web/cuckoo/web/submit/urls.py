# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

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
]
