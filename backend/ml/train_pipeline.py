import sys
import os
# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from ml module
from ml.training_data import TrainingDataGenerator, training_data_gen
from ml.recommendation_model import MissionRecommendationModel
from models import SessionLocal
import logging
import argparse
from datetime import datetime
import numpy as np
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainingPipeline:
    
    def __init__(self):
        self.data_gen = TrainingDataGenerator()
        self.model = MissionRecommendationModel()
        
    def run(self, days_history=365, min_missions=3, test_size=0.2, 
            save_model=True, log_to_db=True):
        
        start_time = time.time()
        
        logger.info("="*60)
        logger.info("🚀 Starting ML Training Pipeline")
        logger.info(f"📊 Using {days_history} days history, min {min_missions} missions")
        logger.info("="*60)
        
        # Step 1: Load data
        logger.info("\n📥 Step 1: Loading training data")
        df = self.data_gen.load_training_data(
            days_history=days_history,
            min_missions=min_missions
        )
        
        if len(df) == 0:
            logger.error("❌ No training data available")
            return
        
        logger.info(f"✅ Loaded {len(df)} total samples")
        
        # Step 2: Prepare features
        logger.info("\n🛠️ Step 2: Preparing features")
        X, y, df_prepared = self.data_gen.prepare_features(df, fit_encoders=True)
        
        logger.info(f"✅ Feature matrix shape: {X.shape}")
        logger.info(f"✅ Class distribution: {np.bincount(y.astype(int))}")
        
        # Step 3: Train/test split
        logger.info("\n📊 Step 3: Splitting data")
        train_df, test_df = self.data_gen.get_train_test_split(
            df_prepared, test_size=test_size
        )
        
        X_train, y_train, _ = self.data_gen.prepare_features(train_df, fit_encoders=False)
        X_test, y_test, _ = self.data_gen.prepare_features(test_df, fit_encoders=False)
        
        logger.info(f"📈 Training samples: {len(X_train)} ({len(X_train)/len(X)*100:.1f}%)")
        logger.info(f"📉 Testing samples: {len(X_test)} ({len(X_test)/len(X)*100:.1f}%)")
        
        # Step 4: Build and train model
        logger.info("\n🧠 Step 4: Training model")
        self.model.build_model()
        
        # Train with progress tracking
        logger.info("   Training in progress... (may take 20-30 seconds for 25,000 samples)")
        self.model.train(
            X_train, y_train,
            X_val=X_test, y_val=y_test,
            feature_names=self.data_gen.feature_columns
        )
        
        # Step 5: Evaluate
        logger.info("\n📈 Step 5: Evaluating model")
        metrics = self.model.evaluate(X_test, y_test)
        
        # Step 6: Save preprocessors
        logger.info("\n💾 Step 6: Saving preprocessors")
        self.data_gen.save_preprocessors()
        
        # Step 7: Save model
        if save_model:
            logger.info("\n💾 Step 7: Saving model")
            metadata = {
                'training_date': datetime.now().isoformat(),
                'days_history': days_history,
                'min_missions': min_missions,
                'test_size': test_size,
                'total_samples': len(df),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'metrics': metrics,
                'feature_columns': self.data_gen.feature_columns
            }
            model_path = self.model.save_model(metadata)
            
            # Step 8: Log to database
            if log_to_db:
                logger.info("\n📝 Step 8: Logging to database")
                db = SessionLocal()
                try:
                    self.model.log_to_database(
                        db, metrics, training_samples=len(X_train)
                    )
                finally:
                    db.close()
        
        elapsed_time = time.time() - start_time
        logger.info("\n" + "="*60)
        logger.info("✅ Training pipeline completed successfully!")
        logger.info(f"⏱️  Total time: {elapsed_time:.2f} seconds")
        logger.info("="*60)
        
        # Print key metrics
        logger.info("\n📊 FINAL MODEL PERFORMANCE:")
        logger.info(f"   Accuracy:  {metrics['accuracy']:.2%}")
        logger.info(f"   Precision: {metrics['precision']:.2%}")
        logger.info(f"   Recall:    {metrics['recall']:.2%}")
        logger.info(f"   F1 Score:  {metrics['f1_score']:.2%}")
        logger.info(f"   AUC-ROC:   {metrics['auc_roc']:.3f}")
        logger.info("="*60)
        
        return {
            'model': self.model,
            'metrics': metrics,
            'model_path': model_path if save_model else None
        }
    
    def retrain_with_new_data(self):
        logger.info("🔄 Starting retraining job...")
        
        # Run with optimized parameters for 25,000 samples
        result = self.run(
            days_history=365,      # Use full year
            min_missions=3,         # Include users with at least 3 missions
            test_size=0.2,          # 80/20 split
            save_model=True,
            log_to_db=True
        )
        
        return result

def main():
    parser = argparse.ArgumentParser(description='Train recommendation model')
    parser.add_argument('--days', type=int, default=365, help='Days of history')
    parser.add_argument('--min-missions', type=int, default=3, help='Minimum missions per user')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set size')
    parser.add_argument('--no-save', action='store_true', help='Skip saving model')
    parser.add_argument('--no-db', action='store_true', help='Skip database logging')
    
    args = parser.parse_args()
    
    pipeline = TrainingPipeline()
    pipeline.run(
        days_history=args.days,
        min_missions=args.min_missions,
        test_size=args.test_size,  
        save_model=not args.no_save,
        log_to_db=not args.no_db
    )

if __name__ == "__main__":
    main()