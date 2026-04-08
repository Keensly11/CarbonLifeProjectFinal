"""
API endpoints for ML data collection and feature access.
Now ML-only - no fallbacks!
Includes emirate-based filtering for location-specific missions.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SessionLocal, User
from ml.prediction_service import prediction_service
import logging
import random

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["ML Recommendations"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== EXPANDED MISSION TEMPLATES WITH EMIRATE FILTERS ==========
MISSION_TEMPLATES = [
    # ENERGY MISSIONS (10) - Applicable to all emirates
    {
        'id': 'rec_001',
        'title': 'Reduce AC during peak hours',
        'description': 'Set thermostat 2°C higher from 2-5 PM',
        'category': 'energy',
        'difficulty': 'easy',
        'savings_kg_co2': 3.5,
        'tokens_reward': 75,
        'estimated_time': '1 minute',
        'uae_context': 'Peak electricity rates apply in UAE',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']  # All emirates
    },
    {
        'id': 'rec_002',
        'title': 'Optimize AC temperature',
        'description': 'Set to 24°C for optimal efficiency',
        'category': 'energy',
        'difficulty': 'easy',
        'savings_kg_co2': 2.5,
        'tokens_reward': 50,
        'estimated_time': '1 minute',
        'uae_context': 'Each degree saves 5-10% on cooling costs',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_003',
        'title': 'Unplug standby devices',
        'description': 'Save energy from electronics on standby',
        'category': 'energy',
        'difficulty': 'easy',
        'savings_kg_co2': 0.8,
        'tokens_reward': 25,
        'estimated_time': '3 minutes',
        'uae_context': 'UAE homes have 10+ devices on standby',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_004',
        'title': 'Use LED bulbs',
        'description': 'Replace old bulbs with LED',
        'category': 'energy',
        'difficulty': 'medium',
        'savings_kg_co2': 2.0,
        'tokens_reward': 40,
        'estimated_time': '15 minutes',
        'uae_context': 'LEDs use 75% less energy',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_005',
        'title': 'Wash clothes in cold water',
        'description': 'Skip the hot cycle',
        'category': 'energy',
        'difficulty': 'easy',
        'savings_kg_co2': 0.5,
        'tokens_reward': 15,
        'estimated_time': '1 minute',
        'uae_context': '90% of energy goes to heating water',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_006',
        'title': 'Air dry laundry',
        'description': 'Skip the dryer, use晾衣架',
        'category': 'energy',
        'difficulty': 'medium',
        'savings_kg_co2': 1.8,
        'tokens_reward': 35,
        'estimated_time': '5 minutes',
        'uae_context': 'UAE sun is perfect for drying',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_007',
        'title': 'Clean AC filters',
        'description': 'Dirty filters reduce efficiency',
        'category': 'energy',
        'difficulty': 'medium',
        'savings_kg_co2': 2.2,
        'tokens_reward': 45,
        'estimated_time': '10 minutes',
        'uae_context': 'Clean filters can save 15% on cooling',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_008',
        'title': 'Check fridge seals',
        'description': 'Ensure door seals are tight',
        'category': 'energy',
        'difficulty': 'medium',
        'savings_kg_co2': 1.2,
        'tokens_reward': 30,
        'estimated_time': '5 minutes',
        'uae_context': 'Fridge works harder in UAE heat',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_009',
        'title': 'Use ceiling fans',
        'description': 'Fans allow higher AC temp',
        'category': 'energy',
        'difficulty': 'easy',
        'savings_kg_co2': 2.8,
        'tokens_reward': 55,
        'estimated_time': '1 minute',
        'uae_context': 'You can raise AC by 2°C with fans',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_010',
        'title': 'Close curtains during peak heat',
        'description': 'Block sunlight, reduce cooling load',
        'category': 'energy',
        'difficulty': 'easy',
        'savings_kg_co2': 1.5,
        'tokens_reward': 30,
        'estimated_time': '2 minutes',
        'uae_context': 'Solar heat gain is huge in UAE',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    
    # TRANSPORT MISSIONS (10) - With emirate-specific filters
    {
        'id': 'rec_011',
        'title': 'Take Dubai Metro',
        'description': 'Use public transport instead of car',
        'category': 'transport',
        'difficulty': 'medium',
        'savings_kg_co2': 8.5,
        'tokens_reward': 100,
        'estimated_time': '25 minutes',
        'uae_context': 'Dubai Metro is world-class',
        'emirates': ['Dubai']  # ONLY Dubai
    },
    {
        'id': 'rec_012',
        'title': 'Carpool with colleagues',
        'description': 'Share ride to reduce emissions',
        'category': 'transport',
        'difficulty': 'medium',
        'savings_kg_co2': 6.5,
        'tokens_reward': 75,
        'estimated_time': '5 minutes',
        'uae_context': 'Average car occupancy in UAE is 1.2',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_013',
        'title': 'Pre-cool car before driving',
        'description': 'Remote start to reduce AC load',
        'category': 'transport',
        'difficulty': 'easy',
        'savings_kg_co2': 1.2,
        'tokens_reward': 40,
        'estimated_time': '2 minutes',
        'uae_context': 'Pre-cooling uses less energy than driving with full AC',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_014',
        'title': 'Check tire pressure',
        'description': 'Proper inflation saves fuel',
        'category': 'transport',
        'difficulty': 'easy',
        'savings_kg_co2': 1.5,
        'tokens_reward': 35,
        'estimated_time': '5 minutes',
        'uae_context': 'Under-inflated tires increase fuel use by 3%',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_015',
        'title': 'Combine errands into one trip',
        'description': 'Plan to drive less',
        'category': 'transport',
        'difficulty': 'easy',
        'savings_kg_co2': 3.0,
        'tokens_reward': 45,
        'estimated_time': '5 minutes planning',
        'uae_context': 'UAE malls have everything in one place',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_016',
        'title': 'Try Abu Dhabi bus',
        'description': 'Use public transport in capital',
        'category': 'transport',
        'difficulty': 'medium',
        'savings_kg_co2': 7.5,
        'tokens_reward': 90,
        'estimated_time': '30 minutes',
        'uae_context': 'Abu Dhabi buses are modern and clean',
        'emirates': ['Abu Dhabi']  # ONLY Abu Dhabi
    },
    {
        'id': 'rec_017',
        'title': 'Work from home one day',
        'description': 'Avoid commute entirely',
        'category': 'transport',
        'difficulty': 'medium',
        'savings_kg_co2': 12.0,
        'tokens_reward': 120,
        'estimated_time': 'All day',
        'uae_context': 'Many UAE companies support remote work',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_018',
        'title': 'Use electric scooter for short trips',
        'description': 'Skip the car for errands',
        'category': 'transport',
        'difficulty': 'medium',
        'savings_kg_co2': 2.5,
        'tokens_reward': 50,
        'estimated_time': '10 minutes',
        'uae_context': 'Dubai has dedicated scooter lanes',
        'emirates': ['Dubai', 'Abu Dhabi']  # Major cities
    },
    {
        'id': 'rec_019',
        'title': 'Avoid peak hour traffic',
        'description': 'Drive when traffic is lighter',
        'category': 'transport',
        'difficulty': 'hard',
        'savings_kg_co2': 4.0,
        'tokens_reward': 60,
        'estimated_time': 'Adjust schedule',
        'uae_context': 'Stop-start traffic increases emissions by 40%',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah']  # Busy emirates
    },
    {
        'id': 'rec_020',
        'title': 'Consider hybrid/electric vehicle',
        'description': 'Research cleaner cars',
        'category': 'transport',
        'difficulty': 'hard',
        'savings_kg_co2': 25.0,
        'tokens_reward': 200,
        'estimated_time': 'Research time',
        'uae_context': 'UAE has growing EV infrastructure',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    
    # WATER CONSERVATION (5) - Applicable to all
    {
        'id': 'rec_021',
        'title': 'Shorten shower by 2 minutes',
        'description': 'Save water and energy',
        'category': 'water',
        'difficulty': 'easy',
        'savings_kg_co2': 0.4,
        'tokens_reward': 20,
        'estimated_time': '2 minutes',
        'uae_context': 'UAE has high water production costs',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_022',
        'title': 'Fix dripping taps',
        'description': 'One drop per second wastes 20L/day',
        'category': 'water',
        'difficulty': 'medium',
        'savings_kg_co2': 0.6,
        'tokens_reward': 25,
        'estimated_time': '15 minutes',
        'uae_context': 'Desalination is energy intensive',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_023',
        'title': 'Use dishwasher efficiently',
        'description': 'Run only when full',
        'category': 'water',
        'difficulty': 'easy',
        'savings_kg_co2': 0.8,
        'tokens_reward': 30,
        'estimated_time': '1 minute',
        'uae_context': 'Modern dishwashers use less water than hand washing',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_024',
        'title': 'Water plants in evening',
        'description': 'Reduce evaporation',
        'category': 'water',
        'difficulty': 'easy',
        'savings_kg_co2': 0.3,
        'tokens_reward': 15,
        'estimated_time': '5 minutes',
        'uae_context': 'UAE sun evaporates water quickly',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    },
    {
        'id': 'rec_025',
        'title': 'Install water-efficient showerhead',
        'description': 'Reduce flow without losing pressure',
        'category': 'water',
        'difficulty': 'hard',
        'savings_kg_co2': 1.2,
        'tokens_reward': 40,
        'estimated_time': '20 minutes',
        'uae_context': 'DEWA offers rebates on efficient fixtures',
        'emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'RAK', 'Fujairah', 'Umm Al Quwain']
    }
]

def generate_personalized_message(mission, user):
    """Create a personalized message using user's profile"""
    templates = {
        'energy': [
            f"{user.full_name or user.username}, your {user.bedrooms}-bedroom {user.home_type} in {user.emirate} could save {mission['savings_kg_co2']}kg CO₂ by {mission['title'].lower()}!",
            f"Based on your {user.home_type}'s energy pattern, try: {mission['title']}",
            f"Perfect for your {user.bedrooms}-bedroom home: {mission['title']}",
        ],
        'transport': [
            f"{user.full_name or user.username}, your {user.vehicle_type} could be greener! {mission['title']} saves {mission['savings_kg_co2']}kg CO₂.",
            f"Since you drive a {user.vehicle_type}, {mission['title'].lower()} would make a big impact.",
            f"Try this {mission['difficulty']} transport tip: {mission['title']}",
        ],
        'water': [
            f"{user.full_name or user.username}, saving water also saves energy! {mission['title']}.",
            f"In {user.emirate}, every drop counts. {mission['title']}",
            f"Water-saving tip for your {user.home_type}: {mission['title']}",
        ]
    }
    return random.choice(templates.get(mission['category'], [mission['description']]))

@router.get("/ml/{user_id}")
async def get_ml_recommendations(
    user_id: int,
    n: int = 5,
    db: Session = Depends(get_db)
):
    """Get ML-powered personalized recommendations for a user - ML ONLY!"""
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Filter missions by user's emirate
        filtered_templates = []
        for mission in MISSION_TEMPLATES:
            # Check if mission has emirates filter
            if 'emirates' in mission:
                # Include only if user's emirate is in the allowed list
                if user.emirate in mission['emirates']:
                    filtered_templates.append(mission)
            else:
                # If no filter, include for all users (backward compatibility)
                filtered_templates.append(mission)
        
        logger.info(f"🎯 Filtered {len(filtered_templates)} missions for user in {user.emirate}")
        
        # Get ML recommendations from prediction service with filtered templates
        recommendations = prediction_service.get_top_recommendations(
            user_id=user_id,
            mission_templates=filtered_templates,
            n=n
        )
        
        # Add user-specific personalization
        for rec in recommendations:
            rec['personalized_message'] = generate_personalized_message(rec, user)
            rec['user_id'] = user_id
            rec['user_name'] = user.full_name or user.username
        
        # Log that we're using ML (for debugging)
        logger.info(f"✅ ML recommendations generated for user {user_id}: {len(recommendations)} missions")
        if recommendations:
            logger.info(f"   Top mission: {recommendations[0]['title']} with {recommendations[0]['relevance_score']}% confidence")
        
        return recommendations
        
    except Exception as e:
        # NO FALLBACK - throw error if ML fails
        logger.error(f"❌ ML recommendation service failed for user {user_id}: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"ML recommendation service unavailable: {str(e)}"
        )