# WebFrontend 모듈 가이드 (WebFrontend Module Guide)

## 개요(Overview)
- 역할(Role): QueryAPI를 호출하여 CVE/패키지 위험 정보를 시각화하는 React 기반 SPA.
- 빌드 도구(Build tool): Vite + TypeScript.
- 스타일(Styles): SCSS 토큰, 반응형 레이아웃.

## 사전 준비(Prerequisites)
- Node.js 18 이상.
- `.env` (프런트엔드용):
  ```env
  VITE_QUERY_API_BASE_URL=http://127.0.0.1:8004/api/v1
  ```

## 설치 및 실행(Setup & Run)
```bash
cd web_frontend
npm install
npm run dev
```
- 개발 서버: `http://127.0.0.1:5173`

## 기능 테스트(Function testing)
1. 검색창에 패키지명 또는 CVE ID 입력.
2. QueryAPI 응답이 카드 형태로 렌더링되는지 확인.
3. 상세 탭 전환 시 추가 정보 표시 확인.

## 프로덕션 빌드(Production build)
```bash
npm run build
npm run preview
```

## Docker 실행(Docker Run)
```bash
docker build -t web-frontend .
docker run --rm -p 5173:4173 --env-file ../.env web-frontend
```

## 상태 관리(State management)
- `src/store/queryContext.tsx` 의 Context API로 검색 상태/결과를 공유합니다.

