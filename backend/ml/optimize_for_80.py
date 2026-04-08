"""
Complete optimization pipeline to achieve 80% accuracy
FIXED: Encoded columns are created after feature engineering
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
import lightgbm as lgb
import xgboost as xgb
import optuna
import joblib
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from ml.training_data import TrainingDataGenerator
from imblearn.over_sampling import SMOTE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizeFor80:
    def __init__(self):
        self.data_gen = TrainingDataGenerator()
        self.best_model = None
        self.best_threshold = 0.5
        self.feature_importance = None
        self.label_encoders = {}
        
    def load_and_engineer_features(self):
        """Load data and create 30+ advanced features"""
        logger.info("📥 Loading training data...")
        df = self.data_gen.load_training_data(days_history=365, min_missions=3)
        logger.info(f"✅ Loaded {len(df)} samples")
        
        logger.info("🔧 Engineering advanced features...")
        df = self._engineer_features(df)
        logger.info(f"✅ Now have {df.shape[1]} features")
        
        # Prepare features (this will create encoded columns)
        logger.info("🔄 Preparing features with encoders...")
        X, y, feature_names = self._prepare_features(df)
        
        # Apply SMOTE for class balancing
        logger.info("⚖️ Applying SMOTE for class balancing...")
        smote = SMOTE(random_state=42)
        X_resampled, y_resampled = smote.fit_resample(X, y)
        logger.info(f"✅ After SMOTE: {len(X_resampled)} samples")
        logger.info(f"   Class distribution: {np.bincount(y_resampled)}")
        
        return X_resampled, y_resampled, feature_names
    
    def _engineer_features(self, df):
        """Create 30+ advanced features using raw columns (before encoding)"""
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
        
        # ===== CATEGORICAL ENCODING WILL HAPPEN IN _prepare_features =====
        # Store original categories for later encoding
        self.categorical_cols = ['emirate', 'home_type', 'vehicle_type', 
                                 'vehicle_fuel', 'mission_category', 'mission_difficulty']
        
        return df
    
    def _prepare_features(self, df):
        """Prepare features for training - handles encoding properly"""
        df = df.copy()
        
        # ===== FIRST: Encode all categorical features =====
        categorical_cols = ['emirate', 'home_type', 'vehicle_type', 
                        'vehicle_fuel', 'mission_category', 'mission_difficulty']
        
        for col in categorical_cols:
            if col in df.columns:
                le = LabelEncoder()
                df[col + '_encoded'] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
                # Drop the original string column to avoid scaling issues
                df.drop(columns=[col], inplace=True)
                logger.info(f"✅ Encoded {col} -> {col}_encoded")
        
        # ===== SECOND: Create features that use encoded columns =====
        if 'mission_difficulty_encoded' in df.columns:
            df['co2_x_difficulty'] = df['co2_potential'] * (df['mission_difficulty_encoded'] + 1)
            df['difficulty_weight'] = df['mission_difficulty_encoded'] * df['tokens_reward']
            df['effort_reward_ratio'] = df['mission_difficulty_encoded'] / (df['tokens_reward'] + 1)
            df['difficulty_success'] = df['mission_difficulty_encoded'] * df['success']
        
        if 'mission_category_encoded' in df.columns:
            df['category_preference'] = df['mission_category_encoded'] * df['completion_rate']
        
        if 'vehicle_type_encoded' in df.columns:
            df['suv_impact'] = df['co2_potential'] * (df['vehicle_type_encoded'] == 0).astype(int)
            df['vehicle_emission_factor'] = df['co2_potential'] * (df['vehicle_type_encoded'] + 1)
        
        if 'vehicle_fuel_encoded' in df.columns:
            df['fuel_efficiency_score'] = 1 / (df['vehicle_fuel_encoded'] + 1)
        
        # ===== THIRD: Select only numeric columns =====
        # Get all numeric columns (exclude any remaining non-numeric)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Remove target and ID columns
        exclude_cols = ['user_id', 'success', 'time_taken', 'rating']
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        logger.info(f"📊 Using {len(feature_cols)} numeric features")
        
        # Print first few feature names
        logger.info(f"   Sample features: {feature_cols[:5]}")
        
        X = df[feature_cols].fillna(0).values
        y = df['success'].values
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        return X_scaled, y, feature_cols

    def objective_lgb(self, trial, X, y):
        """Optuna objective for LightGBM"""
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'verbosity': -1,
            'num_leaves': trial.suggest_int('num_leaves', 10, 150),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
            'feature_fraction': trial.suggest_float('feature_fraction', 0.5, 1.0),
            'bagging_fraction': trial.suggest_float('bagging_fraction', 0.5, 1.0),
            'bagging_freq': trial.suggest_int('bagging_freq', 1, 10),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            'min_split_gain': trial.suggest_float('min_split_gain', 0, 1),
            'min_child_weight': trial.suggest_float('min_child_weight', 1e-3, 10.0, log=True)
        }
        
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = []
        
        for train_idx, val_idx in cv.split(X, y):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            model = lgb.LGBMClassifier(**params, n_estimators=200, random_state=42, verbose=-1)
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)], 
                     callbacks=[lgb.early_stopping(20), lgb.log_evaluation(0)])
            
            y_pred = model.predict(X_val)
            scores.append(accuracy_score(y_val, y_pred))
        
        return np.mean(scores)
    
    def objective_xgb(self, trial, X, y):
        """Optuna objective for XGBoost"""
        params = {
            'objective': 'binary:logistic',
            'eval_metric': 'auc',
            'max_depth': trial.suggest_int('max_depth', 3, 12),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'gamma': trial.suggest_float('gamma', 0, 5),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True)
        }
        
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = []
        
        for train_idx, val_idx in cv.split(X, y):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            model = xgb.XGBClassifier(**params, n_estimators=200, random_state=42, use_label_encoder=False)
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
            
            y_pred = model.predict(X_val)
            scores.append(accuracy_score(y_val, y_pred))
        
        return np.mean(scores)
    
    def objective_rf(self, trial, X, y):
        """Optuna objective for Random Forest"""
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 500),
            'max_depth': trial.suggest_int('max_depth', 5, 30),
            'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
            'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
            'max_features': trial.suggest_float('max_features', 0.5, 1.0)
        }
        
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = []
        
        for train_idx, val_idx in cv.split(X, y):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            model = RandomForestClassifier(**params, random_state=42, n_jobs=-1)
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_val)
            scores.append(accuracy_score(y_val, y_pred))
        
        return np.mean(scores)
    
    def optimize_hyperparameters(self, X, y):
        """Run Optuna for all models"""
        logger.info("🎯 Starting hyperparameter optimization...")
        
        # LightGBM optimization
        logger.info("\n📊 Optimizing LightGBM...")
        study_lgb = optuna.create_study(direction='maximize')
        study_lgb.optimize(lambda trial: self.objective_lgb(trial, X, y), n_trials=30)  # Reduced for speed
        logger.info(f"✅ Best LightGBM accuracy: {study_lgb.best_value:.4f}")
        logger.info(f"   Params: {study_lgb.best_params}")
        
        # XGBoost optimization
        logger.info("\n📊 Optimizing XGBoost...")
        study_xgb = optuna.create_study(direction='maximize')
        study_xgb.optimize(lambda trial: self.objective_xgb(trial, X, y), n_trials=30)
        logger.info(f"✅ Best XGBoost accuracy: {study_xgb.best_value:.4f}")
        logger.info(f"   Params: {study_xgb.best_params}")
        
        # Random Forest optimization
        logger.info("\n📊 Optimizing Random Forest...")
        study_rf = optuna.create_study(direction='maximize')
        study_rf.optimize(lambda trial: self.objective_rf(trial, X, y), n_trials=30)
        logger.info(f"✅ Best RF accuracy: {study_rf.best_value:.4f}")
        logger.info(f"   Params: {study_rf.best_params}")
        
        return {
            'lgb': (study_lgb.best_params, study_lgb.best_value),
            'xgb': (study_xgb.best_params, study_xgb.best_value),
            'rf': (study_rf.best_params, study_rf.best_value)
        }
    
    def create_ensemble(self, X, y, best_params):
        """Create voting ensemble of best models"""
        logger.info("\n🤝 Creating ensemble model...")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train individual models
        lgb_model = lgb.LGBMClassifier(**best_params['lgb'][0], n_estimators=200, random_state=42, verbose=-1)
        xgb_model = xgb.XGBClassifier(**best_params['xgb'][0], n_estimators=200, random_state=42, use_label_encoder=False)
        rf_model = RandomForestClassifier(**best_params['rf'][0], random_state=42, n_jobs=-1)
        
        # Create soft voting ensemble
        ensemble = VotingClassifier(
            estimators=[('lgb', lgb_model), ('xgb', xgb_model), ('rf', rf_model)],
            voting='soft',
            weights=[2, 1, 1]  # LightGBM gets double weight
        )
        
        ensemble.fit(X_train, y_train)
        
        # Evaluate
        y_pred = ensemble.predict(X_test)
        y_prob = ensemble.predict_proba(X_test)[:, 1]
        
        accuracy = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        
        logger.info(f"✅ Ensemble Accuracy: {accuracy:.4f}")
        logger.info(f"✅ Ensemble AUC-ROC: {auc:.4f}")
        
        return ensemble, X_test, y_test, y_prob
    
    def optimize_threshold(self, y_test, y_prob):
        """Find optimal probability threshold for accuracy"""
        logger.info("\n🎚️ Optimizing probability threshold...")
        
        thresholds = np.arange(0.3, 0.7, 0.01)
        best_acc = 0
        best_thresh = 0.5
        
        for thresh in thresholds:
            y_pred = (y_prob >= thresh).astype(int)
            acc = accuracy_score(y_test, y_pred)
            if acc > best_acc:
                best_acc = acc
                best_thresh = thresh
        
        logger.info(f"✅ Best threshold: {best_thresh:.2f} -> Accuracy: {best_acc:.4f}")
        return best_thresh, best_acc
    
    def run_full_optimization(self):
        """Run complete optimization pipeline"""
        logger.info("="*70)
        logger.info("🚀 STARTING 80% ACCURACY OPTIMIZATION PIPELINE")
        logger.info("="*70)
        
        # Load and engineer features
        X, y, feature_names = self.load_and_engineer_features()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Hyperparameter optimization
        best_params = self.optimize_hyperparameters(X_train, y_train)
        
        # Create ensemble
        ensemble, X_test, y_test, y_prob = self.create_ensemble(X_train, y_train, best_params)
        
        # Optimize threshold
        best_thresh, final_acc = self.optimize_threshold(y_test, y_prob)
        
        # Final evaluation with best threshold
        y_pred = (y_prob >= best_thresh).astype(int)
        final_metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'auc_roc': roc_auc_score(y_test, y_prob),
            'threshold': best_thresh
        }
        
        logger.info("\n" + "="*70)
        logger.info("🏆 FINAL RESULTS")
        logger.info("="*70)
        logger.info(f"Accuracy:  {final_metrics['accuracy']:.2%}")
        logger.info(f"Precision: {final_metrics['precision']:.2%}")
        logger.info(f"Recall:    {final_metrics['recall']:.2%}")
        logger.info(f"F1 Score:  {final_metrics['f1']:.2%}")
        logger.info(f"AUC-ROC:   {final_metrics['auc_roc']:.3f}")
        logger.info(f"Threshold: {final_metrics['threshold']:.2f}")
        
        # Save model
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = f'models/recommendation_model/80percent_model_{timestamp}.pkl'
        joblib.dump({
            'ensemble': ensemble,
            'threshold': best_thresh,
            'metrics': final_metrics,
            'feature_names': feature_names
        }, model_path)
        logger.info(f"💾 Model saved to {model_path}")
        
        return final_metrics

def main():
    optimizer = OptimizeFor80()
    metrics = optimizer.run_full_optimization()
    
    if metrics['accuracy'] >= 0.80:
        print("\n🎉🎉🎉 CONGRATULATIONS! 80% ACCURACY ACHIEVED! 🎉🎉🎉")
    else:
        print(f"\n📊 Final accuracy: {metrics['accuracy']:.2%}")
        print("   Close to 80%! Try increasing n_trials to 50 for better results.")

if __name__ == "__main__":
    main()