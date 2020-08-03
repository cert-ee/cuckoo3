# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.shortcuts import render

from cuckoo.common import analyses

def index(request):
    return render(
        request, template_name="reports/index.html",
        context={"analyses": analyses.dictlist()}
    )