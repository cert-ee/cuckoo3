# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

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
        "<analysis_id:analysis_id>/task/",
        include("cuckoo.web.api.analysis.task.urls")
    )
]
