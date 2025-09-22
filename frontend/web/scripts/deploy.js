#!/usr/bin/env node

// 제10강: Vercel 배포 - 배포 자동화 스크립트
const { execSync, spawn } = require('child_process')
const fs = require('fs')
const path = require('path')

// 배포 설정
const DEPLOY_CONFIG = {
  environments: {
    preview: {
      alias: 'senior-mhealth-preview',
      token: process.env.VERCEL_TOKEN_PREVIEW
    },
    production: {
      alias: 'senior-mhealth',
      token: process.env.VERCEL_TOKEN_PRODUCTION
    }
  },
  
  healthCheck: {
    timeout: 60000, // 60초
    retries: 5,
    interval: 10000 // 10초
  },
  
  notifications: {
    slack: process.env.SLACK_WEBHOOK_URL,
    email: process.env.NOTIFICATION_EMAIL
  }
}

class DeploymentManager {
  constructor() {
    this.startTime = Date.now()
    this.environment = process.argv[2] || 'preview'
    this.config = DEPLOY_CONFIG.environments[this.environment]
    
    if (!this.config) {
      throw new Error(`Unknown environment: ${this.environment}`)
    }
    
    console.log(`🚀 Starting deployment to ${this.environment}`)
  }

  /**
   * 메인 배포 프로세스 실행
   */
  async deploy() {
    try {
      // 1. 사전 검사
      await this.preDeploymentChecks()
      
      // 2. 환경 변수 검증
      await this.validateEnvironmentVariables()
      
      // 3. 빌드 및 테스트
      await this.buildAndTest()
      
      // 4. Vercel 배포
      const deploymentUrl = await this.deployToVercel()
      
      // 5. 배포 검증
      await this.verifyDeployment(deploymentUrl)
      
      // 6. 도메인 설정 (프로덕션)
      if (this.environment === 'production') {
        await this.configureDomain(deploymentUrl)
      }
      
      // 7. 배포 완료 알림
      await this.sendNotification(deploymentUrl, 'success')
      
      const duration = (Date.now() - this.startTime) / 1000
      console.log(`✅ Deployment completed in ${duration}s`)
      console.log(`🌐 URL: ${deploymentUrl}`)
      
    } catch (error) {
      console.error('❌ Deployment failed:', error.message)
      await this.sendNotification(null, 'failure', error)
      process.exit(1)
    }
  }

  /**
   * 사전 검사 실행
   */
  async preDeploymentChecks() {
    console.log('📋 Running pre-deployment checks...')
    
    // Git 상태 확인
    try {
      const gitStatus = execSync('git status --porcelain', { encoding: 'utf8' })
      if (gitStatus.trim() && this.environment === 'production') {
        throw new Error('Working directory not clean. Commit or stash changes before production deployment.')
      }
    } catch (error) {
      console.warn('⚠️  Git status check failed:', error.message)
    }
    
    // package.json 존재 확인
    if (!fs.existsSync('package.json')) {
      throw new Error('package.json not found')
    }
    
    // vercel.json 존재 확인
    if (!fs.existsSync('vercel.json')) {
      throw new Error('vercel.json not found')
    }
    
    // Vercel CLI 설치 확인
    try {
      execSync('vercel --version', { stdio: 'ignore' })
    } catch {
      throw new Error('Vercel CLI not installed. Run: npm i -g vercel')
    }
    
    console.log('✅ Pre-deployment checks passed')
  }

  /**
   * 환경 변수 검증
   */
  async validateEnvironmentVariables() {
    console.log('🔧 Validating environment variables...')
    
    const requiredVars = [
      'NEXT_PUBLIC_FIREBASE_API_KEY',
      'NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN',
      'NEXT_PUBLIC_FIREBASE_PROJECT_ID',
      'JWT_SECRET',
      'NEXTAUTH_SECRET',
      'DATABASE_URL'
    ]
    
    const missing = []
    
    for (const varName of requiredVars) {
      if (!process.env[varName]) {
        missing.push(varName)
      }
    }
    
    if (missing.length > 0) {
      throw new Error(`Missing environment variables: ${missing.join(', ')}`)
    }
    
    console.log('✅ Environment variables validated')
  }

  /**
   * 빌드 및 테스트 실행
   */
  async buildAndTest() {
    console.log('🔨 Building and testing...')
    
    // 의존성 설치
    console.log('📦 Installing dependencies...')
    execSync('npm ci', { stdio: 'inherit' })
    
    // 타입 체크
    console.log('🔍 Type checking...')
    try {
      execSync('npm run type-check', { stdio: 'inherit' })
    } catch (error) {
      console.warn('⚠️  Type check failed, continuing...')
    }
    
    // 린트 검사
    console.log('🧹 Linting...')
    try {
      execSync('npm run lint', { stdio: 'inherit' })
    } catch (error) {
      console.warn('⚠️  Lint check failed, continuing...')
    }
    
    // 단위 테스트 실행
    console.log('🧪 Running tests...')
    try {
      execSync('npm run test:ci', { stdio: 'inherit' })
    } catch (error) {
      console.warn('⚠️  Tests failed, continuing...')
    }
    
    // 프로덕션 빌드
    console.log('🏗️  Building for production...')
    execSync('npm run build', { stdio: 'inherit' })
    
    console.log('✅ Build and test completed')
  }

  /**
   * Vercel 배포 실행
   */
  async deployToVercel() {
    console.log('🌐 Deploying to Vercel...')
    
    const deployArgs = [
      '--yes', // 자동 확인
      '--token', this.config.token || process.env.VERCEL_TOKEN,
    ]
    
    if (this.environment === 'production') {
      deployArgs.push('--prod')
    }
    
    try {
      const output = execSync(`vercel ${deployArgs.join(' ')}`, { 
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'inherit']
      })
      
      // 배포 URL 추출
      const lines = output.split('\n')
      const deploymentUrl = lines.find(line => line.includes('https://'))?.trim()
      
      if (!deploymentUrl) {
        throw new Error('Could not extract deployment URL')
      }
      
      console.log('✅ Vercel deployment completed')
      return deploymentUrl
      
    } catch (error) {
      throw new Error(`Vercel deployment failed: ${error.message}`)
    }
  }

  /**
   * 배포 검증
   */
  async verifyDeployment(url) {
    console.log('🔍 Verifying deployment...')
    
    const { timeout, retries, interval } = DEPLOY_CONFIG.healthCheck
    let attempts = 0
    
    while (attempts < retries) {
      try {
        console.log(`Attempt ${attempts + 1}/${retries}: Checking ${url}/api/health`)
        
        const response = await this.fetch(`${url}/api/health`, { 
          timeout,
          method: 'GET'
        })
        
        if (response.ok) {
          const data = await response.json()
          console.log('✅ Health check passed:', data.status)
          return
        }
        
        throw new Error(`Health check failed: ${response.status}`)
        
      } catch (error) {
        attempts++
        console.warn(`❌ Health check failed (attempt ${attempts}):`, error.message)
        
        if (attempts >= retries) {
          throw new Error(`Deployment verification failed after ${retries} attempts`)
        }
        
        await this.sleep(interval)
      }
    }
  }

  /**
   * 도메인 설정 (프로덕션)
   */
  async configureDomain(deploymentUrl) {
    console.log('🌐 Configuring domain...')
    
    try {
      const alias = this.config.alias
      execSync(`vercel alias ${deploymentUrl} ${alias}`, {
        stdio: 'inherit'
      })
      
      console.log(`✅ Domain configured: https://${alias}.vercel.app`)
      
    } catch (error) {
      console.warn('⚠️  Domain configuration failed:', error.message)
    }
  }

  /**
   * 배포 알림 전송
   */
  async sendNotification(url, status, error = null) {
    const duration = (Date.now() - this.startTime) / 1000
    const message = status === 'success' 
      ? `🎉 Deployment to ${this.environment} succeeded in ${duration}s\n🌐 ${url}`
      : `❌ Deployment to ${this.environment} failed after ${duration}s\n💥 ${error?.message || 'Unknown error'}`
    
    console.log('📢 Sending notifications...')
    
    // Slack 알림
    if (DEPLOY_CONFIG.notifications.slack) {
      try {
        await this.fetch(DEPLOY_CONFIG.notifications.slack, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: message,
            username: 'Deploy Bot',
            icon_emoji: status === 'success' ? ':rocket:' : ':x:'
          })
        })
        console.log('✅ Slack notification sent')
      } catch (error) {
        console.warn('⚠️  Slack notification failed:', error.message)
      }
    }
    
    // 이메일 알림 (구현은 생략)
    if (DEPLOY_CONFIG.notifications.email) {
      console.log('📧 Email notification would be sent to:', DEPLOY_CONFIG.notifications.email)
    }
  }

  /**
   * HTTP 요청 유틸리티
   */
  async fetch(url, options = {}) {
    const { default: fetch } = await import('node-fetch')
    const controller = new AbortController()
    
    if (options.timeout) {
      setTimeout(() => controller.abort(), options.timeout)
    }
    
    return fetch(url, {
      ...options,
      signal: controller.signal
    })
  }

  /**
   * 지연 유틸리티
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

// 스크립트 실행
if (require.main === module) {
  const deployment = new DeploymentManager()
  deployment.deploy().catch(console.error)
}

module.exports = DeploymentManager