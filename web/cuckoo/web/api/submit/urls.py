# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.urls import path
from . import views

urlpatterns = [
    path("file", views.SubmitFile.as_view()),
    path("url", views.SubmitURL.as_view()),
    path("platforms", views.PlatformList.as_view())
]
