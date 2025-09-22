"""
Original SincNet Analyzer v5 - Using Authentic Architecture
Based on the original SincNet implementation with proper model reconstruction
"""

import logging
import torch
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Union, Tuple, List
import configparser

from .original_sincnet_model import OriginalSincNetModel, create_config_from_cfg
from .audio_processor import AudioProcessor
from .model_manager import get_model_manager

logger = logging.getLogger(__name__)


class OriginalSincNetAnalyzer:
    """SincNet Analyzer using the original authentic architecture"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configuration for both models (from original .cfg files)
        self.model_configs = {
            'depression': {
                # Windowing - 200ms windows at 16kHz
                'input_dim': 3200,  # 200ms * 16kHz / 1000
                'fs': 16000,
                
                # CNN - 3 layers [80, 60, 60] filters
                'cnn_N_filt': [80, 60, 60],
                'cnn_len_filt': [251, 5, 5],
                'cnn_max_pool_len': [3, 3, 3],
                'cnn_use_laynorm_inp': True,
                'cnn_use_batchnorm_inp': False,
                'cnn_use_laynorm': [True, True, True],
                'cnn_use_batchnorm': [False, False, False],
                'cnn_act': ['leaky_relu', 'leaky_relu', 'leaky_relu'],
                'cnn_drop': [0.0, 0.0, 0.0],
                
                # DNN - 3 layers of 2048 neurons
                'fc_lay': [2048, 2048, 2048],
                'fc_drop': [0.0, 0.0, 0.0],
                'fc_use_laynorm_inp': True,
                'fc_use_batchnorm_inp': False,
                'fc_use_batchnorm': [True, True, True],
                'fc_use_laynorm': [False, False, False],
                'fc_act': ['leaky_relu', 'leaky_relu', 'leaky_relu'],
                
                # Classifier - 2-class output
                'class_lay': 2,
                'class_drop': 0.0,
                'class_use_laynorm_inp': False,
                'class_use_batchnorm_inp': False,
                'class_use_batchnorm': False,
                'class_use_laynorm': False,
                'class_act': 'softmax'
            },
            'insomnia': {
                # Same configuration as depression (both use same architecture)
                'input_dim': 3200,
                'fs': 16000,
                'cnn_N_filt': [80, 60, 60],
                'cnn_len_filt': [251, 5, 5],
                'cnn_max_pool_len': [3, 3, 3],
                'cnn_use_laynorm_inp': True,
                'cnn_use_batchnorm_inp': False,
                'cnn_use_laynorm': [True, True, True],
                'cnn_use_batchnorm': [False, False, False],
                'cnn_act': ['leaky_relu', 'leaky_relu', 'leaky_relu'],
                'cnn_drop': [0.0, 0.0, 0.0],
                'fc_lay': [2048, 2048, 2048],
                'fc_drop': [0.0, 0.0, 0.0],
                'fc_use_laynorm_inp': True,
                'fc_use_batchnorm_inp': False,
                'fc_use_batchnorm': [True, True, True],
                'fc_use_laynorm': [False, False, False],
                'fc_act': ['leaky_relu', 'leaky_relu', 'leaky_relu'],
                'class_lay': 2,
                'class_drop': 0.0,
                'class_use_laynorm_inp': False,
                'class_use_batchnorm_inp': False,
                'class_use_batchnorm': False,
                'class_use_laynorm': False,
                'class_act': 'softmax'
            }
        }
        
        # Audio processor with correct window size
        self.audio_processor = AudioProcessor()
        
        # Model manager for loading checkpoints
        self.model_manager = get_model_manager()
        
        # Models and loaded states
        self.models = {}
        self.model_loaded = {}
        
        # Load both models
        self._load_all_models()
    
    def _load_all_models(self):
        """Load both depression and insomnia models with original architecture"""
        
        model_types = ['depression', 'insomnia']
        
        for model_type in model_types:
            try:
                self.logger.info(f"Loading {model_type} model with original SincNet architecture...")
                
                # Load checkpoint from model manager
                checkpoint = self.model_manager.load_model(model_type)
                if checkpoint is None:
                    self.logger.error(f"Failed to load {model_type} checkpoint")
                    self.model_loaded[model_type] = False
                    continue
                
                # Create model with original architecture
                config = self.model_configs[model_type]
                model = OriginalSincNetModel(config)
                
                # Load weights from checkpoint
                success = self._load_weights_from_checkpoint(model, checkpoint, model_type)
                
                if success:
                    model.eval()
                    self.models[model_type] = model
                    self.model_loaded[model_type] = True
                    self.logger.info(f"✓ {model_type} model loaded successfully")
                    
                    # Log architecture details
                    self.logger.info(f"  CNN: {config['cnn_N_filt']} filters, {config['cnn_len_filt']} kernel sizes")
                    self.logger.info(f"  DNN: {config['fc_lay']} neurons")
                    self.logger.info(f"  Input: {config['input_dim']} samples (200ms at {config['fs']}Hz)")
                else:
                    self.model_loaded[model_type] = False
                    self.logger.error(f"Failed to load weights for {model_type}")
                    
            except Exception as e:
                self.logger.error(f"Error loading {model_type} model: {str(e)}")
                self.model_loaded[model_type] = False
    
    def _load_weights_from_checkpoint(self, model: OriginalSincNetModel, 
                                    checkpoint: Dict, model_type: str) -> bool:
        """Load weights from checkpoint into the original model architecture"""
        try:
            # Get the parameter dictionaries from checkpoint
            cnn_params = checkpoint.get('CNN_model_par', {})
            dnn1_params = checkpoint.get('DNN1_model_par', {})
            dnn2_params = checkpoint.get('DNN2_model_par', {})
            
            if not cnn_params or not dnn1_params or not dnn2_params:
                self.logger.error(f"Missing parameter dictionaries in {model_type} checkpoint")
                return False
            
            # Load CNN parameters
            self._load_cnn_weights(model.cnn, cnn_params)
            
            # Load DNN parameters (DNN1 = main DNN, DNN2 = classifier)
            self._load_dnn_weights(model.dnn, dnn1_params, 'DNN1')
            self._load_dnn_weights(model.classifier, dnn2_params, 'DNN2')
            
            self.logger.info(f"Successfully loaded all weights for {model_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading weights for {model_type}: {str(e)}")
            return False
    
    def _load_cnn_weights(self, cnn_model, cnn_params):
        """Load CNN weights including SincConv parameters"""
        try:
            state_dict = {}
            
            for param_name, param_tensor in cnn_params.items():
                # Map parameter names from checkpoint to model
                if param_name.startswith('conv.0.'):
                    # SincConv layer (first layer)
                    mapped_name = param_name.replace('conv.0.', 'conv.0.')
                elif param_name.startswith('conv.1.') or param_name.startswith('conv.2.'):
                    # Regular conv layers
                    mapped_name = param_name
                elif param_name.startswith('ln'):
                    # Layer normalization
                    mapped_name = param_name
                elif param_name.startswith('bn'):
                    # Batch normalization
                    mapped_name = param_name
                else:
                    mapped_name = param_name
                
                state_dict[mapped_name] = param_tensor
            
            # Load the state dict
            cnn_model.load_state_dict(state_dict, strict=False)
            self.logger.debug("CNN weights loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading CNN weights: {str(e)}")
            raise
    
    def _load_dnn_weights(self, dnn_model, dnn_params, layer_name):
        """Load DNN weights with proper mapping"""
        try:
            state_dict = {}
            
            for param_name, param_tensor in dnn_params.items():
                # Map parameter names
                if param_name.startswith('wx.'):
                    # Linear layer weights
                    mapped_name = param_name
                elif param_name.startswith('ln'):
                    # Layer normalization
                    mapped_name = param_name
                elif param_name.startswith('bn'):
                    # Batch normalization
                    mapped_name = param_name
                else:
                    mapped_name = param_name
                
                state_dict[mapped_name] = param_tensor
            
            # Load the state dict
            dnn_model.load_state_dict(state_dict, strict=False)
            self.logger.debug(f"{layer_name} weights loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading {layer_name} weights: {str(e)}")
            raise
    
    def analyze_audio(self, audio_path: Union[str, Path]) -> Dict:
        """
        Analyze audio file using original SincNet architecture
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Analysis results with depression and insomnia scores
        """
        try:
            if not any(self.model_loaded.values()):
                raise RuntimeError("No models loaded successfully")
            
            # Process audio with correct 200ms windows (3200 samples)
            audio_windows, audio_info = self.audio_processor.process_any_audio(
                audio_path,
                model_window_size=3200,  # 200ms at 16kHz
                overlap=0.5
            )
            
            if audio_windows is None:
                raise RuntimeError("Audio processing failed")
            
            # Apply proper normalization (zero mean, unit variance)
            # This is critical for SincNet
            audio_windows = self._normalize_audio(audio_windows)
            
            self.logger.info(f"Processing {len(audio_windows)} windows of 3200 samples each")
            self.logger.info(f"Audio stats: mean={audio_windows.mean():.6f}, std={audio_windows.std():.6f}")
            self.logger.info(f"Audio range: [{audio_windows.min():.6f}, {audio_windows.max():.6f}]")
            
            # Run inference on all loaded models
            results = {}
            
            for model_type in ['depression', 'insomnia']:
                if self.model_loaded[model_type]:
                    try:
                        result = self._run_model_inference(
                            self.models[model_type], 
                            audio_windows, 
                            model_type,
                            audio_info
                        )
                        results[model_type] = result
                        
                    except Exception as e:
                        self.logger.error(f"Inference failed for {model_type}: {str(e)}")
                        results[model_type] = {'error': str(e)}
                else:
                    self.logger.warning(f"{model_type} model not loaded")
                    results[model_type] = {'error': 'Model not loaded'}
            
            # Generate final result
            return self._generate_final_result(results, audio_path)
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'analysis_failed': True,
                'audio_path': str(audio_path)
            }
    
    def _normalize_audio(self, audio_tensor: torch.Tensor) -> torch.Tensor:
        """
        Apply proper normalization for SincNet
        Zero mean and unit variance normalization
        """
        # Calculate mean and std across all dimensions
        mean = audio_tensor.mean()
        std = audio_tensor.std()
        
        # Apply normalization with epsilon for stability
        normalized = (audio_tensor - mean) / (std + 1e-8)
        
        self.logger.debug(f"Normalization: mean={mean:.6f}, std={std:.6f}")
        self.logger.debug(f"After norm: mean={normalized.mean():.6f}, std={normalized.std():.6f}")
        
        return normalized
    
    def _run_model_inference(self, model: OriginalSincNetModel, 
                           audio_windows: torch.Tensor, 
                           model_type: str, 
                           audio_info: Dict) -> Dict:
        """Run inference on a single model"""
        
        with torch.no_grad():
            # Ensure proper input shape for SincNet: [batch_size, sequence_length]
            # The original SincNet expects [batch, seq_len] and reshapes internally to [batch, 1, seq_len]
            if audio_windows.dim() == 3 and audio_windows.shape[1] == 1:
                # Shape is [batch, 1, seq_len] - squeeze the channel dimension
                audio_windows = audio_windows.squeeze(1)
            
            self.logger.info(f"{model_type} input shape: {audio_windows.shape}")
            
            # Forward pass
            outputs = model(audio_windows)
            
            self.logger.info(f"{model_type} raw outputs: {outputs}")
            self.logger.info(f"{model_type} output shape: {outputs.shape}")
            self.logger.info(f"{model_type} output range: [{outputs.min():.6f}, {outputs.max():.6f}]")
            
            # Apply softmax to get probabilities (if not already applied)
            if model.config['class_act'] != 'softmax':
                probs = torch.softmax(outputs, dim=1)
            else:
                # LogSoftmax was applied, convert to probabilities
                probs = torch.exp(outputs)
            
            # Extract positive class probabilities
            positive_probs = probs[:, 1] if probs.shape[1] > 1 else probs[:, 0]
            
            self.logger.info(f"{model_type} probabilities: {positive_probs}")
            
            # Aggregate results
            result = self._aggregate_predictions(positive_probs, model_type, audio_info)
            
            # Add raw output information for debugging
            result['raw_outputs'] = {
                'logits': outputs.tolist(),
                'probabilities': probs.tolist(),
                'positive_probs': positive_probs.tolist()
            }
            
            return result
    
    def _aggregate_predictions(self, positive_probs: torch.Tensor, 
                             model_type: str, audio_info: Dict) -> Dict:
        """Aggregate predictions across windows"""
        
        # Multiple aggregation strategies
        aggregation = {
            'mean': positive_probs.mean().item(),
            'std': positive_probs.std().item(),
            'max': positive_probs.max().item(),
            'min': positive_probs.min().item(),
            'median': positive_probs.median().item(),
        }
        
        # Final score (0-10 scale)
        final_score = aggregation['mean'] * 10
        
        # Calculate confidence based on consistency
        confidence = max(0.3, min(0.95, 1 - aggregation['std']))
        
        return {
            'score': final_score,
            'confidence': confidence,
            'aggregation': aggregation,
            'n_windows': len(positive_probs),
            'window_scores': positive_probs.tolist(),
            'audio_duration': audio_info.get('duration', 0)
        }
    
    def _generate_final_result(self, results: Dict, audio_path: Union[str, Path]) -> Dict:
        """Generate final analysis result"""
        
        final_result = {
            'audio_path': str(audio_path),
            'analysis_method': 'original_sincnet_v5',
            'window_size_ms': 200,
            'window_samples': 3200,
            'sampling_rate': 16000,
            'models_loaded': {k: v for k, v in self.model_loaded.items()},
            'successful_analyses': len([r for r in results.values() if 'error' not in r])
        }
        
        # Add individual model results
        for model_type, result in results.items():
            if 'error' not in result:
                final_result[model_type] = {
                    'score': float(np.clip(result['score'], 0, 10)),
                    'level': self._score_to_level(result['score']),
                    'confidence': result['confidence'],
                    'n_windows': result['n_windows'],
                    'aggregation_details': result['aggregation']
                }
                
                # Include raw outputs for debugging
                if 'raw_outputs' in result:
                    final_result[model_type]['raw_outputs'] = result['raw_outputs']
        
        # Calculate derived metrics if both models succeeded
        if 'depression' in final_result and 'insomnia' in final_result:
            if isinstance(final_result['depression'], dict) and isinstance(final_result['insomnia'], dict):
                dep_score = final_result['depression']['score']
                ins_score = final_result['insomnia']['score']
                
                # Anxiety (combination of depression and insomnia)
                anxiety_score = dep_score * 0.6 + ins_score * 0.4
                final_result['anxiety'] = {
                    'score': float(anxiety_score),
                    'level': self._score_to_level(anxiety_score),
                    'confidence': (final_result['depression']['confidence'] * 0.6 + 
                                 final_result['insomnia']['confidence'] * 0.4),
                    'derived': True
                }
                
                # Overall risk
                overall_risk = np.mean([dep_score, ins_score, anxiety_score])
                final_result['overall'] = {
                    'risk_score': float(overall_risk),
                    'risk_level': self._risk_to_level(overall_risk),
                    'confidence': np.mean([final_result['depression']['confidence'],
                                         final_result['insomnia']['confidence']])
                }
        
        return final_result
    
    def _score_to_level(self, score: float) -> str:
        """Convert score to level"""
        if score < 3:
            return 'normal'
        elif score < 5:
            return 'mild'
        elif score < 7:
            return 'moderate'
        else:
            return 'severe'
    
    def _risk_to_level(self, risk: float) -> str:
        """Convert risk score to level"""
        if risk < 3:
            return 'low'
        elif risk < 5:
            return 'medium'
        elif risk < 7:
            return 'high'
        else:
            return 'critical'
    
    def get_model_info(self) -> Dict:
        """Get information about loaded models"""
        return {
            'models_loaded': self.model_loaded,
            'architecture': 'original_sincnet',
            'window_size': '200ms (3200 samples)',
            'sampling_rate': '16kHz',
            'cnn_layers': '3 layers [80, 60, 60] filters',
            'dnn_layers': '3 layers [2048, 2048, 2048] neurons',
            'normalization': 'Layer normalization + zero mean/unit variance'
        }