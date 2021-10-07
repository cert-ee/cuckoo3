# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.http import FileResponse

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from cuckoo.common.result import (
    retriever, ResultDoesNotExistError, InvalidResultDataError, Results
)

class Analysis(APIView):

    def get(self, request, analysis_id):
        try:
            analysis = retriever.get_analysis(
                analysis_id, include=[Results.ANALYSIS]
            ).analysis
        except ResultDoesNotExistError:
            return Response(status=404)
        except InvalidResultDataError as e:
            return Response({"error": str(e)}, status=500)

        return Response(analysis.to_dict())

class Identification(APIView):

    def get(self, request, analysis_id):
        try:
            ident = retriever.get_analysis(
                analysis_id, include=[Results.IDENTIFICATION]
            ).identification
        except ResultDoesNotExistError:
            return Response(status=404)
        except InvalidResultDataError as e:
            return Response({"error": str(e)}, status=500)

        return Response(ident.to_dict())

class Pre(APIView):

    def get(self, request, analysis_id):
        try:
            pre = retriever.get_analysis(
                analysis_id, include=[Results.PRE]
            ).pre
        except ResultDoesNotExistError:
            return Response(status=404)
        except InvalidResultDataError as e:
            return Response({"error": str(e)}, status=500)

        return Response(pre.to_dict())

class CompositeRequest(serializers.Serializer):
    retrieve = serializers.ListField(
        allow_empty=False, child=serializers.CharField(),
        help_text="A list of one or more analysis information types to "
                  "retrieve",
    )

class CompositeAnalysis(APIView):

    def post(self, request, analysis_id):
        serializer = CompositeRequest(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, 400)

        retrieve = [r.lower() for r in serializer.data["retrieve"]]
        try:
            composite = retriever.get_analysis(analysis_id, include=retrieve)
            composite.load_requested(missing_report_default={})
        except ResultDoesNotExistError:
            return Response(status=404)
        except InvalidResultDataError as e:
            return Response({"error": str(e)}, status=500)

        return Response(composite.to_dict())

class SubmittedFile(APIView):

    def get(self, request, analysis_id):
        try:
            result = retriever.get_analysis(
                analysis_id, include=[Results.ANALYSIS]
            )
            analysis = result.analysis
            submitted_fp = result.submitted_file
        except ResultDoesNotExistError:
            return Response(status=404)

        return FileResponse(
            submitted_fp, as_attachment=True,
            filename=analysis.submitted.sha256
        )
