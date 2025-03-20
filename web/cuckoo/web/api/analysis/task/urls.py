# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.urls import path, register_converter
from . import views

from cuckoo.web import converters

register_converter(converters.TaskId, "task_id")
register_converter(converters.ScreenshotName, "screenshot")

urlpatterns = [
    path("<task_id:task_id>", views.Task.as_view()),
    path("<task_id:task_id>/post", views.Post.as_view()),
    path("<task_id:task_id>/machine", views.Machine.as_view()),
    path("<task_id:task_id>/composite", views.CompositeTask.as_view()),
    path("<task_id:task_id>/pcap", views.Pcap.as_view()),
    path("<task_id:task_id>/tlsmaster", views.TLSMaster.as_view()),
    path(
        "<task_id:task_id>/screenshot/<screenshot:screenshot>",
        views.Screenshot.as_view()
    )
]
