# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path
from . import views

urlpatterns = [
    path("file", views.SubmitFile.as_view()),
    path("url", views.SubmitURL.as_view()),
    path("platforms", views.AvailablePlatforms.as_view()),
    path("routes", views.AvailableRoutes.as_view())
]
