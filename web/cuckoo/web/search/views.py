# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.shortcuts import render
from django.views import View

class Search(View):
    def get(self, request):
        return render(request, template_name="search/index.html.jinja2")
