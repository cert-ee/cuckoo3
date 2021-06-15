# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path

from . import views

urlpatterns = [
    path("charts", views.Charts.as_view(), name="api/charts"),
]
