# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path, register_converter
from . import views

from cuckoo.web import converters

register_converter(converters.TaskId, "task_id")
register_converter(converters.ScreenshotName, "screenshot")

urlpatterns = [
    path("<task_id:task_id>/pcap", views.Pcap.as_view(), name="Task/pcap"),
    path(
        "<task_id:task_id>/screenshot/<screenshot:screenshot>",
        views.Screenshot.as_view(),
        name="Task/screenshot",
    ),
]
