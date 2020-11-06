# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.urls import path, register_converter

from cuckoo.web import converters

from . import views

register_converter(converters.AnalysisId, "analysis_id")

urlpatterns = [
    path("<analysis_id:analysis_id>", views.index, name="Analysis/index"),
    path(
        "<analysis_id:analysis_id>/static", views.static,
        name="Analysis/static"
    ),
]