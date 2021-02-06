# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from django.http import HttpResponseServerError, HttpResponseNotFound
from django.shortcuts import render

from cuckoo.common.storage import task_to_analysis_id
from cuckoo.common.analyses import States
from cuckoo.common.compare import ComparePostReports, CompareError
from cuckoo.common.result import (
    retriever, Results, ResultDoesNotExistError, InvalidResultDataError
)

def index(request):
    return render(request, template_name="compare/index.html.jinja2",)

def compare(request, task_id1, task_id2):
    try:
        task1result = retriever.get_task(
            task_to_analysis_id(task_id1), task_id1,
            include=[Results.TASK, Results.POST]
        )
        task2result = retriever.get_task(
            task_to_analysis_id(task_id2), task_id2,
            include=[Results.TASK, Results.POST]
        )
        task1 = task1result.task
        task1post = task1result.post
        task2 = task2result.task
        task2post = task2result.post
    except ResultDoesNotExistError:
        return HttpResponseNotFound()
    except InvalidResultDataError as e:
        return HttpResponseServerError(str(e))

    try:
        compared = ComparePostReports([task1post, task2post])
        compared.compare()
    except CompareError as e:
        return HttpResponseServerError(str(e))

    return render(
        request, template_name="compare/compare.html.jinja2",
        context={
            "comparison": compared.to_dict(),
            "lefttask": {
                "report": task1post.to_dict(),
                "task": task1.to_dict()
            },
            "righttask": {
                "report": task2post.to_dict(),
                "task": task2.to_dict()
            }
        }
    )

