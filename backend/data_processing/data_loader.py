# data_processing/data_loader.py
import pandas as pd
from pathlib import Path
import numpy as np
from datetime import datetime, timedelta
import tables
import traceback

class UKDALELoader:
    def __init__(self, data_path=None):
        if data_path is None:
            current_dir = Path(__file__).parent.parent.parent
            self.data_path = current_dir / "datasets" / "ukdale"
        else:
            self.data_path = Path(data_path)
        
        self.h5_file = self.data_path / "ukdale.h5"
        print(f"UK-DALE Data Path: {self.data_path}")
        
        if self.h5_file.exists():
            print(f"✓ UK-DALE file found: {self.h5_file}")
        else:
            print(f"✗ UK-DALE file not found at {self.h5_file}")
    
    def load_house_data(self, house_number=1, sample_size=1000):
        print(f"\nLoading House {house_number} ({sample_size} samples)...")
        
        real_data = self._read_ukdale_dataset(house_number, sample_size)
        
        if real_data is not None:
            print(f"✓ Loaded {len(real_data)} UK-DALE records")
            return real_data
        
        print("✗ Real data load failed")
        return None
    
    def _read_ukdale_dataset(self, house_number, sample_size):
        if not self.h5_file.exists():
            return None
        
        try:
            with tables.open_file(str(self.h5_file), mode='r') as f:
                table_path = f'/building{house_number}/elec/meter1/table'
                
                if table_path not in f:
                    print(f"Table not found: {table_path}")
                    return None
                
                table = f.get_node(table_path)
                read_rows = min(sample_size, table.nrows)
                
                data = table.read(start=0, stop=read_rows)
                
                # Extract timestamps and power values
                timestamps_ns = data['index']
                power_nested = data['values_block_0']
                
                # Convert nested arrays
                if power_nested.ndim == 1 and power_nested.dtype == np.dtype(('float32', (1,))):
                    power_values = np.array([x[0] for x in power_nested])
                else:
                    power_values = power_nested.flatten()
                
                # Convert timestamps
                timestamps_s = timestamps_ns / 1_000_000_000.0
                timestamps = pd.to_datetime(timestamps_s, unit='s', utc=True)
                timestamps = [ts.tz_localize(None) for ts in timestamps]
                
                # Create DataFrame
                result = pd.DataFrame({
                    'timestamp': timestamps,
                    'power_watts': power_values,
                    'appliance': f'Whole House (UK-DALE House {house_number})',
                    'house_id': house_number
                })
                
                return result
                
        except Exception as e:
            print(f"Error reading UK-DALE data: {e}")
            return None
    
    def get_summary_stats(self, df):
        if df is None or df.empty:
            return {"error": "No data available"}
        
        time_span = (df['timestamp'].max() - df['timestamp'].min())
        
        return {
            'total_records': len(df),
            'date_range': f"{df['timestamp'].min().date()} to {df['timestamp'].max().date()}",
            'time_span_hours': f"{time_span.total_seconds() / 3600:.2f}",
            'avg_power_watts': f"{df['power_watts'].mean():.1f}",
            'max_power_watts': f"{df['power_watts'].max():.1f}",
            'min_power_watts': f"{df['power_watts'].min():.1f}",
            'energy_consumed_kwh': f"{df['power_watts'].sum() * (6/3600) / 1000:.3f}",
            'data_source': df['appliance'].iloc[0],
            'house_id': int(df['house_id'].iloc[0])
        }