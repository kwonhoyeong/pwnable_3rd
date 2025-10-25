"""ThreatAgent 프롬프트 템플릿(ThreatAgent prompt templates)."""
from __future__ import annotations

SEARCH_PROMPT_TEMPLATE = """
사용자(User) 요청: npm 패키지 {package} (버전 {version_range})와 관련된 CVE {cve_id}에 대한 최신 공격 사례를 찾아줘.
검색 지침(Guidance):
- 공식 보안 블로그(security blog), GitHub issue, exploit DB 등 신뢰 가능한 출처만 포함.
- 각 결과는 제목(title), 게시일(date), 요약(summary), 원문 링크(source)를 포함.
"""

SUMMARY_PROMPT_TEMPLATE = """
시스템(System): 다음 자료를 바탕으로 CVE {cve_id}가 npm 패키지 {package}에 미치는 영향을 한국어와 영어 키워드를 포함하여 간략히 요약해줘.
자료(References):
{references}
요약 형식(Output format):
- 제목(Title)
- 공격 기법(Attack Technique)
- 영향도(Impact)
- 완화 방안(Mitigation)
"""

