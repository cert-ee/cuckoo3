# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.urls import path, include

urlpatterns = [
    path("analyses/", include("uiapi.analyses.urls")),
    path("search", include("uiapi.search.urls"))
]
