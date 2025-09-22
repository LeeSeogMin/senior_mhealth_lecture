/**
 * 프로젝트 설정 로더 (Universal Configuration System)
 * 환경변수 기반 설정 (프론트엔드용)
 */

export interface ProjectConfig {
  project: {
    id: string
    name: string
    region: string
    location: string
  }
  firebase: {
    projectId: string
    storageBucket: string
    messagingSenderId: string
    appId?: string
    apiKey?: string
  }
  services: {
    aiService: {
      name: string
      url: string
    }
    apiService: {
      name: string
      url: string
    }
    webApp?: {
      url: string
    }
  }
  security?: {
    corsOrigins: string[]
    allowedDomains: string[]
  }
}

// 기본 설정 (fallback)
const DEFAULT_CONFIG: ProjectConfig = {
  project: {
    id: 'senior-mhealth-472007',
    name: 'Senior MHealth',
    region: 'asia-northeast3',
    location: 'asia-northeast3'
  },
  firebase: {
    projectId: 'senior-mhealth-472007',
    storageBucket: 'senior-mhealth-472007.firebasestorage.app',
    messagingSenderId: '1054806937473',
    appId: '1:1054806937473:web:f0a71476f665350937a280',
    apiKey: 'AIzaSyBpaQk82XnXkdZyzrtbgfUSMA70B2s1meA'
  },
  services: {
    aiService: {
      name: 'senior-mhealth-ai',
      url: 'https://senior-mhealth-ai-du6z6zbl2a-du.a.run.app'
    },
    apiService: {
      name: 'senior-mhealth-api',
      url: 'https://senior-mhealth-api-1054806937473.asia-northeast3.run.app'
    },
    webApp: {
      url: 'https://senior-mhealth.vercel.app'
    }
  },
  security: {
    corsOrigins: [
      'https://senior-mhealth.vercel.app',
      'http://localhost:3000'
    ],
    allowedDomains: [
      'senior-mhealth-472007.firebaseapp.com',
      'senior-mhealth.vercel.app'
    ]
  }
}

let cachedConfig: ProjectConfig | null = null

// 파일 시스템 접근 제거 - 환경변수만 사용

/**
 * 환경변수로 설정 덮어쓰기
 */
function applyEnvironmentOverrides(config: ProjectConfig): ProjectConfig {
  // 환경변수가 있으면 덮어쓰기
  if (process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID) {
    config.project.id = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID
    config.firebase.projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID
  }

  if (process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET) {
    config.firebase.storageBucket = process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET
  }

  if (process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID) {
    config.firebase.messagingSenderId = process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID
  }

  if (process.env.NEXT_PUBLIC_FIREBASE_APP_ID) {
    config.firebase.appId = process.env.NEXT_PUBLIC_FIREBASE_APP_ID
  }

  if (process.env.NEXT_PUBLIC_FIREBASE_API_KEY) {
    config.firebase.apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY
  }

  if (process.env.NEXT_PUBLIC_API_URL) {
    config.services.apiService.url = process.env.NEXT_PUBLIC_API_URL
  }

  if (process.env.NEXT_PUBLIC_AI_SERVICE_URL) {
    config.services.aiService.url = process.env.NEXT_PUBLIC_AI_SERVICE_URL
  }

  if (process.env.NEXT_PUBLIC_APP_URL) {
    config.services.webApp = config.services.webApp || { url: '' }
    config.services.webApp.url = process.env.NEXT_PUBLIC_APP_URL
  }

  return config
}

/**
 * 설정을 재귀적으로 병합
 */
function mergeConfigs(base: any, override: any): any {
  const result = { ...base }

  for (const key in override) {
    if (override[key] !== null && typeof override[key] === 'object' && !Array.isArray(override[key])) {
      result[key] = mergeConfigs(result[key] || {}, override[key])
    } else {
      result[key] = override[key]
    }
  }

  return result
}

/**
 * 프로젝트 설정 가져오기 (환경변수 기반)
 */
export function getProjectConfig(): ProjectConfig {
  if (cachedConfig) {
    return cachedConfig
  }

  // 기본 설정으로 시작하고 환경변수로 덮어쓰기
  let config = { ...DEFAULT_CONFIG }
  config = applyEnvironmentOverrides(config)

  cachedConfig = config
  return config
}

/**
 * 특정 설정 값 가져오기 함수들
 */
export function getProjectId(): string {
  return getProjectConfig().project.id
}

export function getFirebaseConfig() {
  return getProjectConfig().firebase
}

export function getApiServiceUrl(): string {
  return getProjectConfig().services.apiService.url
}

export function getAiServiceUrl(): string {
  return getProjectConfig().services.aiService.url
}

export function getWebAppUrl(): string {
  return getProjectConfig().services.webApp?.url || 'http://localhost:3000'
}

export function getCorsOrigins(): string[] {
  return getProjectConfig().security?.corsOrigins || []
}

/**
 * 설정 다시 로드 (캐시 초기화)
 */
export function reloadProjectConfig(): ProjectConfig {
  cachedConfig = null
  return getProjectConfig()
}

/**
 * 개발 환경에서 설정 출력
 */
export function debugProjectConfig() {
  if (process.env.NODE_ENV === 'development') {
    console.log('🔧 프로젝트 설정:', {
      projectId: getProjectId(),
      apiUrl: getApiServiceUrl(),
      aiUrl: getAiServiceUrl(),
      webUrl: getWebAppUrl()
    })
  }
}