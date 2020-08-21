# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common import submit, analyses

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from cuckoo.web.decorators import accepts_json

class Analysis(View):
    def get(self, request, analysis_id):
        try:
            analysis = analyses.get_analysis(analysis_id)
        except analyses.AnalysisError as e:
            return JsonResponse({"error": str(e)}, status=400)

        return JsonResponse(analysis.to_dict())

class Settings(View):

    def get(self, request, analysis_id):
        try:
            analysis = analyses.get_analysis(analysis_id)
        except analyses.AnalysisError as e:
            return JsonResponse({"error": str(e)}, status=400)

        return JsonResponse(analysis.settings.to_dict())

    @method_decorator(accepts_json)
    def put(self, request, analysis_id):
        s_maker = submit.SettingsMaker()
        try:
            s_maker.set_manual(True)
            s_maker.set_timeout(request.json.get("timeout"))
            s_maker.set_priority(request.json.get("priority"))

            fileid = request.json.get("fileid")
            if fileid:
                s_maker.set_extraction_path(
                    submit.find_extrpath_fileid(analysis_id, fileid)
                )
            else:
                s_maker.set_extraction_path(request.json.get("extrpath", []))

            s_maker.set_platforms_list(request.json.get("platforms", []))

            settings = s_maker.make_settings()
            submit.manual_set_settings(analysis_id, settings)
        except submit.SubmissionError as e:
            return JsonResponse({"error": str(e)}, status=400)

        return JsonResponse(settings.to_dict())

class ReadyForManual(View):
    def get(self, request, analysis_id):
        state = analyses.get_state(analysis_id)
        if not state:
            return JsonResponse(
                {"error": "Analysis does not exist"}, status=404
            )

        human_state = analyses.States.to_human(state)
        if state == analyses.States.WAITING_MANUAL:
            return JsonResponse(
                {"ready": True, "state_desc": human_state}
            )

        elif state == analyses.States.FATAL_ERROR:
            try:
                errs = analyses.get_fatal_errors(analysis_id)
            except analyses.AnalysisError as e:
                return JsonResponse(
                    {
                        "error": "Analysis has state 'fatal error'. "
                                 f"Could not retrieve errors. {e}",
                        "ready": False,
                        "state_desc": human_state
                    }
                )

            if errs:
                error = errs[0]
            else:
                error = ""
            return JsonResponse({
                "error": f"Fatal error during analysis. {error}",
                "ready": False,
                "state_desc": human_state
            })

        return JsonResponse({
            "ready": False,
            "state_desc": human_state
        })
