#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
exec uv run --frozen python -m tracker "$@"
