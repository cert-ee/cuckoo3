# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.urls import path, register_converter

from cuckoo.web import converters
from . import views

from django.views.decorators.csrf import csrf_exempt

register_converter(converters.AnalysisId, "analysis_id")

urlpatterns = [
    path("", views.SubmitFile.as_view(), name="Submit/submitfile"),
    path(
        "settings/<analysis_id:analysis_id>/",
        csrf_exempt(views.Settings.as_view()),
        name="Submit/settings"
    ),
]
