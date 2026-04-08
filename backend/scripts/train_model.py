#!/usr/bin/env python3

import sys
import os
# Add the parent directory to path so we can import from ml
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.train_pipeline import TrainingPipeline
import logging
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'training_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Train recommendation model')
    parser.add_argument('--days', type=int, default=90, help='Days of history to use')
    parser.add_argument('--min-missions', type=int, default=5, help='Minimum missions per user')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set size')
    parser.add_argument('--no-save', action='store_true', help='Skip saving model')
    parser.add_argument('--no-db', action='store_true', help='Skip database logging')
    parser.add_argument('--schedule', action='store_true', help='Run as scheduled job')
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("🚀 Starting model training")
    logger.info(f"Args: {args}")
    logger.info("="*60)
    
    pipeline = TrainingPipeline()
    
    if args.schedule:
        # For scheduled retraining, use default parameters
        result = pipeline.retrain_with_new_data()
    else:
        result = pipeline.run(
            days_history=args.days,
            min_missions=args.min_missions,
            test_size=args.test_size,
            save_model=not args.no_save,
            log_to_db=not args.no_db
        )
    
    if result:
        logger.info("✅ Training completed successfully")
        logger.info(f"📊 Model metrics: {result.get('metrics', {})}")
    else:
        logger.error("❌ Training failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
