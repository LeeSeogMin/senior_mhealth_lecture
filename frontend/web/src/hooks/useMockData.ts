'use client';

import { useState, useEffect } from 'react';

// Mock 데이터 타입 정의
export interface Senior {
  id: string;
  name: string;
  age: number;
  status: 'normal' | 'warning' | 'critical';
  lastContact: string;
  riskLevel: number;
}

export interface AnalysisResult {
  id: string;
  seniorId: string;
  type: 'voice' | 'behavior' | 'health';
  score: number;
  timestamp: string;
  insights: string[];
}

export interface DashboardStats {
  totalSeniors: number;
  normalStatus: number;
  warningStatus: number;
  criticalStatus: number;
}

// Mock 데이터 생성 함수들
const generateMockSeniors = (): Senior[] => [
  {
    id: '1',
    name: '김영희',
    age: 78,
    status: 'normal',
    lastContact: '2024-01-07 09:30',
    riskLevel: 2
  },
  {
    id: '2', 
    name: '박철수',
    age: 82,
    status: 'warning',
    lastContact: '2024-01-07 08:15',
    riskLevel: 6
  },
  {
    id: '3',
    name: '이순자',
    age: 75,
    status: 'normal',
    lastContact: '2024-01-07 10:45',
    riskLevel: 3
  },
  {
    id: '4',
    name: '김동수',
    age: 85,
    status: 'critical',
    lastContact: '2024-01-06 14:20',
    riskLevel: 8
  }
];

const generateMockAnalyses = (): AnalysisResult[] => [
  {
    id: '1',
    seniorId: '1',
    type: 'voice',
    score: 85,
    timestamp: '2024-01-07 09:30',
    insights: ['음성 톤이 안정적임', '말하기 속도 정상']
  },
  {
    id: '2',
    seniorId: '2', 
    type: 'behavior',
    score: 65,
    timestamp: '2024-01-07 08:15',
    insights: ['활동량 감소 관찰됨', '수면 패턴 변화']
  },
  {
    id: '3',
    seniorId: '4',
    type: 'health',
    score: 45,
    timestamp: '2024-01-06 14:20',
    insights: ['혈압 상승 의심', '즉시 의료진 상담 필요']
  }
];

const generateMockStats = (seniors: Senior[]): DashboardStats => {
  const normal = seniors.filter(s => s.status === 'normal').length;
  const warning = seniors.filter(s => s.status === 'warning').length;
  const critical = seniors.filter(s => s.status === 'critical').length;
  
  return {
    totalSeniors: seniors.length,
    normalStatus: normal,
    warningStatus: warning,
    criticalStatus: critical
  };
};

// Mock 데이터 훅
export const useMockData = () => {
  const [seniors, setSeniors] = useState<Senior[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisResult[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isUseMockData = process.env.NEXT_PUBLIC_USE_MOCK_DATA === 'true';

  useEffect(() => {
    if (isUseMockData) {
      // Mock 데이터 로딩 시뮬레이션
      const loadMockData = async () => {
        setIsLoading(true);
        
        // 로딩 시뮬레이션
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const mockSeniors = generateMockSeniors();
        const mockAnalyses = generateMockAnalyses();
        const mockStats = generateMockStats(mockSeniors);
        
        setSeniors(mockSeniors);
        setAnalyses(mockAnalyses);
        setStats(mockStats);
        setIsLoading(false);
      };

      loadMockData();
    }
  }, [isUseMockData]);

  // Mock API 함수들
  const refreshData = async () => {
    if (isUseMockData) {
      setIsLoading(true);
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // 약간의 랜덤성 추가
      const mockSeniors = generateMockSeniors();
      mockSeniors.forEach(senior => {
        senior.riskLevel = Math.floor(Math.random() * 10) + 1;
      });
      
      setSeniors(mockSeniors);
      setStats(generateMockStats(mockSeniors));
      setIsLoading(false);
    }
  };

  const simulateEmergency = () => {
    if (isUseMockData && seniors.length > 0) {
      const randomSenior = seniors[Math.floor(Math.random() * seniors.length)];
      const updatedSeniors = seniors.map(senior => 
        senior.id === randomSenior.id 
          ? { ...senior, status: 'critical' as const, riskLevel: 9 }
          : senior
      );
      setSeniors(updatedSeniors);
      setStats(generateMockStats(updatedSeniors));
    }
  };

  return {
    seniors,
    analyses, 
    stats,
    isLoading,
    isUseMockData,
    refreshData,
    simulateEmergency
  };
}; 