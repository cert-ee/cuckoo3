# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path, register_converter, include

from cuckoo.web import converters

from . import views

register_converter(converters.AnalysisId, "analysis_id")

urlpatterns = [
    path("<analysis_id:analysis_id>", views.index, name="Analysis/index"),
    path(
        "<analysis_id:analysis_id>/static", views.static,
        name="Analysis/static"
    ),
    path("<analysis_id:analysis_id>/task/", include("cuckoo.web.analysis.task.urls")),
    path(
        "<analysis_id:analysis_id>/task/",
        include("cuckoo.web.analysis.task.urls")
    )
]
