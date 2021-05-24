# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.urls import path, register_converter
from . import views

from cuckoo.web import converters

register_converter(converters.TaskId, "task_id")

urlpatterns = [
    path("<task_id:task_id>", views.Task.as_view()),
    path("<task_id:task_id>/post", views.Post.as_view()),
    path("<task_id:task_id>/machine", views.Machine.as_view()),
    path("<task_id:task_id>/composite", views.CompositeTask.as_view()),
    path("<task_id:task_id>/pcap", views.Pcap.as_view())
]
