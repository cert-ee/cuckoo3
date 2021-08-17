# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.http import JsonResponse
from django.views import View

from cuckoo.common.config import cfg
from cuckoo.common.resultstats import chartdata_maker, StatisticsError

class Charts(View):

    def get(self, request):
        if not cfg(
            "web.yaml", "elasticsearch", "statistics", "enabled",
            subpkg="web"
        ):
            return JsonResponse(
                {
                    "error": "Search feature is not available when "
                             "Elasticsearch reporting is disabled."
                }, status=403
            )

        try:
            # Set safe to false, Django does not pass this argument to any
            # decoder. It simply throws an exceptions if safe=True and
            # the serializable object is not a dict.
            return JsonResponse(chartdata_maker.get_data(), safe=False)
        except StatisticsError as e:
            return JsonResponse(
                {"error": f"Failed to load statistics data: {e}"}, status=500
            )
