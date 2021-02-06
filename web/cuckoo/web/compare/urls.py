# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.urls import path, register_converter, include

from cuckoo.web import converters

from . import views

register_converter(converters.TaskId, "task_id")

urlpatterns = [
    path("", views.index, name="Compare/index"),
    path(
        "<task_id:task_id1>/<task_id:task_id2>", views.compare,
        name="Compare/compare"
    )
]
