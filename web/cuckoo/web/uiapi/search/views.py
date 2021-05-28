# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from cuckoo.common.elastic import search, ElasticSearchError, SearchError
from cuckoo.common.config import cfg

from cuckoo.web.decorators import accepts_json

class Search(View):

    @method_decorator(accepts_json)
    def post(self, request):
        if not cfg(
            "web.yaml", "elasticsearch", "web_search", "enabled",
            subpkg="web"
        ):
            return JsonResponse(
                {
                    "error": "Search feature is not available when "
                             "Elasticsearch reporting is disabled."
                }, status=403
            )

        limit = request.json.get("limit", 10)
        offset = request.json.get("offset", 0)
        query = request.json.get("query")
        if not query:
            return JsonResponse({"error": "No query specified"}, status=400)

        try:
            return JsonResponse(search(query, limit=limit, offset=offset))
        except SearchError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except ElasticSearchError as e:
            return JsonResponse({"error": str(e)}, status=500)
