// 제10강: Vercel 배포 - 환경 설정 관리
import type { EnvConfig } from '@/types/env'
import { getProjectConfig, getFirebaseConfig, getApiServiceUrl, debugProjectConfig } from './config/project-config'

/**
 * 환경 변수 검증 및 설정 관리
 */
class ConfigManager {
  private _config: EnvConfig | null = null

  get config(): EnvConfig {
    if (!this._config) {
      this._config = this.validateAndCreateConfig()
    }
    return this._config
  }

  private validateAndCreateConfig(): EnvConfig {
    // 필수 환경 변수 검증 (프로덕션에서도 fallback 허용)
    const nodeEnv = process.env.NODE_ENV || 'development'
    const vercelEnv = process.env.VERCEL_ENV
    const isProduction = vercelEnv === 'production' || nodeEnv === 'production'

    // 프로젝트 설정에서 Firebase 기본값 가져오기
    const projectFirebaseConfig = getFirebaseConfig()
    const defaultFirebaseConfig = {
      NEXT_PUBLIC_FIREBASE_API_KEY: projectFirebaseConfig.apiKey || '',
      NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: `${projectFirebaseConfig.projectId}.firebaseapp.com`,
      NEXT_PUBLIC_FIREBASE_PROJECT_ID: projectFirebaseConfig.projectId,
      NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET: projectFirebaseConfig.storageBucket,
      NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID: projectFirebaseConfig.messagingSenderId,
      NEXT_PUBLIC_FIREBASE_APP_ID: projectFirebaseConfig.appId || ''
    }

    const requiredVars = [
      'NEXT_PUBLIC_FIREBASE_API_KEY',
      'NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN',
      'NEXT_PUBLIC_FIREBASE_PROJECT_ID'
    ] as const

    const missing = requiredVars.filter(varName => !process.env[varName])

    if (missing.length > 0) {
      console.warn(`⚠️ Missing environment variables: ${missing.join(', ')}. Using default values.`)
      // 환경 변수가 없으면 기본값 설정
      missing.forEach(varName => {
        const defaultValue = defaultFirebaseConfig[varName as keyof typeof defaultFirebaseConfig]
        if (defaultValue) {
          process.env[varName] = defaultValue
        }
      })
    }

    // 환경 타입 결정 (이미 위에서 정의됨)
    const isDevelopment = nodeEnv === 'development'
    const isPreview = vercelEnv === 'preview'
    const isTest = nodeEnv === 'test'

    // 설정 객체 생성
    const config: EnvConfig = {
      isDevelopment,
      isProduction,
      isPreview,
      isTest,

      app: {
        name: process.env.NEXT_PUBLIC_APP_NAME || 'Senior MHealth Dashboard',
        version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
        url: this.getAppUrl(),
        apiUrl: this.getApiUrl()
      },

      firebase: {
        apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || 'AIzaSyBpaQk82XnXkdZyzrtbgfUSMA70B2s1meA',
        authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || 'senior-mhealth-472007.firebaseapp.com',
        projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || 'senior-mhealth-472007',
        storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || 'senior-mhealth-472007.firebasestorage.app',
        messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '1054806937473',
        appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '1:1054806937473:web:f0a71476f665350937a280',
        measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID
      },

      features: {
        analytics: this.getBooleanEnv('NEXT_PUBLIC_FEATURE_ANALYTICS', isProduction),
        debug: this.getBooleanEnv('NEXT_PUBLIC_FEATURE_DEBUG', !isProduction),
        voiceAnalysis: this.getBooleanEnv('NEXT_PUBLIC_FEATURE_VOICE_ANALYSIS', true),
        realTime: this.getBooleanEnv('NEXT_PUBLIC_FEATURE_REAL_TIME', true)
      },

      security: {
        jwtSecret: process.env.JWT_SECRET || 'dev-jwt-secret',
        nextAuthSecret: process.env.NEXTAUTH_SECRET || 'dev-nextauth-secret'
      },

      external: {
        database: process.env.DATABASE_URL || 'postgresql://localhost:5432/dev',
        redis: process.env.REDIS_URL
      },

      monitoring: {
        sentry: process.env.NEXT_PUBLIC_SENTRY_DSN,
        googleAnalytics: process.env.NEXT_PUBLIC_GOOGLE_ANALYTICS_ID,
        logRocket: process.env.LOGROCKET_APP_ID
      }
    }

    // 개발 환경에서 설정 출력
    if (isDevelopment) {
      console.log('🔧 Config loaded:', {
        environment: vercelEnv || nodeEnv,
        region: process.env.VERCEL_REGION || 'local',
        features: config.features,
        appUrl: config.app.url
      })
      debugProjectConfig()
    }

    return config
  }

  private getAppUrl(): string {
    // Vercel 자동 URL 사용
    if (process.env.VERCEL_URL) {
      return `https://${process.env.VERCEL_URL}`
    }

    // 명시적 URL 설정
    if (process.env.NEXT_PUBLIC_APP_URL) {
      return process.env.NEXT_PUBLIC_APP_URL
    }

    // 개발 환경 기본값
    return 'http://localhost:3000'
  }

  private getApiUrl(): string {
    // 우선순위: NEXT_PUBLIC_API_BASE_URL > NEXT_PUBLIC_API_URL > 프로덕션 기본값
    if (process.env.NEXT_PUBLIC_API_BASE_URL) {
      return process.env.NEXT_PUBLIC_API_BASE_URL
    }
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL
    }
    // 프로덕션 환경에서는 실제 API URL 사용
    const vercelEnv = process.env.VERCEL_ENV
    const nodeEnv = process.env.NODE_ENV
    const isProduction = vercelEnv === 'production' || nodeEnv === 'production'

    if (isProduction) {
      return getApiServiceUrl()
    }

    const baseUrl = this.getAppUrl()
    return `${baseUrl}/api`
  }

  private getBooleanEnv(key: string, defaultValue: boolean): boolean {
    const value = process.env[key]
    if (value === undefined) return defaultValue
    return value === 'true'
  }

  /**
   * 환경별 API 엔드포인트 생성
   */
  getApiEndpoint(path: string): string {
    const apiUrl = this.config.app.apiUrl
    const cleanPath = path.startsWith('/') ? path : `/${path}`
    return `${apiUrl}${cleanPath}`
  }

  /**
   * Vercel 배포 정보 반환
   */
  getDeploymentInfo() {
    return {
      environment: process.env.VERCEL_ENV || process.env.NODE_ENV,
      region: process.env.VERCEL_REGION || 'local',
      commitSha: process.env.VERCEL_GIT_COMMIT_SHA?.substring(0, 7) || 'local',
      commitRef: process.env.VERCEL_GIT_COMMIT_REF || 'local',
      repoOwner: process.env.VERCEL_GIT_REPO_OWNER,
      repoSlug: process.env.VERCEL_GIT_REPO_SLUG,
      url: process.env.VERCEL_URL
    }
  }

  /**
   * 기능 플래그 확인
   */
  isFeatureEnabled(feature: keyof EnvConfig['features']): boolean {
    return this.config.features[feature]
  }

  /**
   * 환경별 조건부 값 반환
   */
  getConditionalValue<T>(values: {
    development?: T
    preview?: T
    production?: T
    default: T
  }): T {
    const { isDevelopment, isPreview, isProduction } = this.config

    if (isDevelopment && values.development !== undefined) {
      return values.development
    }

    if (isPreview && values.preview !== undefined) {
      return values.preview
    }

    if (isProduction && values.production !== undefined) {
      return values.production
    }

    return values.default
  }
}

// 싱글톤 인스턴스 생성
const configManager = new ConfigManager()

// 편의를 위한 내보내기
export const config = Object.assign(configManager.config, {
  isProduction: configManager.config.isProduction,
  isDevelopment: configManager.config.isDevelopment,
  isPreview: configManager.config.isPreview,
  monitoring: configManager.config.monitoring,
  getConditionalValue: configManager.getConditionalValue.bind(configManager)
})

export const getApiEndpoint = configManager.getApiEndpoint.bind(configManager)
export const getDeploymentInfo = configManager.getDeploymentInfo.bind(configManager)
export const isFeatureEnabled = configManager.isFeatureEnabled.bind(configManager)
export const getConditionalValue = configManager.getConditionalValue.bind(configManager)

// 환경별 상수
export const ENV_CONSTANTS = {
  CACHE_TTL: {
    SHORT: getConditionalValue({
      development: 60, // 1분
      preview: 300, // 5분
      production: 3600, // 1시간
      default: 300
    }),
    MEDIUM: getConditionalValue({
      development: 300, // 5분
      preview: 1800, // 30분
      production: 86400, // 24시간
      default: 1800
    }),
    LONG: getConditionalValue({
      development: 3600, // 1시간
      preview: 86400, // 24시간
      production: 604800, // 7일
      default: 86400
    })
  },
  
  API_TIMEOUT: getConditionalValue({
    development: 30000, // 30초
    preview: 20000, // 20초
    production: 10000, // 10초
    default: 15000
  }),
  
  FILE_UPLOAD: {
    MAX_SIZE: getConditionalValue({
      development: 10 * 1024 * 1024, // 10MB
      preview: 5 * 1024 * 1024, // 5MB
      production: 2 * 1024 * 1024, // 2MB
      default: 5 * 1024 * 1024
    }),
    ALLOWED_TYPES: ['audio/wav', 'audio/mp3', 'audio/ogg', 'audio/webm']
  }
} as const

export default configManager