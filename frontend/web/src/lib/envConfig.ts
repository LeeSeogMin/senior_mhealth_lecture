/**
 * 환경변수 설정 및 검증
 */

interface EnvConfig {
  firebase: {
    apiKey: string;
    authDomain: string;
    projectId: string;
    storageBucket: string;
    messagingSenderId: string;
    appId: string;
    measurementId?: string;
  };
  api: {
    baseUrl: string;
  };
  features: {
    useMockData: boolean;
  };
}

/**
 * 환경변수 로드 및 검증
 */
export function loadEnvConfig(): EnvConfig {
  const requiredVars = [
    'NEXT_PUBLIC_FIREBASE_API_KEY',
    'NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN',
    'NEXT_PUBLIC_FIREBASE_PROJECT_ID',
    'NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET',
    'NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID',
    'NEXT_PUBLIC_FIREBASE_APP_ID',
    'NEXT_PUBLIC_API_BASE_URL'
  ];

  // 환경변수 확인 - 개발 단계에서는 비활성화
  // if (process.env.NODE_ENV === 'development') {
  //   const missingVars = requiredVars.filter(varName => !process.env[varName]);
  //   if (missingVars.length > 0) {
  //     console.error('Missing required environment variables:', missingVars);
  //     console.warn('Some environment variables are missing. The app may not function correctly.');
  //   }
  // }

  // 프로덕션에서는 경고만 출력하고 계속 진행
  if (process.env.NODE_ENV === 'production' && typeof window !== 'undefined') {
    const missingVars = requiredVars.filter(varName => !process.env[varName]);
    if (missingVars.length > 0) {
      console.warn('Some environment variables are not set:', missingVars);
      console.warn('Using fallback values where available.');
    }
  }

  return {
    firebase: {
      apiKey: (process.env.NEXT_PUBLIC_FIREBASE_API_KEY || 'AIzaSyBpaQk82XnXkdZyzrtbgfUSMA70B2s1meA').trim(),
      authDomain: (process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || 'senior-mhealth-472007.firebaseapp.com').trim(),
      projectId: (process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || 'senior-mhealth-472007').trim(),
      storageBucket: (process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || 'senior-mhealth-472007.firebasestorage.app').trim(),
      messagingSenderId: (process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '1054806937473').trim(),
      appId: (process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '1:1054806937473:web:f0a71476f665350937a280').trim(),
      measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID?.trim(),
    },
    api: {
      baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'https://senior-mhealth-api-1054806937473.asia-northeast3.run.app',
    },
    features: {
      useMockData: process.env.NEXT_PUBLIC_USE_MOCK_DATA === 'true',
    },
  };
}

/**
 * 환경변수 디버그 정보 출력 (개발 환경용)
 */
export function debugEnvConfig(): void {
  if (process.env.NODE_ENV !== 'development') return;

  const config = loadEnvConfig();
  console.log('🔧 Environment Configuration:');
  console.log('Firebase:', {
    projectId: config.firebase.projectId,
    authDomain: config.firebase.authDomain,
    storageBucket: config.firebase.storageBucket,
  });
  console.log('API:', {
    baseUrl: config.api.baseUrl,
  });
  console.log('Features:', {
    useMockData: config.features.useMockData,
  });
}

// 싱글톤 설정 객체
export const envConfig = loadEnvConfig();