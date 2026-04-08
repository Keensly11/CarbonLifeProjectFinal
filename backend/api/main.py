"""
CarbonLife API Server
Main entry point for the CarbonLife backend application.
"""

import sys
import os
from pathlib import Path
import logging
import random
import threading
import asyncio
import json
from datetime import datetime, timedelta

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from sqlalchemy.orm import Session
import uvicorn

# Local imports
import models
import schemas
import auth
from data_processing.data_loader import UKDALELoader
from data_processing.energy_service import EnergyDataService
from api.ml_data import router as ml_router
from api.nilm_endpoints import router as nilm_router
from ml.nilm_service import nilm_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== CREATE APP INSTANCE ==========
app = FastAPI(
    title="CarbonLife API",
    description="Backend API for CarbonLife Energy Monitoring Mobile App",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ========== INITIALIZE DATABASE AND SERVICES ==========
models.init_db()
data_loader = UKDALELoader()
energy_service = EnergyDataService(data_loader)

# ========== CORS CONFIGURATION ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== INCLUDE ROUTERS ==========
app.include_router(ml_router)
app.include_router(nilm_router)

# ========== DATABASE DEPENDENCY ==========
def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== CURRENT USER DEPENDENCY ==========
async def get_current_user_db(
    token: str = Depends(auth.oauth2_scheme),
    db: Session = Depends(get_db)
):
    username = await auth.get_current_user(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

# ========== KAFKA STREAMING SETUP ==========
realtime_cache = {}
cache_lock = threading.Lock()

def update_cache_from_kafka():
    """Background thread for Kafka consumer"""
    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            'energy_raw',
            bootstrap_servers='localhost:9092',
            auto_offset_reset='latest',
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        logger.info("Kafka consumer started - listening for UAE energy data")
        
        for message in consumer:
            data = message.value
            household = data['household_id']
            
            with cache_lock:
                if household not in realtime_cache:
                    realtime_cache[household] = []
                
                co2 = round((data['total_power_watts'] / 1000) * 0.35, 2)
                
                reading = {
                    'timestamp': data['timestamp'],
                    'power_watts': data['total_power_watts'],
                    'co2_per_hour': co2,
                    'region': data['region'],
                    'temperature': data['temperature_c']
                }
                
                realtime_cache[household].append(reading)
                if len(realtime_cache[household]) > 30:
                    realtime_cache[household] = realtime_cache[household][-30:]
                    
    except Exception as e:
        logger.error(f"Kafka error: {e}")

@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=update_cache_from_kafka, daemon=True)
    thread.start()
    logger.info("Kafka background thread initialized")

# ========== UK-DALE HOUSE ASSIGNMENT ==========
def assign_ukdale_house(user_profile):
    """Assign UK-DALE house based on user profile"""
    house_profiles = {
        1: {'type': 'Villa', 'bedrooms': 4, 'size': 'large'},
        2: {'type': 'Apartment', 'bedrooms': 2, 'size': 'medium'},
        3: {'type': 'Townhouse', 'bedrooms': 3, 'size': 'medium'},
        4: {'type': 'Apartment', 'bedrooms': 1, 'size': 'small'},
        5: {'type': 'Villa', 'bedrooms': 3, 'size': 'medium'},
    }
    
    best_match = 2  # Default
    best_score = -1
    
    for house_id, profile in house_profiles.items():
        score = 0
        if profile['type'] == user_profile.home_type:
            score += 3
        if abs(profile['bedrooms'] - user_profile.bedrooms) <= 1:
            score += 2
        if score > best_score:
            best_score = score
            best_match = house_id
    
    logger.info(f"User {user_profile.username} assigned to House {best_match}")
    return best_match

async def generate_initial_features(user_id, house_id):
    """Generate initial energy readings for new user"""
    from ml.feature_engineering import feature_engineer
    from models import EnergyReading, SessionLocal
    
    db = SessionLocal()
    try:
        loader = UKDALELoader()
        df = loader.load_house_data(house_number=house_id, sample_size=1000)
        
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                power = float(row['power_watts'])
                reading = EnergyReading(
                    user_id=user_id,
                    timestamp=row['timestamp'],
                    power_watts=power,
                    energy_kwh=power * 6 / 3600000,
                    co2_kg=power * 0.35 / 1000,
                    source='ukdale_initial',
                    ukdale_house_id=house_id
                )
                db.add(reading)
            
            db.commit()
            feature_engineer.compute_user_features(user_id, db)
            logger.info(f"Initial data generated for user {user_id}")
    finally:
        db.close()

# ========== PYDANTIC MODELS ==========
class EnergyRecord(BaseModel):
    timestamp: datetime
    power_watts: float
    appliance: str
    house_id: int
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )

class EnergyDataResponse(BaseModel):
    house: int
    count: int
    data: List[EnergyRecord]
    message: str

class StatisticsResponse(BaseModel):
    house: int
    statistics: dict
    message: str

class RecentEnergyResponse(BaseModel):
    house: int
    recent_readings: List[dict]
    current_power: float
    message: str

class APIStatus(BaseModel):
    status: str
    timestamp: datetime
    version: str
    data_source: str

# ========== ROOT ENDPOINT ==========
@app.get("/")
async def root():
    return {
        "app": "CarbonLife API",
        "version": "2.0.0",
        "status": "operational",
        "kafka_status": "connected" if realtime_cache else "waiting for data",
        "endpoints": {
            "health": "/api/health",
            "docs": "/api/docs",
            "auth_register": "/api/auth/register",
            "auth_login": "/api/auth/login",
            "ml_recommendations": "/api/recommendations/ml/{user_id}"
        }
    }

@app.get("/api/health")
async def health_check():
    return APIStatus(
        status="healthy",
        timestamp=datetime.now(),
        version="2.0.0",
        data_source="UK-DALE Dataset"
    )

# ========== ENERGY ENDPOINTS ==========
@app.get("/api/energy/data")
async def get_energy_data(
    house: int = Query(1, ge=1, le=5),
    samples: int = Query(100, ge=10, le=10000)
):
    df = data_loader.load_house_data(house, samples)
    if df is None or df.empty:
        return EnergyDataResponse(house=house, count=0, data=[], message="No data")
    
    records = []
    for _, row in df.iterrows():
        records.append(EnergyRecord(
            timestamp=row['timestamp'],
            power_watts=float(row['power_watts']),
            appliance=str(row.get('appliance', 'Whole House')),
            house_id=house
        ))
    
    return EnergyDataResponse(
        house=house,
        count=len(records),
        data=records,
        message=f"Loaded {len(records)} records"
    )

@app.get("/api/energy/user/{user_id}")
async def get_user_energy_data(
    user_id: int,
    samples: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    readings = db.query(models.EnergyReading).filter(
        models.EnergyReading.user_id == user_id
    ).order_by(models.EnergyReading.timestamp.desc()).limit(samples).all()
    
    if not readings:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.ukdale_house_id:
            asyncio.create_task(generate_initial_features(user_id, user.ukdale_house_id))
            return {"user_id": user_id, "readings": [], "message": "Data generation started"}
    
    return {
        "user_id": user_id,
        "house_id": readings[0].ukdale_house_id if readings else None,
        "readings": [{
            "timestamp": r.timestamp,
            "power_watts": r.power_watts,
            "energy_kwh": r.energy_kwh,
            "co2_kg": r.co2_kg
        } for r in readings]
    }

@app.get("/api/energy/stats")
async def get_energy_stats(
    house: int = Query(1, ge=1, le=5),
    samples: int = Query(500, ge=10, le=10000)
):
    df = data_loader.load_house_data(house, samples)
    if df is None or df.empty:
        return StatisticsResponse(house=house, statistics={"error": "No data"}, message="No data")
    
    stats = data_loader.get_summary_stats(df)
    return StatisticsResponse(house=house, statistics=stats, message="Statistics calculated")

@app.get("/api/energy/recent")
async def get_recent_energy(
    house: int = Query(1, ge=1, le=5),
    limit: int = Query(10, ge=1, le=50)
):
    df = data_loader.load_house_data(house, limit * 2)
    if df is None or df.empty:
        return RecentEnergyResponse(house=house, recent_readings=[], current_power=0, message="No data")
    
    recent_df = df.tail(limit)
    recent_data = []
    for _, row in recent_df.iterrows():
        recent_data.append({
            "timestamp": row['timestamp'].isoformat(),
            "power_watts": float(row['power_watts']),
            "appliance": str(row.get('appliance', 'Whole House'))
        })
    
    current_power = float(df['power_watts'].iloc[-1]) if len(df) > 0 else 0
    
    return RecentEnergyResponse(
        house=house,
        recent_readings=recent_data,
        current_power=current_power,
        message=f"Last {len(recent_data)} readings"
    )

# ========== USER STATS ==========
@app.get("/api/user/stats/{user_id}")
async def get_user_stats(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    missions = db.query(models.Mission).filter(models.Mission.user_id == user_id).all()
    completed = [m for m in missions if m.status == 'completed']
    tokens = db.query(models.TokenTransaction).filter(
        models.TokenTransaction.user_id == user_id
    ).all()
    token_balance = sum(t.amount for t in tokens)
    
    readings = db.query(models.EnergyReading).filter(
        models.EnergyReading.user_id == user_id
    ).all()
    total_co2 = sum(r.co2_kg for r in readings)
    
    return {
        "user_id": user_id,
        "username": user.username,
        "full_name": user.full_name,
        "emirate": user.emirate,
        "home_type": user.home_type,
        "bedrooms": user.bedrooms,
        "vehicle_type": user.vehicle_type,
        "ukdale_house_id": user.ukdale_house_id,
        "missions_completed": len(completed),
        "total_missions": len(missions),
        "current_balance": token_balance,
        "total_co2_saved": round(total_co2, 2)
    }

# ========== AUTHENTICATION ==========
@app.post("/api/auth/register", response_model=schemas.UserResponse)
async def register_user(
    user: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    existing = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()
    
    if existing:
        raise HTTPException(400, "Email or username already registered")
    
    house_id = assign_ukdale_house(user)
    hashed = auth.get_password_hash(user.password)
    
    db_user = models.User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed,
        emirate=user.emirate,
        home_type=user.home_type,
        bedrooms=user.bedrooms,
        vehicle_type=user.vehicle_type,
        vehicle_fuel=user.vehicle_fuel,
        ukdale_house_id=house_id
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    preferences = models.UserPreferences(user_id=db_user.id)
    db.add(preferences)
    db.commit()
    
    background_tasks.add_task(generate_initial_features, db_user.id, house_id)
    
    return db_user

@app.post("/api/auth/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.username == form_data.username
    ).first()
    
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect username or password")
    
    expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = auth.create_access_token(data={"sub": user.username}, expires_delta=expires)
    
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user_db)):
    return current_user

# ========== KAFKA ENDPOINTS ==========
@app.get("/api/kafka/status")
async def kafka_status():
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(bootstrap_servers='localhost:9092')
        producer.close()
        
        with cache_lock:
            return {
                "status": "connected",
                "households_tracked": len(realtime_cache),
                "total_readings": sum(len(r) for r in realtime_cache.values())
            }
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}

@app.get("/api/realtime/energy")
async def get_realtime_energy(household: str = None):
    with cache_lock:
        if household:
            if household in realtime_cache:
                readings = realtime_cache[household]
                return {
                    "household": household,
                    "current": readings[-1] if readings else None,
                    "recent": readings[-10:]
                }
            return {"error": "Household not found"}
        
        summary = {}
        for hh, readings in realtime_cache.items():
            if readings:
                summary[hh] = {
                    "power": readings[-1]['power_watts'],
                    "co2": readings[-1]['co2_per_hour'],
                    "region": readings[-1]['region']
                }
        return {"households": summary}

@app.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        while True:
            with cache_lock:
                data = {}
                for hh, readings in realtime_cache.items():
                    if readings:
                        last = readings[-1]
                        data[hh] = {
                            "power": last['power_watts'],
                            "co2": last['co2_per_hour'],
                            "region": last['region'],
                            "temperature": last['temperature']
                        }
            
            await websocket.send_json({
                "type": "energy_update",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")

# ========== ERROR HANDLERS ==========
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "path": request.url.path,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "details": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

# ========== RUN SERVER ==========
if __name__ == "__main__":
    print("="*60)
    print("Starting CarbonLife API Server")
    print("="*60)
    print(f"Local: http://localhost:8000")
    print(f"Docs:  http://localhost:8000/api/docs")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)