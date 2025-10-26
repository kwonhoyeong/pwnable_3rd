#!/usr/bin/env bash
# 간단 데모 실행 스크립트(Simple demo runner)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REQUEST_FILE="${SCRIPT_DIR}/sample_request.json"

PACKAGE="$(python3 - "${REQUEST_FILE}" <<'PY'
import json
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
request = json.loads(path.read_text(encoding="utf-8"))
print(request.get("package", "lodash"))
PY
)"

VERSION_RANGE="$(python3 - "${REQUEST_FILE}" <<'PY'
import json
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
request = json.loads(path.read_text(encoding="utf-8"))
print(request.get("version_range", "latest"))
PY
)"

python3 "${PROJECT_ROOT}/main.py" --package "${PACKAGE}" --version-range "${VERSION_RANGE}" "$@"
