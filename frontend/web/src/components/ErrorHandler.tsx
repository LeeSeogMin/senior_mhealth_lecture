'use client';

import { useState } from 'react';

interface ErrorHandlerProps {
  error: string | Error;
  onRetry?: () => void;
  onBack?: () => void;
  type?: 'network' | 'server' | 'auth' | 'data' | 'unknown';
  className?: string;
}

export default function ErrorHandler({
  error,
  onRetry,
  onBack,
  type = 'unknown',
  className = ''
}: ErrorHandlerProps) {
  const [isRetrying, setIsRetrying] = useState(false);

  const handleRetry = async () => {
    if (onRetry) {
      setIsRetrying(true);
      try {
        await onRetry();
      } finally {
        setIsRetrying(false);
      }
    }
  };

  const getErrorConfig = () => {
    switch (type) {
      case 'network':
        return {
          icon: '🌐',
          title: '네트워크 연결 오류',
          message: '인터넷 연결을 확인하고 다시 시도해주세요.',
          solutions: [
            '인터넷 연결 상태를 확인하세요',
            'Wi-Fi 또는 모바일 데이터를 확인하세요',
            '잠시 후 다시 시도해주세요'
          ]
        };

      case 'server':
        return {
          icon: '🔧',
          title: '서버 오류',
          message: '서버에서 일시적인 문제가 발생했습니다.',
          solutions: [
            '잠시 후 다시 시도해주세요',
            '서버 상태를 확인해주세요',
            '관리자에게 문의해주세요'
          ]
        };

      case 'auth':
        return {
          icon: '🔐',
          title: '인증 오류',
          message: '로그인이 필요하거나 인증 정보가 잘못되었습니다.',
          solutions: [
            '다시 로그인해주세요',
            '인증 정보를 확인해주세요',
            '브라우저 캐시를 삭제해주세요'
          ]
        };

      case 'data':
        return {
          icon: '📊',
          title: '데이터 오류',
          message: '데이터를 불러오는 중 문제가 발생했습니다.',
          solutions: [
            '페이지를 새로고침해주세요',
            '다시 시도해주세요',
            '관리자에게 문의해주세요'
          ]
        };

      default:
        return {
          icon: '⚠️',
          title: '오류가 발생했습니다',
          message: '예상치 못한 오류가 발생했습니다.',
          solutions: [
            '페이지를 새로고침해주세요',
            '다시 시도해주세요',
            '문제가 지속되면 관리자에게 문의해주세요'
          ]
        };
    }
  };

  const errorConfig = getErrorConfig();
  const errorMessage = typeof error === 'string' ? error : error.message;

  return (
    <div className={`bg-white rounded-lg p-6 shadow-sm border border-red-200 ${className}`}>
      <div className="text-center">
        {/* 아이콘 */}
        <div className="text-6xl mb-4">{errorConfig.icon}</div>
        
        {/* 제목 */}
        <h3 className="text-xl font-semibold text-gray-900 mb-2">
          {errorConfig.title}
        </h3>
        
        {/* 메시지 */}
        <p className="text-gray-600 mb-6">
          {errorConfig.message}
        </p>

        {/* 상세 에러 메시지 (개발 모드에서만 표시) */}
        {process.env.NODE_ENV === 'development' && errorMessage && (
          <div className="mb-6 p-4 bg-red-50 rounded-lg">
            <p className="text-sm font-medium text-red-800 mb-2">상세 오류 정보:</p>
            <p className="text-sm text-red-700 font-mono break-all">
              {errorMessage}
            </p>
          </div>
        )}

        {/* 해결 방법 */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-700 mb-3">해결 방법:</h4>
          <ul className="space-y-2 text-sm text-gray-600">
            {errorConfig.solutions.map((solution, index) => (
              <li key={index} className="flex items-start space-x-2">
                <span className="text-blue-500 mt-1">•</span>
                <span>{solution}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* 액션 버튼들 */}
        <div className="flex justify-center space-x-4">
          {onRetry && (
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {isRetrying ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>재시도 중...</span>
                </>
              ) : (
                <>
                  <span>🔄</span>
                  <span>다시 시도</span>
                </>
              )}
            </button>
          )}

          {onBack && (
            <button
              onClick={onBack}
              className="px-6 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
            >
              ← 돌아가기
            </button>
          )}

          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
          >
            🔄 새로고침
          </button>
        </div>
      </div>
    </div>
  );
}

// 간단한 에러 메시지 컴포넌트
export function SimpleErrorMessage({ 
  message, 
  onRetry, 
  className = '' 
}: { 
  message: string; 
  onRetry?: () => void; 
  className?: string; 
}) {
  return (
    <div className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-center space-x-3">
        <div className="text-red-500">⚠️</div>
        <div className="flex-1">
          <p className="text-sm text-red-800">{message}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-sm text-red-600 hover:text-red-800 underline"
          >
            재시도
          </button>
        )}
      </div>
    </div>
  );
}

// 데이터 없음 컴포넌트
export function EmptyState({ 
  title, 
  message, 
  icon = '📭',
  action,
  className = '' 
}: { 
  title: string; 
  message: string; 
  icon?: string; 
  action?: React.ReactNode; 
  className?: string; 
}) {
  return (
    <div className={`bg-white rounded-lg p-6 shadow-sm text-center ${className}`}>
      <div className="text-6xl mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600 mb-4">{message}</p>
      {action && (
        <div className="mt-4">
          {action}
        </div>
      )}
    </div>
  );
} 