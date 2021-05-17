# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from rest_framework.parsers import MultiPartParser
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from cuckoo.common import submit

class FileSubmission(serializers.Serializer):
    file = serializers.FileField()
    settings = serializers.JSONField()

class SubmitFile(APIView):

    permission_classes = (IsAuthenticated,)
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
            s_maker.set_manual(req_settings.get("manual"))
            s_maker.set_timeout(req_settings.get("timeout"))
            s_maker.set_priority(req_settings.get("priority"))
            s_maker.set_extraction_path(req_settings.get("extrpath", []))
            s_maker.set_platforms_list(req_settings.get("platforms", []))

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
                }, status=500
            )

        return Response({
            "analysis_id": analysis_id,
            "settings": final_settings.to_dict()
        })
