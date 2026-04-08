from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SessionLocal, User
from ml.nilm_service import nilm_service
from ml.prediction_service import prediction_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nilm", tags=["NILM"])

# Pydantic models
class NILMRequest(BaseModel):
    total_power: float
    user_id: Optional[int] = None
    house_id: Optional[int] = None

class NILMResponse(BaseModel):
    ac: int
    fridge: int
    lights: int
    washing_machine: int
    dishwasher: int
    kettle: int
    microwave: int
    tv: int
    computer: int
    oven: int
    dryer: int
    vacuum: int
    water_heater: int
    iron: int
    other: int
    timestamp: datetime

class RealtimeRecommendation(BaseModel):
    id: str
    title: str
    message: str
    appliance: str
    current_power: int
    savings_estimate: float
    tokens_reward: int
    priority: str  # high, medium, low

class RealtimeRecommendationsResponse(BaseModel):
    recommendations: List[RealtimeRecommendation]
    total_power: int
    timestamp: datetime
    appliance_breakdown: Dict[str, int]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/disaggregate", response_model=NILMResponse)
async def nilm_disaggregate(
    request: NILMRequest,
    db: Session = Depends(get_db)
):
    """Disaggregate total power into appliance-level consumption"""
    try:
        house_id = request.house_id
        if request.user_id and not house_id:
            user = db.query(User).filter(User.id == request.user_id).first()
            if user:
                house_id = user.ukdale_house_id
        
        result = nilm_service.disaggregate(
            total_power=request.total_power,
            house_id=house_id
        )
        
        result['timestamp'] = datetime.now()
        
        # Ensure all expected fields exist
        expected_fields = ['ac', 'fridge', 'lights', 'washing_machine', 'dishwasher',
                          'kettle', 'microwave', 'tv', 'computer', 'oven', 'dryer',
                          'vacuum', 'water_heater', 'iron', 'other']
        
        for field in expected_fields:
            if field not in result:
                result[field] = 0
        
        return result
        
    except Exception as e:
        logger.error(f"NILM disaggregation error: {e}")
        return {
            "ac": 0, "fridge": 0, "lights": 0, "washing_machine": 0,
            "dishwasher": 0, "kettle": 0, "microwave": 0, "tv": 0,
            "computer": 0, "oven": 0, "dryer": 0, "vacuum": 0,
            "water_heater": 0, "iron": 0, "other": 0,
            "timestamp": datetime.now()
        }

@router.get("/realtime-recommendations/{user_id}", response_model=RealtimeRecommendationsResponse)
async def get_realtime_recommendations(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate real-time recommendations based on current appliance usage
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get current power (simplified - in production, get from Kafka cache)
    from api.main import realtime_cache
    current_power = 0
    for household, readings in realtime_cache.items():
        if readings:
            current_power = readings[-1]['power_watts']
            break
    
    if current_power == 0:
        current_power = 2000  # Default fallback
    
    # Get appliance breakdown
    appliances = nilm_service.disaggregate(current_power, user.ukdale_house_id)
    
    recommendations = []
    
    # AC recommendations
    ac_power = appliances.get('ac', 0)
    if ac_power > 1500:
        recommendations.append({
            'id': 'nilm_ac_001',
            'title': 'High AC Usage Detected',
            'message': f'Your AC is using {ac_power}W. Raising the temperature by 2°C could save significant energy.',
            'appliance': 'ac',
            'current_power': ac_power,
            'savings_estimate': round(ac_power * 0.15 / 1000 * 0.35, 2),
            'tokens_reward': 75,
            'priority': 'high'
        })
    elif ac_power > 1000:
        recommendations.append({
            'id': 'nilm_ac_002',
            'title': 'Optimize AC Settings',
            'message': f'Your AC is using {ac_power}W. Consider using fan mode during milder hours.',
            'appliance': 'ac',
            'current_power': ac_power,
            'savings_estimate': round(ac_power * 0.08 / 1000 * 0.35, 2),
            'tokens_reward': 50,
            'priority': 'medium'
        })
    
    # Fridge recommendations
    fridge_power = appliances.get('fridge', 0)
    if fridge_power > 250:
        recommendations.append({
            'id': 'nilm_fridge_001',
            'title': 'Fridge Running High',
            'message': f'Your fridge is using {fridge_power}W. Check door seals and temperature settings.',
            'appliance': 'fridge',
            'current_power': fridge_power,
            'savings_estimate': round(fridge_power * 0.15 / 1000 * 0.35, 2),
            'tokens_reward': 40,
            'priority': 'medium'
        })
    
    # Kettle recommendation (short spikes)
    kettle_power = appliances.get('kettle', 0)
    if kettle_power > 2000:
        recommendations.append({
            'id': 'nilm_kettle_001',
            'title': 'Efficient Kettle Use',
            'message': 'Only boil the water you need. A full kettle uses 50% more energy.',
            'appliance': 'kettle',
            'current_power': kettle_power,
            'savings_estimate': 0.05,
            'tokens_reward': 25,
            'priority': 'low'
        })
    
    # Washing machine recommendation
    wm_power = appliances.get('washing_machine', 0)
    if wm_power > 500:
        recommendations.append({
            'id': 'nilm_wm_001',
            'title': 'Wash Smarter',
            'message': 'Use cold water cycle. 90% of washing machine energy goes to heating water.',
            'appliance': 'washing_machine',
            'current_power': wm_power,
            'savings_estimate': round(wm_power * 0.7 / 1000 * 0.35, 2),
            'tokens_reward': 60,
            'priority': 'medium'
        })
    
    # Dishwasher recommendation
    dw_power = appliances.get('dishwasher', 0)
    if dw_power > 800:
        recommendations.append({
            'id': 'nilm_dw_001',
            'title': 'Efficient Dishwasher Use',
            'message': 'Run dishwasher only when full and use eco mode.',
            'appliance': 'dishwasher',
            'current_power': dw_power,
            'savings_estimate': round(dw_power * 0.2 / 1000 * 0.35, 2),
            'tokens_reward': 35,
            'priority': 'low'
        })
    
    # Lights recommendation (evening)
    from datetime import datetime as dt
    current_hour = dt.now().hour
    lights_power = appliances.get('lights', 0)
    if lights_power > 200 and (current_hour >= 18 or current_hour <= 6):
        recommendations.append({
            'id': 'nilm_lights_001',
            'title': 'Lighting Optimization',
            'message': f'Your lights are using {lights_power}W. Consider LED bulbs to reduce by 75%.',
            'appliance': 'lights',
            'current_power': lights_power,
            'savings_estimate': round(lights_power * 0.75 / 1000 * 0.35, 2),
            'tokens_reward': 45,
            'priority': 'medium'
        })
    
    # Dryer recommendation
    dryer_power = appliances.get('dryer', 0)
    if dryer_power > 1000:
        recommendations.append({
            'id': 'nilm_dryer_001',
            'title': 'Air Dry When Possible',
            'message': 'Your dryer is using significant power. Consider air drying in UAE\'s warm climate.',
            'appliance': 'dryer',
            'current_power': dryer_power,
            'savings_estimate': round(dryer_power * 0.5 / 1000 * 0.35, 2),
            'tokens_reward': 55,
            'priority': 'medium'
        })
    
    # Oven recommendation
    oven_power = appliances.get('oven', 0)
    if oven_power > 1500:
        recommendations.append({
            'id': 'nilm_oven_001',
            'title': 'Oven Efficiency',
            'message': 'Use microwave or air fryer for smaller meals - they use 50% less energy.',
            'appliance': 'oven',
            'current_power': oven_power,
            'savings_estimate': round(oven_power * 0.4 / 1000 * 0.35, 2),
            'tokens_reward': 50,
            'priority': 'low'
        })
    
    # Sort by priority (high first)
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
    
    # Limit to top 5
    recommendations = recommendations[:5]
    
    return {
        'recommendations': recommendations,
        'total_power': int(current_power),
        'timestamp': datetime.now(),
        'appliance_breakdown': appliances
    }

@router.get("/status")
async def nilm_status():
    """Check NILM service status"""
    return {
        "available": len(nilm_service.models) > 0,
        "models_loaded": list(nilm_service.models.keys()),
        "appliance_count": len(nilm_service.models),
        "message": "NILM service is running"
    }