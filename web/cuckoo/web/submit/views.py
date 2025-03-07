# Copyright (C) 2019-2023 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from urllib.parse import urlparse

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.http import (
    HttpResponseBadRequest, HttpResponseServerError, HttpResponseNotAllowed,
    HttpResponseNotFound
)
from django.shortcuts import render, redirect
from django.views import View
import re
import logging

from cuckoo.common import submit, analyses
from cuckoo.common.config import cfg
from cuckoo.common.result import (
    retriever, Results, ResultDoesNotExistError, InvalidResultDataError
)
from cuckoo.common.storage import AnalysisPaths

def _validate_website_url(website):
    """Validate website into valid URL"""
    msg = f"Cannot validate this URL: {website}"
    validate = URLValidator(message=msg)
    try:
        validate(website)
    except:
        raise ValidationError(message=msg)
    return website


def _make_web_platforms(available_platforms):
    fallbacks = cfg(
        "analysissettings.yaml", "platform", "fallback_platforms"
    )
    versions = cfg(
        "analysissettings.yaml", "platform", "versions"
    )

    default_platform = ""
    default_version = ""
    if fallbacks:
        default_platform = fallbacks[0]
        platform_versions = versions.get(default_platform, [])
        if platform_versions:
            default_version = platform_versions[0]

    platforms = []
    for platform, os_versions in available_platforms.items():
        entry = {
            "default": False,
            "platform": platform,
            "os_version": list(os_versions)
        }
        platforms.append(entry)
        if platform != default_platform:
            continue

        if not default_version:
            entry["default"] = True
        else:
            # Search for a version matching the default. If we find it,
            # ensure it is the first in the list of versions. This will cause
            # it to be first in dropdown menus.
            versions = entry["os_version"]
            for version in os_versions:
                if version == default_version:
                    versions.insert(0, version)
                    entry["default"] = True
                    entry["os_version"] = list(set(versions))
                    break

    return platforms


class Submit(View):

    def get(self, request):
        return render(request, template_name="submit/index.html.jinja2")

    def post(self, request):
        uploaded = request.FILES.get("file")
        url = request.POST.get("url")
        if url:
            try:
                url = _validate_website_url(request.POST.get("url"))
            except ValidationError as e:
                return render(
                    request, template_name="submit/index.html.jinja2",
                    status=400, context={"error": str(e)}
                )
        if not uploaded and not url:
            return HttpResponseBadRequest()

        try:
            s_maker = submit.settings_maker.new_settings()
            s_maker.set_manual(True)

            password = request.POST.get("password")
            if password:
                s_maker.set_password(password)

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
                ),
                "routes": submit.settings_maker.available_routes(),
                "browsers": submit.settings_maker.available_browsers()
            },
            "default_settings": submit.settings_maker.default,
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



def _validate_analysis_id(analysis_id):
    """Validate analysis id"""
    ANALYSIS_ID_REGEX = "[0-9]{8}-[A-Z0-9]{6}"

    #msg = "Cannot validate analysis_id": %s" % analysis_id
    msg = f"Cannot validate this analysis_id: {analysis_id}"
    complied_regex = re.compile(ANALYSIS_ID_REGEX)
    match = complied_regex.fullmatch(analysis_id)
    if not match:
        raise ValidationError(message=msg)
    return analysis_id

class Resubmit(View):

    def get(self, request, *args, **kwargs):
        analysis_id = kwargs.get("analysis_id")
        #analysis_id = request.GET.get("analysis_id")

        if analysis_id:
            try:
                analysis_id = _validate_analysis_id(analysis_id)
            except ValidationError as e:
                return render(
                    request, template_name="submit/index.html.jinja2",
                    status=400, context={"error": str(e)}
                )
        else:
            return HttpResponseBadRequest()

        analysis = retriever.get_analysis(analysis_id).analysis


        try:
            s_maker = submit.settings_maker.new_settings()
            s_maker.set_manual(True)

            password = analysis.settings.password
            if password:
                s_maker.set_password(password)

            settings = s_maker.make_settings()
            if analysis.category == "file":
                submit_path = AnalysisPaths.submitted_file(analysis_id, resolve=True)
                analysis_id = submit.file(
                    submit_path, settings, file_name=analysis.target.target
                )
            else:
                analysis_id = submit.url(analysis.target.target, settings)
        except submit.SubmissionError as e:
            return render(
                request, template_name="submit/index.html.jinja2",
                status=400, context={"error": str(e)}
            )

        try:
            submit.notify()
        except submit.SubmissionError as e:
            logging.error(f"Failed to notify Cuckoo of new analysis {analysis_id}. Exception: {e}")
            return HttpResponseServerError(
                "Failed to notify Cuckoo of new analysis. Please try again later."
            )

        return redirect("Submit/waitidentify", analysis_id=analysis_id)      
