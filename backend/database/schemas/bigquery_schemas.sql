-- BigQuery 테이블 및 뷰 정의
-- 스마트 레이블링 시스템을 위한 데이터 웨어하우스 구조

-- 데이터셋 생성
CREATE SCHEMA IF NOT EXISTS `mental_health_data`
OPTIONS (
    description = "Mental health AI labeling and analysis data",
    location = "US"
);

-- 1. 레이블링된 데이터 테이블
CREATE OR REPLACE TABLE `mental_health_data.labeled_data` (
    -- 기본 식별 정보
    data_id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    
    -- 레이블링 결과
    label STRING NOT NULL,
    source STRING NOT NULL, -- expert, outcome, llm_consensus, pseudo, weak, active
    confidence FLOAT64 NOT NULL,
    validator_id STRING,
    development_only BOOL DEFAULT TRUE,
    
    -- 원시 입력 데이터
    transcription STRING,
    phq9_score INT64,
    gad7_score INT64,
    audio_duration_seconds FLOAT64,
    user_id STRING,
    
    -- JSON 구조화 데이터
    voice_features_json STRING, -- JSON으로 저장된 음성 특징
    behavioral_patterns_json STRING, -- JSON으로 저장된 행동 패턴
    metadata_json STRING, -- 추가 메타데이터
    clinical_outcome_json STRING, -- 임상 결과 (있는 경우)
    
    -- 품질 지표
    is_high_quality BOOL NOT NULL DEFAULT FALSE,
    data_completeness_score FLOAT64 NOT NULL DEFAULT 0.0,
    source_reliability_score FLOAT64 NOT NULL DEFAULT 0.0,
    requires_expert_review BOOL NOT NULL DEFAULT FALSE,
    has_clinical_outcome BOOL NOT NULL DEFAULT FALSE
)
PARTITION BY DATE(timestamp)
CLUSTER BY source, label, is_high_quality
OPTIONS (
    description = "Labeled mental health data from smart labeling system",
    partition_expiration_days = 2555 -- 7년 보존
);

-- 2. 품질 메트릭 테이블
CREATE OR REPLACE TABLE `mental_health_data.quality_metrics` (
    analysis_id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    
    -- 품질 메트릭
    confidence_score FLOAT64,
    source_reliability FLOAT64,
    data_completeness FLOAT64,
    requires_review BOOL,
    review_reason STRING
)
PARTITION BY DATE(timestamp)
CLUSTER BY requires_review, review_reason
OPTIONS (
    description = "Quality metrics for labeling system monitoring"
);

-- 3. 전문가 레이블링 성과 테이블
CREATE OR REPLACE TABLE `mental_health_data.expert_performance` (
    expert_id STRING NOT NULL,
    date DATE NOT NULL,
    
    -- 성과 지표
    labels_completed INT64 DEFAULT 0,
    avg_confidence FLOAT64,
    accuracy_score FLOAT64, -- 임상 결과 대비 정확도
    consistency_score FLOAT64, -- 다른 전문가와의 일치도
    avg_review_time_minutes FLOAT64,
    
    -- 분야별 전문성
    depression_cases INT64 DEFAULT 0,
    anxiety_cases INT64 DEFAULT 0,
    other_cases INT64 DEFAULT 0,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY expert_id
OPTIONS (
    description = "Expert labeler performance tracking"
);

-- 4. 모델 성능 추적 테이블
CREATE OR REPLACE TABLE `mental_health_data.model_performance` (
    model_version STRING NOT NULL,
    evaluation_date DATE NOT NULL,
    
    -- 성능 메트릭
    accuracy FLOAT64,
    precision FLOAT64,
    recall FLOAT64,
    f1_score FLOAT64,
    auc_roc FLOAT64,
    
    -- 레이블별 성능
    depression_f1 FLOAT64,
    anxiety_f1 FLOAT64,
    normal_f1 FLOAT64,
    
    -- 데이터 분할
    train_samples INT64,
    val_samples INT64,
    test_samples INT64,
    
    -- 메타데이터
    training_config STRING, -- JSON 형태의 훈련 설정
    notes STRING,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY evaluation_date
CLUSTER BY model_version
OPTIONS (
    description = "ML model performance tracking over time"
);

-- 5. 임상 결과 추적 테이블
CREATE OR REPLACE TABLE `mental_health_data.clinical_outcomes` (
    patient_id STRING NOT NULL, -- 익명화된 환자 ID
    prediction_date DATE NOT NULL,
    outcome_date DATE,
    
    -- 예측 정보
    predicted_label STRING NOT NULL,
    prediction_confidence FLOAT64,
    prediction_source STRING, -- 예측한 시스템/모델
    
    -- 실제 결과
    actual_diagnosis STRING,
    diagnostic_confidence STRING, -- 진단 확실성
    treatment_response STRING, -- 치료 반응
    follow_up_months INT64,
    
    -- 일치도 분석
    prediction_accuracy BOOL,
    severity_match BOOL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY prediction_date
CLUSTER BY predicted_label, actual_diagnosis
OPTIONS (
    description = "Clinical outcome tracking for prediction validation"
);

-- === 뷰 정의 ===

-- 1. 훈련 데이터 뷰 (고품질 데이터만)
CREATE OR REPLACE VIEW `mental_health_data.training_data_view` AS
SELECT 
    data_id,
    label,
    source,
    confidence,
    transcription,
    phq9_score,
    gad7_score,
    voice_features_json,
    behavioral_patterns_json,
    is_high_quality,
    data_completeness_score,
    source_reliability_score,
    timestamp,
    development_only
FROM `mental_health_data.labeled_data`
WHERE 
    is_high_quality = TRUE
    AND confidence >= 0.8
    AND data_completeness_score >= 0.7
    AND (development_only = FALSE OR development_only IS NULL)
ORDER BY source_reliability_score DESC, confidence DESC;

-- 2. 레이블링 통계 뷰
CREATE OR REPLACE VIEW `mental_health_data.labeling_stats_view` AS
SELECT 
    DATE(timestamp) as date,
    source,
    label,
    COUNT(*) as sample_count,
    AVG(confidence) as avg_confidence,
    COUNT(CASE WHEN is_high_quality THEN 1 END) as high_quality_count,
    COUNT(CASE WHEN requires_expert_review THEN 1 END) as requires_review_count,
    AVG(data_completeness_score) as avg_completeness
FROM `mental_health_data.labeled_data`
WHERE timestamp >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY date, source, label
ORDER BY date DESC, source, label;

-- 3. 품질 트렌드 뷰
CREATE OR REPLACE VIEW `mental_health_data.quality_trend_view` AS
SELECT 
    DATE(timestamp) as date,
    source,
    
    -- 일일 통계
    COUNT(*) as daily_samples,
    AVG(confidence) as avg_confidence,
    AVG(data_completeness_score) as avg_completeness,
    
    -- 품질 비율
    COUNT(CASE WHEN is_high_quality THEN 1 END) / COUNT(*) as high_quality_ratio,
    COUNT(CASE WHEN requires_expert_review THEN 1 END) / COUNT(*) as review_required_ratio,
    
    -- 신뢰도 분포
    COUNT(CASE WHEN confidence >= 0.95 THEN 1 END) as very_high_conf_count,
    COUNT(CASE WHEN confidence >= 0.8 AND confidence < 0.95 THEN 1 END) as high_conf_count,
    COUNT(CASE WHEN confidence < 0.8 THEN 1 END) as low_conf_count
    
FROM `mental_health_data.labeled_data`
WHERE timestamp >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY date, source
ORDER BY date DESC, source;

-- 4. 전문가 작업량 뷰
CREATE OR REPLACE VIEW `mental_health_data.expert_workload_view` AS
SELECT 
    validator_id,
    DATE(timestamp) as work_date,
    COUNT(*) as labels_completed,
    AVG(confidence) as avg_confidence,
    
    -- 레이블 분포
    COUNT(CASE WHEN label LIKE '%depression%' THEN 1 END) as depression_labels,
    COUNT(CASE WHEN label LIKE '%anxiety%' THEN 1 END) as anxiety_labels,
    COUNT(CASE WHEN label = 'normal' THEN 1 END) as normal_labels,
    
    -- 작업 시간 분석 (근사치)
    DATETIME_DIFF(MAX(timestamp), MIN(timestamp), MINUTE) as work_duration_minutes
    
FROM `mental_health_data.labeled_data`
WHERE source = 'expert' AND validator_id IS NOT NULL
AND timestamp >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY validator_id, work_date
ORDER BY work_date DESC, labels_completed DESC;

-- 5. 임상 검증 뷰
CREATE OR REPLACE VIEW `mental_health_data.clinical_validation_view` AS
SELECT 
    co.predicted_label,
    co.actual_diagnosis,
    
    -- 정확도 통계
    COUNT(*) as total_cases,
    COUNT(CASE WHEN co.prediction_accuracy THEN 1 END) as correct_predictions,
    COUNT(CASE WHEN co.prediction_accuracy THEN 1 END) / COUNT(*) as accuracy_rate,
    
    -- 심각도 일치도
    COUNT(CASE WHEN co.severity_match THEN 1 END) as severity_matches,
    COUNT(CASE WHEN co.severity_match THEN 1 END) / COUNT(*) as severity_match_rate,
    
    -- 신뢰도 분석
    AVG(co.prediction_confidence) as avg_prediction_confidence,
    
    -- 후속 조치
    AVG(co.follow_up_months) as avg_follow_up_months,
    
    -- 최근 업데이트
    MAX(co.created_at) as last_updated
    
FROM `mental_health_data.clinical_outcomes` co
WHERE co.outcome_date IS NOT NULL
GROUP BY co.predicted_label, co.actual_diagnosis
HAVING COUNT(*) >= 5 -- 최소 5케이스 이상만
ORDER BY total_cases DESC;

-- 6. 비용 효율성 분석 뷰
CREATE OR REPLACE VIEW `mental_health_data.cost_efficiency_view` AS
WITH monthly_stats AS (
    SELECT 
        EXTRACT(YEAR FROM timestamp) as year,
        EXTRACT(MONTH FROM timestamp) as month,
        source,
        COUNT(*) as samples,
        
        -- 추정 비용 (소스별 단가 적용)
        CASE source
            WHEN 'expert' THEN COUNT(*) * 50.0 -- 전문가: $50/sample
            WHEN 'llm_consensus' THEN COUNT(*) * 2.0 -- LLM: $2/sample
            WHEN 'pseudo' THEN COUNT(*) * 0.1 -- Pseudo: $0.1/sample
            WHEN 'weak' THEN COUNT(*) * 0.01 -- Weak: $0.01/sample
            ELSE COUNT(*) * 0.05
        END as estimated_cost
        
    FROM `mental_health_data.labeled_data`
    WHERE timestamp >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    GROUP BY year, month, source
)
SELECT 
    year,
    month,
    
    -- 총 샘플 및 비용
    SUM(samples) as total_samples,
    SUM(estimated_cost) as total_cost,
    
    -- 소스별 분포
    SUM(CASE WHEN source = 'expert' THEN samples END) as expert_samples,
    SUM(CASE WHEN source = 'llm_consensus' THEN samples END) as llm_samples,
    SUM(CASE WHEN source = 'pseudo' THEN samples END) as pseudo_samples,
    SUM(CASE WHEN source = 'weak' THEN samples END) as weak_samples,
    
    -- 효율성 지표
    SUM(CASE WHEN source = 'expert' THEN samples END) / SUM(samples) as expert_ratio,
    SUM(estimated_cost) / SUM(samples) as cost_per_sample
    
FROM monthly_stats
GROUP BY year, month
ORDER BY year DESC, month DESC;

-- === 인덱스 및 최적화 ===

-- 레이블링 데이터 테이블 최적화
ALTER TABLE `mental_health_data.labeled_data`
SET OPTIONS (
    require_partition_filter = TRUE -- 파티션 필터 강제
);

-- 검색 최적화를 위한 검색 인덱스 생성
CREATE SEARCH INDEX labeled_data_search_idx
ON `mental_health_data.labeled_data`(ALL COLUMNS)
OPTIONS (
    analyzer = 'STANDARD'
);

-- === 권한 및 보안 설정 ===

-- 개발팀 권한 (읽기/쓰기)
GRANT `roles/bigquery.dataEditor` 
ON SCHEMA `mental_health_data` 
TO "group:ml-dev-team@company.com";

-- 분석팀 권한 (읽기 전용)
GRANT `roles/bigquery.dataViewer` 
ON SCHEMA `mental_health_data` 
TO "group:data-analysts@company.com";

-- 의료진 권한 (제한된 뷰만 접근)
CREATE ROW ACCESS POLICY clinical_data_policy
ON `mental_health_data.labeled_data`
GRANT TO ("group:medical-staff@company.com")
FILTER USING (development_only = FALSE AND source IN ('expert', 'outcome'));

-- === 데이터 거버넌스 ===

-- 데이터 분류 라벨 설정
ALTER TABLE `mental_health_data.labeled_data`
SET OPTIONS (
    labels = [
        ("data-classification", "sensitive"),
        ("compliance", "hipaa"),
        ("retention", "7-years")
    ]
);

-- 컬럼 레벨 보안 (민감 정보)
ALTER TABLE `mental_health_data.labeled_data`
ADD COLUMN sensitive_data_hash STRING OPTIONS (description="Hash of sensitive fields");

-- DLP 정책 태그 (개인정보 보호)
ALTER TABLE `mental_health_data.labeled_data`
ALTER COLUMN transcription
SET OPTIONS (
    labels = [("data-classification", "pii")]
);

-- === 모니터링 및 알림 ===

-- 데이터 품질 모니터링 뷰
CREATE OR REPLACE VIEW `mental_health_data.data_quality_alerts` AS
SELECT 
    'low_confidence' as alert_type,
    COUNT(*) as alert_count,
    CURRENT_TIMESTAMP() as check_time
FROM `mental_health_data.labeled_data`
WHERE DATE(timestamp) = CURRENT_DATE()
AND confidence < 0.7
AND source != 'expert'

UNION ALL

SELECT 
    'high_review_rate' as alert_type,
    COUNT(*) as alert_count,
    CURRENT_TIMESTAMP() as check_time
FROM `mental_health_data.labeled_data`
WHERE DATE(timestamp) = CURRENT_DATE()
AND requires_expert_review = TRUE

UNION ALL

SELECT 
    'data_completeness_drop' as alert_type,
    COUNT(*) as alert_count,
    CURRENT_TIMESTAMP() as check_time
FROM `mental_health_data.labeled_data`
WHERE DATE(timestamp) = CURRENT_DATE()
AND data_completeness_score < 0.5;