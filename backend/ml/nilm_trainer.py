"""
NILM Training Pipeline - Trains ML models on UK-DALE data
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os
import logging
from datetime import datetime

from data_processing.data_loader import UKDALELoader
from ml.nilm_processor import signal_processor

logger = logging.getLogger(__name__)

class NILMTrainer:
    """
    Train NILM models on UK-DALE data
    """
    
    def __init__(self):
        self.loader = UKDALELoader()
        self.processor = signal_processor
        self.models = {}
        self.scaler = StandardScaler()
        
        # Appliance definitions with typical power ranges
        self.appliances = {
            'ac': {'power_range': (1000, 3500), 'channel_pattern': 'continuous'},
            'fridge': {'power_range': (100, 300), 'channel_pattern': 'cyclic'},
            'washing_machine': {'power_range': (300, 800), 'channel_pattern': 'multistage'},
            'dishwasher': {'power_range': (500, 1500), 'channel_pattern': 'multistage'},
            'kettle': {'power_range': (2000, 3000), 'channel_pattern': 'spike'},
            'microwave': {'power_range': (800, 1500), 'channel_pattern': 'intermittent'},
            'lights': {'power_range': (50, 200), 'channel_pattern': 'evening'},
            'tv': {'power_range': (50, 300), 'channel_pattern': 'evening'},
            'computer': {'power_range': (100, 400), 'channel_pattern': 'evening'},
        }
    
    def prepare_training_data(self, house_id=1, samples=100000):
        """
        Prepare training data from UK-DALE
        """
        logger.info(f"📥 Loading House {house_id} data...")
        df = self.loader.load_house_data(house_id, samples)
        
        if df is None or df.empty:
            logger.error(f"❌ Could not load House {house_id}")
            return None, None
        
        # Add time features
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['minute'] = df['timestamp'].dt.minute
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        # Extract features from power signal
        logger.info("🔧 Extracting features from power signal...")
        features_df = self.processor.extract_features(df['power_watts'].values)
        
        # Create synthetic ground truth (in real implementation, this would come from submeters)
        ground_truth = self._create_synthetic_ground_truth(df)
        
        # Combine features and ground truth
        # Align lengths (features might be shorter due to windowing)
        min_len = min(len(features_df), len(ground_truth))
        features_df = features_df.iloc[:min_len]
        ground_truth = ground_truth.iloc[:min_len]
        
        logger.info(f"✅ Prepared {min_len} training samples with {len(features_df.columns)} features")
        
        return features_df, ground_truth
    
    def _create_synthetic_ground_truth(self, df):
        """
        Create synthetic ground truth for training
        In real implementation, this would come from actual submeter data
        """
        ground_truth = pd.DataFrame()
        power = df['power_watts'].values
        hour = df['hour'].values if 'hour' in df.columns else np.zeros(len(power))
        
        # AC (high power, more common in afternoon)
        ac_power = np.where((power > 1500) & (hour >= 12) & (hour <= 17), 
                           power * np.random.uniform(0.6, 0.8, len(power)), 0)
        ground_truth['ac'] = ac_power
        
        # Fridge (cyclic, 150-300W)
        fridge_base = 150 + 50 * np.sin(np.arange(len(power)) * 0.1)
        fridge_power = np.where(power > 100, fridge_base, 0)
        ground_truth['fridge'] = fridge_power
        
        # Washing Machine (multi-stage pattern)
        wash_pattern = (np.sin(np.arange(len(power)) * 0.05) + 1) * 200
        wash_power = np.where((power > 300) & (wash_pattern > 300), wash_pattern, 0)
        ground_truth['washing_machine'] = wash_power
        
        # Dishwasher
        dish_pattern = (np.sin(np.arange(len(power)) * 0.03) + 1) * 300
        dish_power = np.where((power > 400) & (dish_pattern > 400), dish_pattern, 0)
        ground_truth['dishwasher'] = dish_power
        
        # Kettle (short spikes)
        kettle_power = np.where(power > 2000, power * 0.9, 0)
        ground_truth['kettle'] = kettle_power
        
        # Microwave (medium power, variable)
        micro_power = np.where((power > 800) & (power < 1500), power * 0.8, 0)
        ground_truth['microwave'] = micro_power
        
        # Lights (evening, low power)
        lights_power = np.where((hour >= 18) | (hour <= 5), 100 + 50 * np.random.random(len(power)), 0)
        ground_truth['lights'] = lights_power
        
        # TV (evening, medium-low)
        tv_power = np.where((hour >= 19) | (hour <= 23), 150 + 50 * np.random.random(len(power)), 0)
        ground_truth['tv'] = tv_power
        
        # Computer (evening, medium)
        computer_power = np.where((hour >= 19) | (hour <= 23), 200 + 100 * np.random.random(len(power)), 0)
        ground_truth['computer'] = computer_power
        
        return ground_truth
    
    def train_models(self, X, y, test_size=0.2):
        """
        Train ML models for each appliance
        """
        logger.info("🚀 Training NILM models...")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        results = {}
        
        for appliance in y.columns:
            logger.info(f"🔄 Training model for {appliance}...")
            
            # Choose model based on appliance type
            if appliance in ['ac', 'fridge']:
                model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=15,
                    random_state=42,
                    n_jobs=-1
                )
            elif appliance in ['washing_machine', 'dishwasher']:
                model = GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=8,
                    learning_rate=0.1,
                    random_state=42
                )
            else:
                model = MLPRegressor(
                    hidden_layer_sizes=(64, 32),
                    activation='relu',
                    max_iter=500,
                    random_state=42
                )
            
            # Train
            model.fit(X_train_scaled, y_train[appliance])
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test[appliance], y_pred)
            r2 = r2_score(y_test[appliance], y_pred)
            
            logger.info(f"   MAE: {mae:.2f}W, R²: {r2:.3f}")
            
            self.models[appliance] = model
            results[appliance] = {'mae': mae, 'r2': r2}
        
        return results
    
    def save_models(self, path='models/nilm'):
        """Save trained models"""
        os.makedirs(path, exist_ok=True)
        
        # Save scaler
        joblib.dump(self.scaler, f'{path}/scaler.pkl')
        
        # Save models
        for appliance, model in self.models.items():
            joblib.dump(model, f'{path}/{appliance}_model.pkl')
            logger.info(f"✅ Saved {appliance} model")
        
        logger.info(f"✅ All models saved to {path}")
    
    def load_models(self, path='models/nilm'):
        """Load trained models"""
        try:
            self.scaler = joblib.load(f'{path}/scaler.pkl')
            
            for appliance in self.appliances.keys():
                model_path = f'{path}/{appliance}_model.pkl'
                try:
                    self.models[appliance] = joblib.load(model_path)
                    logger.info(f"✅ Loaded {appliance} model")
                except:
                    logger.warning(f"⚠️ No model found for {appliance}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Could not load models: {e}")
            return False

# Global instance
nilm_trainer = NILMTrainer()