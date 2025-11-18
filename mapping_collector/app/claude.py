"""Claude SDK를 이용한 CVE 분석 모듈 (CVE Analysis using Claude SDK)."""
from __future__ import annotations

from typing import Optional

from anthropic import Anthropic

from common_lib.logger import get_logger

logger = get_logger(__name__)


class ClaudeAnalyzer:
    """Claude를 이용한 CVE 데이터 분석 및 인사이트 제공(CVE analysis and insights using Claude)."""

    def __init__(self, model: str = "claude-sonnet-4-5", max_tokens: int = 1024) -> None:
        """Initialize Claude analyzer.

        Args:
            model: Claude 모델명 (Claude model name)
            max_tokens: 최대 토큰 수 (Maximum tokens for response)
        """
        self.client = Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    async def analyze_cves(self, package: str, cve_ids: list[str], context: Optional[str] = None) -> str:
        """분석할 CVE 목록을 Claude에 전달하여 인사이트 얻기.

        Analyze CVE list using Claude to get insights.

        Args:
            package: 패키지명 (Package name)
            cve_ids: CVE ID 목록 (List of CVE IDs)
            context: 추가 컨텍스트 (Additional context)

        Returns:
            Claude의 분석 결과 (Claude's analysis result)
        """
        try:
            # 프롬프트 구성 (Build prompt)
            prompt = f"""다음 패키지의 보안 취약점을 분석해주세요:

패키지: {package}
CVE 목록: {', '.join(cve_ids)}

각 CVE의 심각성, 영향 범위, 권장 완화 방법을 요약해주세요.
{f"추가 정보: {context}" if context else ""}"""

            # Claude API 호출 (Call Claude API)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.content[0].text
        except Exception as exc:
            logger.error(f"Claude API 호출 실패: {exc}", exc_info=exc)
            raise

    async def get_remediation_steps(self, package: str, version: str, cve_id: str) -> str:
        """특정 CVE에 대한 완화 단계 제공.

        Get remediation steps for a specific CVE.

        Args:
            package: 패키지명 (Package name)
            version: 현재 버전 (Current version)
            cve_id: CVE ID

        Returns:
            완화 단계 (Remediation steps)
        """
        try:
            prompt = f"""패키지 '{package}' 버전 '{version}'에서 '{cve_id}' 취약점을 해결하기 위한 단계별 완화 방법을 제공해주세요.

1. 영향받는 버전 범위
2. 해결된 버전
3. 즉시 완화 조치
4. 장기 완화 계획

을 포함해서 설명해주세요."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.content[0].text
        except Exception as exc:
            logger.error(f"Claude 완화 조치 조회 실패: {exc}", exc_info=exc)
            raise

    def simple_prompt(self, user_message: str) -> str:
        """간단한 프롬프트 처리 (Simple prompt processing).

        Example from user's provided code (사용자가 제시한 코드 예제):

        Args:
            user_message: 사용자 메시지 (User message)

        Returns:
            Claude의 응답 (Claude's response)
        """
        try:
            # 사용자가 제시한 코드의 수정된 버전 (Fixed version of user's provided code)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "user", "content": user_message}
                ]
                # 주의: betas 파라미터는 특정 베타 기능이 필요할 때만 사용
                # Note: betas parameter only needed for specific beta features
            )

            return response.content[0].text
        except Exception as exc:
            logger.error(f"Claude 프롬프트 처리 실패: {exc}", exc_info=exc)
            raise
