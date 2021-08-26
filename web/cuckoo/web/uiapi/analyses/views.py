# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common import submit, analyses

from django.http import JsonResponse, HttpResponseNotFound, HttpResponse
from django.urls import reverse
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
        try:
            analysis = analyses.get_analysis(analysis_id)
        except analyses.AnalysisError as e:
            return JsonResponse({"error": str(e)}, status=400)

        s_maker = submit.settings_maker.new_settings()
        try:
            # The given settings are overwriting the existing ones. Ensure
            # a previously given file password is propagated to the new
            # set of settings.
            if analysis.settings.password:
                s_maker.set_password(analysis.settings.password)

            s_maker.from_dict(request.json)
            # We overwrite all settings, but want to retain the 'manual'
            # setting to be able to recognize it was used after this step.
            s_maker.set_manual(True)
            fileid = request.json.get("fileid")
            if fileid:
                s_maker.set_extraction_path(
                    submit.find_extrpath_fileid(analysis_id, fileid)
                )
            else:
                s_maker.set_extraction_path(request.json.get("extrpath", []))

            settings = s_maker.make_settings()
            submit.manual_set_settings(analysis_id, settings)
        except submit.SubmissionError as e:
            return JsonResponse({"error": str(e)}, status=400)

        return JsonResponse(settings.to_dict())

class ReadyForManual(View):
    def get(self, request, analysis_id):
        state = analyses.get_state(analysis_id)
        if not state:
            return HttpResponseNotFound()

        if state == analyses.States.PENDING_IDENTIFICATION:
            # HTTP accepted. Client must wait and ask again until
            # identification has finished.
            return HttpResponse(status=202)
        else:
            resp = HttpResponse()
            # We are using a 200 response with location header, because the
            # UI is using a js fetch to retrieve this API. We want to redirect
            # the page to the location and not to cause the fetch to retrieve
            # the location.
            if state == analyses.States.WAITING_MANUAL:
                # Client can now be redirected to settings page. Tell UI to
                # redirect to it.
                resp["location"] = reverse(
                    "Submit/settings", args=[analysis_id]
                )
                return resp
            if state in (analyses.States.NO_SELECTED,
                           analyses.States.PENDING_PRE):
                # Analysis page cannot (yet) be viewed. Tell UI to redirect
                # to the overview page
                resp["location"] = reverse("Analyses/index")
                return resp

            # Any other state should have a viewable analysis page.
            # Tell UI to redirect to it.
            resp["location"] = reverse("Analysis/index", args=[analysis_id])
            return resp
