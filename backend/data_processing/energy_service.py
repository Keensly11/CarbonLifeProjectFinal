# data_processing/energy_service.py - PRODUCTION VERSION
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class EnergyDataService:
    def __init__(self, data_loader=None):
        # UAE-specific emission factors
        self.emission_factors = {
            "electricity": {
                "dubai": 0.35,
                "abu_dhabi": 0.37,
                "sharjah": 0.36,
                "average": 0.35
            },
            "transport": {
                "petrol_car": 0.18,
                "diesel_car": 0.20,
                "suv_petrol": 0.25,
                "suv_diesel": 0.28,
                "hybrid": 0.10,
                "electric": 0.05,
                "motorcycle": 0.09,
                "bus": 0.07,
                "metro": 0.02,
            }
        }
        
        self.data_loader = data_loader
    
    def get_user_energy_data(self, user_id, db, samples=100):
        """
        Get energy data specifically for a user based on their assigned UK-DALE house.
        Returns a pandas DataFrame with their personalized energy data.
        """
        from models import User, EnergyReading
        
        # Get user's assigned house
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return self.data_loader.load_house_data(1, samples)  # Fallback to House 1
        
        logger.info(f"📊 Fetching energy data for user {user_id} (House {user.ukdale_house_id})")
        
        # First, check if we already have their data in the database
        readings = db.query(EnergyReading).filter(
            EnergyReading.user_id == user_id
        ).order_by(EnergyReading.timestamp.desc()).limit(samples).all()
        
        if len(readings) >= samples:
            # Return their real stored data
            logger.info(f"✅ Found {len(readings)} existing readings for user {user_id}")
            return pd.DataFrame([{
                'timestamp': r.timestamp,
                'power_watts': r.power_watts,
                'energy_kwh': r.energy_kwh,
                'co2_kg': r.co2_kg,
                'source': r.source,
                'house_id': r.ukdale_house_id
            } for r in readings])
        else:
            # Load from UK-DALE and store for this user
            house_id = user.ukdale_house_id or 1  # Default to House 1 if not assigned
            logger.info(f"🔄 Loading {samples} samples from UK-DALE House {house_id} for user {user_id}")
            
            df = self.data_loader.load_house_data(house_id, samples)
            
            if df is None or df.empty:
                logger.error(f"❌ Could not load data for House {house_id}")
                return pd.DataFrame()
            
            # Store in database for this user (avoid duplicates)
            readings_created = 0
            for _, row in df.iterrows():
                # Check if this reading already exists (avoid duplicates)
                existing = db.query(EnergyReading).filter(
                    EnergyReading.user_id == user_id,
                    EnergyReading.timestamp == row['timestamp']
                ).first()
                
                if not existing:
                    power = float(row['power_watts'])
                    reading = EnergyReading(
                        user_id=user_id,
                        timestamp=row['timestamp'],
                        power_watts=power,
                        energy_kwh=power * 6 / 3600000,  # 6-second reading to kWh
                        co2_kg=power * 0.35 / 1000,  # UAE emission factor
                        appliances={'source': 'ukdale', 'house': house_id},
                        source='ukdale',
                        ukdale_house_id=house_id
                    )
                    db.add(reading)
                    readings_created += 1
            
            if readings_created > 0:
                db.commit()
                logger.info(f"✅ Stored {readings_created} new readings for user {user_id}")
            
            return df
    
    def calculate_electricity_emissions(self, power_watts: float, duration_hours: float = 1.0, 
                                      location: str = "dubai") -> Dict:
        try:
            power_kw = power_watts / 1000
            energy_kwh = power_kw * duration_hours
            emission_factor = self.emission_factors["electricity"].get(location, 0.35)
            co2_kg = energy_kwh * emission_factor
            
            return {
                "power_watts": power_watts,
                "duration_hours": duration_hours,
                "energy_kwh": round(energy_kwh, 4),
                "emission_factor_kgco2_kwh": emission_factor,
                "co2_emissions_kg": round(co2_kg, 4),
                "co2_emissions_tonnes": round(co2_kg / 1000, 6),
                "equivalent_trees_needed": round(co2_kg / 21.77, 2),
                "equivalent_car_km": round(co2_kg / 0.18, 2),
                "location": location,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error calculating electricity emissions: {e}")
            return None
    
    def calculate_transportation_emissions(self, distance_km: float, vehicle_type: str,
                                         passengers: int = 1, fuel_efficiency: Optional[float] = None) -> Dict:
        try:
            if vehicle_type not in self.emission_factors["transport"]:
                vehicle_type = "petrol_car"
            
            base_factor = self.emission_factors["transport"][vehicle_type]
            
            if fuel_efficiency:
                adjusted_factor = base_factor * (10.0 / fuel_efficiency)
            else:
                adjusted_factor = base_factor
            
            total_co2_kg = distance_km * adjusted_factor
            per_passenger_co2 = total_co2_kg / passengers if passengers > 0 else total_co2_kg
            
            return {
                "distance_km": distance_km,
                "vehicle_type": vehicle_type,
                "passengers": passengers,
                "fuel_efficiency_km_l": fuel_efficiency,
                "emission_factor_kgco2_km": round(adjusted_factor, 4),
                "total_co2_kg": round(total_co2_kg, 4),
                "per_passenger_co2_kg": round(per_passenger_co2, 4),
                "equivalent_trees_needed": round(total_co2_kg / 21.77, 2),
                "equivalent_energy_kwh": round(total_co2_kg / 0.35, 2),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error calculating transportation emissions: {e}")
            return None
    
    def analyze_energy_dataframe(self, df: pd.DataFrame, location: str = "dubai") -> Dict:
        if df is None or df.empty:
            return {"error": "No data provided"}
        
        try:
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            df = df.sort_values('timestamp')
            time_diffs = df['timestamp'].diff().dt.total_seconds().fillna(6)
            df['duration_hours'] = time_diffs / 3600
            df['energy_kwh'] = (df['power_watts'] / 1000) * df['duration_hours']
            df['co2_kg'] = df['energy_kwh'] * self.emission_factors["electricity"][location]
            
            total_energy_kwh = df['energy_kwh'].sum()
            total_co2_kg = df['co2_kg'].sum()
            avg_power = df['power_watts'].mean()
            
            return {
                "summary": {
                    "total_energy_kwh": round(total_energy_kwh, 4),
                    "total_co2_kg": round(total_co2_kg, 4),
                    "average_power_watts": round(avg_power, 2),
                    "data_points": len(df),
                },
                "location": location,
                "analysis_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def create_daily_summary(self, df: pd.DataFrame, location: str = "dubai") -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        
        try:
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            df['date'] = df['timestamp'].dt.date
            df['duration_hours'] = df['timestamp'].diff().dt.total_seconds().fillna(6) / 3600
            df['energy_kwh'] = (df['power_watts'] / 1000) * df['duration_hours']
            df['co2_kg'] = df['energy_kwh'] * self.emission_factors["electricity"][location]
            
            daily_summary = df.groupby('date').agg({
                'power_watts': ['mean', 'max', 'min'],
                'energy_kwh': 'sum',
                'co2_kg': 'sum'
            }).round(4)
            
            daily_summary.columns = ['_'.join(col).strip() for col in daily_summary.columns.values]
            return daily_summary.reset_index()
        except Exception as e:
            print(f"Error creating daily summary: {e}")
            return pd.DataFrame()