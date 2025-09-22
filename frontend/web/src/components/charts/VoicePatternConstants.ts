// 음성 패턴 데이터 타입
export interface VoicePatternData {
  speechRate: number;      // 말하기 속도 (WPM)
  pauseRatio: number;      // 일시정지 비율 (0-1)
  voiceStability: number;  // 음성 안정성 (0-1)
  emotionTone?: string;    // 감정 톤 (positive/neutral/negative)
  responseTime?: number;   // 응답 시간 (ms)
  pitch?: {
    mean: number;
    variance: number;
  };
  energy?: {
    mean: number;
    variance: number;
  };
}

// 정상 범위 설정
export const VOICE_PATTERN_RANGES = {
  speechRate: {
    min: 120,    // 분당 120단어 이하는 느림
    max: 160,    // 분당 160단어 이상은 빠름
    unit: 'WPM'
  },
  pauseRatio: {
    min: 0.1,    // 10% 이하는 너무 적음
    max: 0.3,    // 30% 이상은 너무 많음
    unit: '%'
  },
  voiceStability: {
    min: 0.7,    // 70% 이하는 불안정
    max: 1.0,    // 100%가 최대 안정성
    unit: '%'
  },
  responseTime: {
    min: 500,    // 0.5초 이하는 매우 빠름
    max: 2000,   // 2초 이상은 매우 느림
    unit: 'ms'
  }
} as const;

// 감정 톤 설정
export const EMOTION_TONE_CONFIG = {
  positive: {
    icon: '😊',
    label: '긍정적',
    color: '#10b981',  // 녹색
    description: '밝고 활기찬 톤'
  },
  neutral: {
    icon: '😐',
    label: '중립적',
    color: '#6b7280',  // 회색
    description: '평온한 톤'
  },
  negative: {
    icon: '😔',
    label: '부정적',
    color: '#ef4444',  // 빨간색
    description: '우울하거나 불안한 톤'
  }
} as const;

// 차트 크기 설정
export const CHART_SIZES = {
  sm: { width: 200, height: 150 },
  md: { width: 300, height: 200 },
  lg: { width: 400, height: 300 }
} as const;

// 차트 타입
export type ChartSize = keyof typeof CHART_SIZES;

// 컴포넌트 Props 타입
export interface VoicePatternChartProps {
  data: VoicePatternData;
  size?: ChartSize;
  showLabels?: boolean;
  showTooltips?: boolean;
  className?: string;
  onPatternClick?: (patternType: keyof VoicePatternData) => void;
}

// 게이지 차트 Props
export interface GaugeChartProps {
  value: number;
  min: number;
  max: number;
  label: string;
  unit: string;
  size?: ChartSize;
  showTooltip?: boolean;
  className?: string;
  onClick?: () => void;
}

// 파이 차트 Props
export interface PieChartProps {
  value: number;
  label: string;
  size?: ChartSize;
  showTooltip?: boolean;
  className?: string;
  onClick?: () => void;
}

// 감정 톤 표시 Props
export interface EmotionToneProps {
  tone: keyof typeof EMOTION_TONE_CONFIG;
  size?: ChartSize;
  showLabel?: boolean;
  className?: string;
  onClick?: () => void;
}