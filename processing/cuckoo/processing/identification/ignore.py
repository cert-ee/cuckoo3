# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.safelist import FileHash

from ..abtracts import Processor

def _make_ignorefile_entry(filename, filetype, md5, sha1, sha256, reason,
                       description):
    return {
        "category": "file",
        "filename": filename,
        "filetype": filetype,
        "md5": md5,
        "sha1": sha1,
        "sha256": sha256,
        "sha512": sha512,        
        "reason": reason,
        "description": description
    }

class FileSafelist(Processor):

    KEY = "ignored"
    CATEGORY = ["file"]

    @classmethod
    def init_once(cls):
        cls.hash_sl = FileHash()
        cls.hash_sl.load_safelist()

    def _safelist_file(self, f):
        for filehash in (f.sha256, f.sha1, f.md5):
            safelist_entry = self.hash_sl.is_safelisted(filehash)
            if safelist_entry:
                f.safelist(
                    f"Hash {filehash} is safelisted in {safelist_entry.name}. "
                    f"Description: {safelist_entry.description}"
                )
                f.unselectable()

                return _make_ignorefile_entry(
                    f.filename, f.magic, f.md5, f.sha1, f.sha256,
                    "safelisted", safelist_entry.description
                )

    def start(self):
        ignored = []
        selection = self.ctx.result.get("identify", {}).get("selection", [])
        for f in selection[:]:
            ignore = self._safelist_file(f)
            if ignore:
                ignored.append(ignore)
                selection.remove(f)

        return ignored
