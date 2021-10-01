# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from rest_framework.parsers import MultiPartParser
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from cuckoo.common import submit

class FileSubmission(serializers.Serializer):
    file = serializers.FileField(help_text="A file to analyze")
    settings = serializers.JSONField(help_text="A settings dictionary")

class URLSubmission(serializers.Serializer):
    url = serializers.CharField(help_text="A URL to analyze")
    settings = serializers.JSONField(help_text="A settings dictionary")

class SubmitFile(APIView):

    serializer_class = FileSubmission
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = FileSubmission(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        uploaded = request.FILES["file"]
        req_settings = serializer.data["settings"]
        final_settings = {}
        try:
            s_maker = submit.settings_maker.new_settings()
            s_maker.from_dict(req_settings)

            final_settings = s_maker.make_settings()
            analysis_id = submit.file(
                uploaded.temporary_file_path(), final_settings,
                file_name=uploaded.name
            )
        except submit.SubmissionError as e:
            return Response({"error": str(e)}, status=400)

        try:
            submit.notify()
        except submit.SubmissionError as e:
            return Response(
                {
                    "error": str(e),
                    "analysis_id": analysis_id
                }, status=503
            )

        return Response({
            "analysis_id": analysis_id,
            "settings": final_settings.to_dict()
        })

class SubmitURL(APIView):

    serializer_class = URLSubmission

    def post(self, request):
        serializer = URLSubmission(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        url = request.data["url"]
        req_settings = serializer.data["settings"]
        final_settings = {}
        try:
            s_maker = submit.settings_maker.new_settings()
            s_maker.from_dict(req_settings)

            final_settings = s_maker.make_settings()
            analysis_id = submit.url(url, final_settings)
        except submit.SubmissionError as e:
            return Response({"error": str(e)}, status=400)

        try:
            submit.notify()
        except submit.SubmissionError as e:
            return Response(
                {
                    "error": str(e),
                    "analysis_id": analysis_id
                }, status=503
            )

        return Response({
            "analysis_id": analysis_id,
            "settings": final_settings.to_dict()
        })

class AvailablePlatforms(APIView):

    def get(self, request):
        return Response(submit.settings_maker.available_platforms())

class AvailableRoutes(APIView):

    def get(self, request):
        return Response(submit.settings_maker.available_routes())

class AvailableBrowsers(APIView):

    def get(self, request):
        return Response(submit.settings_maker.available_browsers())