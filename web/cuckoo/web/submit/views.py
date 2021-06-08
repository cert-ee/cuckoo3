# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.http import (
    HttpResponseBadRequest, HttpResponseServerError, HttpResponseNotAllowed,
    HttpResponseNotFound
)
from django.shortcuts import render, redirect
from django.views import View

from cuckoo.common import submit, analyses
from cuckoo.common.config import cfg
from cuckoo.common.result import (
    retriever, Results, ResultDoesNotExistError, InvalidResultDataError
)

def _make_web_platforms(available_platforms):
    return [
        {
            "default": platform == cfg(
                "cuckoo", "platform", "default_platform", "platform"
            ),
            "platform": platform,
            "os_version": [os_version for os_version in os_versions]
        } for platform, os_versions in available_platforms.items()
    ]


class Submit(View):

    def get(self, request):
        return render(request, template_name="submit/index.html.jinja2")

    def post(self, request):
        uploaded = request.FILES.get("file")
        url = request.POST.get("url")
        if not uploaded and not url:
            return HttpResponseBadRequest()

        try:
            s_maker = submit.settings_maker.new_settings()
            s_maker.set_manual(True)
            settings = s_maker.make_settings()
            if uploaded:
                analysis_id = submit.file(
                    uploaded.temporary_file_path(), settings,
                    file_name=uploaded.name
                )
            else:
                analysis_id = submit.url(url, settings)
        except submit.SubmissionError as e:
            return render(
                request, template_name="submit/index.html.jinja2",
                status=400, context={"error": str(e)}
            )

        try:
            submit.notify()
        except submit.SubmissionError as e:
            return HttpResponseServerError(
                f"Failed to notify Cuckoo of new analysis {analysis_id}. {e}."
            )

        return redirect("Submit/waitidentify", analysis_id=analysis_id)

class WaitIdentify(View):

    def get(self, request, analysis_id):
        return render(
            request, template_name="submit/loading.html.jinja2",
            context={"analysis_id": analysis_id}
        )

class Settings(View):

    def get(self, request, analysis_id):
        if analyses.get_state(analysis_id) != analyses.States.WAITING_MANUAL:
            return HttpResponseNotAllowed(
                "It is only possible to modify settings for analyses that "
                "are waiting for manual input."
            )

        try:
            analysis = retriever.get_analysis(
                analysis_id, include=[Results.ANALYSIS]
            ).analysis
        except ResultDoesNotExistError:
            return HttpResponseNotFound()
        except InvalidResultDataError as e:
            return HttpResponseServerError(str(e))

        context = {
            "possible_settings": {
                "platforms": _make_web_platforms(
                    submit.settings_maker.available_platforms()
                )
            },
            "analysis": analysis,
            "analysis_id": analysis_id
        }

        if analysis.category == "file":
            try:
                context["unpacked"] = analyses.get_filetree_dict(analysis_id)
            except analyses.AnalysisError as e:
                return HttpResponseNotFound(
                    f"Failed to read filetree for analysis. {e}"
                )

        return render(
            request, template_name="submit/settings.html.jinja2",
            context=context
        )
