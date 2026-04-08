"""
Feature engineering pipeline for ML models.
Transforms raw data into ML-ready features.
Includes UK-DALE house assignment for new users.
"""

import pandas as pd
import numpy as np
from sqlalchemy import func
from datetime import datetime, timedelta
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SessionLocal, User, EnergyReading, Mission, UserMLFeatures
from data_processing.data_loader import UKDALELoader

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Transforms raw user data into ML-ready features.
    """
    
    def __init__(self):
        self.feature_version = "1.0"
    
    def compute_all_user_features(self, user_id=None):
        """
        Compute ML features for all users or a specific user.
        """
        db = SessionLocal()
        try:
            query = db.query(User)
            if user_id:
                query = query.filter(User.id == user_id)
            
            users = query.all()
            logger.info(f"📊 Computing features for {len(users)} users")
            
            for user in users:
                self.compute_user_features(user.id, db)
            
            db.commit()
            logger.info("✅ Feature computation complete")
            
        except Exception as e:
            logger.error(f"Error computing features: {e}")
            db.rollback()
        finally:
            db.close()
    
    def compute_user_features(self, user_id, db):
        """
        Compute all ML features for a single user.
        """
        # Get or create ML features record
        ml_features = db.query(UserMLFeatures).filter(
            UserMLFeatures.user_id == user_id
        ).first()
        
        if not ml_features:
            ml_features = UserMLFeatures(user_id=user_id)
            db.add(ml_features)
        
        # Compute each feature group
        self._compute_energy_features(user_id, ml_features, db)
        self._compute_behavioral_features(user_id, ml_features, db)
        self._compute_engagement_features(user_id, ml_features, db)
        
        ml_features.feature_version = self.feature_version
        ml_features.calculated_at = datetime.now()
        
        logger.debug(f"✅ Computed features for user {user_id}")
    
    def _compute_energy_features(self, user_id, ml_features, db):
        """Compute energy consumption patterns"""
        # Last 30 days of energy readings
        thirty_days_ago = datetime.now() - timedelta(days=30)
        readings = db.query(EnergyReading).filter(
            EnergyReading.user_id == user_id,
            EnergyReading.timestamp >= thirty_days_ago
        ).all()
        
        if not readings:
            return
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([{
            'timestamp': r.timestamp,
            'power': r.power_watts,
            'energy': r.energy_kwh
        } for r in readings])
        
        # Daily aggregations
        df['date'] = df['timestamp'].dt.date
        daily = df.groupby('date').agg({
            'energy': 'sum',
            'power': ['mean', 'std']
        }).reset_index()
        
        daily.columns = ['date', 'energy_sum', 'power_mean', 'power_std']
        
        # 30-day averages
        ml_features.avg_daily_energy_30d = float(daily['energy_sum'].mean()) if not daily.empty else None
        
        # 7-day averages (last 7 days)
        last_7 = daily.tail(7)
        ml_features.avg_daily_energy_7d = float(last_7['energy_sum'].mean()) if not last_7.empty else None
        
        # Volatility (coefficient of variation)
        if not daily.empty and daily['energy_sum'].mean() > 0:
            ml_features.energy_volatility = float(daily['energy_sum'].std() / daily['energy_sum'].mean())
        
        # Peak hour usage (12-5 PM)
        df['hour'] = df['timestamp'].dt.hour
        peak_mask = (df['hour'] >= 12) & (df['hour'] <= 17)
        if len(df) > 0:
            ml_features.peak_usage_ratio = float(peak_mask.sum() / len(df))
    
    def _compute_behavioral_features(self, user_id, ml_features, db):
        """Compute user behavior patterns"""
        missions = db.query(Mission).filter(
            Mission.user_id == user_id
        ).all()
        
        if not missions:
            return
        
        completed = [m for m in missions if m.status == 'completed']
        
        # Completion rate
        if missions:
            ml_features.mission_completion_rate = len(completed) / len(missions)
        
        # Average completion time
        times = [m.time_taken_seconds for m in completed if m.time_taken_seconds]
        if times:
            ml_features.avg_completion_time = int(np.mean(times))
        
        # Preferred category
        if completed:
            categories = [m.category for m in completed]
            from collections import Counter
            category_counts = Counter(categories)
            ml_features.preferred_mission_category = category_counts.most_common(1)[0][0] if category_counts else None
    
    def _compute_engagement_features(self, user_id, ml_features, db):
        """Compute user engagement metrics"""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Count days with activity
        missions = db.query(Mission).filter(
            Mission.user_id == user_id,
            Mission.created_at >= thirty_days_ago
        ).all()
        
        if missions:
            days_active = len(set(m.created_at.date() for m in missions))
            ml_features.days_active_last_30d = days_active
            ml_features.sessions_per_week = days_active / 4.3  # Approximate weeks
        
        # Token velocity
        from models import TokenTransaction
        tokens = db.query(TokenTransaction).filter(
            TokenTransaction.user_id == user_id,
            TokenTransaction.transaction_type == 'earned_mission',
            TokenTransaction.timestamp >= thirty_days_ago
        ).all()
        
        if tokens:
            total_tokens = sum(t.amount for t in tokens)
            ml_features.token_velocity = total_tokens / 30  # Tokens per day
        
        # Last active
        last_mission = db.query(Mission).filter(
            Mission.user_id == user_id
        ).order_by(Mission.created_at.desc()).first()
        
        if last_mission:
            ml_features.last_active = last_mission.created_at
    
    def generate_features_for_new_user(self, user_id, house_id, db):
        """
        Generate initial ML features for a brand new user based on their assigned UK-DALE house.
        This ensures they get personalized recommendations immediately.
        """
        logger.info(f"🔄 Generating initial ML features for new user {user_id} from House {house_id}")
        
        loader = UKDALELoader()
        df = loader.load_house_data(house_number=house_id, sample_size=5000)
        
        if df is None or df.empty:
            logger.error(f"❌ Could not load House {house_id} data for new user {user_id}")
            return None
        
        # Create or get ML features record
        ml_features = db.query(UserMLFeatures).filter(
            UserMLFeatures.user_id == user_id
        ).first()
        
        if not ml_features:
            ml_features = UserMLFeatures(user_id=user_id)
            db.add(ml_features)
        
        # Process the data
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['date'] = df['timestamp'].dt.date
        
        # Energy consumption patterns
        avg_power = df['power_watts'].mean()
        peak_power = df[df['hour'].between(12, 17)]['power_watts'].mean() if any(df['hour'].between(12, 17)) else avg_power
        
        # Daily aggregations
        daily = df.groupby('date').agg({
            'power_watts': ['mean', 'std', 'max', 'min']
        }).reset_index()
        
        daily.columns = ['date', 'avg_power', 'std_power', 'max_power', 'min_power']
        
        # Set ML features
        ml_features.avg_daily_energy_30d = float(avg_power * 24 / 1000)  # Convert to kWh/day
        ml_features.avg_daily_energy_7d = float(avg_power * 24 / 1000 * 0.95)  # Slightly lower estimate
        ml_features.energy_volatility = float(df['power_watts'].std() / avg_power) if avg_power > 0 else 0.2
        ml_features.peak_usage_ratio = float((df['hour'].between(12, 17).sum() / len(df))) if len(df) > 0 else 0.5
        
        # Appliance estimates based on house characteristics
        if house_id in [1, 5]:  # Villas
            ml_features.ac_usage_ratio = 0.7
            ml_features.fridge_usage_ratio = 0.15
            ml_features.lighting_ratio = 0.1
        elif house_id in [2, 3]:  # Medium homes
            ml_features.ac_usage_ratio = 0.5
            ml_features.fridge_usage_ratio = 0.2
            ml_features.lighting_ratio = 0.15
        else:  # Small apartment (House 4)
            ml_features.ac_usage_ratio = 0.4
            ml_features.fridge_usage_ratio = 0.25
            ml_features.lighting_ratio = 0.2
        
        # Default behavioral features for new users (will be updated as they use the app)
        ml_features.mission_completion_rate = 0.5  # Assume average to start
        ml_features.days_active_last_30d = 0
        ml_features.token_velocity = 0
        ml_features.source_house_id = house_id
        ml_features.calculated_at = datetime.now()
        ml_features.feature_version = self.feature_version
        
        db.commit()
        logger.info(f"✅ Generated initial ML features for new user {user_id} from House {house_id}")
        
        return ml_features
    
    def get_feature_vector(self, user_id):
        """
        Get feature vector for a user (ready for model input).
        """
        db = SessionLocal()
        try:
            ml_features = db.query(UserMLFeatures).filter(
                UserMLFeatures.user_id == user_id
            ).first()
            
            if not ml_features:
                return None
            
            # Convert to feature vector (numeric only)
            feature_vector = [
                ml_features.avg_daily_energy_30d or 0,
                ml_features.avg_daily_energy_7d or 0,
                ml_features.energy_volatility or 0,
                ml_features.peak_usage_ratio or 0,
                ml_features.ac_usage_ratio or 0,
                ml_features.mission_completion_rate or 0,
                ml_features.days_active_last_30d or 0,
                ml_features.sessions_per_week or 0,
                ml_features.token_velocity or 0,
            ]
            
            # Feature names for reference
            feature_names = [
                'avg_energy_30d', 'avg_energy_7d', 'volatility',
                'peak_ratio', 'ac_ratio', 'completion_rate',
                'days_active', 'sessions_week', 'token_velocity'
            ]
            
            return {
                'user_id': user_id,
                'features': feature_vector,
                'feature_names': feature_names,
                'version': ml_features.feature_version,
                'source_house_id': ml_features.source_house_id
            }
            
        finally:
            db.close()

# Global feature engineer instance
feature_engineer = FeatureEngineer()