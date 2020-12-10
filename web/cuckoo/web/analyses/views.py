# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.shortcuts import render
from django.http import HttpResponseBadRequest

from cuckoo.common import analyses

def index(request):
    limit = request.GET.get("limit", 20)
    offset = request.GET.get("offset", 0)
    desc = request.GET.get("desc", True)

    try:
        limit = int(limit)
        offset = int(offset)
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Offset and limit must be integers")

    if offset < 0:
        offset = 0
    if limit < 0:
        limit = 20

    try:
        analyses_list = analyses.dictlist(
            limit=limit, offset=offset, desc=desc
        )
    except TypeError as e:
        return HttpResponseBadRequest(str(e))

    return render(
        request, template_name="analyses/index.html.jinja2",
        context={
            "analyses": analyses_list,
            "offset": offset,
            "limit": limit,
            "desc": desc
        }
    )
