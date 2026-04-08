"""
Prediction service for real-time recommendations.
Handles feature preparation and model inference.
Uses shared feature definitions for consistency with training.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import logging
import joblib
from datetime import datetime

logger = logging.getLogger(__name__)

from models import SessionLocal, User, UserMLFeatures, ModelMetadata
from ml.training_data import training_data_gen
from ml.recommendation_model import MissionRecommendationModel
from ml.feature_definitions import FeatureDefinitions

class PredictionService:
    """
    Service for generating real-time predictions using ML model only.
    Uses shared feature definitions for consistency with training.
    """
    
    def __init__(self):
        self.model = None
        self.model_metadata = None
        self.model_version = None
        self.threshold = 0.5
        self.metrics = {}
        self.data_gen = training_data_gen
        self.feature_defs = FeatureDefinitions()
        
        # Try to load latest model on startup - fail if not available
        if not self.load_latest_model():
            raise RuntimeError("❌ No ML model available - service cannot start")
    
    def load_latest_model(self):
        """Load the most recent model from disk - handles both model objects and dictionaries"""
        try:
            # Load the model file
            model_path = 'models/recommendation_model/model_latest.pkl'
            logger.info(f"📥 Loading model from {model_path}")
            loaded = joblib.load(model_path)
            
            # Check if it's a dictionary (our ensemble format)
            if isinstance(loaded, dict):
                self.model = loaded['ensemble']  # Extract the actual model
                self.model_metadata = loaded
                self.threshold = loaded.get('threshold', 0.5)
                self.metrics = loaded.get('metrics', {})
                logger.info(f"✅ Loaded ensemble model with threshold {self.threshold}")
                logger.info(f"   Accuracy: {self.metrics.get('accuracy', 0):.2%}")
            else:
                # It's a regular model object
                self.model = loaded
                self.threshold = 0.5
                logger.info(f"✅ Loaded standard model")
            
            # Load preprocessors
            self.data_gen.load_preprocessors()
            
            logger.info(f"✅ ML Prediction Service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Could not load model: {e}")
            return False
    
    def prepare_user_features(self, user_id, db):
        """
        Prepare base feature dictionary for a user.
        These are the raw features before encoding and engineering.
        """
        from ml.feature_engineering import feature_engineer
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        logger.info(f"🔍 Preparing features for user {user_id}:")
        logger.info(f"   - Username: {user.username}")
        logger.info(f"   - House ID: {user.ukdale_house_id}")
        logger.info(f"   - Home Type: {user.home_type}, Bedrooms: {user.bedrooms}")
        logger.info(f"   - Emirate: {user.emirate}")
        
        # Get ML features
        ml_features = db.query(UserMLFeatures).filter(
            UserMLFeatures.user_id == user_id
        ).first()
        
        if not ml_features and user.ukdale_house_id:
            logger.info(f"🔄 Generating initial features for user {user_id} from House {user.ukdale_house_id}")
            ml_features = feature_engineer.generate_features_for_new_user(
                user_id, user.ukdale_house_id, db
            )
        
        # Base features that will be used by the feature engineering pipeline
        features = {
            'user_id': user_id,
            'emirate': user.emirate,
            'home_type': user.home_type,
            'bedrooms': user.bedrooms,
            'vehicle_type': user.vehicle_type,
            'vehicle_fuel': user.vehicle_fuel,
            
            # ML features (use actual values if available, otherwise reasonable defaults)
            'avg_energy_30d': float(ml_features.avg_daily_energy_30d) if ml_features and ml_features.avg_daily_energy_30d else 15.0,
            'avg_energy_7d': float(ml_features.avg_daily_energy_7d) if ml_features and ml_features.avg_daily_energy_7d else 14.5,
            'volatility': float(ml_features.energy_volatility) if ml_features and ml_features.energy_volatility else 0.3,
            'peak_ratio': float(ml_features.peak_usage_ratio) if ml_features and ml_features.peak_usage_ratio else 0.5,
            'ac_ratio': float(ml_features.ac_usage_ratio) if ml_features and ml_features.ac_usage_ratio else 0.6,
            'completion_rate': float(ml_features.mission_completion_rate) if ml_features and ml_features.mission_completion_rate else 0.7,
            'days_active': int(ml_features.days_active_last_30d) if ml_features and ml_features.days_active_last_30d else 25,
            'token_velocity': float(ml_features.token_velocity) if ml_features and ml_features.token_velocity else 100,
            
            # Context
            'hour': datetime.now().hour,
            'day_of_week': datetime.now().weekday(),
            'is_weekend': 1 if datetime.now().weekday() >= 5 else 0,
        }
        
        logger.info(f"✅ Base features prepared for user {user_id}")
        logger.info(f"   avg_energy_30d: {features['avg_energy_30d']:.1f}")
        logger.info(f"   ac_ratio: {features['ac_ratio']:.2f}")
        
        return features

    def score_mission_for_user(self, user_features, mission):
        """
        Score a single mission for a user using ML only.
        Uses the same feature pipeline as training.
        """
        # Add mission-specific features
        features = user_features.copy()
        features.update({
            'mission_category': mission['category'],
            'mission_difficulty': mission['difficulty'],
            'tokens_reward': mission.get('tokens_reward', 10),
            'co2_potential': mission.get('savings_kg_co2', 0),
            'success': 1  # Placeholder for feature engineering (not used as target)
        })
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        # Step 1: Encode categorical variables using saved encoders
        for col in ['emirate', 'home_type', 'vehicle_type', 'vehicle_fuel', 
                   'mission_category', 'mission_difficulty']:
            if col in df.columns and col in self.data_gen.label_encoders:
                le = self.data_gen.label_encoders[col]
                df[col + '_encoded'] = df[col].map(
                    lambda x: le.transform([str(x)])[0] if str(x) in le.classes_ else 0
                )
        
        # Step 2: Add all engineered features using shared definitions
        df = self.feature_defs.engineer_features(df)
        
        # Step 3: Select all feature columns (exclude target and ID)
        feature_cols = [col for col in self.feature_defs.get_all_features() if col in df.columns]
        X = df[feature_cols].fillna(0).values
        
        # Step 4: Scale using saved scaler
        X_scaled = self.data_gen.scaler.transform(X)
        
        print(f"   Feature vector shape: {X_scaled.shape}")  # Should show (1, 57/59)
        
        try:
            # Get probability from the model
            probability = self.model.predict_proba(X_scaled)[0][1]
            print(f"   → ML Score: {probability:.3f}")
            return float(probability)
        except Exception as e:
            logger.error(f"❌ Error getting prediction: {e}")
            return 0.5
    
    def get_top_recommendations(self, user_id, mission_templates, n=5):
        """
        Get top N recommendations for a user using ML only.
        """
        db = SessionLocal()
        try:
            # Prepare user features once
            user_features = self.prepare_user_features(user_id, db)
            
            print(f"\n{'='*60}")
            print(f"🔍 GENERATING RECOMMENDATIONS FOR USER {user_id}")
            print(f"{'='*60}")
            
            # Score each mission
            scored_missions = []
            for mission in mission_templates:
                score = self.score_mission_for_user(user_features, mission)
                scored_missions.append({
                    **mission,
                    'relevance_score': round(score * 100, 1),
                    'ml_confidence': score,
                    'scored_at': datetime.now().isoformat()
                })
            
            # Sort by score and return top N
            top_missions = sorted(
                scored_missions, 
                key=lambda x: x['relevance_score'], 
                reverse=True
            )[:n]
            
            print(f"\n📊 TOP {n} RECOMMENDATIONS FOR USER {user_id}:")
            for i, m in enumerate(top_missions, 1):
                print(f"   {i}. {m['title']} - {m['relevance_score']}%")
            
            logger.info(f"✅ Generated {len(top_missions)} recommendations for user {user_id}")
            
            return top_missions
            
        except Exception as e:
            logger.error(f"❌ ML prediction failed for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise - no fallback
        finally:
            db.close()
    
    def get_model_info(self):
        """Get information about the loaded model"""
        if not self.model:
            return {
                'status': 'error',
                'message': 'No model loaded - system cannot function'
            }
        
        return {
            'status': 'active',
            'model_type': 'ensemble' if self.metrics else 'standard',
            'threshold': self.threshold,
            'metrics': self.metrics,
            'loaded_at': datetime.now().isoformat(),
            'features_used': self.feature_defs.get_feature_count()
        }

# Global prediction service instance - will fail if no model
try:
    prediction_service = PredictionService()
    logger.info("✅ ML Prediction Service initialized successfully")
except Exception as e:
    logger.error(f"❌ FATAL: Could not initialize ML service: {e}")
    raise  # This will crash the backend - GOOD! Forces ML to be available