# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.views import View
from django.http import FileResponse, HttpResponseNotFound

from cuckoo.common.result import retriever, ResultDoesNotExistError

class Pcap(View):

    def get(self, request, analysis_id, task_id):
        try:
            task = retriever.get_task(analysis_id, task_id)
            pcap_fp = task.pcap
        except ResultDoesNotExistError as e:
            return HttpResponseNotFound(str(e))

        return FileResponse(
            pcap_fp, as_attachment=True, filename=f"{task_id}.pcap"
        )

class Screenshot(View):

    def get(self, request, analysis_id, task_id, screenshot):
        try:
            task = retriever.get_task(analysis_id, task_id)
            screenshot_fp = task.screenshot(screenshot)
        except ResultDoesNotExistError as e:
            return HttpResponseNotFound(str(e))

        return FileResponse(screenshot_fp)
