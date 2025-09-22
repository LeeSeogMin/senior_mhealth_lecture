'use client';

import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { ScoreChartProps, CHART_SIZES } from './types';

export default function ScoreChart({ scores, size = 'medium', showLegend, showTooltip }: ScoreChartProps) {
  const chartSize = CHART_SIZES[size];

  // null/undefined 체크
  if (!scores) {
    return (
      <div style={{ width: '100%', height: chartSize.height }} className="flex items-center justify-center">
        <p className="text-gray-500">점수 데이터가 없습니다</p>
      </div>
    );
  }

  const data = [
    { category: '우울감', value: scores.depression || 0, fullMark: 100 },
    { category: '불안감', value: scores.anxiety || 0, fullMark: 100 },
    { category: '스트레스', value: scores.stress || 0, fullMark: 100 },
    { category: '정신건강', value: scores.mentalHealthStatus || 0, fullMark: 100 },
    { category: '감정관리', value: scores.emotionManagement || 0, fullMark: 100 },
    { category: '사회관계', value: scores.socialRelationship || 0, fullMark: 100 }
  ];

  return (
    <div style={{ width: '100%', height: chartSize.height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="category" />
          <PolarRadiusAxis angle={90} domain={[0, 100]} />
          <Radar
            name="점수"
            dataKey="value"
            stroke="#8884d8"
            fill="#8884d8"
            fillOpacity={0.6}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}