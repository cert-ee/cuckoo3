# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path, include, register_converter

from cuckoo.web.converters import Sha256Hash

from . import views

register_converter(Sha256Hash, "sha256")

urlpatterns = [
    path("<sha256:sha256>", views.BinaryDownload.as_view()),
]
