# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator
from django.http import HttpResponseBadRequest, HttpResponseServerError, JsonResponse, HttpResponseNotAllowed, HttpResponseNotFound
import json
import os

from cuckoo.common import submit, analyses
from cuckoo.common.storage import cuckoocwd, AnalysisPaths, Paths
from cuckoo.web.decorators import accepts_json
from cuckoo.common.db import dbms

cuckoocwd.set(cuckoocwd.DEFAULT)

submit.load_machines_dump()
dbms.initialize(f"sqlite:///{Paths.dbfile()}")

class Analysis(View):
    def get(self, request, analysis_id):
        try:
            analysis = analyses.get_analysis(analysis_id)
        except analyses.AnalysisError as e:
            return JsonResponse({"error": str(e)})

        return JsonResponse(analysis.to_dict())

class Settings(View):

    def get(self, request, analysis_id):
        try:
            analysis = analyses.get_analysis(analysis_id)
        except analyses.AnalysisError as e:
            return JsonResponse({"error": str(e)})

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
            return JsonResponse({"error": str(e)})

        return JsonResponse(settings.to_dict())
