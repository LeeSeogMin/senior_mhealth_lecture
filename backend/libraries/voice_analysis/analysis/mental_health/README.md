# 노인 심리분석 AI 시스템 (Senior Mental Health AI System)

## 📌 개요

한국 노인을 위한 멀티모달 정신건강 분석 시스템입니다. 음성 신호와 대화 내용을 분석하여 우울증, 불면증, 인지기능 저하 등의 정신건강 지표를 조기에 감지합니다.

## 🎯 주요 특징

- **화자 분리**: Google Cloud Speech API를 활용한 자동 화자 분리
- **노인 음성 특화**: 한국 노인의 음성 특성에 최적화된 분석
- **5대 정신건강 지표**: DRI, SDI, CFL, ES, OV 종합 평가
- **3단계 구현**: MVP → Enhanced → Optimized 단계적 개선
- **임상 검증**: PHQ-9, ISI, MMSE 기반 검증 시스템

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                         Audio Input                         │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Speaker Diarization (Google Cloud)             │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Senior Voice Detection                      │
└──────┬───────────────┴───────────────┬──────────────────────┘
       ▼                               ▼
┌──────────────┐              ┌─────────────────┐
│   Librosa    │              │     SincNet     │
│   Features   │              │  (Depression/   │
│              │              │   Insomnia)     │
└──────┬───────┘              └────────┬────────┘
       ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    GPT-4o Multimodal                        │
│                      Analysis                               │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  5 Mental Health Indicators                 │
│         (DRI, SDI, CFL, ES, OV)                            │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Clinical Validation                       │
│              (PHQ-9, ISI, MMSE, K-GDS)                     │
└─────────────────────────────────────────────────────────────┘
```

## 📊 5대 정신건강 지표

### 1. DRI (Depression Risk Index) - 우울 위험 지수
- **범위**: 0.0 ~ 1.0 (0: 정상, 1: 매우 우울)
- **구성요소**: 
  - Librosa 음성 특징 (음조, 에너지)
  - GPT-4o 감정 분석
  - SincNet 우울 예측

### 2. SDI (Sleep Disorder Index) - 수면 장애 지수
- **범위**: 0.0 ~ 1.0 (0: 정상 수면, 1: 심각한 불면)
- **구성요소**:
  - 피로도 음성 패턴
  - GPT-4o 피로 분석
  - SincNet 불면증 예측

### 3. CFL (Cognitive Function Level) - 인지 기능 수준
- **범위**: 0.0 ~ 1.0 (0: 심각한 저하, 1: 정상)
- **구성요소**:
  - 말속도 및 일관성
  - GPT-4o 인지 평가
  - 문장 완성도

### 4. ES (Emotional Stability) - 감정 안정성
- **범위**: 0.0 ~ 1.0 (0: 불안정, 1: 안정)
- **구성요소**:
  - 음성 변동성
  - GPT-4o 감정 안정성
  - 감정 표현 패턴

### 5. OV (Overall Vitality) - 전반적 활력
- **범위**: 0.0 ~ 1.0 (0: 매우 낮음, 1: 활력적)
- **구성요소**:
  - 에너지 레벨
  - 대화 참여도
  - 전반적 건강 지표

## 🚀 설치 및 실행

### 필수 요구사항

```bash
# Python 3.8+ 필요
pip install -r requirements.txt
```

### 환경 변수 설정

```bash
# .env 파일 생성
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=senior-health-audio
OPENAI_API_KEY=your-openai-api-key
```

### 기본 사용법

```python
from ai.analysis.pipeline.main_pipeline import SeniorMentalHealthPipeline

# 파이프라인 초기화 (OPTIMIZED 가중치 고정)
pipeline = SeniorMentalHealthPipeline()

# 분석 실행 (비동기)
import asyncio
result = asyncio.run(pipeline.analyze(
    audio_path="path/to/audio.wav"
))

# 결과 확인
print(f"우울 위험도: {result['indicators']['DRI']['score']:.2f}")
print(f"수면 장애: {result['indicators']['SDI']['score']:.2f}")
print(f"인지 기능: {result['indicators']['CFL']['score']:.2f}")
```

## 🧪 테스트

### 기본 테스트
```bash
python test_pipeline.py --test basic
```

### Phase별 비교 테스트
```bash
python test_pipeline.py --test comparison
```

### 전체 테스트
```bash
python test_pipeline.py --test all
```

## 📁 프로젝트 구조

```
ai/analysis/mental_health/
├── senior_voice_features.py      # Librosa 기반 음성 특징 추출
├── mental_health_indicators.py   # 5대 지표 계산 시스템
├── (파이프라인은 ../pipeline/main_pipeline.py로 통합됨)
├── sincnet_analyzer.py           # SincNet 우울/불면 분석 (Phase 2)
├── api_connectors.py             # Google/OpenAI API 연동 (Phase 2)
├── clinical_validation.py        # 임상 검증 시스템 (Phase 2)
├── korean_elderly_finetuning.py  # 한국 노인 특화 학습 (Phase 2)
├── test_pipeline.py              # 통합 테스트
└── README.md                     # 문서
```

## 🔬 Phase별 구현 상태

### ✅ Phase 1: MVP (완료)
- [x] Librosa 음성 특징 추출
- [x] GPT-4o 감정 분석 (스텁 모드)
- [x] 5대 지표 계산
- [x] 기본 리포트 생성

### ✅ Phase 2: Enhanced (완료)
- [x] SincNet 우울/불면 분석 모델
- [x] Google Cloud Speech API 화자 분리
- [x] GPT-4o 멀티모달 분석
- [x] 임상 데이터 검증 시스템
- [x] 한국 노인 특화 fine-tuning

### 🔄 Phase 3: Optimized (계획)
- [ ] 실시간 스트리밍 분석
- [ ] 웹 인터페이스 구축
- [ ] 의료진 대시보드
- [ ] 장기 추적 시스템

## 📈 성능 지표

### 정확도 목표
- 우울증 검출: 85% 이상
- 불면증 검출: 80% 이상
- 인지기능 평가: 75% 이상

### 처리 시간
- 10분 오디오: < 30초 (MVP)
- 10분 오디오: < 45초 (Enhanced)
- 실시간 처리: 1.5x 재생 속도 (Optimized)

## 🏥 임상 검증

### 지원 척도
- **PHQ-9**: Patient Health Questionnaire-9 (우울증)
- **ISI**: Insomnia Severity Index (불면증)
- **MMSE**: Mini-Mental State Examination (인지기능)
- **K-GDS**: Korean Geriatric Depression Scale (한국 노인 우울)

### 검증 메트릭
- Accuracy, Precision, Recall, F1-Score
- ROC AUC, Sensitivity, Specificity
- Pearson Correlation with Clinical Scores

## 🌏 한국 노인 특화 기능

### 언어적 특성
- 존댓말 사용 패턴 분석
- 간투사 빈도 ("그", "저", "음")
- 방언 특성 고려

### 문화적 특성
- 감정 억제 경향 반영
- 간접 표현 패턴 인식
- 가족 중심 대화 분석

### 음성 특성
- 떨림 보정
- 느린 말속도 최적화
- 명료도 향상 처리

## ⚠️ 주의사항

1. **API 키 보안**: 절대 코드에 직접 입력하지 마세요
2. **개인정보 보호**: 오디오 파일은 분석 후 즉시 삭제
3. **의료 진단 제한**: 본 시스템은 보조 도구이며 의료진의 전문 진단을 대체할 수 없습니다
4. **스텁 모드**: API 미연동 시 자동으로 스텁 모드로 전환

## 📝 라이선스

이 프로젝트는 연구 및 교육 목적으로 개발되었습니다.

## 👥 기여자

- 시스템 설계 및 구현
- 임상 검증 프로토콜
- 한국 노인 특화 최적화

## 📞 문의

기술 문의 및 협업 제안은 프로젝트 이슈 트래커를 통해 문의해주세요.

---

*Last Updated: 2024-01-14*
*Version: 2.0.0 (Phase 2 Enhanced)*