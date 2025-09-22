import { EnhancedAnalysis } from '../hooks/useApiData';

// 트렌드 차트용 데이터 타입
export interface TrendData {
  date: string;
  normal: number;
  warning: number;
  critical: number;
  total: number;
}

// 상태 분포 차트용 데이터 타입
export interface StatusDistributionData {
  name: string;
  value: number;
  color: string;
}

// 위험도 레벨 판정 함수
export const getRiskLevel = (score: number): 'normal' | 'warning' | 'critical' => {
  if (score < 30) return 'normal';
  if (score < 70) return 'warning';
  return 'critical';
};

// 분석 결과를 위험도별로 분류
export const categorizeAnalysisByRisk = (analyses: EnhancedAnalysis[]) => {
  const categories = {
    normal: 0,
    warning: 0,
    critical: 0,
  };

  analyses.forEach(analysis => {
    // 우울증 점수를 기준으로 위험도 판정
    const depressionScore = analysis.result?.mentalHealthAnalysis?.depression?.score || 0;
    const riskLevel = getRiskLevel(depressionScore);
    categories[riskLevel]++;
  });

  return categories;
};

// 날짜별 분석 결과를 그룹화
export const groupAnalysesByDate = (analyses: EnhancedAnalysis[]): Record<string, EnhancedAnalysis[]> => {
  const grouped: Record<string, EnhancedAnalysis[]> = {};

  analyses.forEach(analysis => {
    const date = new Date(analysis.recordedAt || '').toLocaleDateString('ko-KR', {
      month: '2-digit',
      day: '2-digit'
    });
    
    if (!grouped[date]) {
      grouped[date] = [];
    }
    grouped[date].push(analysis);
  });

  return grouped;
};

// 트렌드 차트 데이터 생성
export const generateTrendData = (analyses: EnhancedAnalysis[]): TrendData[] => {
  if (!analyses.length) {
    // 데이터가 없을 때 최근 7일 빈 데이터 반환
    const emptyData: TrendData[] = [];
    for (let i = 6; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      emptyData.push({
        date: date.toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }),
        normal: 0,
        warning: 0,
        critical: 0,
        total: 0,
      });
    }
    return emptyData;
  }

  const groupedByDate = groupAnalysesByDate(analyses);
  const trendData: TrendData[] = [];

  // 최근 7일 데이터 생성
  for (let i = 6; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    const dateKey = date.toLocaleDateString('ko-KR', {
      month: '2-digit',
      day: '2-digit'
    });

    const dayAnalyses = groupedByDate[dateKey] || [];
    const categories = categorizeAnalysisByRisk(dayAnalyses);

    trendData.push({
      date: dateKey,
      normal: categories.normal,
      warning: categories.warning,
      critical: categories.critical,
      total: dayAnalyses.length,
    });
  }

  return trendData;
};

// 상태 분포 차트 데이터 생성
export const generateStatusDistributionData = (analyses: EnhancedAnalysis[]): StatusDistributionData[] => {
  if (!analyses.length) {
    return [
      { name: '정상', value: 0, color: '#10b981' },
      { name: '주의', value: 0, color: '#f59e0b' },
      { name: '긴급', value: 0, color: '#ef4444' },
    ];
  }

  const categories = categorizeAnalysisByRisk(analyses);

  return [
    { name: '정상', value: categories.normal, color: '#10b981' },
    { name: '주의', value: categories.warning, color: '#f59e0b' },
    { name: '긴급', value: categories.critical, color: '#ef4444' },
  ];
};

// 전체 통계 계산 (대시보드용)
export const calculateOverallStats = (analyses: EnhancedAnalysis[]) => {
  const categories = categorizeAnalysisByRisk(analyses);
  const total = categories.normal + categories.warning + categories.critical;

  return {
    totalAnalyses: total,
    normalCount: categories.normal,
    warningCount: categories.warning,
    criticalCount: categories.critical,
    normalPercentage: total > 0 ? Math.round((categories.normal / total) * 100) : 0,
    warningPercentage: total > 0 ? Math.round((categories.warning / total) * 100) : 0,
    criticalPercentage: total > 0 ? Math.round((categories.critical / total) * 100) : 0,
  };
}; 