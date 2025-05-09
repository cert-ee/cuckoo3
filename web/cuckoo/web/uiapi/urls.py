# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path, include

urlpatterns = [
    path("analyses/", include("uiapi.analyses.urls")),
    path("search", include("uiapi.search.urls")),
    path("statistics/", include("uiapi.statistics.urls")),
]
