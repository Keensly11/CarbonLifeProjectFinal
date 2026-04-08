"""
Production-ready database models for CarbonLife.
Includes UK-DALE house assignment for personalized user data.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

# Database configuration
DB_USER = "admin"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "carbonlife"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Engine configuration for production
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """Core user model with UAE-specific fields and UK-DALE house assignment"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # UAE-specific demographic fields
    emirate = Column(String(50), nullable=False, default="Dubai")
    home_type = Column(String(50), nullable=False, default="Villa")
    bedrooms = Column(Integer, nullable=False, default=3)
    vehicle_type = Column(String(50), nullable=False, default="SUV")
    vehicle_fuel = Column(String(50), nullable=False, default="Petrol")
    year_built = Column(Integer, nullable=True)
    
    # UK-DALE house assignment (1-5)
    ukdale_house_id = Column(Integer, nullable=True)  # Which UK-DALE house provides their data
    
    # Relationships
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    energy_readings = relationship("EnergyReading", back_populates="user", cascade="all, delete-orphan")
    missions = relationship("Mission", back_populates="user", cascade="all, delete-orphan")
    token_transactions = relationship("TokenTransaction", back_populates="user", cascade="all, delete-orphan")
    ml_features = relationship("UserMLFeatures", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_username', 'username'),
        Index('idx_user_emirate', 'emirate'),
        Index('idx_user_ukdale', 'ukdale_house_id'),
    )


class UserPreferences(Base):
    """User preferences and settings"""
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Notification preferences
    push_notifications = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=False)
    mission_reminders = Column(Boolean, default=True)
    reminder_time = Column(String(5), default="09:00")  # HH:MM format
    
    # Display preferences
    temperature_unit = Column(String(1), default="C")  # C or F
    energy_unit = Column(String(3), default="kWh")
    dark_mode = Column(Boolean, default=False)
    language = Column(String(2), default="en")  # en, ar
    
    # Privacy
    share_anonymous_data = Column(Boolean, default=True)  # For ML training
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship("User", back_populates="preferences")


class EnergyReading(Base):
    """High-resolution energy readings from smart meters or UK-DALE"""
    __tablename__ = "energy_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Reading data
    timestamp = Column(DateTime, nullable=False, index=True)
    power_watts = Column(Float, nullable=False)
    energy_kwh = Column(Float, nullable=False)
    co2_kg = Column(Float, nullable=False)
    
    # Appliance breakdown (JSON for flexibility)
    appliances = Column(JSON, nullable=False, default={})
    
    # Context
    source = Column(String(50), nullable=False, default="ukdale")  # ukdale, smart_meter, manual
    ukdale_house_id = Column(Integer, nullable=True)  # Which UK-DALE house this came from
    outside_temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    is_peak_hours = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    user = relationship("User", back_populates="energy_readings")
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_energy_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_energy_timestamp', 'timestamp'),
        Index('idx_energy_ukdale', 'ukdale_house_id'),
    )


class Mission(Base):
    """Mission system for gamification"""
    __tablename__ = "missions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Mission details
    title = Column(String(200), nullable=False)
    description = Column(String, nullable=False)
    category = Column(String(50), nullable=False)  # energy, transport, water, social
    difficulty = Column(String(20), nullable=False)  # easy, medium, hard
    
    # Rewards
    tokens_reward = Column(Integer, nullable=False, default=10)
    co2_saved_kg = Column(Float, nullable=False, default=0)
    experience_points = Column(Integer, nullable=False, default=10)
    
    # ML-generated fields
    ml_generated = Column(Boolean, default=False)
    ml_confidence = Column(Float, nullable=True)  # 0-1 probability
    ml_features_version = Column(String(10), nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, default="active")  # active, completed, expired, failed
    progress = Column(Integer, nullable=False, default=0)  # 0-100
    
    # Timing
    created_at = Column(DateTime, default=datetime.now, index=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)
    
    # User feedback
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    user_feedback = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="missions")
    
    __table_args__ = (
        Index('idx_mission_user_status', 'user_id', 'status'),
    )


class TokenTransaction(Base):
    """Token economy transactions"""
    __tablename__ = "token_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    amount = Column(Integer, nullable=False)  # Positive for earned, negative for spent
    transaction_type = Column(String(50), nullable=False)  # earned_mission, redeemed_reward, bonus, admin
    description = Column(String(255), nullable=False)
    
    # Reference
    mission_id = Column(Integer, ForeignKey("missions.id", ondelete="SET NULL"), nullable=True)
    reward_id = Column(Integer, ForeignKey("rewards.id", ondelete="SET NULL"), nullable=True)
    
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    # Relationships
    user = relationship("User", back_populates="token_transactions")
    
    __table_args__ = (
        Index('idx_token_user_timestamp', 'user_id', 'timestamp'),
    )


class Reward(Base):
    """Redeemable rewards in UAE"""
    __tablename__ = "rewards"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String, nullable=False)
    tokens_cost = Column(Integer, nullable=False)
    image_url = Column(String(500), nullable=True)
    
    # UAE-specific
    partner = Column(String(100), nullable=False)  # Starbucks, RTA, etc.
    location = Column(String(100), nullable=False)  # Dubai Mall, All UAE, etc.
    emirate = Column(String(50), nullable=True)  # Filter by emirate
    available = Column(Boolean, default=True)
    
    # Limits
    total_quantity = Column(Integer, default=-1)  # -1 for unlimited
    redeemed_count = Column(Integer, default=0)
    user_limit = Column(Integer, default=1)  # Max per user
    
    # Timing
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class UserMLFeatures(Base):
    """ML features derived from user data (for training)"""
    __tablename__ = "user_ml_features"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Feature version
    feature_version = Column(String(20), nullable=False, default="1.0")
    
    # Computed features
    avg_daily_energy_30d = Column(Float, nullable=True)
    avg_daily_energy_7d = Column(Float, nullable=True)
    energy_volatility = Column(Float, nullable=True)  # Standard deviation
    peak_usage_ratio = Column(Float, nullable=True)  # Peak vs off-peak
    
    # Appliance patterns
    ac_usage_ratio = Column(Float, nullable=True)
    fridge_usage_ratio = Column(Float, nullable=True)
    lighting_ratio = Column(Float, nullable=True)
    
    # Behavioral features
    mission_completion_rate = Column(Float, nullable=True)
    avg_completion_time = Column(Integer, nullable=True)  # seconds
    preferred_mission_category = Column(String(50), nullable=True)
    token_velocity = Column(Float, nullable=True)  # tokens earned per day
    
    # Engagement metrics
    days_active_last_30d = Column(Integer, nullable=True)
    sessions_per_week = Column(Float, nullable=True)
    last_active = Column(DateTime, nullable=True)
    
    # UK-DALE reference
    source_house_id = Column(Integer, nullable=True)  # Which UK-DALE house their features are based on
    
    # Timestamps
    calculated_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship("User", back_populates="ml_features")


class ModelMetadata(Base):
    """Track ML model versions and performance"""
    __tablename__ = "model_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    model_version = Column(String(20), nullable=False)
    model_type = Column(String(50), nullable=False)  # classification, regression
    
    # Training metrics
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    auc_roc = Column(Float, nullable=True)
    
    # Training info
    training_date = Column(DateTime, default=datetime.now)
    training_samples = Column(Integer, nullable=True)
    features_used = Column(JSON, nullable=True)  # List of feature names
    
    # Model file
    model_path = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=False)
    
    # Performance in production
    avg_prediction_time_ms = Column(Float, nullable=True)
    total_predictions = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_model_active', 'model_name', 'is_active'),
    )


class RecommendationLog(Base):
    """Log all recommendations for analysis and improvement"""
    __tablename__ = "recommendation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mission_id = Column(Integer, ForeignKey("missions.id", ondelete="CASCADE"), nullable=True)
    
    # Recommendation details
    recommendation_type = Column(String(50), nullable=False)  # ml_generated, rule_based, fallback
    model_version = Column(String(20), nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Context at time of recommendation
    context = Column(JSON, nullable=True)  # hour, day, weather, etc.
    
    # Outcome
    was_shown = Column(Boolean, default=True)
    was_clicked = Column(Boolean, default=False)
    was_completed = Column(Boolean, default=False)
    user_rating = Column(Integer, nullable=True)
    
    # Timing
    shown_at = Column(DateTime, default=datetime.now)
    clicked_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_recommendation_user', 'user_id'),
        Index('idx_recommendation_outcome', 'was_completed'),
    )


# Initialize database
def init_db():
    """Create all tables with proper error handling"""
    try:
        print("🔄 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # Create initial rewards if none exist
        create_initial_rewards()
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

def create_initial_rewards():
    """Seed database with initial UAE rewards"""
    session = SessionLocal()
    try:
        if session.query(Reward).count() == 0:
            rewards = [
                Reward(
                    name="Starbucks Coffee",
                    description="Any tall-sized beverage",
                    tokens_cost=50,
                    partner="Starbucks",
                    location="Dubai Mall",
                    emirate="Dubai",
                    image_url="/rewards/starbucks.png"
                ),
                Reward(
                    name="Metro Day Pass",
                    description="Dubai Metro Silver Day Pass",
                    tokens_cost=75,
                    partner="RTA",
                    location="All Dubai Metro Stations",
                    emirate="Dubai",
                    image_url="/rewards/metro.png"
                ),
                Reward(
                    name="Plant a Tree",
                    description="We'll plant a Ghaf tree in your name",
                    tokens_cost=100,
                    partner="Emirates Green",
                    location="All UAE",
                    image_url="/rewards/tree.png"
                ),
                Reward(
                    name="Movie Ticket",
                    description="VOX Cinemas standard ticket",
                    tokens_cost=120,
                    partner="VOX",
                    location="All UAE",
                    image_url="/rewards/movie.png"
                ),
                Reward(
                    name="Eco-friendly Bag",
                    description="Reusable shopping bag",
                    tokens_cost=30,
                    partner="Carrefour",
                    location="All UAE",
                    image_url="/rewards/bag.png"
                ),
            ]
            session.add_all(rewards)
            session.commit()
            print("✅ Initial rewards created")
    except Exception as e:
        session.rollback()
        print(f"⚠️ Could not create initial rewards: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    init_db()