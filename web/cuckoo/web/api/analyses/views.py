# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from cuckoo.common import analyses

class ListQuery(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=0, default=20)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)
    desc = serializers.BooleanField(required=False, default=True)

class AnalysisList(APIView):

    def get(self, request):
        s = ListQuery(data=request.query_params)
        if not s.is_valid():
            return Response(s.errors, status=400)

        limit = s.data["limit"]
        offset = s.data["offset"]
        desc = s.data["desc"]
        try:
            analyses_list = analyses.dictlist(
                limit=limit, offset=offset, desc=desc
            )
        except TypeError as e:
            return Response({"error": str(e)}, status=400)

        return Response({
            "analyses": analyses_list,
            "offset": offset,
            "limit": limit,
            "desc": desc
        })
