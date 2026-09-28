import json
from pathlib import Path


def test_record_build_defines_current_storage_health_report():
    source=(Path(__file__).resolve().parents[1]/"scripts"/"record_build.py").read_text()
    assert "deployment'/'storage-health.json" in source
    assert "PRAGMA integrity_check" in source
    assert "PRAGMA foreign_key_check" in source
    assert "headroom_to_hard_budget_bytes" in source
    assert "all_archive_binaries_retained" in source
    assert "release_archive=release_health()" in source
    assert "'release_archive':release_archive" in source
    assert "historical migration/verification" in source
