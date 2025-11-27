"""Multi-AI Ensemble Validator - Claude + GPT-5 합의 검증(Multi-AI ensemble validator - Claude + GPT-5 consensus verification)."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from common_lib.logger import get_logger

logger = get_logger(__name__)


class EnsembleValidator:
    """여러 AI 모델의 응답을 비교하여 일관성 확인(Compare multiple AI model responses for consistency)."""

    @staticmethod
    def compare_responses(
        claude_response: str, gpt_response: str, cve_id: str
    ) -> Tuple[bool, List[str], float]:
        """
        Claude와 GPT-5 응답 비교(Compare Claude and GPT-5 responses).

        Args:
            claude_response: Claude가 생성한 보고서
            gpt_response: GPT-5가 생성한 보고서
            cve_id: CVE 식별자

        Returns:
            (일치 여부, 불일치 목록, 합의 신뢰도)
        """
        discrepancies = []
        confidence = 1.0

        # 1. CVE ID 일치 확인
        claude_has_cve = cve_id.upper() in claude_response.upper()
        gpt_has_cve = cve_id.upper() in gpt_response.upper()

        if claude_has_cve != gpt_has_cve:
            discrepancies.append(
                f"CVE ID presence mismatch: Claude={claude_has_cve}, GPT={gpt_has_cve}"
            )
            confidence -= 0.2

        # 2. 주요 키워드 추출 및 비교
        claude_keywords = EnsembleValidator._extract_key_facts(claude_response)
        gpt_keywords = EnsembleValidator._extract_key_facts(gpt_response)

        # 취약점 유형 비교
        if claude_keywords["vulnerability_type"] and gpt_keywords["vulnerability_type"]:
            if (
                claude_keywords["vulnerability_type"].lower()
                != gpt_keywords["vulnerability_type"].lower()
            ):
                discrepancies.append(
                    f"Vulnerability type disagreement: Claude='{claude_keywords['vulnerability_type']}', GPT='{gpt_keywords['vulnerability_type']}'"
                )
                confidence -= 0.15

        # CVSS 점수 비교
        if claude_keywords["cvss_score"] and gpt_keywords["cvss_score"]:
            try:
                claude_cvss = float(claude_keywords["cvss_score"])
                gpt_cvss = float(gpt_keywords["cvss_score"])

                if abs(claude_cvss - gpt_cvss) > 1.0:
                    discrepancies.append(
                        f"CVSS score disagreement: Claude={claude_cvss:.1f}, GPT={gpt_cvss:.1f}"
                    )
                    confidence -= 0.2
            except ValueError:
                pass

        # 심각도 비교
        if claude_keywords["severity"] and gpt_keywords["severity"]:
            if claude_keywords["severity"].lower() != gpt_keywords["severity"].lower():
                discrepancies.append(
                    f"Severity disagreement: Claude='{claude_keywords['severity']}', GPT='{gpt_keywords['severity']}'"
                )
                confidence -= 0.15

        # 3. 공통 사실 추출 비교
        claude_facts = EnsembleValidator._extract_factual_statements(claude_response)
        gpt_facts = EnsembleValidator._extract_factual_statements(gpt_response)

        # 최소 공통 사실 비율 확인
        if claude_facts and gpt_facts:
            common_facts = set(claude_facts) & set(gpt_facts)
            overlap_ratio = len(common_facts) / min(len(claude_facts), len(gpt_facts))

            if overlap_ratio < 0.3:  # 30% 미만 일치
                discrepancies.append(
                    f"Low factual overlap: only {overlap_ratio:.1%} common statements"
                )
                confidence -= 0.1

        # 로그 기록
        if discrepancies:
            logger.warning(
                f"Ensemble validation found {len(discrepancies)} discrepancies for {cve_id} (Consensus Confidence: {confidence:.2f})"
            )
            for disc in discrepancies:
                logger.warning(f"  - {disc}")
        else:
            logger.info(
                f"✅ Ensemble validation: Claude and GPT-5 responses are consistent for {cve_id} (Confidence: {confidence:.2f})"
            )

        is_consistent = len(discrepancies) == 0
        return is_consistent, discrepancies, max(confidence, 0.0)

    @staticmethod
    def _extract_key_facts(response: str) -> Dict[str, str]:
        """응답에서 주요 사실 추출(Extract key facts from response)."""
        facts = {
            "vulnerability_type": None,
            "cvss_score": None,
            "severity": None,
        }

        # 취약점 유형 추출
        vuln_patterns = [
            r"Vulnerability Type[:\s]+([^\n]+)",
            r"취약점 유형[:\s]+([^\n]+)",
            r"Type[:\s]+(Remote Code Execution|SQL Injection|Cross-Site Scripting|Prototype Pollution|[A-Z][a-zA-Z\s]+)",
        ]
        for pattern in vuln_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                facts["vulnerability_type"] = match.group(1).strip()
                break

        # CVSS 점수 추출
        cvss_patterns = [
            r"CVSS[^\d]*([\d\.]+)",
            r"Base Score[:\s]+([\d\.]+)",
        ]
        for pattern in cvss_patterns:
            match = re.search(pattern, response)
            if match:
                facts["cvss_score"] = match.group(1).strip()
                break

        # 심각도 추출
        severity_patterns = [
            r"Severity[:\s]+(Critical|High|Medium|Low)",
            r"심각도[:\s]+(Critical|High|Medium|Low|긴급|높음|중간|낮음)",
        ]
        for pattern in severity_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                facts["severity"] = match.group(1).strip()
                break

        return facts

    @staticmethod
    def _extract_factual_statements(response: str) -> List[str]:
        """사실 기반 문장 추출(Extract factual statements)."""
        # 간단한 구현: "According to", "Based on", "The CVE description" 등으로 시작하는 문장 추출
        citation_indicators = [
            r"According to[^\.]+\.",
            r"Based on[^\.]+\.",
            r"The CVE description[^\.]+\.",
            r"NVD reports[^\.]+\.",
            r"Threat intelligence[^\.]+\.",
        ]

        facts = []
        for pattern in citation_indicators:
            matches = re.findall(pattern, response, re.IGNORECASE)
            facts.extend(matches)

        return facts

    @staticmethod
    def select_consensus_response(
        claude_response: str,
        gpt_response: str,
        discrepancies: List[str],
        confidence: float,
    ) -> str:
        """
        불일치가 있을 경우 어느 응답을 선택할지 결정(Decide which response to use when there's disagreement).

        Args:
            claude_response: Claude 응답
            gpt_response: GPT-5 응답
            discrepancies: 불일치 목록
            confidence: 합의 신뢰도

        Returns:
            선택된 응답 (또는 merge된 응답)
        """
        if confidence >= 0.8:
            # 높은 일치율: Claude 응답 사용 (기본)
            logger.info("High consensus confidence - using Claude response")
            return claude_response

        if confidence < 0.5:
            # 낮은 일치율: 경고와 함께 Claude 응답 사용
            logger.warning(
                f"Low consensus confidence ({confidence:.2f}) - using Claude response with caution"
            )
            # 불일치 경고를 보고서에 추가
            warning_section = f"\n\n---\n\n**⚠️ AI 모델 불일치 감지 (AI Model Disagreement Detected)**\n\n"
            warning_section += f"이 보고서 생성 중 여러 AI 모델 간 {len(discrepancies)}개의 불일치가 감지되었습니다.\n"
            warning_section += "자세한 내용은 공식 CVE 레코드를 참조하시기 바랍니다.\n\n"
            warning_section += "**불일치 항목**:\n"
            for i, disc in enumerate(discrepancies[:3], 1):  # 최대 3개만 표시
                warning_section += f"{i}. {disc}\n"

            return claude_response + warning_section

        # 중간 일치율: Claude 응답 사용
        logger.info(f"Moderate consensus confidence ({confidence:.2f}) - using Claude response")
        return claude_response
