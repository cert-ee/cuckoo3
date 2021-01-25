# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.http import HttpResponseServerError, HttpResponseNotFound
from django.shortcuts import render

from cuckoo.common.task import States
from cuckoo.common.storage import TaskPaths, AnalysisPaths
from cuckoo.common.machines import Machine
from cuckoo.common.strictcontainer import Analysis, Task, Post

def index(request, analysis_id, task_id):
    try:
        analysis = Analysis.from_file(AnalysisPaths.analysisjson(analysis_id))
        task = Task.from_file(TaskPaths.taskjson(task_id))
    except FileNotFoundError:
        return HttpResponseNotFound()
    except (ValueError, KeyError, TypeError) as e:
        return HttpResponseServerError(str(e))

    if task.state == States.FATAL_ERROR:
        return render(
            request, template_name="task/error.html.jinja2",
            context={
                "analysis": analysis.to_dict(),
                "task": task.to_dict(),
                "analysis_id": analysis_id
            }
        )

    try:
        postreport = Post.from_file(TaskPaths.report(task_id))
        machine = Machine.from_file(TaskPaths.machinejson(task_id))
    except FileNotFoundError:
        return HttpResponseNotFound()
    except (ValueError, KeyError, TypeError) as e:
        return HttpResponseServerError(str(e))

    return render(
        request, template_name="task/index.html.jinja2",
        context={
            "analysis": analysis.to_dict(),
            "analysis_id": analysis_id,
            "task": task.to_dict(),
            "report": postreport.to_dict(),
            "machine": machine.to_dict()
        }
    )
