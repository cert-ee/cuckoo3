# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

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
        "<analysis_id:analysis_id>/submittedfile",
        views.SubmittedFileDownload.as_view(), name="Analysis/submittedfile"
    ),
    path(
        "<analysis_id:analysis_id>/task/",
        include("cuckoo.web.uiapi.analyses.task.urls")
    )
]
