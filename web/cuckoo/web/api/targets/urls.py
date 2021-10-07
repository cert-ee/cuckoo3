# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path, include

urlpatterns = [
    path("file/", include("cuckoo.web.api.targets.file.urls"))
]
