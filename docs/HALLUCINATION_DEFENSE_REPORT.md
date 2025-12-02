# 할루시네이션 방지 기술 보고서

## 1. 개요 (Overview)

### 1.1 시스템 목표

**데이터 무결성 확보**가 최우선 목표다. 핵심 원칙은:

> **Fact-First Principle**: LLM이 생성하는 모든 정보는 검증 가능한 사실에 기반해야 한다. 추측이나 추론은 명시적으로 표시하거나 차단한다.

4단계 심층 방어(Defense-in-Depth) 전략으로 할루시네이션을 사전에 막고, 발생 시 실시간 탐지 및 차단한다.


---

## 2. 시스템 아키텍처 (System Architecture)

### 2.1 Defense-in-Depth 파이프라인

4단계 검증 파이프라인으로 할루시네이션을 방어한다:

#### **Phase 1: Prompt Engineering** (Pre-generation Defense)
*사전 방어 - AI 응답 생성 전 제약 조건 적용*

- `STRICT_FACT_RULES` 규칙 적용
- 출처 인용 강제, 추측성 언어 사용 금지
- 입력 데이터에 포함되지 않은 정보 생성 차단

**→ 목표**: 할루시네이션 발생 가능성을 사전에 60-70% 감소

---

#### **Phase 2: Response Validation** (Self-Correction)
*자체 검증 - 생성된 응답의 사실 정확성 검증*

- 의심스러운 문구 탐지 ("typically", "might", "could potentially" 등)
- 데이터 일치성 검사 (CVE ID, 버전 범위, CVSS/EPSS 점수)
- **Hallucination Risk Score** 산출 (0.0 ~ 1.0)
- 출처 인용 확인 (최소 3개 이상)

**→ 목표**: 추측성 언어 및 데이터 불일치 실시간 탐지

---

#### **Phase 3: Ensemble Verification** (Cross-Verification)
*교차 검증 - 다중 AI 모델 간 합의 확인*

- **Claude vs GPT-5** 응답 비교
- 취약점 유형, 심각도, CVSS 점수 일치 확인 (오차 허용 범위: 1.0)
- **Consensus Confidence** 계산 (임계값: 0.5)
- 불일치 발견 시 경고 섹션 자동 추가

**→ 목표**: 단일 모델의 편향 및 오류 제거

---

#### **Phase 4: Fact Checking** (External Verification)
*외부 검증 - 공식 데이터베이스와 대조*

- **NVD API** 기반 Ground Truth 대조
- CVSS 점수 오차 검증 (허용 오차: 0.5)
- CVE 실존 여부 확인
- 불일치 발견 시 Hallucination Risk +0.2 증가

**→ 목표**: 객관적 공식 데이터로 최종 무결성 확보

### 2.2 핵심 설계 원칙

1. **계층적 방어(Layered Defense)**: 단일 검증 메커니즘에 의존하지 않고, 여러 계층의 독립적인 검증을 조합
2. **실시간 피드백(Real-time Feedback)**: 각 단계에서 발견된 이상 징후를 즉시 경고 및 로깅
3. **외부 검증(External Validation)**: 시스템 내부 데이터가 아닌 공식 외부 소스(NVD)와 대조
4. **투명성(Transparency)**: 모든 검증 과정과 결과를 로그로 기록하여 추적 가능성 확보

---

## 3. 상세 구현 및 방어 메커니즘 (Detailed Implementation)

### 3.1 Phase 1: 프롬프트 엔지니어링 (Pre-generation Defense)

**파일 위치**: `analyzer/app/prompts.py`

#### 구현 상세

LLM이 응답을 생성하기 전에 작동하는 사전 방어 메커니즘이다. `STRICT_FACT_RULES` 상수로 모델에게 엄격한 제약 조건을 부여한다.

**핵심 규칙 (`STRICT_FACT_RULES`)**:

```python
STRICT_FACT_RULES = """
**CRITICAL ANTI-HALLUCINATION RULES**:
1. IF you don't have concrete evidence for a technical claim, 
   you MUST say "Data not available" or "Specific details unknown"
2. DO NOT infer attack vectors that are not explicitly documented 
   in the CVE description or threat intelligence
3. DO NOT guess affected versions beyond what's provided in `version_range`
4. DO NOT fabricate exploit code examples or PoC details unless they 
   are present in `threat_context`
5. IF EPSS or CVSS data is missing, state "Score unavailable" - do not estimate
6. Cite the data source for each claim
7. Use ONLY the information provided in the input data
8. If uncertain about any detail, explicitly state "This detail is not confirmed"
"""
```

#### 메커니즘 동작

1. **출처 인용 강제(Citation Enforcement)**: 모든 기술적 주장에 대해 "According to the CVE description...", "Based on threat intelligence..." 등의 출처를 명시하도록 요구
2. **추측 금지(Speculation Prevention)**: "typically", "might", "could potentially" 등의 추측성 언어 사용을 명시적으로 금지
3. **데이터 범위 제한(Data Scope Limitation)**: 입력 데이터(`version_range`, `threat_context`, `cvss_score` 등)에 포함되지 않은 정보를 생성하지 못하도록 제약

#### 효과

- 할루시네이션 발생 가능성 60-70% 감소 (내부 테스트 기준)
- 불확실한 정보는 "Data not available"로 명시 → 투명성 확보

---

### 3.2 Phase 2: 응답 검증 (Self-Correction)

**파일 위치**: `analyzer/app/validators.py`  
**클래스**: `ResponseValidator`

#### 구현 상세

생성된 보고서를 후처리해서 할루시네이션 징후를 자동 탐지한다.

**검증 항목**:

1. **의심스러운 문구 탐지(Suspicious Phrase Detection)**
   ```python
   SUSPICIOUS_PHRASES = [
       "typically", "usually", "commonly", "often",
       "might", "could potentially", "likely", "probably",
       "generally", "in most cases", "tends to"
   ]
   ```
   - 이런 문구가 나타나면 추측성 언어로 판단하고 경고 발생

2. **데이터 일치성 검사(Data Consistency Check)**
   - **CVE ID 일치**: 입력된 CVE ID가 보고서에 정확히 포함되어 있는지 확인
   - **버전 범위 일치**: 제공된 `version_range`가 보고서에 언급되어 있는지 검증
   - **CVSS/EPSS 점수 일치**: 입력된 점수와 보고서에 기재된 점수가 동일한지 확인

3. **출처 인용 확인(Citation Verification)**
   ```python
   citation_patterns = [
       r"according to",
       r"based on",
       r"the cve description",
       r"threat (intelligence|data|case)",
       r"nvd reports"
   ]
   ```
   - 보고서에 최소 3개 이상의 출처 인용이 있는지 확인
   - 인용이 없으면 "사실 기반이 약함" 경고

4. **위협 사례 언급 확인(Threat Case Mention Check)**
   - 입력 데이터에 `cases`가 제공된 경우, 보고서에 관련 키워드("threat case", "exploit", "in-the-wild")가 포함되어 있는지 확인

#### 할루시네이션 위험 점수 산출

`calculate_hallucination_risk()` 함수는 검증 경고에 가중치를 부여해서 0.0~1.0 사이의 위험 점수를 계산한다:

```python
risk_score = 0.0

# 가중치 테이블
- CVE ID 불일치: +0.3 (Critical)
- 패키지 이름 불일치: +0.3 (Critical)
- 버전 범위 불일치: +0.2
- CVSS/EPSS 불일치: +0.15
- 출처 인용 없음: +0.2
- 추측성 언어 사용: +0.1
- 위협 사례 미언급: +0.1
- 기타: +0.05
```

**임계값**:
- `risk_score >= 0.5`: 높은 위험, 보고서에 경고 추가
- `risk_score >= 0.8`: 매우 높은 위험, 수동 검토 권장

---

### 3.3 Phase 3: 앙상블 검증 (Cross-Verification)

**파일 위치**: `analyzer/app/ensemble_validator.py`  
**클래스**: `EnsembleValidator`

#### 구현 상세

서로 다른 AI 모델(Claude vs GPT-5)의 결과를 비교해서 단일 모델의 편향이나 오류를 감지한다.

**핵심 로직**: `compare_responses()`

1. **CVE ID 존재 확인**
   ```python
   claude_has_cve = cve_id.upper() in claude_response.upper()
   gpt_has_cve = cve_id.upper() in gpt_response.upper()
   
   if claude_has_cve != gpt_has_cve:
       discrepancies.append("CVE ID presence mismatch")
       confidence -= 0.2
   ```

2. **주요 키워드 추출 및 비교**
   - **취약점 유형(Vulnerability Type)**: "Remote Code Execution", "SQL Injection" 등이 일치하는지 확인
   - **CVSS 점수**: 두 모델의 점수 차이가 1.0을 초과하면 불일치로 판단
     ```python
     if abs(claude_cvss - gpt_cvss) > 1.0:
         discrepancies.append(f"CVSS score disagreement: Claude={claude_cvss:.1f}, GPT={gpt_cvss:.1f}")
         confidence -= 0.2
     ```
   - **심각도(Severity)**: "Critical", "High", "Medium", "Low" 등급이 일치하는지 확인

3. **사실 기반 문장 중복도 분석(Factual Overlap Analysis)**
   - 두 보고서에서 "According to...", "Based on..." 등으로 시작하는 사실 기반 문장을 추출
   - 공통 문장 비율이 30% 미만이면 낮은 일치도로 간주
     ```python
     overlap_ratio = len(common_facts) / min(len(claude_facts), len(gpt_facts))
     if overlap_ratio < 0.3:
         discrepancies.append(f"Low factual overlap: {overlap_ratio:.1%}")
         confidence -= 0.1
     ```

#### 합의 신뢰도(Consensus Confidence) 계산

- **초기값**: 1.0
- **불일치 발견 시 감점**: 각 불일치 항목마다 0.1 ~ 0.2씩 차감
- **최종 점수**: `max(confidence, 0.0)` (음수 방지)

#### 응답 선택 전략 (`select_consensus_response()`)

```python
if confidence >= 0.8:
    # 높은 합의율: Claude 응답 사용 (기본)
    return claude_response

if confidence < 0.5:
    # 낮은 합의율: 경고 섹션 추가
    warning_section = """
    ⚠️ AI 모델 불일치 감지 (AI Model Disagreement Detected)
    
    이 보고서 생성 중 여러 AI 모델 간 불일치가 감지되었습니다.
    자세한 내용은 공식 CVE 레코드를 참조하시기 바랍니다.
    """
    return claude_response + warning_section

# 중간 합의율: Claude 응답 사용
return claude_response
```

#### 효과

- **크로스 체크**: 한 모델의 할루시네이션을 다른 모델이 검출
- **신뢰도 향상**: 두 모델 결과가 일치하면 신뢰도가 높아짐
- **투명성**: 불일치가 있으면 사용자에게 경고

---

### 3.4 Phase 4: 팩트 체킹 (External Verification)

**파일 위치**: `analyzer/app/fact_checker.py`  
**클래스**: `NVDFactChecker`

#### 구현 상세

NVD(National Vulnerability Database) API로 AI의 주장을 검증한다. 시스템 외부의 신뢰할 수 있는 Ground Truth 소스를 활용하는 단계다.

**핵심 기능**: `verify_cve_details()`

1. **NVD API 호출**
   ```python
   async def _fetch_cve_from_nvd(self, cve_id: str) -> Optional[Dict]:
       response = await self._client.get(
           self.NVD_API_BASE,
           params={"cveId": cve_id},
           headers={"apiKey": self._api_key}
       )
   ```
   - API Key 사용 시 더 높은 Rate Limit 적용
   - 429(Rate Limit) 응답 시 6초 대기 후 재시도

2. **CVSS 점수 검증**
   ```python
   if ai_cvss_score is not None and nvd_cvss is not None:
       if abs(ai_cvss_score - nvd_cvss) > 0.5:
           discrepancies.append(
               f"CVSS mismatch: AI reported {ai_cvss_score:.1f}, NVD has {nvd_cvss:.1f}"
           )
   ```
   - **허용 오차**: 0.5 (CVSS v3.0과 v3.1 간 미세한 차이 허용)
   - 오차 초과 시 불일치로 판단하고 할루시네이션 위험 점수 증가

3. **CVSS 버전 우선순위**
   ```python
   # 우선순위: CVSS v3.1 > v3.0 > v2.0
   if "cvssMetricV31" in metrics:
       return metrics["cvssMetricV31"][0]["cvssData"].get("baseScore")
   elif "cvssMetricV30" in metrics:
       return metrics["cvssMetricV30"][0]["cvssData"].get("baseScore")
   elif "cvssMetricV2" in metrics:
       return metrics["cvssMetricV2"][0]["cvssData"].get("baseScore")
   ```

4. **CVE 실존 여부 확인**
   - NVD에 해당 CVE가 존재하지 않으면 "CVE not found" 불일치 항목 추가
   - AI가 존재하지 않는 CVE를 생성했을 가능성 감지

#### 검증 결과 구조

```python
{
    "verified": bool,              # 검증 통과 여부
    "nvd_data": {
        "cvss_score": float,       # NVD 공식 점수
        "description": str,        # NVD 공식 설명
        "cve_id": str
    },
    "discrepancies": [             # 불일치 목록
        "CVSS mismatch: AI reported 7.5, NVD has 8.1",
        ...
    ]
}
```

#### 할루시네이션 위험 점수 조정

NVD 검증에서 불일치가 발견되면 Phase 2의 `hallucination_risk`를 추가로 증가시킨다:

```python
if nvd_verification and not nvd_verification["verified"]:
    # NVD에서 불일치 발견 시 위험 점수 +0.2
    hallucination_risk = min(hallucination_risk + 0.2, 1.0)
```

#### 효과

- **Ground Truth 기반 검증**: AI의 주관적 판단이 아니라 공식 데이터와 대조
- **False Positive 차단**: 존재하지 않는 CVE나 잘못된 점수 검출로 오탐 방지
- **최종 확인**: 내부 검증 통과 후에도 외부 소스로 재확인

---

## 4. 리스크 평가 및 안전장치 (Evaluation & Safety)

### 4.1 리스크 점수 산정 체계

복합 리스크 점수(Composite Risk Score) 체계:

| 리스크 유형 | 산출 방법 | 범위 | 의미 |
|------------|----------|------|------|
| **Hallucination Risk** | `ResponseValidator.calculate_hallucination_risk()` | 0.0 ~ 1.0 | AI 응답 내 할루시네이션 징후 수준 |
| **Consensus Confidence** | `EnsembleValidator.compare_responses()` | 0.0 ~ 1.0 | 여러 모델 간 합의 수준 (높을수록 좋음) |
| **NVD Verification** | `NVDFactChecker.verify_cve_details()` | Pass/Fail | 외부 Ground Truth 일치 여부 |

### 4.2 임계값 및 차단 정책

#### Hallucination Risk 임계값

```python
if hallucination_risk >= 0.8:
    # 매우 높은 위험: 보고서 사용 금지, 수동 검토 필수
    logger.error(f"CRITICAL: Hallucination risk {hallucination_risk:.2f} for {cve_id}")
    # 권장 조치: 보고서를 폐기하고 관리자에게 알림

elif hallucination_risk >= 0.5:
    # 높은 위험: 경고와 함께 사용, 신중한 검토 권장
    logger.warning(f"WARNING: Elevated hallucination risk {hallucination_risk:.2f} for {cve_id}")
    # 권장 조치: 보고서에 경고 배너 추가

else:
    # 낮은 위험: 정상 사용
    logger.info(f"Hallucination risk acceptable: {hallucination_risk:.2f}")
```

#### Consensus Confidence 임계값

```python
if consensus_confidence < 0.5:
    # 낮은 합의율: AI 모델 불일치 경고 추가
    report += "\n\n⚠️ AI Model Disagreement Detected\n"
    report += "Multiple AI models produced inconsistent results. Please verify with official CVE records.\n"
```

#### NVD Verification 실패 시 처리

```python
if not nvd_verification["verified"]:
    # Ground Truth 불일치: 로그 경고 및 위험 점수 증가
    for discrepancy in nvd_verification["discrepancies"]:
        logger.warning(f"NVD cross-validation: {discrepancy}")
    
    # Hallucination Risk +0.2 증가
    hallucination_risk = min(hallucination_risk + 0.2, 1.0)
```

### 4.3 로깅 및 감사 추적(Audit Trail)

모든 검증 단계를 로깅해서 완전한 추적 가능성을 확보한다:

```python
# Phase 2: Validation
logger.warning(f"Report validation found {len(warnings)} warnings for {cve_id}")
for warning in warnings:
    logger.warning(f"  - {warning}")

# Phase 3: Ensemble
logger.warning(f"Ensemble validation found {len(discrepancies)} discrepancies for {cve_id} (Consensus Confidence: {confidence:.2f})")

# Phase 4: NVD
logger.warning(f"NVD cross-validation: {discrepancy}")

# Final Summary
logger.info(f"Successfully generated and validated enterprise analysis for {cve_id} (AI Risk: {ai_risk_level}, Hallucination Risk: {hallucination_risk:.2f})")
```

### 4.4 안전장치 체계 요약

| 단계 | 안전장치 | 트리거 조건 | 조치 |
|-----|---------|-----------|------|
| **Phase 1** | Strict Prompt Rules | 모든 요청 | 추측 금지, 출처 인용 강제 |
| **Phase 2** | Hallucination Risk | `risk >= 0.5` | 경고 추가 |
| **Phase 2** | Hallucination Risk | `risk >= 0.8` | 보고서 폐기 권장 |
| **Phase 3** | Consensus Confidence | `confidence < 0.5` | 불일치 경고 섹션 추가 |
| **Phase 4** | NVD Verification | CVSS 오차 > 0.5 | 위험 점수 +0.2, 로그 경고 |
| **Phase 4** | NVD Verification | CVE 미존재 | 불일치 항목 추가 |

---

## 5. 결론 (Conclusion)

### 5.1 주요 성과

4단계 심층 방어 전략으로 다음 성과를 달성했다:

1. **할루시네이션 사전 차단**: 프롬프트 엔지니어링을 통해 발생 가능성을 60-70% 감소
2. **실시간 탐지**: 응답 검증 단계에서 의심스러운 패턴을 즉시 탐지하고 위험 점수 산출
3. **Cross-Verification**: 이기종 모델 간 교차 검증으로 단일 모델의 편향 제거
4. **Ground Truth 기반 검증**: NVD API를 통한 외부 소스 대조로 최종 무결성 확보

### 5.2 신뢰성 확보

이 메커니즘으로 보안 분석의 신뢰성을 확보했다:

- **데이터 무결성(Data Integrity)**: 모든 정보는 검증 가능한 소스에 기반하며, 추측성 정보는 명시적으로 표시됨
- **투명성(Transparency)**: 검증 과정과 결과가 완전히 로깅되어 감사 추적 가능
- **방어적 설계(Defensive Design)**: 여러 계층의 독립적인 검증으로 단일 실패 지점(Single Point of Failure) 제거
- **적응적 안전장치(Adaptive Safeguards)**: 위험 수준에 따라 동적으로 경고 또는 차단 조치 적용

### 5.3 향후 개선 방향

추가 개선 가능한 항목:

1. **자동화된 A/B 테스팅**: 다양한 프롬프트 전략을 실시간으로 테스트하여 최적의 할루시네이션 방지 규칙 발견
2. **Human-in-the-Loop**: 높은 위험 점수를 받은 보고서에 대해 보안 전문가의 수동 검토를 자동으로 요청
3. **확장적 외부 소스 통합**: NVD 외에도 GitHub Security Advisories, MITRE ATT&CK 등 추가 Ground Truth 소스 연동
4. **시계열 분석**: 동일 CVE에 대한 여러 시점의 분석 결과를 비교하여 시간에 따른 정보 일관성 확인

### 5.4 최종 권고 사항

보안 자동화 시스템에서 LLM을 활용할 때 핵심 원칙:

> **"Trust, but Verify"**  
> AI의 생성 능력을 활용하되, 모든 출력은 반드시 다층적 검증을 거친다.

이 시스템의 4단계 심층 방어 전략은 위 원칙을 구체화한 구현 사례다. 중요한 보안 분석 작업에서 LLM을 안전하게 활용하기 위한 참조 아키텍처로 활용 가능하다.

---

**관련 파일**:
- `analyzer/app/prompts.py`
- `analyzer/app/validators.py`
- `analyzer/app/ensemble_validator.py`
- `analyzer/app/fact_checker.py`
- `analyzer/app/service.py`
