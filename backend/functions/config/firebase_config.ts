/**
 * Firebase 설정 - 비용 최적화 버전
 */

import * as admin from 'firebase-admin';
import { getApps } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { getStorage } from 'firebase-admin/storage';

export class FirebaseConfig {
    private static instance: FirebaseConfig;
    private app: admin.app.App;
    private db: FirebaseFirestore.Firestore;
    private storage: admin.storage.Storage;
    private connectionPool: Map<string, any>;
    
    private constructor() {
        // 연결 풀 초기화
        this.connectionPool = new Map();
        
        // Firebase 초기화
        try {
            if (getApps().length === 0) {
                this.app = admin.initializeApp({
                    credential: admin.credential.applicationDefault(),
                    projectId: process.env.PROJECT_ID || 'test-project',
                    storageBucket: process.env.STORAGE_BUCKET || 'test-bucket'
                });
            } else {
                this.app = getApps()[0];
            }
            
            // Firestore 초기화 (최적화 설정)
            this.db = getFirestore(this.app);
            this.db.settings({
                ignoreUndefinedProperties: true,  // 불필요한 필드 제외
                minimumCapacity: 1,  // 최소 용량
                maxCapacity: 10,  // 최대 용량
                cacheEnabled: true  // 캐싱 활성화
            });
            
            // Storage 초기화
            this.storage = getStorage(this.app);
        } catch (error) {
            console.error('Firebase initialization error:', error);
            throw error;
        }
    }
    
    public static getInstance(): FirebaseConfig {
        if (!FirebaseConfig.instance) {
            FirebaseConfig.instance = new FirebaseConfig();
        }
        return FirebaseConfig.instance;
    }
    
    /**
     * 최적화된 Firestore 연결 가져오기
     */
    public async getOptimizedDb(): Promise<FirebaseFirestore.Firestore> {
        try {
            // 연결 풀에서 가져오기
            const poolKey = 'firestore';
            if (this.connectionPool.has(poolKey)) {
                return this.connectionPool.get(poolKey);
            }
            
            // 새 연결 생성 및 풀에 추가
            const db = getFirestore();
            this.connectionPool.set(poolKey, db);
            
            // 연결 상태 모니터링
            this.monitorConnection(db, poolKey);
            
            return db;
        } catch (error) {
            console.error('Error getting optimized DB:', error);
            throw error;
        }
    }
    
    /**
     * 최적화된 Storage 연결 가져오기
     */
    public async getOptimizedStorage(): Promise<admin.storage.Storage> {
        try {
            // 연결 풀에서 가져오기
            const poolKey = 'storage';
            if (this.connectionPool.has(poolKey)) {
                return this.connectionPool.get(poolKey);
            }
            
            // 새 연결 생성 및 풀에 추가
            const storage = getStorage();
            this.connectionPool.set(poolKey, storage);
            
            return storage;
        } catch (error) {
            console.error('Error getting optimized storage:', error);
            throw error;
        }
    }
    
    /**
     * 오프라인 지원 설정
     */
    public async enableOfflineSupport(): Promise<void> {
        try {
            await this.db.enablePersistence({
                synchronizeTabs: true,  // 탭 간 동기화
                experimentalForceOwningTab: true  // 탭 소유권 강제
            });
            
            // 오프라인 이벤트 처리
            this.db.enableNetwork().catch(error => {
                console.error('Error enabling network:', error);
            });
            
        } catch (error) {
            console.error('Error enabling offline support:', error);
            throw error;
        }
    }
    
    /**
     * 연결 상태 모니터링
     */
    private monitorConnection(
        connection: any,
        poolKey: string
    ): void {
        // 연결 상태 확인
        const connRef = this.db.collection('_status').doc('conn');
        
        this.db.collection('_status')
            .doc('conn')
            .onSnapshot(async (doc) => {
                if (doc.exists && doc.data()?.connected) {
                    console.log(`Connection ${poolKey} is healthy`);
                } else {
                    console.warn(`Connection ${poolKey} is unhealthy`);
                    
                    // 연결 재설정
                    this.connectionPool.delete(poolKey);
                    await this.recreateConnection(poolKey);
                }
            });
    }
    
    /**
     * 연결 재생성
     */
    private async recreateConnection(poolKey: string): Promise<void> {
        try {
            let newConnection;
            
            switch (poolKey) {
                case 'firestore':
                    newConnection = getFirestore();
                    break;
                case 'storage':
                    newConnection = getStorage();
                    break;
                default:
                    throw new Error(`Unknown connection type: ${poolKey}`);
            }
            
            this.connectionPool.set(poolKey, newConnection);
            console.log(`Recreated connection for ${poolKey}`);
            
        } catch (error) {
            console.error(`Error recreating connection for ${poolKey}:`, error);
            throw error;
        }
    }
    
    /**
     * 리소스 정리
     */
    public async cleanup(): Promise<void> {
        try {
            // 연결 풀 정리
            for (const [key, connection] of this.connectionPool.entries()) {
                if (connection.terminate) {
                    await connection.terminate();
                }
                this.connectionPool.delete(key);
            }
            
            // 앱 종료
            if (this.app) {
                await this.app.delete();
            }
            
            console.log('Firebase resources cleaned up');
            
        } catch (error) {
            console.error('Error cleaning up Firebase resources:', error);
            throw error;
        }
    }
}

export const firebaseConfig = FirebaseConfig.getInstance();
