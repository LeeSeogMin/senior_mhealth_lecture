import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging
import warnings

# 한글 폰트 설정 (선택사항)
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.style.use('seaborn-v0_8')

class TimeSeriesVisualizer:
    """
    시계열 분석 결과 시각화 클래스
    
    추세, 변화점, 베이스라인, 예측 결과 등을 시각화하는
    다양한 플롯팅 기능을 제공합니다.
    """
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        """
        Args:
            figsize: 기본 그래프 크기
        """
        self.figsize = figsize
        self.logger = logging.getLogger(__name__)
        
        # 색상 팔레트 설정
        self.colors = {
            'depression': '#FF6B6B',
            'cognitive': '#4ECDC4',
            'baseline': '#95A5A6',
            'trend': '#3498DB',
            'change_point': '#E74C3C',
            'prediction': '#9B59B6',
            'alert': '#E67E22',
            'normal': '#2ECC71'
        }
    
    def create_comprehensive_report(self, data: List[Dict], 
                                  analysis_results: Dict,
                                  save_path: Optional[str] = None) -> Dict:
        """
        종합적인 시계열 분석 보고서 생성
        
        Args:
            data: 원본 시계열 데이터
            analysis_results: 분석 결과 딕셔너리
            save_path: 저장 경로 (선택사항)
            
        Returns:
            생성된 플롯 정보 딕셔너리
        """
        plot_info = {
            'plots_created': [],
            'save_paths': [],
            'recommendations': []
        }
        
        # 1. 기본 시계열 플롯
        fig1 = self.plot_timeseries_overview(data, analysis_results)
        plot_info['plots_created'].append('timeseries_overview')
        
        # 2. 추세 분석 플롯
        if 'trends' in analysis_results:
            fig2 = self.plot_trend_analysis(data, analysis_results['trends'])
            plot_info['plots_created'].append('trend_analysis')
        
        # 3. 변화점 탐지 플롯
        if 'change_detection' in analysis_results:
            fig3 = self.plot_change_detection(data, analysis_results['change_detection'])
            plot_info['plots_created'].append('change_detection')
        
        # 4. 위험도 예측 플롯
        if 'risk_prediction' in analysis_results:
            fig4 = self.plot_risk_prediction(data, analysis_results['risk_prediction'])
            plot_info['plots_created'].append('risk_prediction')
        
        # 5. 베이스라인 비교 플롯
        if 'baseline' in analysis_results:
            fig5 = self.plot_baseline_comparison(data, analysis_results['baseline'])
            plot_info['plots_created'].append('baseline_comparison')
        
        # 저장
        if save_path:
            import os
            os.makedirs(save_path, exist_ok=True)
            for i, plot_name in enumerate(plot_info['plots_created'], 1):
                plt.figure(i)
                save_file = os.path.join(save_path, f"{plot_name}.png")
                plt.savefig(save_file, dpi=300, bbox_inches='tight')
                plot_info['save_paths'].append(save_file)
        
        plt.show()
        return plot_info
    
    def plot_timeseries_overview(self, data: List[Dict], 
                               analysis_results: Dict = None) -> plt.Figure:
        """기본 시계열 데이터 개요 플롯"""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('시계열 분석 개요', fontsize=16, fontweight='bold')
        
        # 데이터 추출
        timestamps = [datetime.fromisoformat(d['analysis_timestamp'].replace('Z', '+00:00')) 
                     for d in data]
        depression_scores = [d['mentalHealthAnalysis']['depression']['score'] for d in data]
        cognitive_scores = [d['mentalHealthAnalysis']['cognitive']['score'] for d in data]
        
        # 1. 우울증 점수 시계열
        axes[0, 0].plot(timestamps, depression_scores, 
                       color=self.colors['depression'], marker='o', linewidth=2)
        axes[0, 0].set_title('우울증 점수 추이', fontweight='bold')
        axes[0, 0].set_ylabel('우울증 점수')
        axes[0, 0].grid(True, alpha=0.3)
        self._format_date_axis(axes[0, 0])
        
        # 2. 인지기능 점수 시계열
        axes[0, 1].plot(timestamps, cognitive_scores, 
                       color=self.colors['cognitive'], marker='s', linewidth=2)
        axes[0, 1].set_title('인지기능 점수 추이', fontweight='bold')
        axes[0, 1].set_ylabel('인지기능 점수')
        axes[0, 1].grid(True, alpha=0.3)
        self._format_date_axis(axes[0, 1])
        
        # 3. 상관관계 산점도
        axes[1, 0].scatter(depression_scores, cognitive_scores, 
                          alpha=0.6, color=self.colors['trend'])
        correlation = np.corrcoef(depression_scores, cognitive_scores)[0, 1]
        axes[1, 0].set_title(f'우울증 vs 인지기능 (상관계수: {correlation:.3f})', fontweight='bold')
        axes[1, 0].set_xlabel('우울증 점수')
        axes[1, 0].set_ylabel('인지기능 점수')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 분포 히스토그램
        axes[1, 1].hist(depression_scores, bins=15, alpha=0.7, 
                       color=self.colors['depression'], label='우울증')
        axes[1, 1].hist(cognitive_scores, bins=15, alpha=0.7, 
                       color=self.colors['cognitive'], label='인지기능')
        axes[1, 1].set_title('점수 분포', fontweight='bold')
        axes[1, 1].set_xlabel('점수')
        axes[1, 1].set_ylabel('빈도')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def plot_trend_analysis(self, data: List[Dict], trend_results: Dict) -> plt.Figure:
        """추세 분석 결과 시각화"""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('추세 분석 결과', fontsize=16, fontweight='bold')
        
        timestamps = [datetime.fromisoformat(d['analysis_timestamp'].replace('Z', '+00:00')) 
                     for d in data]
        
        metrics = ['depression', 'cognitive']
        colors = [self.colors['depression'], self.colors['cognitive']]
        
        for i, (metric, color) in enumerate(zip(metrics, colors)):
            if metric not in trend_results:
                continue
                
            values = [d['mentalHealthAnalysis'][metric]['score'] for d in data]
            trend_info = trend_results[metric]
            
            # 원본 데이터와 추세선
            ax = axes[i, 0]
            ax.plot(timestamps, values, 'o-', color=color, alpha=0.7, label='원본 데이터')
            
            # Mann-Kendall 추세
            if 'mann_kendall' in trend_info and trend_info['mann_kendall']['significant']:
                trend_direction = trend_info['mann_kendall']['trend']
                if trend_direction != 'no_trend':
                    # Sen's slope를 이용한 추세선
                    sens_slope = trend_info['sens_slope']['slope']
                    x_numeric = np.arange(len(values))
                    trend_line = values[0] + sens_slope * x_numeric
                    ax.plot(timestamps, trend_line, '--', color='red', linewidth=2, 
                           label=f'추세선 (기울기: {sens_slope:.3f})')
            
            ax.set_title(f'{metric.title()} 추세 분석')
            ax.set_ylabel('점수')
            ax.legend()
            ax.grid(True, alpha=0.3)
            self._format_date_axis(ax)
            
            # 추세 통계 표시
            ax_stats = axes[i, 1]
            ax_stats.axis('off')
            
            stats_text = []
            if 'mann_kendall' in trend_info:
                mk = trend_info['mann_kendall']
                stats_text.append(f"Mann-Kendall 검정:")
                stats_text.append(f"  추세: {mk['trend']}")
                stats_text.append(f"  p-value: {mk['p_value']:.4f}")
                stats_text.append(f"  Tau: {mk['tau']:.3f}")
            
            if 'sens_slope' in trend_info:
                ss = trend_info['sens_slope']
                stats_text.append(f"\nSen's Slope:")
                stats_text.append(f"  기울기: {ss['slope']:.4f}")
                stats_text.append(f"  해석: {ss['interpretation']}")
            
            if 'trend_strength' in trend_info:
                stats_text.append(f"\n추세 강도: {trend_info['trend_strength']}")
            
            ax_stats.text(0.1, 0.9, '\n'.join(stats_text), 
                         transform=ax_stats.transAxes, fontsize=10,
                         verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat'))
        
        plt.tight_layout()
        return fig
    
    def plot_change_detection(self, data: List[Dict], 
                            change_results: Dict) -> plt.Figure:
        """변화점 탐지 결과 시각화"""
        
        fig, axes = plt.subplots(2, 1, figsize=(15, 10))
        fig.suptitle('변화점 탐지 결과', fontsize=16, fontweight='bold')
        
        timestamps = [datetime.fromisoformat(d['analysis_timestamp'].replace('Z', '+00:00')) 
                     for d in data]
        
        metrics = ['depression', 'cognitive']
        colors = [self.colors['depression'], self.colors['cognitive']]
        
        for i, (metric, color) in enumerate(zip(metrics, colors)):
            values = [d['mentalHealthAnalysis'][metric]['score'] for d in data]
            
            axes[i].plot(timestamps, values, 'o-', color=color, linewidth=2, 
                        label=f'{metric.title()} 점수')
            
            # 변화점 표시
            if 'change_points' in change_results:
                for cp in change_results['change_points']:
                    if cp['metric'] == metric:
                        cp_timestamp = datetime.fromisoformat(cp['timestamp'].replace('Z', '+00:00'))
                        axes[i].axvline(x=cp_timestamp, color=self.colors['change_point'], 
                                       linestyle='--', linewidth=2, alpha=0.8,
                                       label='변화점')
                        axes[i].plot(cp_timestamp, cp['value'], 'ro', markersize=10)
            
            # 추세선 표시 (있는 경우)
            if 'trend_analysis' in change_results and metric in change_results['trend_analysis']:
                trend_info = change_results['trend_analysis'][metric]
                if trend_info.get('significance', False):
                    slope = trend_info['slope']
                    x_numeric = np.arange(len(values))
                    trend_line = values[0] + slope * x_numeric
                    axes[i].plot(timestamps, trend_line, '--', color='gray', 
                               alpha=0.7, label='추세선')
            
            axes[i].set_title(f'{metric.title()} 변화점 분석')
            axes[i].set_ylabel('점수')
            axes[i].legend()
            axes[i].grid(True, alpha=0.3)
            self._format_date_axis(axes[i])
        
        plt.tight_layout()
        return fig
    
    def plot_risk_prediction(self, data: List[Dict], 
                           risk_results: Dict) -> plt.Figure:
        """위험도 예측 결과 시각화"""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('위험도 예측 결과', fontsize=16, fontweight='bold')
        
        timestamps = [datetime.fromisoformat(d['analysis_timestamp'].replace('Z', '+00:00')) 
                     for d in data]
        
        # 1. 위험도 점수 추이
        if 'predictions' in risk_results:
            predictions = risk_results['predictions']
            
            dep_scores = [d['mentalHealthAnalysis']['depression']['score'] for d in data]
            cog_scores = [d['mentalHealthAnalysis']['cognitive']['score'] for d in data]
            
            axes[0, 0].plot(timestamps, dep_scores, 'o-', color=self.colors['depression'], 
                           label='우울증 실제')
            axes[0, 1].plot(timestamps, cog_scores, 'o-', color=self.colors['cognitive'], 
                           label='인지기능 실제')
            
            # 예측값 표시 (있는 경우)
            if 'depression' in predictions:
                pred_dep = predictions['depression']['predicted']
                last_timestamp = timestamps[-1]
                pred_timestamp = last_timestamp + timedelta(days=7)  # 1주 후 예측
                axes[0, 0].plot([last_timestamp, pred_timestamp], 
                               [dep_scores[-1], pred_dep], 
                               'r--o', linewidth=2, label='예측값')
            
            if 'cognitive' in predictions:
                pred_cog = predictions['cognitive']['predicted']
                last_timestamp = timestamps[-1]
                pred_timestamp = last_timestamp + timedelta(days=7)
                axes[0, 1].plot([last_timestamp, pred_timestamp], 
                               [cog_scores[-1], pred_cog], 
                               'r--o', linewidth=2, label='예측값')
        
        axes[0, 0].set_title('우울증 점수 예측')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        self._format_date_axis(axes[0, 0])
        
        axes[0, 1].set_title('인지기능 점수 예측')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        self._format_date_axis(axes[0, 1])
        
        # 2. 위험도 레벨 표시
        if 'risk_assessment' in risk_results:
            risk_assessment = risk_results['risk_assessment']
            
            # 원형 차트로 위험도 표시
            ax = axes[1, 0]
            if 'overall' in risk_assessment:
                risk_level = risk_assessment['overall']['level']
                risk_score = risk_assessment['overall']['score']
                
                # 위험도 색상 매핑
                risk_colors = {
                    'low': self.colors['normal'],
                    'mild': '#F39C12',
                    'moderate': '#E67E22',
                    'high': self.colors['alert']
                }
                
                color = risk_colors.get(risk_level, '#BDC3C7')
                
                # 위험도 게이지 차트
                theta = np.linspace(0, 2 * np.pi, 100)
                r = np.ones_like(theta)
                ax.fill_between(theta, 0, r, alpha=0.3, color='lightgray')
                
                # 위험도에 따른 각도 계산 (0-10 스케일)
                risk_angle = (risk_score / 10) * 2 * np.pi
                risk_theta = np.linspace(0, risk_angle, 50)
                risk_r = np.ones_like(risk_theta)
                ax.fill_between(risk_theta, 0, risk_r, alpha=0.8, color=color)
                
                ax.set_title(f'위험도: {risk_level.upper()}\n점수: {risk_score:.2f}/10')
                ax.set_ylim(0, 1.2)
                ax.set_theta_zero_location('N')
                ax.set_theta_direction(-1)
                ax.set_rlabel_position(0)
        
        # 3. 경고 지표
        ax_warnings = axes[1, 1]
        ax_warnings.axis('off')
        
        warning_text = []
        if 'warning_indicators' in risk_results:
            warning_text.append("경고 지표:")
            for warning in risk_results['warning_indicators']:
                warning_text.append(f"• {warning}")
        
        if 'confidence_scores' in risk_results:
            conf = risk_results['confidence_scores']
            warning_text.append(f"\n신뢰도:")
            warning_text.append(f"• 데이터 충분성: {conf.get('data_sufficiency', 0):.2f}")
            warning_text.append(f"• 데이터 일관성: {conf.get('data_consistency', 0):.2f}")
        
        ax_warnings.text(0.1, 0.9, '\n'.join(warning_text), 
                        transform=ax_warnings.transAxes, fontsize=10,
                        verticalalignment='top', 
                        bbox=dict(boxstyle='round', facecolor='lightyellow'))
        
        plt.tight_layout()
        return fig
    
    def plot_baseline_comparison(self, data: List[Dict], 
                               baseline_info: Dict) -> plt.Figure:
        """베이스라인 비교 시각화"""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('베이스라인 비교 분석', fontsize=16, fontweight='bold')
        
        timestamps = [datetime.fromisoformat(d['analysis_timestamp'].replace('Z', '+00:00')) 
                     for d in data]
        
        metrics = ['depression', 'cognitive']
        colors = [self.colors['depression'], self.colors['cognitive']]
        
        for i, (metric, color) in enumerate(zip(metrics, colors)):
            if metric not in baseline_info.get('mental_health', {}):
                continue
                
            values = [d['mentalHealthAnalysis'][metric]['score'] for d in data]
            baseline_stats = baseline_info['mental_health'][metric]
            
            # 시계열 데이터와 베이스라인
            axes[i, 0].plot(timestamps, values, 'o-', color=color, linewidth=2,
                           label=f'{metric.title()} 점수')
            
            # 베이스라인 평균
            baseline_mean = baseline_stats['mean']
            axes[i, 0].axhline(y=baseline_mean, color=self.colors['baseline'], 
                              linestyle='-', linewidth=2, label='베이스라인 평균')
            
            # 정상 범위 (베이스라인 ± 1 표준편차)
            baseline_std = baseline_stats['std']
            upper_bound = baseline_mean + baseline_std
            lower_bound = baseline_mean - baseline_std
            
            axes[i, 0].fill_between(timestamps, lower_bound, upper_bound, 
                                   color=self.colors['baseline'], alpha=0.2, 
                                   label='정상 범위 (±1σ)')
            
            # 이상 범위 표시
            upper_alert = baseline_mean + 2 * baseline_std
            lower_alert = baseline_mean - 2 * baseline_std
            axes[i, 0].axhline(y=upper_alert, color=self.colors['alert'], 
                              linestyle='--', alpha=0.7, label='경고 수준')
            axes[i, 0].axhline(y=lower_alert, color=self.colors['alert'], 
                              linestyle='--', alpha=0.7)
            
            axes[i, 0].set_title(f'{metric.title()} 베이스라인 비교')
            axes[i, 0].set_ylabel('점수')
            axes[i, 0].legend()
            axes[i, 0].grid(True, alpha=0.3)
            self._format_date_axis(axes[i, 0])
            
            # 베이스라인 편차 분석
            deviations = [v - baseline_mean for v in values]
            axes[i, 1].bar(range(len(deviations)), deviations, 
                          color=[color if abs(d) <= baseline_std else self.colors['alert'] 
                                for d in deviations], alpha=0.7)
            axes[i, 1].axhline(y=0, color='black', linestyle='-', linewidth=1)
            axes[i, 1].axhline(y=baseline_std, color=self.colors['alert'], 
                              linestyle='--', alpha=0.7)
            axes[i, 1].axhline(y=-baseline_std, color=self.colors['alert'], 
                              linestyle='--', alpha=0.7)
            axes[i, 1].set_title(f'{metric.title()} 베이스라인 편차')
            axes[i, 1].set_ylabel('편차')
            axes[i, 1].set_xlabel('측정 순서')
            axes[i, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def _format_date_axis(self, ax):
        """날짜 축 포맷팅"""
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(ax.get_xticklabels()) // 10)))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    def create_summary_dashboard(self, data: List[Dict], 
                               analysis_results: Dict) -> plt.Figure:
        """요약 대시보드 생성"""
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
        
        # 메인 제목
        fig.suptitle('시니어 정신건강 모니터링 대시보드', fontsize=20, fontweight='bold')
        
        timestamps = [datetime.fromisoformat(d['analysis_timestamp'].replace('Z', '+00:00')) 
                     for d in data]
        
        # 1. 주요 지표 시계열 (상단 대형)
        ax_main = fig.add_subplot(gs[0, :2])
        dep_scores = [d['mentalHealthAnalysis']['depression']['score'] for d in data]
        cog_scores = [d['mentalHealthAnalysis']['cognitive']['score'] for d in data]
        
        ax_main.plot(timestamps, dep_scores, 'o-', color=self.colors['depression'], 
                    linewidth=3, markersize=6, label='우울증 점수')
        ax_main.plot(timestamps, cog_scores, 's-', color=self.colors['cognitive'], 
                    linewidth=3, markersize=6, label='인지기능 점수')
        ax_main.set_title('정신건강 지표 추이', fontsize=14, fontweight='bold')
        ax_main.legend(fontsize=12)
        ax_main.grid(True, alpha=0.3)
        self._format_date_axis(ax_main)
        
        # 2. 현재 상태 (우상단)
        ax_status = fig.add_subplot(gs[0, 2:])
        ax_status.axis('off')
        
        latest_dep = dep_scores[-1] if dep_scores else 0
        latest_cog = cog_scores[-1] if cog_scores else 0
        
        status_text = [
            "현재 상태",
            f"우울증: {latest_dep:.1f}/10",
            f"인지기능: {latest_cog:.1f}/10",
            f"마지막 측정: {timestamps[-1].strftime('%Y-%m-%d')}" if timestamps else ""
        ]
        
        # 위험도 평가 추가
        if 'risk_prediction' in analysis_results:
            risk_level = analysis_results['risk_prediction'].get('risk_assessment', {}).get('overall', {}).get('level', 'unknown')
            status_text.append(f"위험도: {risk_level.upper()}")
        
        ax_status.text(0.1, 0.9, '\n'.join(status_text), 
                      transform=ax_status.transAxes, fontsize=14,
                      verticalalignment='top',
                      bbox=dict(boxstyle='round,pad=1', facecolor='lightblue', alpha=0.8))
        
        # 3-6. 하위 차트들
        # 추세 분석
        ax_trend = fig.add_subplot(gs[1, 0])
        if 'trends' in analysis_results:
            # 간단한 추세 방향 표시
            ax_trend.bar(['우울증', '인지기능'], [0.5, 0.5], color=['lightgray', 'lightgray'])
            ax_trend.set_title('추세 분석')
            ax_trend.set_ylim(0, 1)
        
        # 변화점 요약
        ax_changes = fig.add_subplot(gs[1, 1])
        if 'change_detection' in analysis_results:
            change_count = len(analysis_results['change_detection'].get('change_points', []))
            ax_changes.pie([change_count, max(1, len(data) - change_count)], 
                          labels=['변화점', '정상'], autopct='%1.1f%%',
                          colors=[self.colors['change_point'], self.colors['normal']])
            ax_changes.set_title('변화점 탐지')
        
        # 알림 상황
        ax_alerts = fig.add_subplot(gs[1, 2])
        if 'alerts' in analysis_results:
            alert_count = len(analysis_results['alerts'])
            ax_alerts.bar(['알림'], [alert_count], color=self.colors['alert'])
            ax_alerts.set_title('활성 알림')
            ax_alerts.set_ylabel('개수')
        
        # 데이터 품질
        ax_quality = fig.add_subplot(gs[1, 3])
        quality_score = analysis_results.get('analysis_quality', {}).get('confidence_level', 0.5)
        ax_quality.pie([quality_score, 1-quality_score], 
                      labels=['신뢰할 수 있음', '불확실'], autopct='%1.1f%%',
                      colors=[self.colors['normal'], 'lightgray'])
        ax_quality.set_title('데이터 품질')
        
        # 7. 권장사항 (하단 전체)
        ax_recommendations = fig.add_subplot(gs[2, :])
        ax_recommendations.axis('off')
        
        recommendations = []
        if 'alerts' in analysis_results:
            for alert in analysis_results['alerts'][:3]:  # 상위 3개만
                recommendations.append(f"• {alert.get('message', 'N/A')}")
        
        if not recommendations:
            recommendations = ["• 현재 특별한 주의사항이 없습니다.", "• 정기적인 모니터링을 계속하세요."]
        
        rec_text = "권장사항:\n" + '\n'.join(recommendations)
        ax_recommendations.text(0.05, 0.9, rec_text, 
                               transform=ax_recommendations.transAxes, fontsize=12,
                               verticalalignment='top',
                               bbox=dict(boxstyle='round,pad=1', facecolor='lightyellow', alpha=0.8))
        
        return fig 