#!/usr/bin/env python3
"""
Train NILM models on UK-DALE data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from ml.nilm_trainer import nilm_trainer
from ml.nilm_processor import signal_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Train NILM models on all UK-DALE houses"""
    logger.info("="*60)
    logger.info("🚀 Training NILM Models on UK-DALE")
    logger.info("="*60)
    
    all_features = []
    all_ground_truth = []
    
    # Train on each house
    for house_id in range(1, 6):
        logger.info(f"\n🏠 Processing House {house_id}")
        
        # Prepare training data
        X, y = nilm_trainer.prepare_training_data(
            house_id=house_id,
            samples=100000  # Use 100k samples per house
        )
        
        if X is not None and y is not None:
            all_features.append(X)
            all_ground_truth.append(y)
    
    if not all_features:
        logger.error("❌ No training data available")
        return
    
    # Combine all houses
    import pandas as pd
    X_combined = pd.concat(all_features, ignore_index=True)
    y_combined = pd.concat(all_ground_truth, ignore_index=True)
    
    logger.info(f"\n📊 Combined dataset: {len(X_combined)} samples")
    
    # Train models
    results = nilm_trainer.train_models(X_combined, y_combined)
    
    # Save models
    nilm_trainer.save_models()
    
    # Print results
    logger.info("\n" + "="*60)
    logger.info("📊 NILM Training Results")
    logger.info("="*60)
    for appliance, metrics in results.items():
        logger.info(f"{appliance:15} MAE: {metrics['mae']:5.2f}W  R²: {metrics['r2']:.3f}")
    
    logger.info("\n✅ NILM training complete!")

if __name__ == "__main__":
    main()