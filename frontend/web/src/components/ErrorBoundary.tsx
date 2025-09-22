'use client';

import { Component, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: any) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('❌❌❌ ErrorBoundary caught an error:', error);
    console.error('❌❌❌ Error Info:', errorInfo);
    console.error('❌❌❌ Error Stack:', error.stack);
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
          <div className="text-4xl mb-2">⚠️</div>
          <h3 className="text-lg font-semibold text-red-800 mb-2">오류가 발생했습니다</h3>
          <p className="text-red-600 text-sm">
            이 섹션을 불러오는 중 문제가 발생했습니다. 페이지를 새로고침해주세요.
          </p>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
