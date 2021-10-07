# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path, register_converter, include
from . import views

from cuckoo.web import converters

register_converter(converters.AnalysisId, "analysis_id")

urlpatterns = [
    path("<analysis_id:analysis_id>", views.Analysis.as_view()),
    path(
        "<analysis_id:analysis_id>/identification",
        views.Identification.as_view()
    ),
    path("<analysis_id:analysis_id>/pre", views.Pre.as_view()),
    path(
        "<analysis_id:analysis_id>/composite",
        views.CompositeAnalysis.as_view()
    ),
    path(
        "<analysis_id:analysis_id>/submittedfile",
        views.SubmittedFile.as_view()
    ),
    path(
        "<analysis_id:analysis_id>/task/",
        include("cuckoo.web.api.analysis.task.urls")
    )
]
