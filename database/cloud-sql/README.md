# Cloud SQL MySQL 구현

Senior_MHealth 프로젝트의 Cloud SQL MySQL 데이터베이스 구현입니다.

## 📋 개요

Phase 1에서 구현하는 Cloud SQL MySQL은 다음과 같은 역할을 합니다:
- **관계형 데이터 관리**: 사용자 계정, 시니어 정보, 보호자-시니어 관계
- **복잡한 쿼리 처리**: 조인, 집계, 트랜잭션
- **데이터 무결성**: 외래키, 제약조건, 자동 타임스탬프

## 🗄️ 데이터베이스 스키마

### 핵심 테이블

#### 1. users (사용자 계정)
```sql
- id: 기본키 (AUTO_INCREMENT)
- uid: Firebase UID (고유)
- email: 이메일 (고유)
- display_name: 표시명
- phone_number: 전화번호
- role: 역할 (ENUM: caregiver, senior, admin)
- created_at, updated_at: 타임스탬프 (자동 업데이트)
- is_active: 활성 상태
```

#### 2. seniors (시니어 정보)
```sql
- id: 기본키 (AUTO_INCREMENT)
- user_id: users 테이블 참조 (외래키)
- name: 이름
- birth_date: 생년월일
- gender: 성별 (ENUM: male, female, other)
- address: 주소
- emergency_contact: 비상연락처
- medical_history: 병력
```

#### 3. caregiver_senior_relationships (보호자-시니어 관계)
```sql
- id: 기본키 (AUTO_INCREMENT)
- caregiver_id: 보호자 ID (users 참조)
- senior_id: 시니어 ID (seniors 참조)
- relationship_type: 관계 유형 (자녀, 배우자 등)
- is_primary_caregiver: 주보호자 여부
- UNIQUE KEY: (caregiver_id, senior_id)
```

#### 4. analysis_sessions (분석 세션)
```sql
- id: 기본키 (AUTO_INCREMENT)
- senior_id: 시니어 ID
- caregiver_id: 보호자 ID
- session_type: 세션 유형 (ENUM: voice, video, text)
- file_path: 파일 경로
- status: 상태 (ENUM: pending, processing, completed, failed)
- firestore_doc_id: Firestore 문서 ID 참조
```

#### 5. analysis_results (분석 결과)
```sql
- id: 기본키 (AUTO_INCREMENT)
- session_id: 분석 세션 ID
- depression_score: 우울증 점수 (0.00-1.00)
- anxiety_score: 불안 점수
- stress_score: 스트레스 점수
- overall_mood: 전반적 기분 (ENUM: positive, neutral, negative)
- confidence_score: 신뢰도
- analysis_summary: 분석 요약
- recommendations: 권장사항
```

## 🔗 하이브리드 데이터베이스 아키텍처

### Cloud SQL (MySQL)
- **용도**: 관계형 데이터, 복잡한 쿼리
- **데이터**: 사용자 계정, 시니어 정보, 관계 관리
- **특징**: ACID 트랜잭션, 외래키 제약조건, 자동 타임스탬프

### Firestore (NoSQL)
- **용도**: 실시간 데이터, 세션 데이터
- **데이터**: 분석 세션, 실시간 상태, 캐시
- **특징**: 실시간 동기화, 자동 스케일링

### 데이터 동기화
- `analysis_sessions.firestore_doc_id`: Firestore 문서 참조
- 양방향 데이터 동기화 메커니즘
- 일관성 보장을 위한 트랜잭션 처리

## 🚀 Phase별 구현 계획

### Phase 1: 기초 인프라 구축 ✅
- [x] 기본 스키마 설계 및 구현 (MySQL)
- [x] 연결 설정 및 모델 클래스 (mysql2)
- [x] 기본 CRUD 작업

### Phase 2: 백엔드 구축
- [ ] API 엔드포인트 구현
- [ ] 데이터 검증 및 보안
- [ ] 캐싱 전략

### Phase 3: AI/ML 통합
- [ ] 분석 결과 저장 최적화
- [ ] 성능 모니터링
- [ ] 데이터 파이프라인 연동

### Phase 4: 프론트엔드 연결
- [ ] 실시간 데이터 동기화
- [ ] 오프라인 지원
- [ ] 데이터 마이그레이션

### Phase 5: 운영 및 최적화
- [ ] 백업 및 복구
- [ ] 성능 튜닝
- [ ] 모니터링 및 알림

## 📁 파일 구조

```
database/cloud-sql/
├── schema.sql              # MySQL 데이터베이스 스키마
├── connection.ts           # MySQL 연결 설정 (mysql2)
├── package.json           # 의존성 관리
├── models/                 # 데이터 모델
│   ├── User.ts            # 사용자 모델 (MySQL)
│   ├── Senior.ts          # 시니어 모델 (MySQL)
│   └── Analysis.ts        # 분석 모델 (Phase 2)
├── migrations/             # 마이그레이션 스크립트
├── seeds/                  # 초기 데이터
└── README.md              # 이 문서
```

## 🔧 설정 및 배포

### 의존성 설치
```bash
cd database/cloud-sql
npm install
```

### 환경변수
```bash
DB_HOST=your-cloud-sql-host
DB_PORT=3306
DB_NAME=senior_mhealth
DB_USER=root
DB_PASSWORD=your-password
DB_SSL=true
```

### 로컬 개발
```bash
# MySQL 설치 후
mysql -u root -p < schema.sql
```

### Cloud SQL 배포
```bash
# GCP Cloud SQL MySQL 인스턴스 생성 후
gcloud sql connect your-instance --user=root
source schema.sql
```

## 📊 성능 최적화

### 인덱스
- `users(uid)`: Firebase UID 조회 최적화
- `users(email)`: 이메일 조회 최적화
- `analysis_sessions(senior_id, status)`: 시니어별 분석 조회
- `analysis_results(session_id)`: 분석 결과 조회

### 뷰
- `senior_caregiver_view`: 보호자-시니어 관계 조회 최적화

### MySQL 특화 기능
- **자동 타임스탬프**: `ON UPDATE CURRENT_TIMESTAMP`
- **ENUM 타입**: 데이터 무결성 보장
- **InnoDB 엔진**: 트랜잭션 지원
- **UTF8MB4**: 이모지 및 특수문자 지원

## 🔒 보안 고려사항

1. **연결 보안**: SSL/TLS 암호화
2. **인증**: Firebase UID 기반 사용자 인증
3. **권한 관리**: 역할 기반 접근 제어 (RBAC)
4. **데이터 암호화**: 민감 정보 암호화
5. **SQL 인젝션 방지**: 파라미터화된 쿼리 사용 (mysql2)

## 📈 모니터링

### 주요 지표
- 연결 풀 상태
- 쿼리 성능
- 트랜잭션 처리량
- 오류율

### 로깅
- 연결 이벤트
- 쿼리 실행 시간
- 오류 및 예외

## 🆚 PostgreSQL vs MySQL 비교

### MySQL 선택 이유
- **성능**: 읽기 중심 워크로드에 최적화
- **호환성**: 더 넓은 호스팅 서비스 지원
- **단순성**: 설정 및 관리가 상대적으로 간단
- **비용**: 일반적으로 더 저렴한 호스팅 옵션

### 주요 차이점
- **타임스탬프**: MySQL은 `ON UPDATE CURRENT_TIMESTAMP` 자동 지원
- **ENUM**: MySQL의 ENUM 타입으로 데이터 무결성 강화
- **파라미터**: `$1, $2` → `?, ?` (mysql2)
- **트랜잭션**: `ON CONFLICT` → `ON DUPLICATE KEY UPDATE`

이 Cloud SQL MySQL 구현을 통해 Senior_MHealth 시스템의 핵심 데이터를 안전하고 효율적으로 관리할 수 있습니다.
