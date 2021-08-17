# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import json

from django.http import JsonResponse

MAX_JSON_SIZE = 10 * 1024 * 1024

def accepts_json(view_func):

    def _wrapper(request, *args, **kwargs):
        if request.content_type.lower() != "application/json":
            return JsonResponse({
                    "error": "The only accepted content type is "
                             "'application/json'"
                }, status=400)
        if not request.body:
            return JsonResponse({
                "error": "No valid JSON body provided"
            }, status=400)
        elif len(request.body) > MAX_JSON_SIZE:
            return JsonResponse({
                "error": f"Maximum body size is {MAX_JSON_SIZE}"
            }, status=413)

        try:
            request.json = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                "error": "Invalid JSON provided"
            }, status=400)

        return view_func(request, *args, **kwargs)

    return _wrapper
