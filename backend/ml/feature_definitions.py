"""
Feature definitions for CarbonLife ML pipeline.
Single source of truth for ALL features used in training and inference.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any

class FeatureDefinitions:
    """Defines all features used in the ML pipeline"""
    
    # Base features (from original data)
    BASE_FEATURES = [
        'bedrooms',
        'avg_energy_30d',
        'avg_energy_7d',
        'volatility',
        'peak_ratio',
        'ac_ratio',
        'completion_rate',
        'days_active',
        'token_velocity',
        'tokens_reward',
        'co2_potential',
        'hour',
        'day_of_week',
        'is_weekend',
        'emirate_encoded',
        'home_type_encoded',
        'vehicle_type_encoded',
        'vehicle_fuel_encoded',
        'mission_category_encoded',
        'mission_difficulty_encoded'
    ]
    
    # Engineered features (39 total)
    ENGINEERED_FEATURES = [
        # Energy efficiency (5)
        'energy_per_bedroom',
        'energy_per_room',
        'peak_to_avg',
        'ac_intensity',
        'volatility_score',
        
        # Token economy (6)
        'tokens_per_co2',
        'token_efficiency',
        'token_velocity_scaled',
        'reward_intensity',
        'token_roi',
        
        # Interactions (8)
        'energy_x_tokens',
        'co2_x_energy',
        'bedrooms_x_ac',
        'peak_x_ac',
        'energy_x_completion',
        'tokens_x_completion',
        'volatility_x_peak',
        
        # User behavior (6)
        'engagement_score',
        'consistency_score',
        'green_consciousness',
        'mission_momentum',
        'activity_density',
        'user_experience',
        
        # Time-based (8)
        'is_morning',
        'is_afternoon',
        'is_evening',
        'is_night',
        'sin_hour',
        'cos_hour',
        'sin_day',
        'cos_day',
        
        # Vehicle impact (3)
        'vehicle_emission_factor',
        'fuel_efficiency_score',
        'suv_impact',
        
        # Difficulty features (3)
        'difficulty_weight',
        'effort_reward_ratio',
        'difficulty_success'
    ]
    
    @classmethod
    def get_all_features(cls) -> List[str]:
        """Get list of all 59 features"""
        return cls.BASE_FEATURES + cls.ENGINEERED_FEATURES
    
    @classmethod
    def get_feature_count(cls) -> int:
        """Get total number of features"""
        return len(cls.get_all_features())
    
    @classmethod
    def engineer_features(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add all engineered features to the dataframe.
        This should be called AFTER categorical encoding.
        """
        df = df.copy()
        
        # ===== ENERGY EFFICIENCY FEATURES (5) =====
        df['energy_per_bedroom'] = df['avg_energy_30d'] / (df['bedrooms'] + 1)
        df['energy_per_room'] = df['avg_energy_30d'] / (df['bedrooms'] * 1.5 + 1)
        df['peak_to_avg'] = df['peak_ratio'] / (df['avg_energy_30d'] + 0.1)
        df['ac_intensity'] = df['ac_ratio'] * df['avg_energy_30d']
        df['volatility_score'] = df['volatility'] * 100
        
        # ===== TOKEN ECONOMY FEATURES (6) =====
        df['tokens_per_co2'] = df['tokens_reward'] / (df['co2_potential'] + 0.1)
        df['token_efficiency'] = df['tokens_reward'] * df['completion_rate']
        df['token_velocity_scaled'] = df['token_velocity'] / 100
        df['reward_intensity'] = df['tokens_reward'] * df['co2_potential']
        df['token_roi'] = df['co2_potential'] / (df['tokens_reward'] + 1)
        
        # ===== INTERACTION FEATURES (8) =====
        df['energy_x_tokens'] = df['avg_energy_30d'] * df['tokens_reward']
        df['co2_x_energy'] = df['co2_potential'] * df['avg_energy_30d']
        df['bedrooms_x_ac'] = df['bedrooms'] * df['ac_ratio']
        df['peak_x_ac'] = df['peak_ratio'] * df['ac_ratio']
        df['energy_x_completion'] = df['avg_energy_30d'] * df['completion_rate']
        df['tokens_x_completion'] = df['tokens_reward'] * df['completion_rate']
        df['volatility_x_peak'] = df['volatility'] * df['peak_ratio']
        
        # ===== USER BEHAVIOR FEATURES (6) =====
        df['engagement_score'] = df['completion_rate'] * df['days_active'] / 30
        df['consistency_score'] = 1 / (df['volatility'] + 0.1)
        df['green_consciousness'] = df['ac_ratio'] * df['co2_potential']
        df['mission_momentum'] = df['completion_rate'] * df['token_velocity']
        df['activity_density'] = df['days_active'] * df['completion_rate']
        df['user_experience'] = np.log1p(df['days_active'])
        
        # ===== TIME-BASED FEATURES (8) =====
        df['is_morning'] = ((df['hour'] >= 6) & (df['hour'] <= 11)).astype(int)
        df['is_afternoon'] = ((df['hour'] >= 12) & (df['hour'] <= 17)).astype(int)
        df['is_evening'] = ((df['hour'] >= 18) & (df['hour'] <= 22)).astype(int)
        df['is_night'] = ((df['hour'] >= 23) | (df['hour'] <= 5)).astype(int)
        df['sin_hour'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['cos_hour'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['sin_day'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['cos_day'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # ===== VEHICLE IMPACT FEATURES (3) =====
        if 'vehicle_type_encoded' in df.columns:
            df['vehicle_emission_factor'] = df['co2_potential'] * (df['vehicle_type_encoded'] + 1)
            df['fuel_efficiency_score'] = 1 / (df['vehicle_fuel_encoded'] + 1)
            df['suv_impact'] = df['co2_potential'] * (df['vehicle_type_encoded'] == 0).astype(int)
        else:
            df['vehicle_emission_factor'] = df['co2_potential']
            df['fuel_efficiency_score'] = 0.5
            df['suv_impact'] = 0
        
        # ===== DIFFICULTY FEATURES (3) =====
        if 'mission_difficulty_encoded' in df.columns:
            df['difficulty_weight'] = df['mission_difficulty_encoded'] * df['tokens_reward']
            df['effort_reward_ratio'] = df['mission_difficulty_encoded'] / (df['tokens_reward'] + 1)
            df['difficulty_success'] = df['mission_difficulty_encoded'] * df.get('success', 1)
        else:
            df['difficulty_weight'] = df['tokens_reward']
            df['effort_reward_ratio'] = 1 / (df['tokens_reward'] + 1)
            df['difficulty_success'] = df['tokens_reward']
        
        return df
    
    @classmethod
    def prepare_feature_vector(cls, df: pd.DataFrame, label_encoders: Dict = None) -> np.ndarray:
        """
        Complete feature preparation pipeline:
        1. Encode categoricals
        2. Add engineered features
        3. Return feature matrix
        """
        from sklearn.preprocessing import LabelEncoder
        
        df = df.copy()
        
        # Encode categorical features if encoders provided
        if label_encoders:
            categorical_cols = ['emirate', 'home_type', 'vehicle_type', 
                               'vehicle_fuel', 'mission_category', 'mission_difficulty']
            
            for col in categorical_cols:
                if col in df.columns and col in label_encoders:
                    le = label_encoders[col]
                    df[col + '_encoded'] = df[col].map(
                        lambda x: le.transform([str(x)])[0] if str(x) in le.classes_ else -1
                    )
        
        # Add engineered features
        df = cls.engineer_features(df)
        
        # Select only feature columns (exclude target)
        feature_cols = [col for col in cls.get_all_features() if col in df.columns]
        return df[feature_cols].fillna(0).values

# Global instance
feature_defs = FeatureDefinitions()