"""Bounded validation for ZIP-based office document packages."""
from __future__ import annotations

import io
from pathlib import PurePosixPath
import zipfile

MAX_OOXML_MEMBERS=4096
MAX_OOXML_TOTAL_BYTES=128*1024*1024
MAX_OOXML_MEMBER_BYTES=64*1024*1024


def validate_ooxml_package(
    content: bytes,
    *,
    max_members: int = MAX_OOXML_MEMBERS,
    max_total_bytes: int = MAX_OOXML_TOTAL_BYTES,
    max_member_bytes: int = MAX_OOXML_MEMBER_BYTES,
):
    """Reject malformed or excessively expanded OOXML packages before parsing."""
    if not content.startswith(b"PK"):
        raise ValueError("Office document is not a ZIP-based OOXML package")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos=[info for info in archive.infolist() if not info.is_dir()]
    except zipfile.BadZipFile as exc:
        raise ValueError("Office document is not a valid ZIP package") from exc
    if not infos:
        raise ValueError("Office document ZIP contains no files")
    if len(infos)>max_members:
        raise ValueError("Office document contains too many ZIP members")
    total=0
    for info in infos:
        name=PurePosixPath(info.filename.replace("\\","/"))
        if name.is_absolute() or ".." in name.parts:
            raise ValueError("Office document contains an unsafe ZIP path")
        if info.flag_bits & 0x1:
            raise ValueError("Encrypted Office document ZIP members are unsupported")
        if info.file_size<0 or info.file_size>max_member_bytes:
            raise ValueError("Office document contains an oversized ZIP member")
        total+=info.file_size
        if total>max_total_bytes:
            raise ValueError("Office document expands beyond the allowed size")
    return {"members":len(infos),"uncompressed_bytes":total}
