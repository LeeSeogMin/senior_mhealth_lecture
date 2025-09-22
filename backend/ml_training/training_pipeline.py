"""
멀티모달 모델 학습 파이프라인
Wav2Vec2 + KoBERT 통합 학습 (Cross-Modal Fusion)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import torch
import numpy as np
import pandas as pd
from google.cloud import bigquery, aiplatform, storage
from transformers import (
    Wav2Vec2ForSequenceClassification,
    Wav2Vec2Processor,
    BertModel,
    BertTokenizer,
    Trainer,
    TrainingArguments,
    EvalPrediction
)
from peft import LoraConfig, get_peft_model, TaskType
from sklearn.metrics import mean_absolute_error, accuracy_score
import wandb

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultimodalMentalHealthTrainer:
    """
    멀티모달 정신건강 분석 모델 학습
    """

    def __init__(self, project_id: str = "senior-mhealth-472007"):
        self.project_id = project_id
        self.bigquery_client = bigquery.Client(project=project_id)

        # Vertex AI 초기화
        aiplatform.init(
            project=project_id,
            location='asia-northeast3'
        )

        # 모델 설정
        self.wav2vec2_model_name = "kresnik/wav2vec2-large-xlsr-korean"
        self.kobert_model_name = "skt/kobert-base-v1"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # W&B 초기화 (실험 추적)
        wandb.init(
            project="senior-mhealth-multimodal",
            config={
                "wav2vec2_model": self.wav2vec2_model_name,
                "kobert_model": self.kobert_model_name,
                "project": project_id
            }
        )

    def prepare_dataset(self, days_back: int = 30) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        BigQuery에서 학습 데이터 로드
        """
        query = f"""
        SELECT
            sample_id,
            text_content,
            voice_features.speech_rate,
            voice_features.pause_ratio,
            voice_features.energy_level,
            voice_features.pitch_variance,
            labels.depression as label_depression,
            labels.anxiety as label_anxiety,
            labels.cognitive as label_cognitive,
            label_confidence,
            split
        FROM `{self.project_id}.ml_training.multimodal_dataset`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days_back} DAY)
        AND label_confidence > 0.6
        """

        df = self.bigquery_client.query(query).to_dataframe()

        # Train/Val 분리
        train_df = df[df['split'] == 'train'].copy()
        val_df = df[df['split'] == 'val'].copy()

        logger.info(f"Loaded {len(train_df)} training samples, {len(val_df)} validation samples")

        return train_df, val_df

    def create_multimodal_dataset_class(self):
        """
        멀티모달 PyTorch Dataset 클래스 생성
        """
        class MultimodalMentalHealthDataset(torch.utils.data.Dataset):
            def __init__(self, dataframe, wav2vec2_processor, kobert_tokenizer, max_audio_length=30):
                self.df = dataframe
                self.wav2vec2_processor = wav2vec2_processor
                self.kobert_tokenizer = kobert_tokenizer
                self.max_audio_length = max_audio_length

            def __len__(self):
                return len(self.df)

            def __getitem__(self, idx):
                row = self.df.iloc[idx]

                # 음성 특징 처리 (실제로는 오디오 파일에서 로드)
                # 여기서는 시뮬레이션을 위해 특징값 사용
                audio_features = np.random.randn(self.max_audio_length * 16000)  # 30초
                audio_inputs = self.wav2vec2_processor(
                    audio_features,
                    sampling_rate=16000,
                    return_tensors="pt",
                    padding=True
                )

                # 텍스트 처리
                text = row['text_content']
                text_inputs = self.kobert_tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    padding='max_length',
                    max_length=512
                )

                # 5대 지표 레이블
                labels = torch.tensor([
                    row.get('label_depression', 0.5),
                    row.get('label_anxiety', 0.5),
                    row.get('label_cognitive', 0.5),
                    row.get('label_emotional', 0.5),
                    row.get('label_vitality', 0.5)
                ], dtype=torch.float32)

                return {
                    'audio_input': audio_inputs.input_values.squeeze(),
                    'text_input_ids': text_inputs.input_ids.squeeze(),
                    'text_attention_mask': text_inputs.attention_mask.squeeze(),
                    'labels': labels
                }

        return MultimodalMentalHealthDataset

    def setup_multimodal_model(self):
        """
        Wav2Vec2 + KoBERT 멀티모달 모델 설정
        """
        import torch.nn as nn

        class MultimodalMentalHealthModel(nn.Module):
            def __init__(self, wav2vec2_name, kobert_name):
                super().__init__()
                # 음성 인코더: Wav2Vec2
                self.wav2vec2 = Wav2Vec2ForSequenceClassification.from_pretrained(
                    wav2vec2_name,
                    num_labels=768,  # 임베딩 차원
                    output_hidden_states=True
                )

                # 텍스트 인코더: KoBERT
                self.kobert = BertModel.from_pretrained(kobert_name)

                # Cross-Modal Attention
                self.cross_attention = nn.MultiheadAttention(
                    embed_dim=768,
                    num_heads=12,
                    batch_first=True
                )

                # Fusion Layer
                self.fusion_layer = nn.Sequential(
                    nn.Linear(768 * 2, 512),
                    nn.ReLU(),
                    nn.Dropout(0.1),
                    nn.Linear(512, 256),
                    nn.ReLU(),
                    nn.Dropout(0.1)
                )

                # 5대 지표 예측 헤드
                self.dri_head = nn.Linear(256, 1)  # Depression Risk Index
                self.sdi_head = nn.Linear(256, 1)  # Sleep Disorder Index
                self.cfl_head = nn.Linear(256, 1)  # Cognitive Function Level
                self.es_head = nn.Linear(256, 1)   # Emotional Stability
                self.ov_head = nn.Linear(256, 1)   # Overall Vitality

            def forward(self, audio_input, text_input_ids, text_attention_mask):
                # 음성 특징 추출
                audio_outputs = self.wav2vec2(audio_input)
                audio_features = audio_outputs.hidden_states[-1].mean(dim=1)  # [batch, 768]

                # 텍스트 특징 추출
                text_outputs = self.kobert(
                    input_ids=text_input_ids,
                    attention_mask=text_attention_mask
                )
                text_features = text_outputs.last_hidden_state.mean(dim=1)  # [batch, 768]

                # Cross-Modal Attention
                attended_features, _ = self.cross_attention(
                    text_features.unsqueeze(1),
                    audio_features.unsqueeze(1),
                    audio_features.unsqueeze(1)
                )
                attended_features = attended_features.squeeze(1)

                # Feature Fusion
                fused = torch.cat([text_features, attended_features], dim=-1)
                fused = self.fusion_layer(fused)

                # 5대 지표 예측
                predictions = {
                    'DRI': torch.sigmoid(self.dri_head(fused)),
                    'SDI': torch.sigmoid(self.sdi_head(fused)),
                    'CFL': torch.sigmoid(self.cfl_head(fused)),
                    'ES': torch.sigmoid(self.es_head(fused)),
                    'OV': torch.sigmoid(self.ov_head(fused))
                }

                return predictions

        # 모델 초기화
        model = MultimodalMentalHealthModel(
            self.wav2vec2_model_name,
            self.kobert_model_name
        )

        # LoRA 설정 (효율적 파인튜닝)
        lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["query", "value", "key", "dense"],
            lora_dropout=0.1,
            bias="none"
        )

        # LoRA 적용
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

        return model

    def compute_metrics(self, eval_pred: EvalPrediction) -> Dict:
        """
        평가 메트릭 계산
        """
        predictions = eval_pred.predictions
        labels = eval_pred.label_ids

        # Sigmoid 적용 (0-1 범위로 정규화)
        predictions = torch.sigmoid(torch.tensor(predictions)).numpy()

        metrics = {
            'depression_mae': mean_absolute_error(labels[:, 0], predictions[:, 0]),
            'anxiety_mae': mean_absolute_error(labels[:, 1], predictions[:, 1]),
            'cognitive_mae': mean_absolute_error(labels[:, 2], predictions[:, 2]),
            'overall_mae': mean_absolute_error(labels, predictions)
        }

        # 임계값 기반 정확도
        threshold = 0.5
        pred_binary = (predictions > threshold).astype(int)
        label_binary = (labels > threshold).astype(int)

        metrics['accuracy'] = accuracy_score(
            label_binary.flatten(),
            pred_binary.flatten()
        )

        return metrics

    def train(self, num_epochs: int = 3, batch_size: int = 8):
        """
        모델 학습 실행
        """
        # 데이터 준비
        train_df, val_df = self.prepare_dataset()

        # 프로세서 로드
        wav2vec2_processor = Wav2Vec2Processor.from_pretrained(self.wav2vec2_model_name)
        kobert_tokenizer = BertTokenizer.from_pretrained(self.kobert_model_name)

        # Dataset 생성
        DatasetClass = self.create_multimodal_dataset_class()
        train_dataset = DatasetClass(train_df, wav2vec2_processor, kobert_tokenizer)
        val_dataset = DatasetClass(val_df, wav2vec2_processor, kobert_tokenizer)

        # 멀티모달 모델 설정
        model = self.setup_multimodal_model()
        model.to(self.device)

        # 학습 설정
        training_args = TrainingArguments(
            output_dir=f"./models/mental_health_v{datetime.now().strftime('%Y%m%d')}",
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir='./logs',
            logging_steps=10,
            evaluation_strategy="steps",
            eval_steps=100,
            save_strategy="steps",
            save_steps=500,
            load_best_model_at_end=True,
            metric_for_best_model="overall_mae",
            greater_is_better=False,
            push_to_hub=False,
            report_to="wandb",  # W&B 로깅
            fp16=torch.cuda.is_available(),  # GPU에서만 FP16
        )

        # Trainer 초기화
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=self.compute_metrics,
        )

        # 학습 실행
        logger.info("Starting training...")
        trainer.train()

        # 최종 평가
        eval_results = trainer.evaluate()
        logger.info(f"Evaluation results: {eval_results}")

        # 모델 저장
        model_path = self.save_model(model, eval_results)

        return model_path, eval_results

    def save_model(self, model, metrics: Dict) -> str:
        """
        학습된 모델 저장 및 버전 관리
        """
        version = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 로컬 저장
        local_path = f"./models/mental_health_v{version}"
        model.save_pretrained(local_path)

        # GCS 업로드
        gcs_path = f"gs://senior-mhealth-models/mental_health/v{version}"
        storage_client = storage.Client()
        bucket = storage_client.bucket("senior-mhealth-models")

        # 모델 파일 업로드
        for filename in os.listdir(local_path):
            blob = bucket.blob(f"mental_health/v{version}/{filename}")
            blob.upload_from_filename(os.path.join(local_path, filename))

        # BigQuery에 모델 정보 저장
        self.register_model(version, metrics, gcs_path)

        logger.info(f"Model saved to {gcs_path}")
        return gcs_path

    def register_model(self, version: str, metrics: Dict, model_path: str):
        """
        모델 레지스트리에 등록
        """
        query = f"""
        INSERT INTO `{self.project_id}.ml_training.model_performance` (
            model_id,
            model_version,
            trained_at,
            architecture,
            training_samples,
            epochs,
            learning_rate,
            metrics,
            deployment_status
        ) VALUES (
            '{version}',
            'v{version}',
            CURRENT_TIMESTAMP(),
            'wav2vec2_kobert_multimodal',
            {len(self.train_df) if hasattr(self, 'train_df') else 0},
            3,
            0.0001,
            STRUCT(
                {metrics.get('overall_mae', 0)} as train_loss,
                {metrics.get('overall_mae', 0)} as val_loss,
                {metrics.get('depression_mae', 0)} as depression_mae,
                {metrics.get('anxiety_mae', 0)} as anxiety_mae,
                {metrics.get('cognitive_mae', 0)} as cognitive_mae,
                {metrics.get('accuracy', 0)} as overall_accuracy
            ),
            'testing'
        )
        """

        self.bigquery_client.query(query).result()

    def deploy_to_vertex_ai(self, model_path: str, traffic_split: int = 20):
        """
        Vertex AI Endpoint 배포
        """
        # 모델 업로드
        model = aiplatform.Model.upload(
            display_name=f"mental-health-multimodal-{datetime.now().strftime('%Y%m%d')}",
            artifact_uri=model_path,
            serving_container_image_uri="asia-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.1-11:latest"
        )

        # 엔드포인트 생성 또는 업데이트
        endpoints = aiplatform.Endpoint.list(
            filter='display_name="mental-health-multimodal"'
        )

        if endpoints:
            endpoint = endpoints[0]
            # Canary 배포 (새 모델에 20% 트래픽)
            endpoint.deploy(
                model=model,
                deployed_model_display_name=f"v{datetime.now().strftime('%Y%m%d')}",
                traffic_percentage=traffic_split,
                machine_type="n1-standard-4",
                accelerator_type="NVIDIA_TESLA_T4",
                accelerator_count=1,
                min_replica_count=1,
                max_replica_count=3,
            )
        else:
            # 새 엔드포인트 생성
            endpoint = model.deploy(
                deployed_model_display_name=f"v{datetime.now().strftime('%Y%m%d')}",
                machine_type="n1-standard-4",
                accelerator_type="NVIDIA_TESLA_T4",
                accelerator_count=1,
                min_replica_count=1,
                max_replica_count=3,
            )

        logger.info(f"Model deployed to endpoint: {endpoint.resource_name}")
        return endpoint


def main():
    """
    학습 파이프라인 실행
    """
    trainer = MultimodalMentalHealthTrainer()

    # 모델 학습
    model_path, metrics = trainer.train(num_epochs=3, batch_size=8)

    # 성능이 기준치를 만족하면 배포
    if metrics['overall_mae'] < 0.15:  # MAE < 0.15
        logger.info("Model performance meets criteria, deploying...")
        trainer.deploy_to_vertex_ai(model_path, traffic_split=20)
    else:
        logger.warning(f"Model performance below threshold: {metrics['overall_mae']}")

    # W&B 종료
    wandb.finish()


if __name__ == "__main__":
    main()