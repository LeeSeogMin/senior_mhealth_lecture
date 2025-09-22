# Database

Senior_MHealth 프로젝트의 데이터베이스 구성요소들입니다.

## 📁 구조

```
database/
├── firestore/        # Firestore 스키마 및 규칙
├── cloud-sql/        # Cloud SQL 스키마 및 마이그레이션 (Phase 1에서 구현)
└── bigquery/         # BigQuery 데이터 웨어하우스 (Phase 3에서 구현)
```

## 🗄️ 데이터베이스별 역할

### Firestore (NoSQL - Document)
- **용도**: 실시간 운영 데이터
- **데이터**: 사용자 프로필, 세션 데이터, 분석 결과 캐시

### Cloud SQL (PostgreSQL)
- **용도**: 관계형 데이터, 복잡한 쿼리
- **데이터**: 사용자 계정, 돌봄 관계, 조직 관리, 권한 관리

### BigQuery (Data Warehouse)  
- **용도**: 대규모 분석, ML 데이터
- **데이터**: 집계 데이터, 트렌드 분석, 연구 데이터

## 🚀 Phase별 구현 계획

### Phase 1: 기초 인프라 구축
- Cloud SQL 기본 스키마 구현
- Firestore 스키마 최적화

### Phase 2: 백엔드 구축
- 하이브리드 데이터베이스 연동
- 데이터 동기화 메커니즘

### Phase 3: AI/ML 통합
- BigQuery 데이터 파이프라인
- ML 학습 데이터 준비

### Phase 4: 프론트엔드 연결
- 실시간 데이터 동기화
- 캐싱 전략 최적화

### Phase 5: 운영 및 최적화
- 백업 및 복구 시스템
- 성능 튜닝
