"""통합 파이프라인 오케스트레이터(Integrated pipeline orchestrator)."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Callable, Dict, Iterable, Optional

from dotenv import load_dotenv

from agent_orchestrator import AgentOrchestrator, ProgressCallback
from common_lib.logger import get_logger

# Load .env file at startup
load_dotenv()

logger = get_logger(__name__)


def _default_progress(step: str, message: str) -> None:
    """기본 진행 상황 콜백(Default progress callback)."""

    logger.info("[%s] %s", step, message)


async def run_pipeline(
    package: str,
    version_range: str,
    skip_threat_agent: bool,
    force: bool,
    progress_cb: ProgressCallback = _default_progress,
) -> Dict[str, Any]:
    """전체 파이프라인을 실행하고 결과 반환(Run the full pipeline and return results)."""

    orchestrator = AgentOrchestrator()
    return await orchestrator.orchestrate_pipeline(
        package=package,
        version_range=version_range,
        skip_threat_agent=skip_threat_agent,
        force=force,
        progress_cb=progress_cb,
    )


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    """커맨드라인 인자 파싱(Parse CLI arguments)."""

    parser = argparse.ArgumentParser(description="npm CVE/EPSS 통합 실행기")
    parser.add_argument("--package", required=True, help="대상 패키지명(Target package)")
    parser.add_argument(
        "--version-range",
        default="latest",
        help="분석할 버전 범위(Version range)",
    )
    parser.add_argument(
        "--skip-threat-agent",
        action="store_true",
        help="ThreatAgent 단계를 건너뜀(Skip threat aggregation)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="캐시 무시 후 강제 조회(Force refresh by bypassing cache)",
    )
    return parser.parse_args(argv)


async def main_async(args: argparse.Namespace) -> None:
    """비동기 메인 루틴(Async main routine)."""

    result = await run_pipeline(
        package=args.package,
        version_range=args.version_range,
        skip_threat_agent=args.skip_threat_agent,
        force=args.force,
        progress_cb=_default_progress,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main() -> None:
    """동기 진입점(Synchronous entrypoint)."""

    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
