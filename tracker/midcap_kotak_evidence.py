"""Bounded diagnostics for already-fetched, rejected Kotak responses."""
from __future__ import annotations

import base64
import hashlib

from . import db

FAMILY = "Kotak Mid Cap Fund"
BODY_LIMIT = 64 * 1024


class KotakSourceRejected(ValueError):
    """Keep exact rejected bytes separate from accepted portfolio evidence."""

    def __init__(self, message, *, source, content, content_type, stage):
        super().__init__(message)
        self.source_evidence = {
            "source": source,
            "source_sha256": hashlib.sha256(content).hexdigest(),
            "source_bytes": len(content),
            "source_content_type": content_type,
            "source_observed_at": db.now(),
            "source_validation_stage": stage,
            "source_body_retained": len(content) <= BODY_LIMIT,
        }
        if len(content) <= BODY_LIMIT:
            self.source_evidence.update({
                "source_body_encoding": "base64",
                "source_body_base64": base64.b64encode(content).decode("ascii"),
            })
        else:
            self.source_evidence["source_body_omitted_reason"] = "exceeds_64_kib_limit"
