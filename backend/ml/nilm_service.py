"""
NILM Service - Real-time appliance disaggregation
"""

import logging
from collections import deque
import numpy as np
import joblib
from ml.nilm_processor import signal_processor

logger = logging.getLogger(__name__)

class NILMService:
    """Real-time NILM service for appliance disaggregation"""
    
    def __init__(self):
        self.models = {}
        self.scaler = None
        self.processor = signal_processor
        self.power_buffer = deque(maxlen=50)
        
        self.appliance_config = {
            'ac': {'name': 'Air Conditioner', 'icon': 'snow', 'color': '#D1FAE5'},
            'fridge': {'name': 'Refrigerator', 'icon': 'water', 'color': '#FEF3C7'},
            'lights': {'name': 'LED Lights', 'icon': 'bulb', 'color': '#DBEAFE'},
            'washing_machine': {'name': 'Washing Machine', 'icon': 'resize', 'color': '#FCE7F3'},
            'dishwasher': {'name': 'Dishwasher', 'icon': 'water', 'color': '#E0E7FF'},
            'kettle': {'name': 'Electric Kettle', 'icon': 'cafe', 'color': '#FEE2E2'},
            'microwave': {'name': 'Microwave', 'icon': 'flame', 'color': '#FEF9C3'},
            'tv': {'name': 'TV', 'icon': 'tv', 'color': '#E9D5FF'},
            'computer': {'name': 'Computer', 'icon': 'desktop', 'color': '#D9F99D'},
        }
        
        self.load_models()
    
    def load_models(self):
        """Load trained NILM models"""
        try:
            self.scaler = joblib.load('models/nilm/scaler.pkl')
            
            for appliance in self.appliance_config.keys():
                try:
                    model_path = f'models/nilm/{appliance}_model.pkl'
                    self.models[appliance] = joblib.load(model_path)
                    logger.info(f"Loaded {appliance} model")
                except:
                    continue
            
            if self.models:
                logger.info(f"NILM ready with {len(self.models)} models")
        except Exception as e:
            logger.warning(f"No NILM models found: {e}")
    
    def add_reading(self, power):
        self.power_buffer.append(power)
    
    def disaggregate(self, total_power, house_id=None):
        self.add_reading(total_power)
        
        if self.models and self.scaler and len(self.power_buffer) >= 10:
            return self._ml_disaggregate(total_power)
        return self._rule_based_disaggregate(total_power, house_id)
    
    def _ml_disaggregate(self, total_power):
        """ML-based disaggregation"""
        try:
            readings = list(self.power_buffer)
            features_df = self.processor.extract_features(readings)
            
            if features_df.empty:
                return self._rule_based_disaggregate(total_power, None)
            
            X = features_df.iloc[-1:].fillna(0).values.reshape(1, -1)
            X_scaled = self.scaler.transform(X)
            
            results = {}
            predicted_total = 0
            
            for appliance, model in self.models.items():
                pred = float(model.predict(X_scaled)[0])
                pred = max(0, min(pred, total_power))
                results[appliance] = int(pred)
                predicted_total += pred
            
            results['other'] = max(0, int(total_power - predicted_total))
            return results
            
        except Exception as e:
            logger.error(f"ML disaggregation error: {e}")
            return self._rule_based_disaggregate(total_power, None)
    
    def _rule_based_disaggregate(self, total_power, house_id=None):
        """Rule-based fallback"""
        profiles = {
            1: (0.65, 0.15, 0.10),  # Villa
            2: (0.55, 0.20, 0.15),  # Apartment
            3: (0.58, 0.18, 0.14),  # Townhouse
            4: (0.45, 0.25, 0.20),  # Small apt
            5: (0.60, 0.17, 0.13),  # Medium villa
        }
        
        ac_pct, fridge_pct, lights_pct = profiles.get(house_id, (0.50, 0.20, 0.15))
        
        return {
            'ac': int(total_power * ac_pct),
            'fridge': int(total_power * fridge_pct),
            'lights': int(total_power * lights_pct),
            'other': int(total_power * (1 - ac_pct - fridge_pct - lights_pct))
        }
    
    def get_active_appliances(self, min_power=50):
        if not self.power_buffer:
            return []
        
        results = self.disaggregate(self.power_buffer[-1])
        active = []
        
        for key, power in results.items():
            if power >= min_power and key in self.appliance_config:
                cfg = self.appliance_config[key]
                active.append({
                    'key': key,
                    'name': cfg['name'],
                    'power': power,
                    'icon': cfg['icon'],
                    'color': cfg['color']
                })
        
        return sorted(active, key=lambda x: x['power'], reverse=True)

nilm_service = NILMService()