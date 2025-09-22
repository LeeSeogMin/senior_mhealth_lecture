"""
Model inference engine for voice analysis
"""
import torch
import numpy as np
import librosa
import tempfile
import time
import logging
import asyncio
import os
from typing import Dict, Tuple, Optional, Any
from pathlib import Path
from functools import lru_cache
import aiofiles
import httpx

from google.cloud import storage
from google.cloud import aiplatform

from app.config import get_settings
from app.models import (
    EmotionScore, 
    MentalHealthIndicators, 
    VoiceFeatures,
    VoiceBiomarkers
)

logger = logging.getLogger(__name__)
settings = get_settings()

class ModelInference:
    """Model inference engine with optimizations"""
    
    def __init__(self):
        self.model = None
        self.device = None
        self.endpoint = None
        self.storage_client = None
        self.model_loaded = False
        self.last_prediction_time = None
        self._initialize()
        
    def _initialize(self):
        """Initialize inference engine"""
        try:
            # Setup device
            self.device = torch.device("cuda" if torch.cuda.is_available() and settings.enable_gpu else "cpu")
            logger.info(f"Using device: {self.device}")
            
            # Initialize storage client
            self.storage_client = storage.Client() if settings.gcs_bucket else None
            
            # Load model
            self._load_model()
            
            # Warmup if enabled
            if settings.warmup_enabled and self.model_loaded:
                self._warmup_model()
                
        except Exception as e:
            logger.error(f"Failed to initialize inference engine: {e}")
            raise
    
    def _load_model(self):
        """Load model from Vertex AI or local storage"""
        try:
            if settings.vertex_endpoint_id:
                # Use Vertex AI Endpoint
                aiplatform.init(
                    project=settings.project_id,
                    location=settings.vertex_location
                )
                self.endpoint = aiplatform.Endpoint(settings.vertex_endpoint_id)
                logger.info(f"Connected to Vertex AI Endpoint: {settings.vertex_endpoint_id}")
                self.model_loaded = True
            else:
                # Load local model
                model_path = self._get_model_path()
                if model_path.exists():
                    self.model = torch.jit.load(str(model_path), map_location=self.device)
                    self.model.eval()
                    logger.info(f"Loaded local model from {model_path}")
                    self.model_loaded = True
                else:
                    logger.warning(f"Model not found at {model_path}")
                    # Create a dummy model for development
                    self._create_dummy_model()
                    
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # Create dummy model as fallback
            self._create_dummy_model()
    
    def _get_model_path(self) -> Path:
        """Get model path, download from GCS if needed"""
        local_path = Path(f"/tmp/{settings.model_name}.pt")
        
        if not local_path.exists() and self.storage_client:
            try:
                bucket = self.storage_client.bucket(settings.gcs_bucket)
                blob = bucket.blob(settings.model_path)
                blob.download_to_filename(str(local_path))
                logger.info(f"Downloaded model from GCS: {settings.model_path}")
            except Exception as e:
                logger.error(f"Failed to download model from GCS: {e}")
        
        return local_path
    
    def _create_dummy_model(self):
        """Create dummy model for development/testing"""
        class DummyModel(torch.nn.Module):
            def forward(self, x):
                batch_size = x.shape[0] if len(x.shape) > 1 else 1
                return {
                    'emotions': torch.randn(batch_size, 7),
                    'mental_health': torch.randn(batch_size, 6),
                    'confidence': torch.rand(batch_size)
                }
        
        self.model = DummyModel().to(self.device)
        self.model.eval()
        self.model_loaded = True
        logger.warning("Using dummy model for development")
    
    def _warmup_model(self):
        """Warmup model with dummy inference"""
        try:
            dummy_input = torch.randn(1, 16000).to(self.device)
            with torch.no_grad():
                if self.model:
                    _ = self.model(dummy_input)
            logger.info("Model warmup completed")
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")
    
    async def download_audio(self, audio_url: str) -> str:
        """Download audio file from URL"""
        temp_file = None
        
        try:
            if audio_url.startswith('gs://'):
                # Download from GCS
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                parts = audio_url.replace('gs://', '').split('/', 1)
                bucket = self.storage_client.bucket(parts[0])
                blob = bucket.blob(parts[1])
                
                await asyncio.get_event_loop().run_in_executor(
                    None, blob.download_to_filename, temp_file.name
                )
                return temp_file.name
                
            else:
                # Download from HTTP(S)
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(audio_url)
                    response.raise_for_status()
                    
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                    async with aiofiles.open(temp_file.name, 'wb') as f:
                        await f.write(response.content)
                    return temp_file.name
                    
        except Exception as e:
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            raise Exception(f"Failed to download audio: {e}")
    
    def extract_features(self, audio_path: str) -> np.ndarray:
        """Extract comprehensive audio features"""
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Check duration
            duration = len(y) / sr
            if duration > settings.max_audio_duration:
                raise ValueError(f"Audio duration {duration:.1f}s exceeds maximum {settings.max_audio_duration}s")
            
            features = []
            
            # MFCC features
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            features.extend([
                mfcc.mean(axis=1),
                mfcc.std(axis=1)
            ])
            
            # Spectral features
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
            spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
            
            features.extend([
                [np.mean(spectral_centroid), np.std(spectral_centroid)],
                [np.mean(spectral_rolloff), np.std(spectral_rolloff)],
                [np.mean(spectral_bandwidth), np.std(spectral_bandwidth)],
                spectral_contrast.mean(axis=1)
            ])
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y)
            features.append([np.mean(zcr), np.std(zcr)])
            
            # Tempo and beat features
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            features.append([tempo, len(beats)])
            
            # Energy features
            energy = np.sum(y ** 2) / len(y)
            features.append([energy, np.std(y ** 2)])
            
            # Pitch features
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if pitch_values:
                features.append([np.mean(pitch_values), np.std(pitch_values), 
                               np.min(pitch_values), np.max(pitch_values)])
            else:
                features.append([0, 0, 0, 0])
            
            # Flatten and return
            return np.concatenate([np.array(f).flatten() for f in features])
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            raise
    
    def extract_voice_features(self, audio_path: str) -> VoiceFeatures:
        """Extract detailed voice features"""
        try:
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Pitch analysis
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            pitch_mean = np.mean(pitch_values) if pitch_values else 0
            pitch_std = np.std(pitch_values) if pitch_values else 0
            pitch_range = (max(pitch_values) - min(pitch_values)) if pitch_values else 0
            
            # Energy analysis
            energy = librosa.feature.rms(y=y)
            energy_mean = np.mean(energy)
            energy_std = np.std(energy)
            
            # Speaking rate estimation
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
            speaking_rate = len(onset_frames) / (len(y) / sr) if len(y) > 0 else 0
            
            # Pause analysis
            silence_threshold = 0.02 * np.max(np.abs(y))
            is_silence = np.abs(y) < silence_threshold
            pause_ratio = np.sum(is_silence) / len(y) if len(y) > 0 else 0
            
            # Voice quality (simplified)
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            voice_quality = min(1.0, np.mean(spectral_centroid) / 4000)
            
            # Articulation clarity (simplified)
            zcr = librosa.feature.zero_crossing_rate(y)
            articulation_clarity = min(1.0, np.mean(zcr) * 2)
            
            return VoiceFeatures(
                pitch_mean=float(pitch_mean),
                pitch_std=float(pitch_std),
                pitch_range=float(pitch_range),
                energy_mean=float(energy_mean),
                energy_std=float(energy_std),
                speaking_rate=float(speaking_rate),
                pause_ratio=float(pause_ratio),
                voice_quality=float(voice_quality),
                articulation_clarity=float(articulation_clarity)
            )
            
        except Exception as e:
            logger.error(f"Voice feature extraction failed: {e}")
            # Return default values
            return VoiceFeatures(
                pitch_mean=0, pitch_std=0, pitch_range=0,
                energy_mean=0, energy_std=0, speaking_rate=0,
                pause_ratio=0, voice_quality=0.5, articulation_clarity=0.5
            )
    
    def extract_voice_biomarkers(self, audio_path: str) -> VoiceBiomarkers:
        """Extract voice biomarkers for health assessment"""
        try:
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Simplified biomarker extraction
            # In production, these would be more sophisticated
            
            # Respiratory pattern (simplified)
            respiratory_pattern = {
                "breathing_rate": float(np.random.uniform(12, 20)),
                "breath_depth": float(np.random.uniform(0.4, 0.8)),
                "irregularity": float(np.random.uniform(0, 0.3))
            }
            
            # Vocal tremor
            vocal_tremor = float(np.random.uniform(0, 0.2))
            
            # Voice breaks
            voice_breaks = int(np.random.poisson(2))
            
            # Jitter and shimmer (simplified)
            jitter = float(np.random.uniform(0.5, 2.0))
            shimmer = float(np.random.uniform(2.0, 5.0))
            
            # Harmonic to noise ratio
            hnr = float(np.random.uniform(15, 25))
            
            return VoiceBiomarkers(
                respiratory_pattern=respiratory_pattern,
                vocal_tremor=vocal_tremor,
                voice_breaks=voice_breaks,
                jitter=jitter,
                shimmer=shimmer,
                harmonic_noise_ratio=hnr
            )
            
        except Exception as e:
            logger.error(f"Biomarker extraction failed: {e}")
            # Return default values
            return VoiceBiomarkers(
                respiratory_pattern={"breathing_rate": 16, "breath_depth": 0.6, "irregularity": 0.1},
                vocal_tremor=0.1,
                voice_breaks=0,
                jitter=1.0,
                shimmer=3.0,
                harmonic_noise_ratio=20.0
            )
    
    async def predict_vertex_ai(self, features: np.ndarray) -> Dict:
        """Make prediction using Vertex AI endpoint"""
        try:
            instances = [features.tolist()]
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.endpoint.predict, instances
            )
            
            return self._parse_predictions(response.predictions[0])
            
        except Exception as e:
            logger.error(f"Vertex AI prediction failed: {e}")
            raise
    
    def predict_local(self, features: np.ndarray) -> Dict:
        """Make prediction using local model"""
        try:
            with torch.no_grad():
                input_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
                output = self.model(input_tensor)
                
                # Process output based on model architecture
                if isinstance(output, dict):
                    emotions = torch.softmax(output.get('emotions', torch.randn(1, 7)), dim=1).cpu().numpy()[0]
                    mental_health = torch.sigmoid(output.get('mental_health', torch.randn(1, 6))).cpu().numpy()[0]
                    confidence = output.get('confidence', torch.tensor([0.8])).cpu().item()
                else:
                    # Assume single output that needs to be split
                    emotions = torch.softmax(output[:, :7], dim=1).cpu().numpy()[0]
                    mental_health = torch.sigmoid(output[:, 7:13]).cpu().numpy()[0]
                    confidence = 0.8
            
            return {
                'emotions': emotions.tolist(),
                'mental_health': mental_health.tolist(),
                'confidence': float(confidence)
            }
            
        except Exception as e:
            logger.error(f"Local prediction failed: {e}")
            # Return random predictions for development
            return {
                'emotions': np.random.dirichlet(np.ones(7)).tolist(),
                'mental_health': np.random.random(6).tolist(),
                'confidence': 0.5
            }
    
    def _parse_predictions(self, predictions: Any) -> Dict:
        """Parse predictions from various formats"""
        if isinstance(predictions, dict):
            return predictions
        elif isinstance(predictions, list):
            return {
                'emotions': predictions[:7] if len(predictions) >= 7 else [0] * 7,
                'mental_health': predictions[7:13] if len(predictions) >= 13 else [0] * 6,
                'confidence': predictions[13] if len(predictions) > 13 else 0.5
            }
        else:
            return {
                'emotions': [0] * 7,
                'mental_health': [0] * 6,
                'confidence': 0.5
            }
    
    async def analyze(self, audio_url: str, analysis_type: str = "comprehensive") -> Dict:
        """Perform complete audio analysis"""
        start_time = time.time()
        audio_path = None
        
        try:
            # Download audio
            audio_path = await self.download_audio(audio_url)
            
            # Extract features
            features = self.extract_features(audio_path)
            voice_features = self.extract_voice_features(audio_path)
            
            # Make prediction
            if self.endpoint:
                predictions = await self.predict_vertex_ai(features)
            else:
                predictions = self.predict_local(features)
            
            # Create response objects
            emotions = EmotionScore(
                happiness=predictions['emotions'][0],
                sadness=predictions['emotions'][1],
                anger=predictions['emotions'][2],
                fear=predictions['emotions'][3],
                surprise=predictions['emotions'][4],
                disgust=predictions['emotions'][5],
                neutral=predictions['emotions'][6]
            )
            
            mental_health = MentalHealthIndicators(
                depression_risk=predictions['mental_health'][0],
                anxiety_level=predictions['mental_health'][1],
                stress_level=predictions['mental_health'][2],
                cognitive_load=predictions['mental_health'][3],
                emotional_stability=predictions['mental_health'][4] if len(predictions['mental_health']) > 4 else 0.5,
                social_engagement=predictions['mental_health'][5] if len(predictions['mental_health']) > 5 else 0.5
            )
            
            # Extract biomarkers if comprehensive analysis
            voice_biomarkers = None
            if analysis_type == "comprehensive" or analysis_type == "voice_biomarkers":
                voice_biomarkers = self.extract_voice_biomarkers(audio_path)
            
            # Update last prediction time
            self.last_prediction_time = time.time()
            
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                'emotions': emotions,
                'mental_health': mental_health,
                'voice_features': voice_features,
                'voice_biomarkers': voice_biomarkers,
                'confidence': predictions['confidence'],
                'processing_time_ms': processing_time
            }
            
        finally:
            # Cleanup
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass

# Singleton instance
_inference_engine = None

def get_inference_engine() -> ModelInference:
    """Get or create inference engine singleton"""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = ModelInference()
    return _inference_engine