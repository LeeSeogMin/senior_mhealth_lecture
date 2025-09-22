# Week 5: Firestore 실시간 데이터베이스 - 이론편

## 📚 학습 목표
NoSQL 데이터베이스의 개념을 이해하고, Firestore를 사용하여 실시간 데이터 동기화가 가능한 애플리케이션을 구축하는 방법을 학습합니다.

## 🌟 핵심 개념

### 1. SQL vs NoSQL 데이터베이스
**관계형(SQL) 데이터베이스**:
```
테이블 구조:
┌────┬──────┬─────┬──────┐
│ ID │ Name │ Age │ City │  <- 고정된 스키마
├────┼──────┼─────┼──────┤
│ 1  │ 김철수 │ 75  │ 서울  │
│ 2  │ 이영희 │ 72  │ 부산  │
└────┴──────┴─────┴──────┘
```

**NoSQL(Firestore) 데이터베이스**:
```
문서 구조:
📁 users
  └── 📄 user001 {
        name: "김철수",
        age: 75,
        city: "서울",
        healthData: {        <- 중첩 가능
          heartRate: 72,
          bloodPressure: "120/80"
        }
      }
```

### 2. Firestore 데이터 모델
Firestore는 문서(Document)와 컬렉션(Collection)으로 구성됩니다.

```
🗂️ Firestore 구조
├── 📁 Collection (컬렉션)
│   ├── 📄 Document (문서)
│   │   ├── Field (필드)
│   │   └── 📁 Sub-collection (하위 컬렉션)
│   │       └── 📄 Document
│   └── 📄 Document
```

**실제 예시**:
```javascript
// 경로: users/user001/seniors/senior001/healthData/doc001
{
  seniorId: "senior001",
  date: Timestamp,
  measurements: {
    heartRate: 75,
    bloodPressure: {
      systolic: 120,
      diastolic: 80
    },
    steps: 5000,
    mood: "happy"
  },
  metadata: {
    deviceType: "smartwatch",
    recordedBy: "자동측정"
  }
}
```

### 3. 보안 규칙 (Security Rules)
Firestore 보안 규칙은 데이터 접근을 제어합니다.

```javascript
// 보안 규칙 구조
match /경로/{변수} {
  allow 동작: if 조건;
}

// 실제 예시
match /users/{userId} {
  // 자신의 데이터만 읽기/쓰기 가능
  allow read, write: if request.auth != null && request.auth.uid == userId;
}
```

### 4. 인덱스 (Indexes)
데이터 조회 성능을 향상시키는 데이터 구조

**단일 필드 인덱스**: 자동 생성
```javascript
// date 필드로 정렬
.orderBy('date', 'desc')
```

**복합 인덱스**: 수동 설정 필요
```javascript
// 여러 필드 조합
.where('seniorId', '==', 'senior001')
.orderBy('date', 'desc')
```

## 🔧 주요 기능

### CRUD 작업
| 작업 | 설명 | Firestore 메서드 |
|------|------|-----------------|
| **Create** | 데이터 생성 | `.add()` 또는 `.set()` |
| **Read** | 데이터 조회 | `.get()` 또는 `.onSnapshot()` |
| **Update** | 데이터 수정 | `.update()` |
| **Delete** | 데이터 삭제 | `.delete()` |

### 실시간 동기화
```javascript
// 실시간 리스너
db.collection('healthData')
  .onSnapshot((snapshot) => {
    // 데이터 변경 시 자동 호출
    snapshot.forEach(doc => {
      console.log(doc.data());
    });
  });
```

## 💡 용어 설명

| 용어 | 설명 | 예시 |
|-----|------|------|
| **Collection** | 문서들의 컨테이너 | `users`, `seniors` |
| **Document** | 데이터 단위 | `user001`, `senior001` |
| **Field** | 문서 내 속성 | `name`, `age` |
| **Timestamp** | 시간 데이터 타입 | `2024-01-20T10:30:00Z` |
| **Query** | 데이터 조회문 | `.where().orderBy()` |
| **Snapshot** | 특정 시점의 데이터 | 실시간 리스너 결과 |

## 📊 데이터 구조 설계 패턴

### 1. 정규화 vs 비정규화
```javascript
// 정규화 (참조 사용)
users/user001 → { name: "김철수", seniorRef: "seniors/senior001" }
seniors/senior001 → { name: "김시니어", age: 75 }

// 비정규화 (중복 저장)
users/user001 → {
  name: "김철수",
  senior: {
    id: "senior001",
    name: "김시니어",
    age: 75
  }
}
```

### 2. 계층 구조 설계
```
최적 구조:
users/{userId}/
  └── seniors/{seniorId}/
      ├── healthData/{docId}
      ├── summaries/{date}
      └── alerts/{alertId}

이유:
- 사용자별 데이터 격리
- 효율적인 쿼리
- 보안 규칙 적용 용이
```

## 🎯 학습 체크리스트

- [ ] NoSQL 데이터베이스 특징 이해
- [ ] Collection과 Document 관계 파악
- [ ] 보안 규칙 작성 방법 이해
- [ ] 인덱스의 필요성과 종류 구분
- [ ] 실시간 동기화 원리 이해
- [ ] 데이터 구조 설계 패턴 숙지

## 🔍 심화 개념

### 트랜잭션 (Transactions)
여러 문서를 원자적으로 업데이트

```javascript
await db.runTransaction(async (transaction) => {
  const doc = await transaction.get(docRef);
  const newValue = doc.data().count + 1;
  transaction.update(docRef, { count: newValue });
});
```

### 배치 작업 (Batch Writes)
여러 쓰기 작업을 한 번에 수행

```javascript
const batch = db.batch();
batch.set(doc1, data1);
batch.update(doc2, data2);
batch.delete(doc3);
await batch.commit();
```

### 오프라인 지원
```javascript
// 오프라인 지속성 활성화
firebase.firestore().enablePersistence()
  .then(() => {
    // 오프라인에서도 작동
  });
```

## 🚀 다음 단계
Week 6에서는 Firebase Authentication을 사용하여 사용자 인증 시스템을 구축하고, 역할 기반 접근 제어를 구현합니다.