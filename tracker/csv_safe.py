"""Safe CSV export helpers for spreadsheet-facing downloads."""
from __future__ import annotations

DANGEROUS_PREFIXES=("=","+","-","@","\t","\r","\n")


def safe_cell(value):
    """Neutralize spreadsheet formula prefixes without changing numeric cells."""
    if not isinstance(value,str) or not value:
        return value
    probe=value.lstrip(" ")
    if probe.startswith(DANGEROUS_PREFIXES):
        return "'"+value
    return value


def safe_record(record):
    return {key:safe_cell(value) for key,value in record.items()}
