# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from django.http import HttpResponseServerError, HttpResponseNotFound
from django.shortcuts import render

from cuckoo.common.analyses import States
from cuckoo.common.storage import AnalysisPaths
from cuckoo.common.strictcontainer import Analysis, Pre

def index(request, analysis_id):
    try:
        analysis = Analysis.from_file(AnalysisPaths.analysisjson(analysis_id))
    except FileNotFoundError:
        return HttpResponseNotFound()
    except (ValueError, KeyError, TypeError) as e:
        return HttpResponseServerError(str(e))

    if analysis.state == States.FATAL_ERROR:
        return render(
            request, template_name="analysis/error.html.jinja2",
            context={
                "analysis": analysis.to_dict(),
                "analysis_id": analysis_id
            }
        )

    try:
        pre = Pre.from_file(AnalysisPaths.prejson(analysis_id))
    except FileNotFoundError:
        return HttpResponseNotFound()
    except (ValueError, KeyError, TypeError) as e:
        return HttpResponseServerError(str(e))

    return render(
        request, template_name="analysis/index.html.jinja2",
        context={
             "analysis": analysis.to_dict(),
             "pre": pre.to_dict(),
             "analysis_id": analysis_id
        }
    )

def static(request, analysis_id):
    try:
        analysis = Analysis.from_file(AnalysisPaths.analysisjson(analysis_id))
        pre = Pre.from_file(AnalysisPaths.prejson(analysis_id))
    except FileNotFoundError:
        return HttpResponseNotFound()
    except (ValueError, KeyError, TypeError) as e:
        return HttpResponseServerError(str(e))

    return render(
        request, template_name="analysis/static.html.jinja2",
        context={
            "analysis": analysis.to_dict(),
            "pre": pre.to_dict(),
            "analysis_id": analysis_id
        }
    )

def compare(request, analysis_id):
    try:
        analysis = Analysis.from_file(AnalysisPaths.analysisjson(analysis_id))
    except FileNotFoundError:
        return HttpResponseNotFound()
    except (ValueError, KeyError, TypeError) as e:
        return HttpResponseServerError(str(e))

    return render(
        request, template_name="analysis/compare.html.jinja2",
        context={
            "analysis": analysis.to_dict(),
            "analysis_id": analysis_id
        }
    )
