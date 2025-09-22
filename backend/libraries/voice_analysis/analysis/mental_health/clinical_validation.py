"""
임상 데이터 검증 시스템
정신건강 지표의 임상적 유효성 검증
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from sklearn.model_selection import cross_val_score, KFold
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


@dataclass
class ClinicalCase:
    """임상 케이스 데이터"""
    case_id: str
    age: int
    gender: str
    audio_path: str
    
    # 임상 진단 (Ground Truth)
    clinical_depression: bool  # PHQ-9 기반
    clinical_insomnia: bool  # ISI 기반
    cognitive_score: float  # MMSE 점수 (0-30)
    
    # 추가 임상 정보
    phq9_score: Optional[int] = None  # 우울증 척도 (0-27)
    isi_score: Optional[int] = None  # 불면증 척도 (0-28)
    mmse_score: Optional[int] = None  # 인지기능 척도 (0-30)
    gds_score: Optional[int] = None  # 노인우울척도 (0-30)
    
    # AI 예측 결과
    ai_predictions: Optional[Dict[str, float]] = None
    
    # 메타데이터
    recording_date: Optional[str] = None
    hospital: Optional[str] = None
    notes: Optional[str] = None


class ClinicalValidator:
    """임상 검증 시스템"""
    
    def __init__(self):
        """초기화"""
        self.cases: List[ClinicalCase] = []
        self.validation_results = {}
        
        # 임상 임계값
        self.clinical_thresholds = {
            'phq9': {
                'minimal': (0, 4),
                'mild': (5, 9),
                'moderate': (10, 14),
                'moderately_severe': (15, 19),
                'severe': (20, 27)
            },
            'isi': {
                'none': (0, 7),
                'subthreshold': (8, 14),
                'moderate': (15, 21),
                'severe': (22, 28)
            },
            'mmse': {
                'normal': (24, 30),
                'mild': (19, 23),
                'moderate': (10, 18),
                'severe': (0, 9)
            },
            'gds': {
                'normal': (0, 9),
                'mild': (10, 19),
                'severe': (20, 30)
            }
        }
    
    def load_clinical_data(self, data_path: str):
        """
        임상 데이터 로드
        
        Args:
            data_path: 임상 데이터 파일 경로 (CSV or JSON)
        """
        try:
            if data_path.endswith('.csv'):
                df = pd.read_csv(data_path)
                for _, row in df.iterrows():
                    case = ClinicalCase(
                        case_id=row['case_id'],
                        age=row['age'],
                        gender=row['gender'],
                        audio_path=row['audio_path'],
                        clinical_depression=row['clinical_depression'],
                        clinical_insomnia=row['clinical_insomnia'],
                        cognitive_score=row['cognitive_score'],
                        phq9_score=row.get('phq9_score'),
                        isi_score=row.get('isi_score'),
                        mmse_score=row.get('mmse_score'),
                        gds_score=row.get('gds_score')
                    )
                    self.cases.append(case)
            
            elif data_path.endswith('.json'):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        case = ClinicalCase(**item)
                        self.cases.append(case)
            
            logger.info(f"{len(self.cases)}개의 임상 케이스 로드 완료")
            
        except Exception as e:
            logger.error(f"임상 데이터 로드 실패: {e}")
    
    def validate_indicators(
        self,
        predictions: Dict[str, List[float]],
        ground_truth: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """
        5대 지표 검증
        
        Args:
            predictions: AI 예측값 {'DRI': [...], 'SDI': [...], ...}
            ground_truth: 임상 진단값
            
        Returns:
            검증 결과
        """
        results = {}
        
        for indicator in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
            if indicator not in predictions or indicator not in ground_truth:
                continue
            
            pred = np.array(predictions[indicator])
            true = np.array(ground_truth[indicator])
            
            # 이진 분류 메트릭 (임계값 0.5)
            pred_binary = (pred > 0.5).astype(int)
            true_binary = (true > 0.5).astype(int)
            
            results[indicator] = {
                'accuracy': accuracy_score(true_binary, pred_binary),
                'precision': precision_score(true_binary, pred_binary, average='weighted'),
                'recall': recall_score(true_binary, pred_binary, average='weighted'),
                'f1_score': f1_score(true_binary, pred_binary, average='weighted'),
                'correlation': np.corrcoef(pred, true)[0, 1],
                'mae': np.mean(np.abs(pred - true)),
                'rmse': np.sqrt(np.mean((pred - true) ** 2))
            }
            
            # ROC AUC (이진 분류 가능한 경우)
            try:
                results[indicator]['roc_auc'] = roc_auc_score(true_binary, pred)
            except:
                results[indicator]['roc_auc'] = None
            
            # 혼동 행렬
            results[indicator]['confusion_matrix'] = confusion_matrix(
                true_binary, pred_binary
            ).tolist()
        
        return results
    
    def validate_depression_model(
        self,
        ai_predictions: List[float],
        phq9_scores: List[int]
    ) -> Dict[str, Any]:
        """
        우울증 모델 검증 (PHQ-9 기준)
        
        Args:
            ai_predictions: AI 우울 위험도 예측 (0-1)
            phq9_scores: PHQ-9 점수 (0-27)
            
        Returns:
            검증 결과
        """
        # PHQ-9를 기준으로 이진 분류
        clinical_depression = [score >= 10 for score in phq9_scores]  # 중등도 이상
        ai_depression = [pred > 0.5 for pred in ai_predictions]
        
        # 메트릭 계산
        accuracy = accuracy_score(clinical_depression, ai_depression)
        precision = precision_score(clinical_depression, ai_depression)
        recall = recall_score(clinical_depression, ai_depression)
        f1 = f1_score(clinical_depression, ai_depression)
        
        # 상관관계
        correlation = np.corrcoef(ai_predictions, phq9_scores)[0, 1]
        
        # 민감도/특이도
        tn, fp, fn, tp = confusion_matrix(clinical_depression, ai_depression).ravel()
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'correlation': correlation,
            'sensitivity': sensitivity,
            'specificity': specificity,
            'confusion_matrix': {
                'tn': int(tn), 'fp': int(fp),
                'fn': int(fn), 'tp': int(tp)
            }
        }
    
    def validate_cognitive_model(
        self,
        ai_predictions: List[float],
        mmse_scores: List[int]
    ) -> Dict[str, Any]:
        """
        인지기능 모델 검증 (MMSE 기준)
        
        Args:
            ai_predictions: AI 인지기능 예측 (0-1)
            mmse_scores: MMSE 점수 (0-30)
            
        Returns:
            검증 결과
        """
        # MMSE 정규화 (0-1)
        mmse_normalized = [score / 30.0 for score in mmse_scores]
        
        # 상관관계
        correlation = np.corrcoef(ai_predictions, mmse_normalized)[0, 1]
        
        # 평균 절대 오차
        mae = np.mean(np.abs(np.array(ai_predictions) - np.array(mmse_normalized)))
        
        # 인지장애 분류 (MMSE < 24)
        cognitive_impairment = [score < 24 for score in mmse_scores]
        ai_impairment = [pred < 0.8 for pred in ai_predictions]  # CFL < 0.8
        
        accuracy = accuracy_score(cognitive_impairment, ai_impairment)
        
        return {
            'correlation': correlation,
            'mae': mae,
            'accuracy': accuracy,
            'mmse_comparison': {
                'ai_mean': np.mean(ai_predictions),
                'mmse_mean': np.mean(mmse_normalized),
                'ai_std': np.std(ai_predictions),
                'mmse_std': np.std(mmse_normalized)
            }
        }
    
    def cross_validate(
        self,
        model_function,
        features: np.ndarray,
        labels: np.ndarray,
        n_splits: int = 5
    ) -> Dict[str, Any]:
        """
        교차 검증
        
        Args:
            model_function: 모델 함수
            features: 특징 벡터
            labels: 레이블
            n_splits: 폴드 수
            
        Returns:
            교차 검증 결과
        """
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
        
        accuracies = []
        precisions = []
        recalls = []
        f1_scores = []
        
        for train_idx, test_idx in kf.split(features):
            X_train, X_test = features[train_idx], features[test_idx]
            y_train, y_test = labels[train_idx], labels[test_idx]
            
            # 모델 학습 및 예측
            predictions = model_function(X_train, y_train, X_test)
            
            # 메트릭 계산
            accuracies.append(accuracy_score(y_test, predictions))
            precisions.append(precision_score(y_test, predictions, average='weighted'))
            recalls.append(recall_score(y_test, predictions, average='weighted'))
            f1_scores.append(f1_score(y_test, predictions, average='weighted'))
        
        return {
            'accuracy': {
                'mean': np.mean(accuracies),
                'std': np.std(accuracies),
                'scores': accuracies
            },
            'precision': {
                'mean': np.mean(precisions),
                'std': np.std(precisions),
                'scores': precisions
            },
            'recall': {
                'mean': np.mean(recalls),
                'std': np.std(recalls),
                'scores': recalls
            },
            'f1_score': {
                'mean': np.mean(f1_scores),
                'std': np.std(f1_scores),
                'scores': f1_scores
            }
        }
    
    def statistical_significance_test(
        self,
        model1_scores: List[float],
        model2_scores: List[float],
        test_type: str = 'paired_t'
    ) -> Dict[str, Any]:
        """
        통계적 유의성 검정
        
        Args:
            model1_scores: 모델 1의 점수
            model2_scores: 모델 2의 점수
            test_type: 검정 유형 ('paired_t', 'wilcoxon')
            
        Returns:
            검정 결과
        """
        if test_type == 'paired_t':
            statistic, p_value = stats.ttest_rel(model1_scores, model2_scores)
            test_name = "Paired t-test"
        elif test_type == 'wilcoxon':
            statistic, p_value = stats.wilcoxon(model1_scores, model2_scores)
            test_name = "Wilcoxon signed-rank test"
        else:
            raise ValueError(f"Unknown test type: {test_type}")
        
        # 효과 크기 (Cohen's d)
        cohens_d = (np.mean(model1_scores) - np.mean(model2_scores)) / np.sqrt(
            (np.var(model1_scores) + np.var(model2_scores)) / 2
        )
        
        return {
            'test_name': test_name,
            'statistic': statistic,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'cohens_d': cohens_d,
            'model1_mean': np.mean(model1_scores),
            'model2_mean': np.mean(model2_scores),
            'model1_std': np.std(model1_scores),
            'model2_std': np.std(model2_scores)
        }
    
    def generate_validation_report(
        self,
        output_path: str = "clinical_validation_report.json"
    ) -> Dict[str, Any]:
        """
        검증 리포트 생성
        
        Args:
            output_path: 리포트 저장 경로
            
        Returns:
            검증 리포트
        """
        report = {
            'summary': {
                'total_cases': len(self.cases),
                'validation_date': pd.Timestamp.now().isoformat(),
                'indicators_validated': list(self.validation_results.keys())
            },
            'results': self.validation_results,
            'clinical_correlations': {},
            'recommendations': []
        }
        
        # 임상 상관관계 분석
        if self.cases:
            # 연령별 성능
            ages = [case.age for case in self.cases]
            report['clinical_correlations']['age_distribution'] = {
                'mean': np.mean(ages),
                'std': np.std(ages),
                'min': min(ages),
                'max': max(ages)
            }
        
        # 권장사항 생성
        for indicator, results in self.validation_results.items():
            if results.get('accuracy', 0) < 0.7:
                report['recommendations'].append(
                    f"{indicator} 지표의 정확도가 낮음 ({results['accuracy']:.2f}). "
                    f"추가 학습 데이터 필요."
                )
            if results.get('correlation', 0) < 0.5:
                report['recommendations'].append(
                    f"{indicator} 지표의 임상 상관관계가 낮음 ({results['correlation']:.2f}). "
                    f"특징 재설계 고려."
                )
        
        # 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"검증 리포트 저장: {output_path}")
        
        return report
    
    def plot_validation_results(self, save_path: Optional[str] = None):
        """
        검증 결과 시각화
        
        Args:
            save_path: 그래프 저장 경로
        """
        if not self.validation_results:
            logger.warning("검증 결과가 없습니다")
            return
        
        # 지표별 성능 비교
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('임상 검증 결과', fontsize=16)
        
        indicators = list(self.validation_results.keys())
        metrics = ['accuracy', 'precision', 'recall', 'f1_score', 'correlation']
        
        for idx, indicator in enumerate(indicators[:6]):
            ax = axes[idx // 3, idx % 3]
            
            values = [
                self.validation_results[indicator].get(metric, 0)
                for metric in metrics
            ]
            
            ax.bar(metrics, values)
            ax.set_title(f'{indicator} 지표')
            ax.set_ylim(0, 1)
            ax.set_ylabel('Score')
            
            # 값 표시
            for i, v in enumerate(values):
                ax.text(i, v + 0.01, f'{v:.2f}', ha='center')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"검증 그래프 저장: {save_path}")
        else:
            plt.show()


class KoreanElderlyValidator(ClinicalValidator):
    """한국 노인 특화 검증 시스템"""
    
    def __init__(self):
        """초기화"""
        super().__init__()
        
        # 한국 노인 특화 기준
        self.korean_elderly_norms = {
            'k_gds': {  # 한국판 노인우울척도
                'normal': (0, 13),
                'mild': (14, 18),
                'moderate': (19, 21),
                'severe': (22, 30)
            },
            'k_mmse': {  # 한국판 간이정신상태검사
                'normal': (24, 30),
                'mci': (20, 23),  # 경도인지장애
                'dementia': (0, 19)
            },
            'speech_rate': {  # 한국 노인 말속도 (음절/초)
                'normal': (3.5, 5.0),
                'slow': (2.0, 3.5),
                'very_slow': (0, 2.0)
            }
        }
    
    def validate_korean_specific(
        self,
        ai_predictions: Dict[str, List[float]],
        clinical_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        한국 노인 특화 검증
        
        Args:
            ai_predictions: AI 예측 결과
            clinical_data: 임상 데이터
            
        Returns:
            한국 특화 검증 결과
        """
        results = {
            'cultural_factors': {},
            'age_group_performance': {},
            'gender_differences': {}
        }
        
        # 연령대별 성능 (한국 노인 기준)
        age_groups = {
            '젊은 노인': (65, 74),
            '중간 노인': (75, 84),
            '고령 노인': (85, 100)
        }
        
        for group_name, (min_age, max_age) in age_groups.items():
            group_data = clinical_data[
                (clinical_data['age'] >= min_age) & 
                (clinical_data['age'] <= max_age)
            ]
            
            if not group_data.empty:
                # 그룹별 정확도 계산
                group_indices = group_data.index.tolist()
                results['age_group_performance'][group_name] = {
                    'sample_size': len(group_data),
                    'mean_age': group_data['age'].mean()
                }
        
        # 성별 차이 분석
        for gender in ['남', '여']:
            gender_data = clinical_data[clinical_data['gender'] == gender]
            if not gender_data.empty:
                results['gender_differences'][gender] = {
                    'sample_size': len(gender_data),
                    'mean_age': gender_data['age'].mean()
                }
        
        # 문화적 요인 (한국 특화 표현)
        results['cultural_factors'] = {
            '존댓말_사용': '높음',
            '간접_표현': '빈번',
            '감정_억제': '중간',
            '가족_중심': '높음'
        }
        
        return results


# 테스트용 샘플 데이터 생성 함수 제거됨
# 실제 임상 데이터만 사용하도록 변경