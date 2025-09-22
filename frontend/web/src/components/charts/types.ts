// Chart component types and constants

export interface ScoreChartProps {
  scores: MentalHealthScore;
  size?: keyof typeof CHART_SIZES;
  showLegend?: boolean;
  showTooltip?: boolean;
  animate?: boolean;
}

export interface ScoreDataPoint {
  category: string;
  value: number;
  fullMark: number;
}

export interface MentalHealthScore {
  depression: number;
  anxiety: number;
  stress: number;
  mentalHealthStatus: number;
  emotionManagement: number;
  socialRelationship: number;
}

export const SCORE_COLORS = {
  good: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  neutral: '#6b7280'
};

export const CHART_SIZES = {
  small: { width: 300, height: 200 },
  medium: { width: 400, height: 300 },
  large: { width: 500, height: 400 }
};

export const DEFAULT_CHART_OPTIONS = {
  animate: true,
  showLegend: true,
  showTooltip: true
};

// Voice pattern types
export interface VoicePatternData {
  timestamp: string;
  pitch: number;
  volume: number;
  speechRate: number;
  pauseDuration: number;
}

export interface VoicePatternChartProps {
  data: VoicePatternData[];
  height?: number;
}

// Emotion tone types
export interface EmotionData {
  emotion: string;
  value: number;
  color?: string;
}

export interface EmotionToneProps {
  emotions: EmotionData[];
  showPercentage?: boolean;
}

// Gauge chart types
export interface GaugeChartProps {
  value: number;
  max?: number;
  label?: string;
  color?: string;
  showPercentage?: boolean;
}

// Pie chart types
export interface PieChartData {
  name: string;
  value: number;
  color?: string;
}

export interface PieChartProps {
  data: PieChartData[];
  showLabel?: boolean;
  showPercentage?: boolean;
}