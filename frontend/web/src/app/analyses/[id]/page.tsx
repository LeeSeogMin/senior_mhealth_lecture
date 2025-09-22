'use client';

import { useParams } from 'next/navigation';
import { useState, useEffect } from 'react';
import apiClient from '../../../lib/apiClient';
import AnalysisDetail from '../../../components/AnalysisDetail';

export default function AnalysisDetailPage() {
  const params = useParams();
  const [analysis, setAnalysis] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const analysisId = params.id as string;
  
  useEffect(() => {
    const fetchPublicAnalysis = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        console.log('🔍 공개 분석 결과 조회 시작:', analysisId);
        const response = await apiClient.getPublicAnalysis(analysisId);
        
        if (response.success && response.data) {
          console.log('✅ 공개 분석 결과 조회 성공');
          setAnalysis(response.data);
        } else {
          console.error('❌ 공개 분석 결과 조회 실패:', response.error);
          setError(response.error || '분석 결과를 불러올 수 없습니다');
        }
      } catch (err) {
        console.error('❌ 공개 분석 결과 조회 오류:', err);
        setError('분석 결과를 불러오는 중 오류가 발생했습니다');
      } finally {
        setIsLoading(false);
      }
    };

    if (analysisId) {
      fetchPublicAnalysis();
    }
  }, [analysisId]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-red-800">오류가 발생했습니다</h2>
            <p className="text-red-600 mt-2">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-lg p-6 shadow-sm">
            <div className="text-center text-gray-500">
              <div className="text-4xl mb-2">📋</div>
              <p className="text-lg font-medium">분석 결과를 찾을 수 없습니다</p>
              <p className="text-sm">요청하신 분석 ID: {analysisId}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <AnalysisDetail analysis={analysis} />
      </div>
    </div>
  );
} 