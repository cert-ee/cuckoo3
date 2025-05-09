# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.http import HttpResponseServerError, HttpResponseNotFound
from django.shortcuts import render

from cuckoo.common.task import States
from cuckoo.common.result import (
    retriever,
    Results,
    ResultDoesNotExistError,
    InvalidResultDataError,
)


def index(request, analysis_id, task_id):
    try:
        result = retriever.get_task(
            analysis_id,
            task_id,
            include=[Results.ANALYSIS, Results.TASK, Results.POST, Results.MACHINE],
        )
        analysis = result.analysis
        task = result.task
    except ResultDoesNotExistError:
        return HttpResponseNotFound()
    except InvalidResultDataError as e:
        return HttpResponseServerError(str(e))

    if task.state == States.FATAL_ERROR:
        return render(
            request,
            template_name="task/error.html.jinja2",
            context={
                "analysis": analysis.to_dict(),
                "task": task.to_dict(),
                "analysis_id": analysis_id,
            },
        )

    try:
        postreport = result.post
        machine = result.machine
    except ResultDoesNotExistError:
        return HttpResponseNotFound()
    except InvalidResultDataError as e:
        return HttpResponseServerError(str(e))

    return render(
        request,
        template_name="task/index.html.jinja2",
        context={
            "analysis": analysis.to_dict(),
            "analysis_id": analysis_id,
            "task": task.to_dict(),
            "report": postreport.to_dict(),
            "machine": machine.to_dict(),
        },
    )
