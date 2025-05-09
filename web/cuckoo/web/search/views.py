# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.shortcuts import render
from django.views import View


class Search(View):
    def get(self, request):
        return render(request, template_name="search/index.html.jinja2")
