# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.shortcuts import render


def index(request):
    return render(request, template_name="dashboard/index.html.jinja2")
