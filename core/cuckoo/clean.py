# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import datetime
import tempfile
import os.path
from pathlib import Path

from cuckoo.common.storage import delete_dirtree, Paths
from cuckoo.common.importing import (
    AnalysisZipper, AnalysisZippingError
)
from cuckoo.common.clients import (
    APIBadRequestError, ClientError, APIResourceConfictError,
    StateControllerClient
)
from cuckoo.common import analyses
from cuckoo.common.log import CuckooGlobalLogger

log = CuckooGlobalLogger(__name__)

class CleanerError(Exception):
    pass


def find_analyses(older_than_days, state):
    match_before = datetime.datetime.now() - datetime.timedelta(
        days=older_than_days
    )

    return analyses.list_analyses(
        state=state, older_than=match_before,
        remote=False
    ), match_before

def find_analyses_hours(older_than_hours, state):
    match_before = datetime.datetime.now() - datetime.timedelta(
        hours=older_than_hours
    )

    return analyses.list_analyses(
        state=state, older_than=match_before,
        remote=False
    ), match_before


class AnalysisRemoteExporter:

    EXPORT_STEP_SIZE = 5

    def __init__(self, analysis_ids, api_client, ignore_task_dirs=[],
                 ignore_task_files=[]):
        self._analysis_ids = analysis_ids
        self._api = api_client
        self._ignore_task_dirs = ignore_task_dirs
        self._ignore_task_files = ignore_task_files

        self._zips = []
        self._tmpdir = tempfile.mkdtemp()

    def start(self):
        log.info("Exporting analyses", count=len(self._analysis_ids))
        while self._analysis_ids:
            exportables = self._analysis_ids[0:self.EXPORT_STEP_SIZE]
            del self._analysis_ids[0:self.EXPORT_STEP_SIZE]

            # No analyses left to export. Quit
            if not exportables:
                return

            delete = []
            for analysis_id in exportables:
                log.debug("Exporting analysis", analysis_id=analysis_id)
                if self._export_analysis(analysis_id):
                    delete.append(analysis_id)

            # Clean temp zips, which are now uploaded.
            self._clean_zips()

            # Notify the remote storage Cuckoo that it can now start with
            # processing the exported analyses.
            try:
                self._api.import_notify()
            except ClientError as e:
                raise CleanerError(
                    f"Failed to notify remote import controller of "
                    f"new imports: {e}"
                )

            # Notify the local Cuckoo state controller that it should
            # mark the location of analysis ids in cwd/storage/export as
            # remote.
            try:
                StateControllerClient.notify_exports(
                    Paths.unix_socket("statecontroller.sock")
                )
            except ClientError as e:
                raise CleanerError(e)

            for analysis_id in delete:
                analyses.delete_analysis_disk(analysis_id)

    def _clean_zips(self):
        for zipped in self._zips:
            zipped.delete()

        self._zips = []

    def _export_analysis(self, analysis_id):
        try:
            zipped_analysis = self._zip_analysis(analysis_id)
        except AnalysisZippingError as e:
            log.warning(
                "Failed to zip analysis. Skipping export",
                analysis_id=analysis_id, error=e
            )
            return False

        self._zips.append(zipped_analysis)
        self._upload_to_remote(zipped_analysis, analysis_id)
        return True

    def _zip_analysis(self, analysis_id):
        zipper = AnalysisZipper(
            analysis_id, ignore_dirs=self._ignore_task_dirs,
            ignore_files=self._ignore_task_files
        )
        zippath = os.path.join(self._tmpdir, f"{analysis_id}.zip")
        return zipper.make_zip(zippath)

    def _upload_to_remote(self, zipped_analysis, analysis_id):
        with zipped_analysis:
            try:
                self._api.import_analysis(zipped_analysis.fp)
                Path(Paths.exported(analysis_id)).touch(exist_ok=True)
            except APIResourceConfictError as e:
                log.warning(
                    "Export already exists on remote host",
                    analysis_id=analysis_id, error=e
                )
            except APIBadRequestError as e:
                log.warning("Export failed", analysis_id=analysis_id, error=e)
            except ClientError as e:
                raise CleanerError(f"Export of {analysis_id} failed. {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        delete_dirtree(self._tmpdir)
