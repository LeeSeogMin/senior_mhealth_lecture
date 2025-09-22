-- Migration: Add notifications_log table for HybridDataManager
-- Date: 2025-09-12

USE senior_mhealth;

-- Notifications log table for audit trail
CREATE TABLE IF NOT EXISTS notifications_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    notification_id VARCHAR(128) UNIQUE NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    senior_id VARCHAR(128) NOT NULL,
    type VARCHAR(50) NOT NULL,
    priority ENUM('low', 'normal', 'high', 'critical') DEFAULT 'normal',
    title VARCHAR(255),
    message TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_senior_id (senior_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Update analysis_sessions table to include analysis results
ALTER TABLE analysis_sessions 
ADD COLUMN IF NOT EXISTS emotion_score FLOAT,
ADD COLUMN IF NOT EXISTS stress_level FLOAT,
ADD COLUMN IF NOT EXISTS analysis_results JSON,
ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMP NULL;