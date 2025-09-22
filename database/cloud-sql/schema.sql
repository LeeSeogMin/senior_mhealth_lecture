-- Senior_MHealth Cloud SQL MySQL 스키마
-- Phase 1: 기초 인프라 구축 - Cloud SQL 기본 스키마

-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS senior_mhealth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE senior_mhealth;

-- 사용자 계정 관리
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uid VARCHAR(128) UNIQUE NOT NULL, -- Firebase UID
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    phone_number VARCHAR(20),
    role ENUM('caregiver', 'senior', 'admin') NOT NULL DEFAULT 'caregiver',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 시니어 정보
CREATE TABLE seniors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    birth_date DATE,
    gender ENUM('male', 'female', 'other'),
    address TEXT,
    emergency_contact VARCHAR(20),
    medical_history TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 보호자-시니어 관계
CREATE TABLE caregiver_senior_relationships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    caregiver_id INT NOT NULL,
    senior_id INT NOT NULL,
    relationship_type VARCHAR(50), -- 자녀, 배우자, 친척 등
    is_primary_caregiver BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_relationship (caregiver_id, senior_id),
    FOREIGN KEY (caregiver_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (senior_id) REFERENCES seniors(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 분석 세션
CREATE TABLE analysis_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    senior_id INT NOT NULL,
    caregiver_id INT NOT NULL,
    session_type ENUM('voice', 'video', 'text') NOT NULL,
    file_path VARCHAR(500),
    file_size BIGINT,
    duration_seconds INT,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    firestore_doc_id VARCHAR(255), -- Firestore 문서 ID 참조
    FOREIGN KEY (senior_id) REFERENCES seniors(id) ON DELETE CASCADE,
    FOREIGN KEY (caregiver_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 분석 결과 (요약)
CREATE TABLE analysis_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    depression_score DECIMAL(3,2), -- 0.00-1.00
    anxiety_score DECIMAL(3,2),
    stress_score DECIMAL(3,2),
    overall_mood ENUM('positive', 'neutral', 'negative'),
    confidence_score DECIMAL(3,2),
    analysis_summary TEXT,
    recommendations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 알림 설정
CREATE TABLE notification_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    notification_type ENUM('email', 'push', 'sms') NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    threshold_score DECIMAL(3,2) DEFAULT 0.7, -- 알림 임계값
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 인덱스 생성
CREATE INDEX idx_users_uid ON users(uid);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_seniors_user_id ON seniors(user_id);
CREATE INDEX idx_relationships_caregiver ON caregiver_senior_relationships(caregiver_id);
CREATE INDEX idx_relationships_senior ON caregiver_senior_relationships(senior_id);
CREATE INDEX idx_sessions_senior ON analysis_sessions(senior_id);
CREATE INDEX idx_sessions_status ON analysis_sessions(status);
CREATE INDEX idx_results_session ON analysis_results(session_id);
CREATE INDEX idx_notifications_user ON notification_settings(user_id);

-- 뷰 생성
CREATE VIEW senior_caregiver_view AS
SELECT 
    s.id as senior_id,
    s.name as senior_name,
    s.birth_date,
    u.id as caregiver_id,
    u.display_name as caregiver_name,
    u.email as caregiver_email,
    csr.relationship_type,
    csr.is_primary_caregiver
FROM seniors s
JOIN caregiver_senior_relationships csr ON s.id = csr.senior_id
JOIN users u ON csr.caregiver_id = u.id;
