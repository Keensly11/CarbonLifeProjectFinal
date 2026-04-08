"""
ML Model for personalized mission recommendations.
Uses LightGBM for high performance and interpretability.
"""

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import joblib
import json
import logging
import os
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SessionLocal, ModelMetadata

logger = logging.getLogger(__name__)

class MissionRecommendationModel:
    """
    LightGBM model that predicts mission success probability.
    """
    
    def __init__(self, model_path='models/recommendation_model'):
        self.model_path = model_path
        self.model = None
        self.feature_importance = None
        self.model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metadata = None
        
    def build_model(self, params=None):
        """
        Build LightGBM model with optimized parameters.
        """
        default_params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'min_data_in_leaf': 20,
            'num_threads': 4,
            'random_state': 42
        }
        
        if params:
            default_params.update(params)
        
        self.model = lgb.LGBMClassifier(**default_params)
        logger.info(f"✅ Model built with params: {default_params}")
        
    def train(self, X_train, y_train, X_val=None, y_val=None, 
              feature_names=None, categorical_features=None):
        """
        Train the model with early stopping.
        """
        if self.model is None:
            self.build_model()
        
        # Prepare evaluation set
        eval_set = [(X_train, y_train)]
        eval_names = ['train']
        
        if X_val is not None and y_val is not None:
            eval_set.append((X_val, y_val))
            eval_names.append('validation')
        
        # Train with early stopping
        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            eval_names=eval_names,
            eval_metric=['auc', 'binary_logloss'],
            callbacks=[
                lgb.early_stopping(stopping_rounds=50),
                lgb.log_evaluation(50)
            ],
            categorical_feature=categorical_features or 'auto'
        )
        
        # Store feature importance
        self.feature_importance = pd.DataFrame({
            'feature': feature_names if feature_names else [f'f{i}' for i in range(X_train.shape[1])],
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        logger.info("✅ Model training complete")
        logger.info(f"\nTop 10 important features:\n{self.feature_importance.head(10)}")
        
    def evaluate(self, X_test, y_test):
        """
        Evaluate model performance on test set.
        """
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1_score': f1_score(y_test, y_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_test, y_prob)
        }
        
        logger.info("📊 Model Evaluation:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")
        
        return metrics
    
    def predict_proba(self, features):
        """
        Predict probability of mission success.
        """
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        return self.model.predict_proba(features)[:, 1]
    
    def predict(self, features, threshold=0.5):
        """
        Predict binary outcome (success/failure).
        """
        proba = self.predict_proba(features)
        return (proba >= threshold).astype(int)
    
    def save_model(self, metadata=None):
        """
        Save model and metadata to disk.
        """
        os.makedirs(self.model_path, exist_ok=True)
        
        # Save model
        model_file = f"{self.model_path}/model_{self.model_version}.pkl"
        joblib.dump(self.model, model_file)
        
        # Save feature importance
        if self.feature_importance is not None:
            self.feature_importance.to_csv(
                f"{self.model_path}/feature_importance_{self.model_version}.csv", 
                index=False
            )
        
        # Save metadata
        self.metadata = metadata or {}
        self.metadata.update({
            'model_version': self.model_version,
            'saved_at': datetime.now().isoformat(),
            'feature_importance': self.feature_importance.to_dict() if self.feature_importance is not None else None
        })
        
        with open(f"{self.model_path}/metadata_{self.model_version}.json", 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
        
        logger.info(f"✅ Model saved to {model_file}")
        
        # Also save as latest version (for easy loading)
        joblib.dump(self.model, f"{self.model_path}/model_latest.pkl")
        with open(f"{self.model_path}/metadata_latest.json", 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
        
        return model_file
    
    def load_model(self, version='latest'):
        """
        Load a trained model.
        
        Args:
            version: 'latest' or specific version string
        """
        if version == 'latest':
            model_file = f"{self.model_path}/model_latest.pkl"
            metadata_file = f"{self.model_path}/metadata_latest.json"
        else:
            model_file = f"{self.model_path}/model_{version}.pkl"
            metadata_file = f"{self.model_path}/metadata_{version}.json"
        
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Model not found: {model_file}")
        
        self.model = joblib.load(model_file)
        
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                self.metadata = json.load(f)
            self.model_version = self.metadata.get('model_version', version)
        
        logger.info(f"✅ Model loaded from {model_file}")
        return self.model
    
    def log_to_database(self, db, metrics, training_samples):
        """
        Log model metadata to database for tracking.
        """
        model_metadata = ModelMetadata(
            model_name='mission_recommendation',
            model_version=self.model_version,
            model_type='lightgbm_classifier',
            accuracy=metrics.get('accuracy'),
            precision=metrics.get('precision'),
            recall=metrics.get('recall'),
            f1_score=metrics.get('f1_score'),
            auc_roc=metrics.get('auc_roc'),
            training_date=datetime.now(),
            training_samples=training_samples,
            features_used=json.dumps(list(self.feature_importance['feature']) if self.feature_importance is not None else []),
            model_path=f"{self.model_path}/model_{self.model_version}.pkl",
            is_active=True
        )
        
        # Deactivate old models
        db.query(ModelMetadata).filter(
            ModelMetadata.model_name == 'mission_recommendation'
        ).update({'is_active': False})
        
        db.add(model_metadata)
        db.commit()
        
        logger.info(f"✅ Model metadata logged to database, ID: {model_metadata.id}")
        return model_metadata.id