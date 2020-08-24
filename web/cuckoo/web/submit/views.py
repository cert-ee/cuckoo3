# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common import submit, analyses
from cuckoo.common.machines import get_platforms_versions

from django.http import (
    HttpResponseBadRequest, HttpResponseServerError, HttpResponseNotAllowed,
    HttpResponseNotFound
)
from django.shortcuts import render, redirect
from django.views import View

_available_platforms = [
    {
        "platform": platform,
        "os_version": [os_version for os_version in os_versions]
     } for platform, os_versions in get_platforms_versions().items()
]

class SubmitFile(View):
    def get(self, request):
        return render(request, template_name="submit/index.html")

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return HttpResponseBadRequest()

        try:
            s_maker = submit.SettingsMaker()
            s_maker.set_manual(True)
            analysis_id = submit.file(
                uploaded.temporary_file_path(), s_maker.make_settings(),
                file_name=uploaded.name
            )
        except submit.SubmissionError as e:
            return render(
                request, template_name="submit/index.html",
                status=400, context={"error": str(e)}
            )

        try:
            submit.notify()
        except submit.SubmissionError as e:
            return HttpResponseServerError(
                f"Failed to notify Cuckoo of new analysis {analysis_id}. {e}."
            )

        return redirect("Submit/settings", analysis_id=analysis_id)

class Settings(View):

    def get(self, request, analysis_id):
        if analyses.get_state(analysis_id) != analyses.States.WAITING_MANUAL:
            return HttpResponseNotAllowed(
                "It is only possible to modify settings for analyses that "
                "are waiting for manual input."
            )

        try:
            filetree = analyses.get_filetree_dict(analysis_id)
        except analyses.AnalysisError as e:
            return HttpResponseNotFound(
                f"Failed to read filetree for analysis. {e}"
            )

        return render(
            request, template_name="submit/settings.html",
            context={
                "unpacked": filetree,
                "possible_settings": {"platforms" :_available_platforms}
            }
        )
