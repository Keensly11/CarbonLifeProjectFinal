import json
import random
import time
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from typing import Dict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UAEEnergyProducer:
    """Produces simulated UAE smart meter data to Kafka with auto-reconnect"""
    
    def __init__(self, bootstrap_servers='localhost:9092', max_retries=5, retry_interval=5):
        self.bootstrap_servers = bootstrap_servers
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.producer = None
        self.connect()
        
        # UAE-specific appliance profiles
        self.uae_appliances = {
            'AC': {
                'base_power': 1500,
                'variance': 1000,
                'active_prob': 0.8,
                'typical_hours': [10, 11, 12, 13, 14, 15, 16, 17, 18],
                'summer_multiplier': 1.5
            },
            'Water_Cooler': {
                'base_power': 300,
                'variance': 100,
                'active_prob': 0.9,
                'typical_hours': list(range(24)),
                'summer_multiplier': 1.2
            },
            'Fridge': {
                'base_power': 200,
                'variance': 50,
                'active_prob': 0.95,
                'typical_hours': list(range(24)),
                'summer_multiplier': 1.1
            },
            'LED_Lights': {
                'base_power': 50,
                'variance': 30,
                'active_prob': 0.7,
                'typical_hours': [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6],
                'summer_multiplier': 1.0
            },
            'Washing_Machine': {
                'base_power': 500,
                'variance': 200,
                'active_prob': 0.1,
                'typical_hours': [9, 10, 11, 14, 15, 16, 17],
                'summer_multiplier': 1.0
            }
        }
        
        # UAE regions and typical patterns
        self.uae_regions = ['Dubai', 'Abu_Dhabi', 'Sharjah', 'Ajman', 'RAK']
        
    def connect(self):
        """Establish connection to Kafka with retry logic"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔄 Attempting to connect to Kafka at {self.bootstrap_servers} (attempt {attempt + 1}/{self.max_retries})")
                
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',
                    retries=3,
                    max_block_ms=5000  # 5 second timeout
                )
                
                # Test connection
                self.producer.metrics()
                logger.info("✅ Successfully connected to Kafka!")
                return True
                
            except NoBrokersAvailable:
                if attempt < self.max_retries - 1:
                    logger.warning(f"❌ Kafka not available, retrying in {self.retry_interval} seconds...")
                    time.sleep(self.retry_interval)
                else:
                    logger.error("❌ Failed to connect to Kafka after all retries")
                    logger.error("💡 Make sure Kafka is running: docker-compose up -d")
                    raise
            except Exception as e:
                logger.error(f"❌ Unexpected error connecting to Kafka: {e}")
                raise
    
    def simulate_uae_household(self, household_id: str, timestamp: datetime) -> Dict:
        """Generate UAE-style energy data for a household"""
        
        total_power = 0
        appliance_states = {}
        current_hour = timestamp.hour
        
        # UAE summer factor (April-October)
        is_summer = timestamp.month in [4, 5, 6, 7, 8, 9, 10]
        summer_factor = 1.3 if is_summer else 1.0
        
        for appliance, specs in self.uae_appliances.items():
            # Check if appliance is typically active at this hour
            hour_active = current_hour in specs['typical_hours']
            
            # Adjust probability based on hour and season
            adjusted_prob = specs['active_prob']
            if not hour_active:
                adjusted_prob *= 0.3  # 70% less likely
            
            if random.random() < adjusted_prob:
                # Generate power with UAE adjustments
                base = specs['base_power'] * summer_factor * specs['summer_multiplier']
                power = base + random.uniform(-specs['variance'], specs['variance'])
                power = max(power, 0)
                
                total_power += power
                appliance_states[appliance] = round(power, 1)
        
        # Add UAE-specific baseload (always-on devices)
        baseload = 100 + random.uniform(-20, 20)
        total_power += baseload
        
        return {
            'household_id': household_id,
            'timestamp': timestamp.isoformat(),
            'total_power_watts': round(total_power, 1),
            'appliance_breakdown': appliance_states,
            'region': random.choice(self.uae_regions),
            'temperature_c': round(random.uniform(25, 45), 1),
            'humidity_percent': round(random.uniform(30, 85), 1),
            'season': 'summer' if is_summer else 'winter',
            'data_type': 'smart_meter',
            'emirate_code': f'AE-{random.randint(1, 7)}'
        }
    
    def start_producing(self, num_households=5, interval_seconds=5):
        """Start producing simulated UAE data to Kafka with auto-reconnect"""
        
        if not self.producer:
            logger.error("❌ No Kafka connection available")
            return
        
        logger.info(f"🚀 Starting UAE Energy Producer for {num_households} households...")
        logger.info(f"📡 Kafka: {self.bootstrap_servers}")
        logger.info(f"⏱️  Interval: {interval_seconds}s")
        logger.info("-" * 50)
        
        household_ids = [f'UAE_HH_{i:03d}' for i in range(1, num_households + 1)]
        
        try:
            while True:
                for household_id in household_ids:
                    data = self.simulate_uae_household(household_id, datetime.now())
                    
                    # Send to energy_raw topic
                    self.producer.send(
                        'energy_raw',
                        value=data,
                        key=household_id.encode('utf-8')
                    )
                    
                    # Send appliance events if AC is running (common in UAE)
                    if 'AC' in data['appliance_breakdown']:
                        ac_event = {
                            'household_id': household_id,
                            'appliance': 'AC',
                            'power_watts': data['appliance_breakdown']['AC'],
                            'timestamp': data['timestamp'],
                            'temperature': data['temperature_c'],
                            'event_type': 'cooling_demand',
                            'uae_context': 'High cooling demand detected'
                        }
                        self.producer.send('appliance_events', value=ac_event)
                    
                    # Send to carbon_calculations if power is high
                    if data['total_power_watts'] > 2000:
                        carbon_data = {
                            'household_id': household_id,
                            'timestamp': data['timestamp'],
                            'power_kw': data['total_power_watts'] / 1000,
                            'co2_kg_per_hour': round((data['total_power_watts'] / 1000) * 0.35, 3),
                            'emission_factor': 0.35,
                            'location': data['region']
                        }
                        self.producer.send('carbon_calculations', value=carbon_data)
                
                logger.info(f"✅ Produced batch at {datetime.now().strftime('%H:%M:%S')}")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopping producer...")
        except Exception as e:
            logger.error(f"❌ Error in producer loop: {e}")
        finally:
            if self.producer:
                self.producer.flush()
                self.producer.close()

def main():
    """Main entry point with retry logic"""
    producer = UAEEnergyProducer(
        bootstrap_servers='localhost:9092',
        max_retries=5,
        retry_interval=5
    )
    producer.start_producing(num_households=5, interval_seconds=5)

if __name__ == "__main__":
    main()