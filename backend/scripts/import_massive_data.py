"""
Import massive training data (25,000 samples) into database
"""

import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from models import SessionLocal, User, Mission, UserMLFeatures
from datetime import datetime
import random

print('📥 Loading massive training data...')
df = pd.read_csv('ukdale_training_data_massive.csv')
print(f'✅ Loaded {len(df)} samples')

db = SessionLocal()
try:
    # Clear old training data
    print('🧹 Clearing old training data...')
    db.query(Mission).filter(Mission.title.like('Training%')).delete()
    db.query(UserMLFeatures).filter(UserMLFeatures.user_id > 100).delete()
    db.query(User).filter(User.username.like('training%')).delete()
    db.commit()
    
    # Create users for each house with variations
    users = {}
    print('👥 Creating training users...')
    
    # Get unique house IDs
    house_ids = df['user_id'].unique()
    print(f"Found houses: {house_ids}")
    
    for house_id in house_ids:
        for i in range(5):  # Create 5 variations per house
            # Get a sample row for this house
            house_rows = df[df['user_id'] == house_id]
            if len(house_rows) == 0:
                continue
                
            user_data = house_rows.iloc[0]
            username = f'training_house_{int(house_id)}_v{i}'
            
            user = User(
                username=username,
                email=f'{username}@training.local',
                full_name=f'Training House {int(house_id)} Var {i}',
                hashed_password='training_password',
                emirate=str(user_data['emirate']),
                home_type=str(user_data['home_type']),
                bedrooms=int(user_data['bedrooms']),
                vehicle_type=str(user_data['vehicle_type']),
                vehicle_fuel=str(user_data['vehicle_fuel']),
                ukdale_house_id=int(house_id),
                is_active=True
            )
            db.add(user)
            db.flush()
            users[f'{int(house_id)}_{i}'] = user.id
            print(f"  Created user: {username}")
    
    db.commit()
    print(f'✅ Created {len(users)} training users')
    
    # Create missions
    mission_count = 0
    print('🎯 Creating missions...')
    
    # Process in batches to avoid memory issues
    batch_size = 1000
    total_rows = len(df)
    
    for start_idx in range(0, total_rows, batch_size):
        end_idx = min(start_idx + batch_size, total_rows)
        batch_df = df.iloc[start_idx:end_idx]
        
        for _, row in batch_df.iterrows():
            # Randomly assign to one of the 5 user variations for this house
            user_key = f"{int(row['user_id'])}_{random.randint(0,4)}"
            
            if user_key in users:
                mission = Mission(
                    user_id=users[user_key],
                    title=f"Training: {row['mission_category']}",
                    description=f"Complete this {row['mission_category']} mission",
                    category=str(row['mission_category']),
                    difficulty=str(row['mission_difficulty']),
                    tokens_reward=int(row['tokens_reward']),
                    co2_saved_kg=float(row['co2_potential']),
                    experience_points=int(row['tokens_reward']) // 2,
                    status='completed' if row['success'] == 1 else 'failed',
                    progress=100 if row['success'] == 1 else 0,
                    ml_generated=True,
                    ml_confidence=0.8,
                    created_at=datetime.now()
                )
                db.add(mission)
                mission_count += 1
        
        db.commit()
        print(f'  ✅ {mission_count} missions created...')
    
    print(f'✅ Created {mission_count} missions!')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
    print('👋 Done!')