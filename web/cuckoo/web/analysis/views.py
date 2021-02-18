# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.http import HttpResponseServerError, HttpResponseNotFound
from django.shortcuts import render

from cuckoo.common.analyses import States
from cuckoo.common.result import (
    retriever, Results, ResultDoesNotExistError, InvalidResultDataError
)

def index(request, analysis_id):
    try:
        result = retriever.get_analysis(
            analysis_id, include=[Results.ANALYSIS, Results.PRE]
        )
        analysis = result.analysis
    except ResultDoesNotExistError:
        return HttpResponseNotFound()
    except InvalidResultDataError as e:
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
        pre = result.pre
    except ResultDoesNotExistError:
        return HttpResponseNotFound()
    except InvalidResultDataError as e:
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
        result = retriever.get_analysis(
            analysis_id, include=[Results.ANALYSIS, Results.PRE]
        )
        analysis = result.analysis
        pre = result.pre
    except ResultDoesNotExistError:
        return HttpResponseNotFound()
    except InvalidResultDataError as e:
        return HttpResponseServerError(str(e))

    return render(
        request, template_name="analysis/static.html.jinja2",
        context={
            "analysis": analysis.to_dict(),
            "pre": pre.to_dict(),
            "analysis_id": analysis_id
        }
    )
