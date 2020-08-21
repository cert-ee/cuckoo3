# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.urls import path

from . import views

from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path("", csrf_exempt(views.Search.as_view())),
]
