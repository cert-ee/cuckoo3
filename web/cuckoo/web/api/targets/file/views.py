# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.http import FileResponse

from rest_framework.response import Response
from rest_framework.views import APIView

from cuckoo.common.result import retriever, ResultDoesNotExistError


class BinaryDownload(APIView):
    def get(self, request, sha256):
        sha256 = sha256.lower()
        try:
            binary_fp = retriever.get_binary(sha256)
        except ResultDoesNotExistError:
            return Response(status=404)

        return FileResponse(binary_fp, as_attachment=True, filename=sha256)
