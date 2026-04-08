"""
Compare multiple ML models to find the best performer for mission recommendations.
Tests: LightGBM, XGBoost, Random Forest, Logistic Regression
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import lightgbm as lgb
import xgboost as xgb
import joblib
import json
from datetime import datetime
import logging

from ml.training_data import TrainingDataGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelComparator:
    def __init__(self):
        self.data_gen = TrainingDataGenerator()
        self.results = {}
        
    def load_and_prepare_data(self):
        """Load training data and prepare features"""
        logger.info("📥 Loading training data...")
        
        # Load from database or CSV
        try:
            from models import SessionLocal, Mission
            df = self.data_gen.load_training_data(days_history=365, min_missions=3)
        except:
            # Fallback to CSV
            df = pd.read_csv('ukdale_training_data_v2.csv')
        
        logger.info(f"✅ Loaded {len(df)} samples")
        
        # Prepare features
        X, y, _ = self.data_gen.prepare_features(df, fit_encoders=True)
        
        # Split data
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        logger.info(f"Training samples: {len(X_train)}")
        logger.info(f"Testing samples: {len(X_test)}")
        
        return X_train, X_test, y_train, y_test
    
    def test_lightgbm(self, X_train, X_test, y_train, y_test):
        """Test LightGBM classifier"""
        logger.info("\n🧪 Testing LightGBM...")
        
        model = lgb.LGBMClassifier(
            n_estimators=100,
            learning_rate=0.05,
            num_leaves=31,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        results = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_test, y_prob)
        }
        
        logger.info(f"   Accuracy: {results['accuracy']:.4f}")
        logger.info(f"   F1 Score: {results['f1']:.4f}")
        logger.info(f"   AUC-ROC: {results['auc_roc']:.4f}")
        
        return results, model
    
    def test_xgboost(self, X_train, X_test, y_train, y_test):
        """Test XGBoost classifier"""
        logger.info("\n🧪 Testing XGBoost...")
        
        model = xgb.XGBClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=6,
            random_state=42,
            n_jobs=-1,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        results = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_test, y_prob)
        }
        
        logger.info(f"   Accuracy: {results['accuracy']:.4f}")
        logger.info(f"   F1 Score: {results['f1']:.4f}")
        logger.info(f"   AUC-ROC: {results['auc_roc']:.4f}")
        
        return results, model
    
    def test_random_forest(self, X_train, X_test, y_train, y_test):
        """Test Random Forest classifier"""
        logger.info("\n🧪 Testing Random Forest...")
        
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        results = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_test, y_prob)
        }
        
        logger.info(f"   Accuracy: {results['accuracy']:.4f}")
        logger.info(f"   F1 Score: {results['f1']:.4f}")
        logger.info(f"   AUC-ROC: {results['auc_roc']:.4f}")
        
        return results, model
    
    def test_logistic_regression(self, X_train, X_test, y_train, y_test):
        """Test Logistic Regression baseline"""
        logger.info("\n🧪 Testing Logistic Regression...")
        
        model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        results = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_test, y_prob)
        }
        
        logger.info(f"   Accuracy: {results['accuracy']:.4f}")
        logger.info(f"   F1 Score: {results['f1']:.4f}")
        logger.info(f"   AUC-ROC: {results['auc_roc']:.4f}")
        
        return results, model
    
    def run_comparison(self):
        """Run all models and compare results"""
        logger.info("="*60)
        logger.info("🔬 MODEL COMPARISON TEST")
        logger.info("="*60)
        
        # Load data
        X_train, X_test, y_train, y_test = self.load_and_prepare_data()
        
        # Test all models
        results = {}
        models = {}
        
        # LightGBM
        results['LightGBM'], models['LightGBM'] = self.test_lightgbm(
            X_train, X_test, y_train, y_test
        )
        
        # XGBoost
        results['XGBoost'], models['XGBoost'] = self.test_xgboost(
            X_train, X_test, y_train, y_test
        )
        
        # Random Forest
        results['RandomForest'], models['RandomForest'] = self.test_random_forest(
            X_train, X_test, y_train, y_test
        )
        
        # Logistic Regression (baseline)
        results['LogisticRegression'], models['LogisticRegression'] = self.test_logistic_regression(
            X_train, X_test, y_train, y_test
        )
        
        # Create comparison dataframe
        comparison = pd.DataFrame(results).T
        comparison = comparison.round(4)
        
        # Add ranking
        comparison['rank_accuracy'] = comparison['accuracy'].rank(ascending=False)
        comparison['rank_f1'] = comparison['f1'].rank(ascending=False)
        comparison['avg_rank'] = (comparison['rank_accuracy'] + comparison['rank_f1']) / 2
        
        logger.info("\n" + "="*60)
        logger.info("📊 MODEL COMPARISON RESULTS")
        logger.info("="*60)
        logger.info("\n" + comparison.to_string())
        
        # Find best model
        best_model = comparison['avg_rank'].idxmin()
        logger.info(f"\n🏆 BEST MODEL: {best_model}")
        logger.info(f"   Accuracy: {comparison.loc[best_model, 'accuracy']:.4f}")
        logger.info(f"   F1 Score: {comparison.loc[best_model, 'f1']:.4f}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison.to_csv(f'model_comparison_{timestamp}.csv')
        logger.info(f"\n💾 Results saved to model_comparison_{timestamp}.csv")
        
        return comparison, models

def main():
    comparator = ModelComparator()
    comparison, models = comparator.run_comparison()
    
    # Ask user if they want to switch to the best model
    best_model_name = comparison['avg_rank'].idxmin()
    print(f"\n🎯 Best model is: {best_model_name}")
    
    response = input(f"\nSwitch to {best_model_name} as the default model? (yes/no): ")
    if response.lower() == 'yes':
        # Save the best model
        best_model = models[best_model_name]
        
        # Create model directory if it doesn't exist
        os.makedirs('models/recommendation_model', exist_ok=True)
        
        # Save as new best model
        joblib.dump(best_model, 'models/recommendation_model/model_best.pkl')
        
        # Update metadata
        metadata = {
            'model_name': best_model_name,
            'metrics': comparison.loc[best_model_name].to_dict(),
            'timestamp': datetime.now().isoformat(),
            'features': comparator.data_gen.feature_columns
        }
        
        with open('models/recommendation_model/metadata_best.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Switched to {best_model_name} as default model!")
    else:
        print("Keeping current model (LightGBM)")

if __name__ == "__main__":
    main()