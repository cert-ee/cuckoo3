# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from . import db

class TargetError(Exception):
    pass

class TargetCategories:
    FILE = "file"
    URL = "url"

def update_target_row(analysis, target):
    if analysis.category == TargetCategories.URL:
        row = {
            "target": target.target
        }
    elif analysis.category == TargetCategories.FILE:
        row = {
            "target": target.target,
            "media_type": target.media_type,
            "md5": target.md5,
            "sha1": target.sha1,
            "sha256": target.sha256,
            "sha512": target.sha512
        }
    else:
        raise TargetError(f"No such target category: {analysis.category!r}")

    ses = db.dbms.session()
    try:
        ses.query(db.Target).filter_by(analysis_id=analysis.id).update(row)
        ses.commit()
    finally:
        ses.close()
