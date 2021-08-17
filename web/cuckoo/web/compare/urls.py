# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path, register_converter

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
