# Claude SDK 통합 가이드 (Claude SDK Integration Guide)

## 개요 (Overview)
mapping_collector에 Anthropic Claude SDK를 통합했습니다. 이를 통해 CVE 데이터에 대한 고급 분석 및 인사이트를 얻을 수 있습니다.

## 설치 (Installation)
anthropic SDK는 `requirements.txt`에 추가되어 있습니다:
```bash
pip install -r requirements.txt
```

## 기본 사용법 (Basic Usage)

### 1. 간단한 프롬프트 처리 (Simple Prompt Processing)
사용자가 제시한 코드의 **정정된 버전**:

```python
from mapping_collector.app.claude import ClaudeAnalyzer

# 클라이언트 생성 및 설정
analyzer = ClaudeAnalyzer(
    model="claude-sonnet-4-5",
    max_tokens=1024
)

# 간단한 프롬프트 처리
response = analyzer.simple_prompt(
    user_message="Hello, Claude"
)
print(response)
```

**주요 수정사항:**
- `model="claude-sonnet-4-5"` 뒤에 **쉼표 추가** ✓
- `messages` 구문을 올바르게 수정 (배열로 정의) ✓
- `betas` 파라미터 제거 (특정 베타 기능이 필요할 때만 사용) ✓

### 2. CVE 분석 (CVE Analysis)

```python
from mapping_collector.app.service import MappingService

# 서비스 초기화 (Claude 분석 활성화)
service = MappingService(use_claude_analysis=True)

# CVE 목록 조회
cve_ids = await service.fetch_cves("lodash", "<4.17.21")

# Claude를 사용한 CVE 분석
analysis = await service.analyze_cves_with_claude(
    package="lodash",
    cve_ids=cve_ids,
    context="프로덕션 환경에서 사용 중"
)

print(analysis)
```

### 3. 완화 단계 조회 (Get Remediation Steps)

```python
# 특정 CVE에 대한 완화 단계 조회
remediation = await service.get_remediation_steps(
    package="lodash",
    version="4.17.20",
    cve_id="CVE-2021-23337"
)

print(remediation)
```

## API 설정 (API Configuration)

### 환경 변수 설정 (Environment Setup)
`.env` 파일에서 Anthropic API 키를 설정하세요:
```env
ANTHROPIC_API_KEY=your-api-key-here
```

### MappingService 옵션 (MappingService Options)

```python
# Claude 분석 비활성화
service = MappingService(use_claude_analysis=False)

# 커스텀 모델 사용
analyzer = ClaudeAnalyzer(
    model="claude-opus-4-1",  # 또는 다른 Claude 모델
    max_tokens=2048
)
```

## 코드 구조 (Code Structure)

### claude.py
- `ClaudeAnalyzer` 클래스: Claude SDK를 직접 사용하는 분석 도구
  - `analyze_cves()`: CVE 목록 분석
  - `get_remediation_steps()`: 완화 단계 조회
  - `simple_prompt()`: 일반적인 프롬프트 처리

### service.py (수정사항)
- `MappingService.__init__()`: Claude 분석기 초기화
- `analyze_cves_with_claude()`: CVE 분석을 위한 래퍼 메서드
- `get_remediation_steps()`: 완화 단계를 위한 래퍼 메서드

## 에러 처리 (Error Handling)

모든 Claude API 호출은 예외 처리되어 있습니다:
```python
try:
    analysis = await service.analyze_cves_with_claude(...)
except Exception as exc:
    logger.error(f"Claude 분석 실패: {exc}")
    # Fallback 로직
```

Claude 분석이 비활성화되거나 실패해도 서비스는 정상 동작합니다.

## 사용 예제 (Full Example)

```python
import asyncio
from mapping_collector.app.service import MappingService

async def main():
    # 서비스 초기화
    service = MappingService(use_claude_analysis=True)

    # 1. CVE 조회
    package = "express"
    cve_ids = await service.fetch_cves(package, "<4.18.0")
    print(f"Found CVEs: {cve_ids}")

    # 2. Claude 분석
    if cve_ids:
        analysis = await service.analyze_cves_with_claude(
            package=package,
            cve_ids=cve_ids,
            context="Node.js 웹 프레임워크"
        )
        print("Analysis:")
        print(analysis)

    # 3. 완화 단계
    if cve_ids:
        remediation = await service.get_remediation_steps(
            package=package,
            version="4.17.1",
            cve_id=cve_ids[0]
        )
        print("Remediation Steps:")
        print(remediation)

asyncio.run(main())
```

## 참고사항 (Notes)

- Claude Sonnet 4.5 모델 사용 (다른 모델로 변경 가능)
- API 비용이 발생할 수 있으니 주의하세요
- 성능을 위해 Claude 분석은 선택적으로 활성화 가능
- 모든 로깅은 `common_lib.logger`를 통해 관리됩니다

## 문서 참고

- Anthropic SDK 문서: https://docs.anthropic.com/en/docs/about-claude/models/latest
- 모델 선택 가이드: https://docs.anthropic.com/en/docs/about-claude/models/latest
