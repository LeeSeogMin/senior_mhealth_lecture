# BigQuery - 분석 데이터베이스

## 개요
BigQuery는 Senior_MHealth의 분석 데이터베이스로 사용됩니다. 운영 데이터베이스에서 수집된 데이터를 분석하고 ML 모델 훈련 데이터를 제공합니다.

## 구현 예정 (Phase 3)

### 데이터 파이프라인
- **실시간 스트리밍**: 운영 DB → Pub/Sub → BigQuery
- **배치 처리**: Firestore → Cloud Dataflow → BigQuery
- **시계열 데이터**: 음성 지표 추적 및 분석

### 주요 테이블 설계
```sql
-- 사용자 행동 분석
CREATE TABLE user_behavior_analytics (
    user_id STRING,
    session_id STRING,
    action_type STRING,
    timestamp TIMESTAMP,
    metadata STRUCT<
        device_type STRING,
        location STRING,
        duration INT64
    >
);

-- 음성 분석 결과 집계
CREATE TABLE voice_analysis_summary (
    senior_id STRING,
    analysis_date DATE,
    total_sessions INT64,
    avg_confidence FLOAT64,
    risk_level STRING,
    emotional_state STRING
);

-- ML 모델 훈련 데이터
CREATE TABLE ml_training_data (
    session_id STRING,
    audio_features ARRAY<FLOAT64>,
    ground_truth STRING,
    model_version STRING,
    created_at TIMESTAMP
);
```

### 데이터 흐름
1. **운영 데이터베이스** (Firestore/Cloud SQL) → **데이터 파이프라인** → **BigQuery**
2. **실시간 분석**: Pub/Sub을 통한 즉시 데이터 전송
3. **배치 분석**: Cloud Dataflow를 통한 정기적 데이터 전송
4. **ML 모델 훈련**: BigQuery에서 생성된 데이터셋 활용

## 보안 및 규정 준수
- 데이터 암호화 (저장/전송)
- 접근 제어 및 감사 로그
- 개인정보보호법 준수
- HIPAA 준수 (의료 데이터)

## 비용 최적화
- 파티셔닝 전략
- 클러스터링 인덱스
- 예약 쿼리 활용
- 데이터 수명 주기 관리
