#!/usr/bin/env bash
# npm 패키지 위협 평가 파이프라인 실행 스크립트(Run npm threat evaluation pipeline)
set -euo pipefail

usage() {
  cat <<'USAGE'
사용법(Usage):
  bash run_pipeline.sh --package <패키지명(package)> [옵션(options)]

옵션 설명(Option details):
  --version-range <범위(range)>   기본값(default): latest
  --skip-threat-agent             ThreatAgent 단계를 생략(skip)
  --force                         캐시 무시(Force cache bypass)
  --python <python>               기본값(default): python3
  --install-deps                  requirements.txt 의존성 설치(Install dependencies)
  -h, --help                      도움말 표시(Show this help)
USAGE
}

PACKAGE=""
VERSION_RANGE="latest"
SKIP_THREAT=""
FORCE=""
PYTHON_BIN="${PYTHON:-python3}"
INSTALL_DEPS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --package)
      PACKAGE="$2"
      shift 2
      ;;
    --version-range)
      VERSION_RANGE="$2"
      shift 2
      ;;
    --skip-threat-agent)
      SKIP_THREAT="--skip-threat-agent"
      shift 1
      ;;
    --force)
      FORCE="--force"
      shift 1
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --install-deps)
      INSTALL_DEPS=1
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "알 수 없는 옵션(Unknown option): $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$PACKAGE" ]]; then
  echo "--package 옵션은 필수입니다(--package is required)." >&2
  usage
  exit 1
fi

if [[ $INSTALL_DEPS -eq 1 ]]; then
  echo "[INFO] 의존성 설치 중(Installing dependencies)"
  "$PYTHON_BIN" -m pip install --upgrade pip >/dev/null
  "$PYTHON_BIN" -m pip install -r requirements.txt
fi

if [[ ! -f .env ]]; then
  echo "[WARN] .env 파일이 없습니다(.env file is missing). .env.example을 복사하세요." >&2
fi

echo "[INFO] 파이프라인 실행 중(Running pipeline)..."
exec "$PYTHON_BIN" main.py --package "$PACKAGE" --version-range "$VERSION_RANGE" $SKIP_THREAT $FORCE
