# AI/ML Training Database

## 📊 BigQuery 데이터 웨어하우스

AI 서비스 전용 데이터베이스로, 학습 데이터 관리 및 모델 성능 추적을 담당합니다.

### 📁 구조
```
schemas/
├── bigquery_schemas.sql      # BigQuery 테이블 및 뷰 정의
└── labeled_data_schema.py    # Python 데이터 클래스
```

### 🎯 용도
- **스마트 레이블링**: 자동/반자동 데이터 레이블링
- **학습 데이터 관리**: 고품질 학습 데이터 축적
- **모델 성능 추적**: 버전별 성능 메트릭
- **임상 검증**: 예측 결과와 실제 진단 비교

### 📊 주요 테이블

#### 1. labeled_data
- 레이블링된 정신건강 데이터
- 음성 특징, 텍스트, 임상 점수 포함
- 일 500+ 샘플 자동 축적

#### 2. quality_metrics
- 데이터 품질 평가 지표
- 신뢰도, 완성도 점수

#### 3. model_performance
- 모델 버전별 성능 추적
- F1 score, AUC-ROC 등

#### 4. clinical_outcomes
- 실제 임상 결과와 예측 비교
- 정확도 검증

### 🔗 의존성
- `backend/functions/labeling_pipeline_trigger.py`가 이 스키마 사용
- ⚠️ **주의**: 파일 경로 변경 시 import 오류 발생

### 🚀 사용 방법

#### BigQuery 테이블 생성
```bash
# BigQuery 콘솔에서 실행
bq query --use_legacy_sql=false < schemas/bigquery_schemas.sql
```

#### Python에서 사용
```python
from labeled_data_schema import LabeledDataDocument

doc = LabeledDataDocument(
    data_id="unique-id",
    label="depression_moderate",
    source="expert",
    confidence=0.92
)
```

### 📈 향후 계획
- Phase 5에서 `/database/bigquery/`로 통합 예정
- Wav2Vec2 + KoBERT 모델 학습 데이터 관리
- 실시간 모델 성능 모니터링 대시보드

---
담당: AI팀
최종 수정: 2024.12.20