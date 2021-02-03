# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from cuckoo.common.result import (
    retriever, ResultDoesNotExistError, InvalidResultDataError, Results
)

class Analysis(APIView):

    permission_classes = (IsAuthenticated,)

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

    permission_classes = (IsAuthenticated,)

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

    permission_classes = (IsAuthenticated,)

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

    permission_classes = (IsAuthenticated,)

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
