# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.urls import path, register_converter, include

from cuckoo.web import converters
from . import views

register_converter(converters.AnalysisId, "analysis_id")

urlpatterns = [
    path(
        "<analysis_id:analysis_id>/settings", views.Settings.as_view(),
        name="Analyses/settings",
    ),
    path("<analysis_id:analysis_id>", views.Analysis.as_view()),
    path(
        "<analysis_id:analysis_id>/manualstatus",
        views.ReadyForManual.as_view()
    ),
    path(
        "<analysis_id:analysis_id>/task/",
        include("cuckoo.web.uiapi.analyses.task.urls")
    )
]
