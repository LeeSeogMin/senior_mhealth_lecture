# Backend

Senior_MHealth 프로젝트의 백엔드 서비스들입니다.

## 📁 구조

```
backend/
├── functions/        # Cloud Functions (기존 backend/api/ 마이그레이션)
├── run/              # Cloud Run 서비스 (Python/FastAPI)
├── api-gateway/      # Cloud Endpoints API Gateway (Phase 2에서 구현)
└── graphql/          # GraphQL Server (Apollo) (Phase 2에서 구현)
```

## 🚀 Phase별 구현 계획

### Phase 1: 기초 인프라 구축
- 기존 backend/api/ 코드를 functions/로 마이그레이션
- Cloud SQL 연동 기본 구현

### Phase 2: 백엔드 구축
- API Gateway 구현 (api-gateway/)
- GraphQL 서버 구현 (graphql/)
- 마이크로서비스 아키텍처 완성

### Phase 3: AI/ML 통합
- Vertex AI 연동
- ML 파이프라인 구현

### Phase 4: 프론트엔드 연결
- API 최적화
- 실시간 통신 구현

### Phase 5: 운영 및 최적화
- 성능 모니터링
- 자동 스케일링
