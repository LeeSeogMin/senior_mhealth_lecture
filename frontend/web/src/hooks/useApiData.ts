'use client';

import { useState, useEffect, useCallback } from 'react';
import apiClient, { Senior, Call, Analysis, ApiResponse } from '../lib/apiClient';
import { getAuth, onAuthStateChanged } from 'firebase/auth';

// 대시보드 통계 타입
export interface DashboardStats {
  totalSeniors: number;
  normalStatus: number;
  warningStatus: number;
  criticalStatus: number;
}

// 분석 결과를 위한 확장 타입
export interface EnhancedAnalysis extends Omit<Analysis, 'recordedAt'> {
  seniorName?: string;
  recordedAt?: Date | string; // Allow both Date and string
}

export const useApiData = () => {
  const [seniors, setSeniors] = useState<Senior[]>([]);
  const [calls, setCalls] = useState<Call[]>([]);
  const [analyses, setAnalyses] = useState<EnhancedAnalysis[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // 인증 상태 확인
  useEffect(() => {
    const auth = getAuth();

    // 먼저 현재 사용자 확인
    const currentUser = auth.currentUser;
    if (currentUser) {
      console.log('초기 사용자 확인됨:', currentUser.email);
      setIsAuthenticated(true);
      // 바로 데이터 가져오기
      fetchDataWithAuth();
    }

    // 상태 변경 감시
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      console.log('인증 상태 변경:', user ? '로그인됨' : '로그아웃됨');
      console.log('사용자 정보:', user ? { uid: user.uid, email: user.email } : '없음');
      setIsAuthenticated(!!user);
      console.log('isAuthenticated 설정:', !!user);

      if (user) {
        console.log('사용자 인증됨 - 즉시 데이터 가져오기 시작');
        fetchDataWithAuth();
      } else {
        console.log('사용자 인증 안됨 - 데이터 초기화');
        setSeniors([]);
        setCalls([]);
        setAnalyses([]);
        setStats(null);
        setIsLoading(false);
      }
    });

    return () => unsubscribe();
  }, []);

  // 대시보드 통계 계산
  const calculateStats = useCallback((seniors: Senior[]): DashboardStats => {
    const stats = {
      totalSeniors: seniors.length,
      normalStatus: 0,
      warningStatus: 0,
      criticalStatus: 0,
    };

    seniors.forEach(senior => {
      const recentScore = senior.recentScores?.depression || 0;
      if (recentScore < 30) {
        stats.normalStatus++;
      } else if (recentScore < 70) {
        stats.warningStatus++;
      } else {
        stats.criticalStatus++;
      }
    });

    return stats;
  }, []);

  // 인증된 상태에서 즉시 데이터 가져오기 (상태 체크 없음)
  const fetchDataWithAuth = useCallback(async () => {
    console.log('fetchDataWithAuth 호출됨 - 인증 확인된 상태로 즉시 실행');
    setIsLoading(true);
    setError(null);

    try {
      // 1. 시니어 데이터 가져오기 (API 실패 시 빈 데이터로 처리)
      console.log('시니어 데이터 요청...');

      try {
        const seniorsRes = await apiClient.getSeniors();
        if (seniorsRes.success && seniorsRes.data) {
          console.log('시니어 데이터 수신:', seniorsRes.data.seniors.length, '명');
          setSeniors(seniorsRes.data.seniors);
          setStats(calculateStats(seniorsRes.data.seniors));
        } else {
          // API 실패 시 빈 데이터로 설정
          console.log('시니어 데이터 없음 - 빈 데이터로 초기화');
          setSeniors([]);
          setStats(calculateStats([]));
        }
      } catch (seniorError) {
        // API 호출 실패 시 빈 데이터로 설정
        console.log('시니어 API 호출 실패 - 빈 데이터로 초기화');
        setSeniors([]);
        setStats(calculateStats([]));
      }

      // 2. 통화 및 분석 데이터 가져오기 (Firestore에서 직접)
      console.log('🔍 통화 및 분석 데이터 요청 시작...');

      try {
        const callsAnalysesRes = await apiClient.getCallsWithAnalyses();
        console.log('📊 getCallsWithAnalyses 응답:', callsAnalysesRes);

        if (callsAnalysesRes.success && callsAnalysesRes.data) {
          console.log('통화 데이터 수신:', callsAnalysesRes.data.calls.length, '개');
          console.log('분석 결과 수신:', callsAnalysesRes.data.analyses.length, '개');

          setCalls(callsAnalysesRes.data.calls);
          setAnalyses(callsAnalysesRes.data.analyses);
        } else {
          console.warn('통화/분석 데이터 가져오기 실패:', callsAnalysesRes.error);
          // 데이터가 없어도 빈 배열로 설정하여 UI가 정상 작동하도록 함
          setCalls([]);
          setAnalyses([]);
        }
      } catch (callsError) {
        console.error('통화/분석 데이터 요청 오류:', callsError);
        // 오류 발생 시에도 빈 배열로 설정하여 UI가 정상 작동하도록 함
        setCalls([]);
        setAnalyses([]);
      }

      console.log('데이터 가져오기 성공');
    } catch (error) {
      console.error('데이터 가져오기 중 전체 오류:', error);
      const errorMessage = error instanceof Error ? error.message : '데이터를 불러오는 중 오류가 발생했습니다';
      setError(errorMessage);

      // 오류 발생 시에도 빈 데이터로 초기화
      setSeniors([]);
      setCalls([]);
      setAnalyses([]);
      setStats(calculateStats([]));
    } finally {
      setIsLoading(false);
      console.log('데이터 가져오기 완료');
    }
  }, [calculateStats]);

  // 모든 데이터 가져오기 (Firebase Auth 상태 직접 확인)
  const fetchAllData = useCallback(async () => {
    const auth = getAuth();
    const user = auth.currentUser;
    console.log('fetchAllData 호출됨, 현재 사용자:', user ? user.email : '없음');

    if (!user) {
      console.log('인증되지 않음 - 데이터 가져오기 중단');
      return;
    }

    return fetchDataWithAuth();
  }, [fetchDataWithAuth]);

  // 데이터 새로고침 - Firebase Auth 상태를 직접 확인
  const refreshData = useCallback(async () => {
    console.log('데이터 새로고침 요청');
    const auth = getAuth();
    const user = auth.currentUser;

    if (user) {
      console.log('현재 사용자 확인됨:', user.email);
      return fetchDataWithAuth();
    } else {
      console.log('사용자 인증되지 않음');
      setError('로그인이 필요합니다');
      return;
    }
  }, [fetchDataWithAuth]);

  return {
    seniors,
    calls,
    analyses,
    stats,
    isLoading,
    error,
    refreshData,
    isAuthenticated
  };
};