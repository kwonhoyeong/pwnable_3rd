"""ThreatAgent 프롬프트 템플릿(ThreatAgent prompt templates)."""
from __future__ import annotations

SEARCH_PROMPT_TEMPLATE = """
사용자(User) 요청: npm 패키지 {package} (버전 {version_range})와 관련된 CVE {cve_id}에 대한 최신 공격 사례를 찾아줘.

작성 지침(Writing Guidelines):
⚠️ 중요: 모든 응답은 반드시 '한국어'로 작성되어야 합니다.
- 주 언어: 한국어 (100%)
- 영어 용어: 필요시 한국어 표현 다음 괄호 안에 영어 병기 가능 (예: 원격코드실행(Remote Code Execution, RCE))
- 영어 문장이나 한국어 없는 순수 영문 응답은 절대 금지

검색 지침(Guidance):
- 공식 보안 블로그(Security Blog), GitHub issue, exploit DB 등 신뢰 가능한 출처만 포함
- 각 결과는 제목(Title), 게시일(Date), 요약(Summary), 원문 링크(Source)를 포함
- 모든 필드를 한국어로 작성
"""

SUMMARY_PROMPT_TEMPLATE = """
시스템(System): 다음 자료를 바탕으로 CVE {cve_id}가 npm 패키지 {package}에 미치는 영향을 한국어로 간략히 요약해줘.

작성 지침(Writing Guidelines):
⚠️ 중요: 모든 응답은 반드시 '한국어'로 작성되어야 합니다.
- 주 언어: 한국어 (100%)
- 영어 용어: 필요시 한국어 표현 다음 괄호 안에 영어 병기 가능 (예: 원격코드실행(Remote Code Execution, RCE))
- 영어 문장이나 한국어 없는 순수 영문 응답은 절대 금지

자료(References):
{references}

요약 형식(Output format):
- 제목(Title): 한국어로 CVE의 핵심 내용을 요약
- 공격 기법(Attack Technique): 한국어로 공격 방법 설명
- 영향도(Impact): 한국어로 {package} 패키지에 미치는 영향 설명
- 완화 방안(Mitigation): 한국어로 대응 방안 제시
"""

