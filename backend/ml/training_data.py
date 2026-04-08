"""
Generates training data from database for ML models.
Handles data loading, preprocessing, and train/test splitting.
Uses shared feature definitions for consistency with inference.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from sqlalchemy import func
from datetime import datetime, timedelta
import logging

from models import SessionLocal, User, Mission, UserMLFeatures, RecommendationLog
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib
import json

# Import shared feature definitions
from ml.feature_definitions import FeatureDefinitions

logger = logging.getLogger(__name__)

class TrainingDataGenerator:
    """
    Generates training datasets for ML models from database.
    Uses shared feature definitions for consistency.
    """
    
    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_columns = None
        self.feature_defs = FeatureDefinitions()
        
    def load_training_data(self, days_history=365, min_missions=3):
        """
        Load training data from database.
        
        Args:
            days_history: Number of days of history to use
            min_missions: Minimum missions a user must have to be included
        """
        db = SessionLocal()
        try:
            since = datetime.now() - timedelta(days=days_history)
            
            # Get all missions with their outcomes
            missions = db.query(
                Mission,
                User,
                UserMLFeatures
            ).join(
                User, Mission.user_id == User.id
            ).outerjoin(
                UserMLFeatures, User.id == UserMLFeatures.user_id
            ).filter(
                Mission.created_at >= since,
                Mission.status.in_(['completed', 'failed'])
            ).all()
            
            logger.info(f"📊 Loaded {len(missions)} mission records")
            
            # Convert to DataFrame
            data = []
            mission_count = 0
            skipped_count = 0
            
            for mission, user, features in missions:
                if not features:  # Skip users without ML features
                    skipped_count += 1
                    continue
                    
                row = {
                    # User features
                    'user_id': user.id,
                    'emirate': user.emirate,
                    'home_type': user.home_type,
                    'bedrooms': user.bedrooms,
                    'vehicle_type': user.vehicle_type,
                    'vehicle_fuel': user.vehicle_fuel,
                    
                    # ML features
                    'avg_energy_30d': float(features.avg_daily_energy_30d) if features.avg_daily_energy_30d else 15.0,
                    'avg_energy_7d': float(features.avg_daily_energy_7d) if features.avg_daily_energy_7d else 14.5,
                    'volatility': float(features.energy_volatility) if features.energy_volatility else 0.3,
                    'peak_ratio': float(features.peak_usage_ratio) if features.peak_usage_ratio else 0.5,
                    'ac_ratio': float(features.ac_usage_ratio) if features.ac_usage_ratio else 0.6,
                    'completion_rate': float(features.mission_completion_rate) if features.mission_completion_rate else 0.7,
                    'days_active': int(features.days_active_last_30d) if features.days_active_last_30d else 25,
                    'token_velocity': float(features.token_velocity) if features.token_velocity else 100,
                    
                    # Mission features
                    'mission_category': mission.category,
                    'mission_difficulty': mission.difficulty,
                    'tokens_reward': mission.tokens_reward,
                    'co2_potential': mission.co2_saved_kg,
                    
                    # Context
                    'hour': mission.created_at.hour,
                    'day_of_week': mission.created_at.weekday(),
                    'is_weekend': 1 if mission.created_at.weekday() >= 5 else 0,
                    
                    # Outcome (target variable)
                    'success': 1 if mission.status == 'completed' else 0,
                    'time_taken': mission.time_taken_seconds,
                    'rating': mission.user_rating or 0
                }
                data.append(row)
                mission_count += 1
                
                # Progress update for large datasets
                if mission_count % 5000 == 0:
                    logger.info(f"  ✅ Processed {mission_count} missions...")
            
            logger.info(f"✅ Processed {mission_count} missions, skipped {skipped_count} (no ML features)")
            
            df = pd.DataFrame(data)
            
            # Filter users with minimum missions
            if len(df) > 0 and 'user_id' in df.columns:
                user_mission_counts = df.groupby('user_id').size()
                valid_users = user_mission_counts[user_mission_counts >= min_missions].index
                df = df[df['user_id'].isin(valid_users)]
                
                logger.info(f"✅ Final dataset: {len(df)} samples from {len(valid_users)} users")
                logger.info(f"   Class distribution: {df['success'].value_counts().to_dict()}")
            else:
                logger.warning("⚠️ No valid training data found")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error loading training data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
        finally:
            db.close()
    
    def prepare_features(self, df, fit_encoders=True):
        """
        Prepare features for model training using shared feature definitions.
        This ensures training and inference use exactly the same features.
        
        Args:
            df: DataFrame with raw data
            fit_encoders: Whether to fit label encoders (True for training, False for inference)
        """
        df = df.copy()
        
        # ===== STEP 1: Encode categorical features =====
        categorical_cols = ['emirate', 'home_type', 'vehicle_type', 
                           'vehicle_fuel', 'mission_category', 'mission_difficulty']
        
        for col in categorical_cols:
            if col in df.columns:
                if fit_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    df[col + '_encoded'] = self.label_encoders[col].fit_transform(df[col].astype(str))
                else:
                    # Handle unseen categories in inference
                    df[col + '_encoded'] = df[col].map(
                        lambda x: self.label_encoders[col].transform([str(x)])[0] 
                        if str(x) in self.label_encoders[col].classes_ 
                        else -1
                    )
        
        # ===== STEP 2: Add all engineered features using shared definitions =====
        df = self.feature_defs.engineer_features(df)
        
        # ===== STEP 3: Get all feature columns =====
        all_features = self.feature_defs.get_all_features()
        self.feature_columns = [col for col in all_features if col in df.columns]
        
        logger.info(f"📊 Using {len(self.feature_columns)} features")
        
        X = df[self.feature_columns].fillna(0).values
        
        # ===== STEP 4: Scale numerical features =====
        if fit_encoders:
            X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = self.scaler.transform(X)
        
        # Target variable
        y = df['success'].values if 'success' in df.columns else None
        
        logger.info(f"✅ Feature matrix shape: {X_scaled.shape}")
        
        return X_scaled, y, df
    
    def get_train_test_split(self, df, test_size=0.2, random_state=42):
        """
        Split data into training and testing sets.
        Ensures users don't appear in both train and test.
        """
        # Split by user to prevent data leakage
        users = df['user_id'].unique()
        train_users, test_users = train_test_split(
            users, test_size=test_size, random_state=random_state
        )
        
        train_df = df[df['user_id'].isin(train_users)]
        test_df = df[df['user_id'].isin(test_users)]
        
        logger.info(f"📊 Train: {len(train_df)} samples from {len(train_users)} users")
        logger.info(f"📊 Test: {len(test_df)} samples from {len(test_users)} users")
        
        return train_df, test_df
    
    def save_preprocessors(self, path='models/preprocessors'):
        """Save label encoders and scaler for inference"""
        os.makedirs(path, exist_ok=True)
        
        # Save label encoders
        for name, encoder in self.label_encoders.items():
            joblib.dump(encoder, f"{path}/{name}_encoder.pkl")
        
        # Save scaler
        joblib.dump(self.scaler, f"{path}/scaler.pkl")
        
        # Save feature columns (now using the full 59 features)
        with open(f"{path}/feature_columns.json", 'w') as f:
            json.dump(self.feature_columns, f)
        
        logger.info(f"✅ Preprocessors saved to {path}")
    
    def load_preprocessors(self, path='models/preprocessors'):
        """Load preprocessors for inference"""
        # Load feature columns
        with open(f"{path}/feature_columns.json", 'r') as f:
            self.feature_columns = json.load(f)
        
        # Load scaler
        self.scaler = joblib.load(f"{path}/scaler.pkl")
        
        # Load label encoders
        self.label_encoders = {}
        for col in ['emirate', 'home_type', 'vehicle_type', 
                   'vehicle_fuel', 'mission_category', 'mission_difficulty']:
            try:
                self.label_encoders[col] = joblib.load(f"{path}/{col}_encoder.pkl")
            except:
                logger.warning(f"Could not load encoder for {col}")
        
        logger.info(f"✅ Preprocessors loaded from {path}")
        logger.info(f"📊 Loaded {len(self.feature_columns)} feature definitions")

# Global instance
training_data_gen = TrainingDataGenerator()