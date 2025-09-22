import { initializeApp, getApps } from 'firebase/app';
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut, onAuthStateChanged, User, browserLocalPersistence, setPersistence } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';
import { getStorage } from 'firebase/storage';
import { getAnalytics, isSupported } from 'firebase/analytics';
import { envConfig } from './envConfig';

// 환경변수를 통한 Firebase 설정
const firebaseConfig = envConfig.firebase;

// Firebase 설정 완료
// Firebase configuration loaded

// 전역 app 변수
let app: any = null;

// 앱이 이미 초기화되었는지 확인 후 초기화
export const initializeFirebase = () => {
  try {
    if (getApps().length === 0) {
      // Initialize Firebase app
      app = initializeApp(firebaseConfig);
      return app;
    }
    // Firebase already initialized
    app = getApps()[0];
    return app;
  } catch (error) {
    console.error('Firebase 초기화 오류:', error);
    throw error;
  }
};

// Firebase 앱 초기화 (한 번만 실행)
if (!app) {
  app = initializeFirebase();
}

// 서비스 초기화 (lazy initialization)
let _auth: any = null;
let _db: any = null;
let _storage: any = null;

export const auth = (() => {
  if (!_auth) {
    _auth = getAuth(app);
    // 로컬 저장소 지속성 설정
    if (typeof window !== 'undefined') {
      setPersistence(_auth, browserLocalPersistence).catch((error) => {
        console.error('Auth persistence 설정 실패:', error);
      });
    }
  }
  return _auth;
})();

export const db = (() => {
  if (!_db) {
    _db = getFirestore(app);
  }
  return _db;
})();

export const storage = (() => {
  if (!_storage) {
    _storage = getStorage(app);
  }
  return _storage;
})();

// Analytics는 브라우저에서만 초기화
let analytics = null;
if (typeof window !== 'undefined') {
  isSupported().then((supported) => {
    if (supported) {
      analytics = getAnalytics(app);
    }
  });
}

// 인증 관련 함수들
export const loginWithEmail = (email: string, password: string) => {
  return signInWithEmailAndPassword(auth, email, password);
};

export const registerWithEmail = (email: string, password: string) => {
  return createUserWithEmailAndPassword(auth, email, password);
};

export const logOut = () => {
  return signOut(auth);
};

// 사용자 인증 상태 감시 함수 (초기 상태 보장)
export const watchAuthState = (callback: (user: User | null) => void) => {
  // 먼저 현재 사용자 상태를 즉시 확인
  const currentUser = auth.currentUser;
  if (currentUser !== undefined) {
    callback(currentUser);
  }
  
  // 그 다음 상태 변경 감시
  return onAuthStateChanged(auth, (user) => {
    callback(user);
  });
};

// Auth 준비 상태 확인 함수 - 동기식
export const waitForAuth = (): Promise<User | null> => {
  // 이미 currentUser가 있으면 즉시 반환
  if (auth.currentUser) {
    return Promise.resolve(auth.currentUser);
  }
  
  // authStateReady가 있으면 사용 (Firebase 9.0+)
  if ('authStateReady' in auth) {
    return (auth as any).authStateReady().then(() => auth.currentUser);
  }
  
  // 폴백: onAuthStateChanged 사용
  return new Promise((resolve) => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      unsubscribe();
      resolve(user);
    });
  });
};
