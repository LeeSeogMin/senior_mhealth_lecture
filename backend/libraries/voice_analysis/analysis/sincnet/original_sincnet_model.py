"""
Original SincNet Model Implementation
Based on the authentic SincNet architecture from the original repository
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def act_fun(act_type):
    """Activation function factory"""
    if act_type == "relu":
        return nn.ReLU()
    if act_type == "tanh":
        return nn.Tanh()
    if act_type == "sigmoid":
        return nn.Sigmoid()
    if act_type == "leaky_relu":
        return nn.LeakyReLU(0.2)
    if act_type == "elu":
        return nn.ELU()
    if act_type == "softmax":
        return nn.LogSoftmax(dim=1)
    if act_type == "linear":
        return nn.LeakyReLU(1)  # initialized like this, but not used in forward!


class LayerNorm(nn.Module):
    """Custom Layer Normalization"""
    def __init__(self, features, eps=1e-6):
        super(LayerNorm, self).__init__()
        self.gamma = nn.Parameter(torch.ones(features))
        self.beta = nn.Parameter(torch.zeros(features))
        self.eps = eps

    def forward(self, x):
        mean = x.mean(-1, keepdim=True)
        std = x.std(-1, keepdim=True)
        return self.gamma * (x - mean) / (std + self.eps) + self.beta


class SincConv_fast(nn.Module):
    """
    Sinc-based convolution - Original implementation
    From: Speaker Recognition from raw waveform with SincNet
    """

    @staticmethod
    def to_mel(hz):
        return 2595 * np.log10(1 + hz / 700)

    @staticmethod
    def to_hz(mel):
        return 700 * (10 ** (mel / 2595) - 1)

    def __init__(self, out_channels, kernel_size, sample_rate=16000, in_channels=1,
                 stride=1, padding=0, dilation=1, bias=False, groups=1, 
                 min_low_hz=50, min_band_hz=50):
        
        super(SincConv_fast, self).__init__()

        if in_channels != 1:
            msg = "SincConv only support one input channel (here, in_channels = {%i})" % (in_channels)
            raise ValueError(msg)

        self.out_channels = out_channels
        self.kernel_size = kernel_size
        
        # Forcing the filters to be odd (i.e, perfectly symmetrics)
        if kernel_size % 2 == 0:
            self.kernel_size = self.kernel_size + 1
            
        self.stride = stride
        self.padding = padding
        self.dilation = dilation

        if bias:
            raise ValueError('SincConv does not support bias.')
        if groups > 1:
            raise ValueError('SincConv does not support groups.')

        self.sample_rate = sample_rate
        self.min_low_hz = min_low_hz
        self.min_band_hz = min_band_hz

        # initialize filterbanks such that they are equally spaced in Mel scale
        low_hz = 30
        high_hz = self.sample_rate / 2 - (self.min_low_hz + self.min_band_hz)

        mel = np.linspace(self.to_mel(low_hz),
                          self.to_mel(high_hz),
                          self.out_channels + 1)
        hz = self.to_hz(mel)

        # filter lower frequency (out_channels, 1)
        self.low_hz_ = nn.Parameter(torch.Tensor(hz[:-1]).view(-1, 1))

        # filter frequency band (out_channels, 1)
        self.band_hz_ = nn.Parameter(torch.Tensor(np.diff(hz)).view(-1, 1))

        # Hamming window
        n_lin = torch.linspace(0, (self.kernel_size/2)-1, 
                              steps=int((self.kernel_size/2)))
        self.window_ = 0.54 - 0.46 * torch.cos(2*math.pi*n_lin/self.kernel_size)

        # (1, kernel_size/2)
        n = (self.kernel_size - 1) / 2.0
        self.n_ = 2*math.pi*torch.arange(-n, 0).view(1, -1) / self.sample_rate

    def forward(self, waveforms):
        """
        Parameters
        ----------
        waveforms : `torch.Tensor` (batch_size, 1, n_samples)
            Batch of waveforms.
        Returns
        -------
        features : `torch.Tensor` (batch_size, out_channels, n_samples_out)
            Batch of sinc filters activations.
        """
        self.n_ = self.n_.to(waveforms.device)
        self.window_ = self.window_.to(waveforms.device)

        low = self.min_low_hz + torch.abs(self.low_hz_)
        high = torch.clamp(low + self.min_band_hz + torch.abs(self.band_hz_),
                          self.min_low_hz, self.sample_rate/2)
        band = (high - low)[:, 0]
        
        f_times_t_low = torch.matmul(low, self.n_)
        f_times_t_high = torch.matmul(high, self.n_)

        # Equivalent of Eq.4 of the reference paper
        band_pass_left = ((torch.sin(f_times_t_high) - torch.sin(f_times_t_low)) / 
                         (self.n_/2)) * self.window_
        band_pass_center = 2 * band.view(-1, 1)
        band_pass_right = torch.flip(band_pass_left, dims=[1])
        
        band_pass = torch.cat([band_pass_left, band_pass_center, band_pass_right], dim=1)
        band_pass = band_pass / (2 * band[:, None])

        self.filters = band_pass.view(self.out_channels, 1, self.kernel_size)

        return F.conv1d(waveforms, self.filters, stride=self.stride,
                       padding=self.padding, dilation=self.dilation,
                       bias=None, groups=1)


class MLP(nn.Module):
    """Multi-Layer Perceptron with Layer/Batch Normalization"""
    
    def __init__(self, options):
        super(MLP, self).__init__()
        self.input_dim = int(options['input_dim'])
        self.fc_lay = options['fc_lay']
        self.fc_drop = options['fc_drop']
        self.fc_use_batchnorm = options['fc_use_batchnorm']
        self.fc_use_laynorm = options['fc_use_laynorm']
        self.fc_use_laynorm_inp = options['fc_use_laynorm_inp']
        self.fc_use_batchnorm_inp = options['fc_use_batchnorm_inp']
        self.fc_act = options['fc_act']

        self.wx = nn.ModuleList([])
        self.bn = nn.ModuleList([])
        self.ln = nn.ModuleList([])
        self.act = nn.ModuleList([])
        self.drop = nn.ModuleList([])
        
        # input layer normalization
        if self.fc_use_laynorm_inp:
            self.ln0 = LayerNorm(self.input_dim)
            
        # input batch normalization    
        if self.fc_use_batchnorm_inp:
            self.bn0 = nn.BatchNorm1d([self.input_dim], momentum=0.05)
            
        self.N_fc_lay = len(self.fc_lay)
        current_input = self.input_dim
        
        # Initialization of hidden layers
        for i in range(self.N_fc_lay):
            # dropout
            self.drop.append(nn.Dropout(p=self.fc_drop[i]))
            # activation
            self.act.append(act_fun(self.fc_act[i]))
            
            add_bias = True
            
            # layer norm initialization
            self.ln.append(LayerNorm(self.fc_lay[i]))
            self.bn.append(nn.BatchNorm1d(self.fc_lay[i], momentum=0.05))
            
            if self.fc_use_laynorm[i] or self.fc_use_batchnorm[i]:
                add_bias = False
            
            # Linear operations
            self.wx.append(nn.Linear(current_input, self.fc_lay[i], bias=add_bias))
            
            # weight initialization
            self.wx[i].weight = torch.nn.Parameter(
                torch.Tensor(self.fc_lay[i], current_input).uniform_(
                    -np.sqrt(0.01/(current_input+self.fc_lay[i])),
                    np.sqrt(0.01/(current_input+self.fc_lay[i]))
                )
            )
            self.wx[i].bias = torch.nn.Parameter(torch.zeros(self.fc_lay[i]))
            
            current_input = self.fc_lay[i]

    def forward(self, x):
        # Applying Layer/Batch Norm
        if bool(self.fc_use_laynorm_inp):
            x = self.ln0(x)
            
        if bool(self.fc_use_batchnorm_inp):
            x = self.bn0(x)

        for i in range(self.N_fc_lay):
            if self.fc_act[i] != 'linear':
                if self.fc_use_laynorm[i]:
                    x = self.drop[i](self.act[i](self.ln[i](self.wx[i](x))))
                
                if self.fc_use_batchnorm[i]:
                    x = self.drop[i](self.act[i](self.bn[i](self.wx[i](x))))
                
                if self.fc_use_batchnorm[i] == False and self.fc_use_laynorm[i] == False:
                    x = self.drop[i](self.act[i](self.wx[i](x)))
                    
            else:
                if self.fc_use_laynorm[i]:
                    x = self.drop[i](self.ln[i](self.wx[i](x)))
                
                if self.fc_use_batchnorm[i]:
                    x = self.drop[i](self.bn[i](self.wx[i](x)))
                
                if self.fc_use_batchnorm[i] == False and self.fc_use_laynorm[i] == False:
                    x = self.drop[i](self.wx[i](x))

        return x


class SincNet(nn.Module):
    """Original SincNet CNN implementation"""
    
    def __init__(self, options):
        super(SincNet, self).__init__()
        self.cnn_N_filt = options['cnn_N_filt']
        self.cnn_len_filt = options['cnn_len_filt']
        self.cnn_max_pool_len = options['cnn_max_pool_len']
        
        self.cnn_act = options['cnn_act']
        self.cnn_drop = options['cnn_drop']
        
        self.cnn_use_laynorm = options['cnn_use_laynorm']
        self.cnn_use_batchnorm = options['cnn_use_batchnorm']
        self.cnn_use_laynorm_inp = options['cnn_use_laynorm_inp']
        self.cnn_use_batchnorm_inp = options['cnn_use_batchnorm_inp']
        
        self.input_dim = int(options['input_dim'])
        self.fs = options['fs']
        
        self.N_cnn_lay = len(options['cnn_N_filt'])
        self.conv = nn.ModuleList([])
        self.bn = nn.ModuleList([])
        self.ln = nn.ModuleList([])
        self.act = nn.ModuleList([])
        self.drop = nn.ModuleList([])
                
        if self.cnn_use_laynorm_inp:
            self.ln0 = LayerNorm(self.input_dim)
            
        if self.cnn_use_batchnorm_inp:
            self.bn0 = nn.BatchNorm1d([self.input_dim], momentum=0.05)
            
        current_input = self.input_dim
        
        for i in range(self.N_cnn_lay):
            N_filt = int(self.cnn_N_filt[i])
            len_filt = int(self.cnn_len_filt[i])
            
            # dropout
            self.drop.append(nn.Dropout(p=self.cnn_drop[i]))
            
            # activation
            self.act.append(act_fun(self.cnn_act[i]))
                        
            # layer norm initialization         
            output_len = int((current_input - self.cnn_len_filt[i] + 1) / self.cnn_max_pool_len[i])
            self.ln.append(LayerNorm([N_filt, output_len]))
            self.bn.append(nn.BatchNorm1d(N_filt, momentum=0.05))
            
            if i == 0:
                self.conv.append(SincConv_fast(self.cnn_N_filt[0], self.cnn_len_filt[0], self.fs))
            else:
                self.conv.append(nn.Conv1d(self.cnn_N_filt[i-1], self.cnn_N_filt[i], self.cnn_len_filt[i]))
            
            current_input = output_len
            
        self.out_dim = current_input * N_filt

    def forward(self, x):
        batch = x.shape[0]
        seq_len = x.shape[1]
        
        if bool(self.cnn_use_laynorm_inp):
            x = self.ln0(x)
            
        if bool(self.cnn_use_batchnorm_inp):
            x = self.bn0(x)

        x = x.view(batch, 1, seq_len)
        
        for i in range(self.N_cnn_lay):
            if self.cnn_use_laynorm[i]:
                if i == 0:
                    x = self.drop[i](self.act[i](self.ln[i](F.max_pool1d(torch.abs(self.conv[i](x)), self.cnn_max_pool_len[i]))))
                else:
                    x = self.drop[i](self.act[i](self.ln[i](F.max_pool1d(self.conv[i](x), self.cnn_max_pool_len[i]))))
            
            if self.cnn_use_batchnorm[i]:
                x = self.drop[i](self.act[i](self.bn[i](F.max_pool1d(self.conv[i](x), self.cnn_max_pool_len[i]))))

            if self.cnn_use_batchnorm[i] == False and self.cnn_use_laynorm[i] == False:
                x = self.drop[i](self.act[i](F.max_pool1d(self.conv[i](x), self.cnn_max_pool_len[i])))
        
        x = x.view(batch, -1)
        return x


class OriginalSincNetModel(nn.Module):
    """Complete original SincNet model with CNN + DNN + Classifier"""
    
    def __init__(self, config_dict: Dict):
        super(OriginalSincNetModel, self).__init__()
        
        # CNN options
        cnn_options = {
            'input_dim': config_dict['input_dim'],  # 3200 for 200ms windows
            'fs': config_dict['fs'],  # 16000
            'cnn_N_filt': config_dict['cnn_N_filt'],  # [80, 60, 60]
            'cnn_len_filt': config_dict['cnn_len_filt'],  # [251, 5, 5]
            'cnn_max_pool_len': config_dict['cnn_max_pool_len'],  # [3, 3, 3]
            'cnn_use_laynorm_inp': config_dict['cnn_use_laynorm_inp'],  # True
            'cnn_use_batchnorm_inp': config_dict['cnn_use_batchnorm_inp'],  # False
            'cnn_use_laynorm': config_dict['cnn_use_laynorm'],  # [True, True, True]
            'cnn_use_batchnorm': config_dict['cnn_use_batchnorm'],  # [False, False, False]
            'cnn_act': config_dict['cnn_act'],  # ['leaky_relu', 'leaky_relu', 'leaky_relu']
            'cnn_drop': config_dict['cnn_drop']  # [0.0, 0.0, 0.0]
        }
        
        # Initialize CNN
        self.cnn = SincNet(cnn_options)
        
        # DNN options
        dnn_options = {
            'input_dim': self.cnn.out_dim,
            'fc_lay': config_dict['fc_lay'],  # [2048, 2048, 2048]
            'fc_drop': config_dict['fc_drop'],  # [0.0, 0.0, 0.0]
            'fc_use_laynorm_inp': config_dict['fc_use_laynorm_inp'],  # True
            'fc_use_batchnorm_inp': config_dict['fc_use_batchnorm_inp'],  # False
            'fc_use_batchnorm': config_dict['fc_use_batchnorm'],  # [True, True, True]
            'fc_use_laynorm': config_dict['fc_use_laynorm'],  # [False, False, False]
            'fc_act': config_dict['fc_act']  # ['leaky_relu', 'leaky_relu', 'leaky_relu']
        }
        
        # Initialize DNN
        self.dnn = MLP(dnn_options)
        
        # Classifier
        class_options = {
            'input_dim': config_dict['fc_lay'][-1],  # 2048
            'fc_lay': [config_dict['class_lay']],  # [2]
            'fc_drop': [config_dict['class_drop']],  # [0.0]
            'fc_use_laynorm_inp': config_dict['class_use_laynorm_inp'],  # False
            'fc_use_batchnorm_inp': config_dict['class_use_batchnorm_inp'],  # False
            'fc_use_batchnorm': [config_dict['class_use_batchnorm']],  # [False]
            'fc_use_laynorm': [config_dict['class_use_laynorm']],  # [False]
            'fc_act': [config_dict['class_act']]  # ['softmax']
        }
        
        # Initialize classifier
        self.classifier = MLP(class_options)
        
        # Store config for reference
        self.config = config_dict
        
    def forward(self, x):
        """
        Forward pass through the complete model
        
        Args:
            x: Input tensor [batch_size, seq_len] where seq_len=3200 for 200ms
            
        Returns:
            Output probabilities [batch_size, num_classes]
        """
        # CNN feature extraction
        cnn_out = self.cnn(x)
        
        # DNN processing
        dnn_out = self.dnn(cnn_out)
        
        # Classification
        class_out = self.classifier(dnn_out)
        
        return class_out


def create_config_from_cfg(cfg_data: Dict) -> Dict:
    """Convert configuration dictionary to model config"""
    config = {
        # Windowing
        'input_dim': int(cfg_data['windowing']['cw_len']) * int(cfg_data['windowing']['fs']) // 1000,  # 200ms * 16kHz / 1000 = 3200
        'fs': int(cfg_data['windowing']['fs']),
        
        # CNN
        'cnn_N_filt': [int(x) for x in cfg_data['cnn']['cnn_N_filt'].split(',')],
        'cnn_len_filt': [int(x) for x in cfg_data['cnn']['cnn_len_filt'].split(',')],
        'cnn_max_pool_len': [int(x) for x in cfg_data['cnn']['cnn_max_pool_len'].split(',')],
        'cnn_use_laynorm_inp': cfg_data['cnn']['cnn_use_laynorm_inp'] == 'True',
        'cnn_use_batchnorm_inp': cfg_data['cnn']['cnn_use_batchnorm_inp'] == 'True',
        'cnn_use_laynorm': [x == 'True' for x in cfg_data['cnn']['cnn_use_laynorm'].split(',')],
        'cnn_use_batchnorm': [x == 'True' for x in cfg_data['cnn']['cnn_use_batchnorm'].split(',')],
        'cnn_act': cfg_data['cnn']['cnn_act'].split(','),
        'cnn_drop': [float(x) for x in cfg_data['cnn']['cnn_drop'].split(',')],
        
        # DNN
        'fc_lay': [int(x) for x in cfg_data['dnn']['fc_lay'].split(',')],
        'fc_drop': [float(x) for x in cfg_data['dnn']['fc_drop'].split(',')],
        'fc_use_laynorm_inp': cfg_data['dnn']['fc_use_laynorm_inp'] == 'True',
        'fc_use_batchnorm_inp': cfg_data['dnn']['fc_use_batchnorm_inp'] == 'True',
        'fc_use_batchnorm': [x == 'True' for x in cfg_data['dnn']['fc_use_batchnorm'].split(',')],
        'fc_use_laynorm': [x == 'True' for x in cfg_data['dnn']['fc_use_laynorm'].split(',')],
        'fc_act': cfg_data['dnn']['fc_act'].split(','),
        
        # Classifier
        'class_lay': int(cfg_data['class']['class_lay']),
        'class_drop': float(cfg_data['class']['class_drop']),
        'class_use_laynorm_inp': cfg_data['class']['class_use_laynorm_inp'] == 'True',
        'class_use_batchnorm_inp': cfg_data['class']['class_use_batchnorm_inp'] == 'True',
        'class_use_batchnorm': cfg_data['class']['class_use_batchnorm'] == 'True',
        'class_use_laynorm': cfg_data['class']['class_use_laynorm'] == 'True',
        'class_act': cfg_data['class']['class_act']
    }
    
    return config