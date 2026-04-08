"""
NILM Signal Processing - Feature extraction from power signals
"""

import numpy as np
import pandas as pd
from scipy.fft import fft
import logging

logger = logging.getLogger(__name__)

class NILMSignalProcessor:
    """Extract 22 features from power signals for NILM"""
    
    def __init__(self, sampling_rate=6):
        self.sampling_rate = sampling_rate
    
    def extract_features(self, power_series, window_size=10):
        """
        Extract 22 comprehensive features from power signal
        """
        features = []
        
        for i in range(len(power_series) - window_size + 1):
            window = power_series[i:i+window_size]
            features.append(self._extract_window_features(window, i))
        
        return pd.DataFrame(features)
    
    def _extract_window_features(self, window, position):
        """
        Extract ALL 22 features from a single window
        """
        window = np.array(window, dtype=float)
        
        # ===== 1. Basic Statistics (8 features) =====
        mean_power = float(np.mean(window))
        std_power = float(np.std(window))
        max_power = float(np.max(window))
        min_power = float(np.min(window))
        median_power = float(np.median(window))
        power_range = max_power - min_power
        power_variance = float(np.var(window))
        
        # Skew (with safe calculation)
        if len(window) > 1 and np.std(window) > 0:
            power_skew = float(pd.Series(window).skew())
        else:
            power_skew = 0.0
        
        # ===== 2. Edge Detection (4 features) =====
        edges = np.diff(window)
        positive_edges = int(np.sum(edges > 50))      # Appliance turned ON
        negative_edges = int(np.sum(edges < -50))     # Appliance turned OFF
        net_edges = positive_edges - negative_edges
        max_edge = float(np.max(np.abs(edges))) if len(edges) > 0 else 0
        
        # ===== 3. Harmonic Analysis (5 features) =====
        fft_vals = fft(window)
        magnitudes = np.abs(fft_vals[:len(fft_vals)//2])
        
        fundamental = float(magnitudes[1]) if len(magnitudes) > 1 else 0
        harmonic_3 = float(magnitudes[3]) if len(magnitudes) > 3 else 0
        harmonic_5 = float(magnitudes[5]) if len(magnitudes) > 5 else 0
        total_harmonic = float(np.sum(magnitudes[1:]))
        harmonic_ratio = harmonic_3 / (fundamental + 0.01)
        
        # ===== 4. Power Quality (3 features) =====
        crest_factor = max_power / (mean_power + 0.01)
        form_factor = float(np.sqrt(np.mean(window**2))) / (mean_power + 0.01)
        rate_of_change = float(np.mean(np.abs(edges))) if len(edges) > 0 else 0
        
        # ===== 5. Steady State (1 feature) =====
        is_steady = 1 if (std_power / (mean_power + 0.01) < 0.1) else 0
        
        # ===== 6. Time Context (1 feature) =====
        time_of_day = position % 24
        
        # ===== RETURN ALL 22 FEATURES =====
        return {
            # Statistical (8)
            'mean_power': mean_power,
            'std_power': std_power,
            'max_power': max_power,
            'min_power': min_power,
            'median_power': median_power,
            'power_range': power_range,
            'power_variance': power_variance,
            'power_skew': power_skew,
            
            # Edge (4)
            'positive_edges': positive_edges,
            'negative_edges': negative_edges,
            'net_edges': net_edges,
            'max_edge': max_edge,
            
            # Harmonic (5)
            'fundamental': fundamental,
            'harmonic_3': harmonic_3,
            'harmonic_5': harmonic_5,
            'total_harmonic': total_harmonic,
            'harmonic_ratio': harmonic_ratio,
            
            # Power Quality (3)
            'crest_factor': crest_factor,
            'form_factor': form_factor,
            'rate_of_change': rate_of_change,
            
            # Steady State (1)
            'steady_state': is_steady,
            
            # Time Context (1)
            'time_of_day': time_of_day,
        }
    
    def get_feature_names(self):
        """Return list of all 22 feature names"""
        return [
            'mean_power', 'std_power', 'max_power', 'min_power', 'median_power',
            'power_range', 'power_variance', 'power_skew',
            'positive_edges', 'negative_edges', 'net_edges', 'max_edge',
            'fundamental', 'harmonic_3', 'harmonic_5', 'total_harmonic', 'harmonic_ratio',
            'crest_factor', 'form_factor', 'rate_of_change',
            'steady_state', 'time_of_day'
        ]

# Global instance
signal_processor = NILMSignalProcessor()