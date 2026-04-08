"""
Pydantic schemas for request/response validation.
All data entering/leaving the API is validated here.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ========== ENUMS ==========

class EmirateEnum(str, Enum):
    DUBAI = "Dubai"
    ABU_DHABI = "Abu Dhabi"
    SHARJAH = "Sharjah"
    AJMAN = "Ajman"
    RAK = "RAK"
    FUJAIRAH = "Fujairah"
    UMM_AL_QUWAIN = "Umm Al Quwain"

class HomeTypeEnum(str, Enum):
    VILLA = "Villa"
    APARTMENT = "Apartment"
    TOWNHOUSE = "Townhouse"
    PALACE = "Palace"

class VehicleTypeEnum(str, Enum):
    SUV = "SUV"
    SEDAN = "Sedan"
    SPORTS = "Sports Car"
    ELECTRIC = "Electric"
    HYBRID = "Hybrid"
    NONE = "None"

class FuelTypeEnum(str, Enum):
    PETROL = "Petrol"
    DIESEL = "Diesel"
    HYBRID = "Hybrid"
    ELECTRIC = "Electric"
    NONE = "None"

class DifficultyEnum(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class MissionStatusEnum(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


# ========== USER SCHEMAS ==========

class UserBase(BaseModel):
    """Base user information"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    
    # UAE-specific fields
    emirate: EmirateEnum = EmirateEnum.DUBAI
    home_type: HomeTypeEnum = HomeTypeEnum.VILLA
    bedrooms: int = Field(3, ge=1, le=10)
    vehicle_type: VehicleTypeEnum = VehicleTypeEnum.SUV
    vehicle_fuel: FuelTypeEnum = FuelTypeEnum.PETROL
    year_built: Optional[int] = Field(None, ge=1950, le=datetime.now().year)
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v

class UserCreate(UserBase):
    """User registration request"""
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v

class UserUpdate(BaseModel):
    """User profile update request"""
    full_name: Optional[str] = Field(None, max_length=100)
    emirate: Optional[EmirateEnum] = None
    home_type: Optional[HomeTypeEnum] = None
    bedrooms: Optional[int] = Field(None, ge=1, le=10)
    vehicle_type: Optional[VehicleTypeEnum] = None
    vehicle_fuel: Optional[FuelTypeEnum] = None
    year_built: Optional[int] = Field(None, ge=1950, le=datetime.now().year)

class UserResponse(UserBase):
    """User data returned to client"""
    id: int
    is_active: bool
    created_at: datetime
    token_balance: int = 0
    missions_completed: int = 0
    total_co2_saved: float = 0.0
    
    class Config:
        orm_mode = True


# ========== AUTH SCHEMAS ==========

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes

class TokenData(BaseModel):
    """Data stored in JWT token"""
    username: Optional[str] = None
    user_id: Optional[int] = None

class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str


# ========== ENERGY SCHEMAS ==========

class EnergyReadingBase(BaseModel):
    """Energy reading data"""
    timestamp: datetime
    power_watts: float = Field(..., ge=0)
    energy_kwh: float = Field(..., ge=0)
    co2_kg: float = Field(..., ge=0)
    appliances: Dict[str, float] = {}
    outside_temperature: Optional[float] = None
    humidity: Optional[float] = None

class EnergyReadingCreate(EnergyReadingBase):
    """Create energy reading request"""
    source: str = "smart_meter"

class EnergyReadingResponse(EnergyReadingBase):
    """Energy reading response"""
    id: int
    user_id: int
    source: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class EnergyStats(BaseModel):
    """Energy statistics"""
    period_start: datetime
    period_end: datetime
    total_energy_kwh: float
    total_co2_kg: float
    avg_power_watts: float
    max_power_watts: float
    min_power_watts: float
    readings_count: int


# ========== MISSION SCHEMAS ==========

class MissionBase(BaseModel):
    """Mission base data"""
    title: str = Field(..., max_length=200)
    description: str
    category: str
    difficulty: DifficultyEnum
    tokens_reward: int = Field(10, ge=0)
    co2_saved_kg: float = Field(0.0, ge=0)
    experience_points: int = Field(10, ge=0)

class MissionCreate(MissionBase):
    """Create mission request"""
    expires_in_days: Optional[int] = 7

class MissionUpdate(BaseModel):
    """Update mission request"""
    status: Optional[MissionStatusEnum] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_feedback: Optional[str] = None

class MissionResponse(MissionBase):
    """Mission response"""
    id: int
    user_id: int
    ml_generated: bool
    ml_confidence: Optional[float] = None
    status: MissionStatusEnum
    progress: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    time_taken_seconds: Optional[int] = None
    
    class Config:
        orm_mode = True


# ========== ML RECOMMENDATION SCHEMAS ==========

class MLFeatures(BaseModel):
    """ML features for a user"""
    user_id: int
    avg_daily_energy_30d: Optional[float] = None
    avg_daily_energy_7d: Optional[float] = None
    energy_volatility: Optional[float] = None
    peak_usage_ratio: Optional[float] = None
    ac_usage_ratio: Optional[float] = None
    mission_completion_rate: Optional[float] = None
    days_active_last_30d: Optional[int] = None
    preferred_category: Optional[str] = None
    
    class Config:
        orm_mode = True

class PersonalizedMission(MissionBase):
    """Mission with ML-generated personalization"""
    id: str
    relevance_score: float = Field(..., ge=0, le=100)
    personalized_message: str
    savings_kg_co2: float
    tokens_reward: int
    ml_confidence: float
    reason: str  # Why this mission was recommended

class MLRecommendationResponse(BaseModel):
    """ML-powered recommendations response"""
    user_id: int
    user_name: str
    generated_at: datetime
    recommendations: List[PersonalizedMission]
    model_version: str
    model_accuracy: Optional[float] = None
    context: Dict[str, Any] = {}


# ========== TOKEN SCHEMAS ==========

class TokenTransactionBase(BaseModel):
    """Token transaction base"""
    amount: int
    transaction_type: str
    description: str

class TokenTransactionCreate(TokenTransactionBase):
    """Create token transaction"""
    mission_id: Optional[int] = None
    reward_id: Optional[int] = None

class TokenTransactionResponse(TokenTransactionBase):
    """Token transaction response"""
    id: int
    user_id: int
    timestamp: datetime
    mission_id: Optional[int] = None
    reward_id: Optional[int] = None
    
    class Config:
        orm_mode = True

class TokenBalance(BaseModel):
    """User token balance"""
    user_id: int
    username: str
    balance: int
    total_earned: int
    total_spent: int
    last_transaction: Optional[datetime] = None


# ========== REWARD SCHEMAS ==========

class RewardBase(BaseModel):
    """Reward base"""
    name: str
    description: str
    tokens_cost: int
    partner: str
    location: str
    emirate: Optional[str] = None

class RewardResponse(RewardBase):
    """Reward response"""
    id: int
    available: bool
    image_url: Optional[str] = None
    
    class Config:
        orm_mode = True

class RedeemRequest(BaseModel):
    """Redeem reward request"""
    reward_id: int

class RedeemResponse(BaseModel):
    """Redeem reward response"""
    success: bool
    message: str
    tokens_spent: int
    new_balance: int
    redemption_code: Optional[str] = None


# ========== USER STATISTICS ==========

class UserStats(BaseModel):
    """Comprehensive user statistics"""
    user_id: int
    username: str
    member_since: datetime
    
    # Energy stats
    total_energy_kwh: float
    total_co2_kg: float
    avg_daily_energy: float
    energy_trend: float  # Percentage change
    
    # Mission stats
    missions_completed: int
    missions_attempted: int
    completion_rate: float
    avg_completion_time: Optional[int] = None
    
    # Token stats
    tokens_earned: int
    tokens_spent: int
    current_balance: int
    
    # Impact
    co2_saved_kg: float
    equivalent_trees: float
    equivalent_car_km: float
    
    # UAE context
    emirate: str
    home_type: str
    ranking: Optional[int] = None  # Leaderboard position
    
    class Config:
        orm_mode = True