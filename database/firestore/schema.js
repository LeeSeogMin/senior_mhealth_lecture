/**
 * Firestore Database Schema - Single Source of Truth Architecture
 * Senior MHealth Project (2025.09.13)
 *
 * 핵심 원칙:
 * 1. 단일 소스 원칙 (Single Source of Truth)
 * 2. 계층적 데이터 구조
 * 3. 세션 중심 데이터 저장
 * 4. 명확한 권한 경계
 */
// Storage 경로 헬퍼
export const StoragePaths = {
    audioFile: (userId, seniorId, sessionId, fileName) => `audio-files/${userId}/${seniorId}/${sessionId}/${fileName}`,
};
// 컬렉션 경로 헬퍼
export const COLLECTION_PATHS = {
    users: 'users',
    userProfile: (userId) => `users/${userId}/profile`,
    seniors: (userId) => `users/${userId}/seniors`,
    seniorProfile: (userId, seniorId) => `users/${userId}/seniors/${seniorId}/profile`,
    sessions: (userId, seniorId) => `users/${userId}/seniors/${seniorId}/sessions`,
    session: (userId, seniorId, sessionId) => `users/${userId}/seniors/${seniorId}/sessions/${sessionId}`,
    settings: (userId) => `users/${userId}/settings`,
    notifications: (userId) => `users/${userId}/settings/notifications`
};
//# sourceMappingURL=schema.js.map