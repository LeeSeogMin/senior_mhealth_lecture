// 애플리케이션 설정
export const config = {
  app: {
    name: "시니어 마음건강 대시보드",
    version: "1.0.0",
    description: "시니어 정신건강 모니터링 시스템",
  },
  features: {
    realTime: process.env.ENABLE_REALTIME === "true",
    analytics: process.env.ENABLE_ANALYTICS === "true",
    notifications: process.env.ENABLE_NOTIFICATIONS !== "false", // 기본값: true
    regionOptimization: process.env.ENABLE_REGION_OPTIMIZATION === "true",
  },
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || "/api",
    timeout: parseInt(process.env.API_TIMEOUT || "10000"),
    retries: parseInt(process.env.API_RETRIES || "3"),
  },
  firebase: {
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  },
  security: {
    rateLimitWindow: parseInt(process.env.RATE_LIMIT_WINDOW || "3600000"), // 1시간
    rateLimitMax: parseInt(process.env.RATE_LIMIT_MAX || "100"),
    jwtSecret: process.env.JWT_SECRET,
    enableCSP: process.env.ENABLE_CSP !== "false", // 기본값: true
  },
};

export default config;
