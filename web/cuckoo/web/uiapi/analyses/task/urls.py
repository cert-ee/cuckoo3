# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.urls import path, register_converter
from . import views

from cuckoo.web import converters

register_converter(converters.TaskId, "task_id")

urlpatterns = [
    path("<task_id:task_id>/pcap", views.Pcap.as_view(), name="Task/pcap"),
]
