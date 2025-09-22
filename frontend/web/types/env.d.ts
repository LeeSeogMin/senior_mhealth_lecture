// 제10강: Vercel 배포 - 환경 변수 타입 정의
declare global {
  namespace NodeJS {
    interface ProcessEnv {
      // Firebase Admin SDK (서버사이드)
      FIREBASE_PROJECT_ID: string
      FIREBASE_CLIENT_EMAIL: string
      FIREBASE_PRIVATE_KEY: string
      
      // Firebase Client SDK (Public - 클라이언트)
      NEXT_PUBLIC_FIREBASE_API_KEY: string
      NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: string
      NEXT_PUBLIC_FIREBASE_PROJECT_ID: string
      NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET: string
      NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID: string
      NEXT_PUBLIC_FIREBASE_APP_ID: string
      NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID?: string
      
      // Vercel 시스템 변수 (자동 제공)
      VERCEL_ENV?: 'production' | 'preview' | 'development'
      VERCEL_URL?: string
      VERCEL_REGION?: string
      VERCEL_GIT_COMMIT_SHA?: string
      VERCEL_GIT_COMMIT_REF?: string
      VERCEL_GIT_REPO_OWNER?: string
      VERCEL_GIT_REPO_SLUG?: string
      
      // 데이터베이스
      DATABASE_URL: string
      REDIS_URL?: string
      
      // 인증 및 보안
      JWT_SECRET: string
      NEXTAUTH_SECRET: string
      NEXTAUTH_URL?: string
      
      // 외부 API 키
      GOOGLE_CLOUD_PROJECT_ID?: string
      GOOGLE_CLOUD_SERVICE_KEY?: string
      OPENAI_API_KEY?: string
      TWILIO_ACCOUNT_SID?: string
      TWILIO_AUTH_TOKEN?: string
      
      // 모니터링 및 분석
      NEXT_PUBLIC_SENTRY_DSN?: string
      SENTRY_AUTH_TOKEN?: string
      NEXT_PUBLIC_GOOGLE_ANALYTICS_ID?: string
      LOGROCKET_APP_ID?: string
      
      // 커스텀 애플리케이션 설정
      NEXT_PUBLIC_APP_URL: string
      NEXT_PUBLIC_API_URL: string
      NEXT_PUBLIC_APP_NAME?: string
      NEXT_PUBLIC_APP_VERSION?: string
      
      // 이메일 서비스
      SMTP_HOST?: string
      SMTP_PORT?: string
      SMTP_USER?: string
      SMTP_PASSWORD?: string
      
      // 파일 저장소
      AWS_ACCESS_KEY_ID?: string
      AWS_SECRET_ACCESS_KEY?: string
      AWS_REGION?: string
      AWS_S3_BUCKET?: string
      
      // 개발 환경
      NODE_ENV: 'development' | 'test' | 'production'
      PORT?: string
      
      // 기능 플래그
      NEXT_PUBLIC_FEATURE_ANALYTICS?: 'true' | 'false'
      NEXT_PUBLIC_FEATURE_DEBUG?: 'true' | 'false'
      NEXT_PUBLIC_FEATURE_VOICE_ANALYSIS?: 'true' | 'false'
      NEXT_PUBLIC_FEATURE_REAL_TIME?: 'true' | 'false'
    }
  }
}

// 환경 변수 검증을 위한 타입
export interface EnvConfig {
  isDevelopment: boolean
  isProduction: boolean
  isPreview: boolean
  isTest: boolean
  
  app: {
    name: string
    version: string
    url: string
    apiUrl: string
  }
  
  firebase: {
    apiKey: string
    authDomain: string
    projectId: string
    storageBucket: string
    messagingSenderId: string
    appId: string
    measurementId?: string
  }
  
  features: {
    analytics: boolean
    debug: boolean
    voiceAnalysis: boolean
    realTime: boolean
  }
  
  security: {
    jwtSecret: string
    nextAuthSecret: string
  }
  
  external: {
    database: string
    redis?: string
  }
  
  monitoring: {
    sentry?: string
    googleAnalytics?: string
    logRocket?: string
  }
}

export {}