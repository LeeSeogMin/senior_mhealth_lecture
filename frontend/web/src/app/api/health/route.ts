// 제10강: Vercel 배포 - Health Check API
import { NextRequest, NextResponse } from 'next/server'
import { config, getDeploymentInfo } from '@/lib/config'

/**
 * Health Check API 엔드포인트
 * Vercel 배포 상태 및 시스템 상태 확인
 */
export async function GET(request: NextRequest) {
  try {
    const deploymentInfo = getDeploymentInfo()
    const timestamp = new Date().toISOString()
    
    // 기본 상태 정보
    const healthStatus = {
      status: 'healthy',
      timestamp,
      environment: deploymentInfo.environment,
      deployment: deploymentInfo,
      config: {
        isDevelopment: config.isDevelopment,
        isProduction: config.isProduction,
        isPreview: config.isPreview,
        features: config.features
      }
    }

    // 운영 환경에서는 민감한 정보 제거
    const response = config.isProduction
      ? { ...healthStatus, config: undefined }
      : healthStatus

    return NextResponse.json(response, {
      status: 200,
      headers: {
        'Cache-Control': 'no-store, must-revalidate',
        'Content-Type': 'application/json'
      }
    })
  } catch (error) {
    console.error('Health check failed:', error)
    
    return NextResponse.json({
      status: 'unhealthy',
      error: 'Health check failed',
      timestamp: new Date().toISOString()
    }, {
      status: 500,
      headers: {
        'Cache-Control': 'no-store, must-revalidate',
        'Content-Type': 'application/json'
      }
    })
  }
}

export const runtime = 'edge'