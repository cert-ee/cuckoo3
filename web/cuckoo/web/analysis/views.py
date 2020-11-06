# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from django.http import HttpResponseServerError, HttpResponseNotFound
from django.shortcuts import render

from cuckoo.common.storage import AnalysisPaths
from cuckoo.common.strictcontainer import Analysis, Pre

def index(request, analysis_id):
    try:
        analysis = Analysis.from_file(AnalysisPaths.analysisjson(analysis_id))
    except FileNotFoundError:
        return HttpResponseNotFound()
    except (ValueError, KeyError, TypeError) as e:
        return HttpResponseServerError(str(e))

    return render(
        request, template_name="report/index.html.jinja2",
        context={"analysis": analysis.to_dict()}
    )

def static(request, analysis_id):
    path = os.getenv("PRE_REPORT")
    if not path or not os.path.isfile(path):
        return HttpResponseNotFound(f"Not found: {path}")

    try:
        pre = Pre.from_file(path)
    except FileNotFoundError:
        return HttpResponseNotFound()
    except (ValueError, KeyError, TypeError) as e:
        return HttpResponseServerError(str(e))

    return render(
        request, template_name="report/static.html.jinja2",
        context={"pre": pre.to_dict()}
    )
