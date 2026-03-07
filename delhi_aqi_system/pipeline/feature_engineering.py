import pandas as pd
import numpy as np
import datetime

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies feature engineering tailored for Delhi AQI Prediction:
    - DateTime parsing (hour, day of week, month, season, etc.)
    - Lag features (1-day, 2-day, 3-day)
    - Rolling window features (3-day, 7-day)
    - Interaction features
    """
    print("Starting feature engineering...")
    
    # Ensure datetime is parsed
    if not np.issubdtype(df['datetime'].dtype, np.datetime64):
        df['datetime'] = pd.to_datetime(df['datetime'])
        
    # Re-sort to be safe
    if 'region_name' in df.columns:
        df.sort_values(by=['region_name', 'datetime'], ascending=True, inplace=True)
    else:
        df.sort_values(by=['datetime'], ascending=True, inplace=True)
        
    df.reset_index(drop=True, inplace=True)
    
    # 1. Parse datetime
    df['month'] = df['datetime'].dt.month
    df['day_of_week'] = df['datetime'].dt.dayofweek
    df['day_of_month'] = df['datetime'].dt.day
    df['hour'] = df['datetime'].dt.hour
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # Identify season (1: Winter, 2: Spring, 3: Summer, 4: Monsoon/Autumn)
    # Mapping commonly used for North India:
    # Winter: Dec-Feb (1), Summer: Mar-May (2), Monsoon: Jun-Sep (3), Post-Monsoon/Autumn: Oct-Nov (4)
    def get_season(month):
        if month in [12, 1, 2]: return 1
        elif month in [3, 4, 5]: return 2
        elif month in [6, 7, 8, 9]: return 3
        else: return 4
        
    df['season'] = df['month'].apply(get_season)
    
    # Check if 'is_gazetted_holiday' or 'is_restricted_holiday' exist, combine as 'is_holiday'
    if 'is_gazetted_holiday' in df.columns and 'is_restricted_holiday' in df.columns:
        df['is_holiday'] = ((df['is_gazetted_holiday'] == 1) | (df['is_restricted_holiday'] == 1)).astype(int)
    elif 'is_gazetted_holiday' in df.columns:
        df['is_holiday'] = df['is_gazetted_holiday']
    
    # 2. Lag features for AQI
    print("Generating lag features...")
    if 'region_name' in df.columns:
        grouped = df.groupby('region_name')
        
        df['AQI_lag1'] = grouped['AQI'].shift(1)
        df['AQI_lag2'] = grouped['AQI'].shift(2)
        df['AQI_lag3'] = grouped['AQI'].shift(3)
        
        # Also lag some major pollutants if we have them
        for col in ['pm25', 'pm10', 'no2', 'so2', 'co']:
            if col in df.columns:
                df[f'{col}_lag1'] = grouped[col].shift(1)
                
        # 3. Rolling window features
        print("Generating rolling window features...")
        df['AQI_rolling_mean_3'] = grouped['AQI'].transform(lambda x: x.rolling(window=3, min_periods=1).mean())
        df['AQI_rolling_mean_7'] = grouped['AQI'].transform(lambda x: x.rolling(window=7, min_periods=1).mean())
    else:
        df['AQI_lag1'] = df['AQI'].shift(1)
        df['AQI_lag2'] = df['AQI'].shift(2)
        df['AQI_lag3'] = df['AQI'].shift(3)
        
        df['AQI_rolling_mean_3'] = df['AQI'].rolling(window=3, min_periods=1).mean()
        df['AQI_rolling_mean_7'] = df['AQI'].rolling(window=7, min_periods=1).mean()

    # 4. Interaction features
    print("Generating interaction features...")
    if 't2m' in df.columns and 'humidity' in df.columns:
        df['temp_humidity_interaction'] = df['t2m'] * df['humidity']
        # Wind x pm25
    if 'wind_speed' in df.columns and 'pm25' in df.columns:
        df['wind_pm25_interaction'] = df['wind_speed'] * df['pm25']
    if 'wind_speed' in df.columns and 'AQI' in df.columns:
        df['wind_aqi_interaction'] = df['wind_speed'] * df['AQI']
        
    # Drop NaNs that originated from the lags
    df.dropna(subset=['AQI_lag3'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    print(f"Feature engineering completed. New shape: {df.shape}")
    return df

def run_data_pipeline(input_csv: str, output_csv: str):
    import sys
    import os
    # Add pipeline folder to path so we can import data_loader when running as script
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from data_loader import load_and_validate_data
    
    df = load_and_validate_data(input_csv)
    df_processed = engineer_features(df)
    
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_processed.to_csv(output_csv, index=False)
    print(f"✅ Processed data saved successfully to {output_csv}")

if __name__ == "__main__":
    import os
    # When running directly from the pipeline folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file = os.path.join(base_dir, 'data', 'raw', 'Delhi_AQI_final.csv')
    output_file = os.path.join(base_dir, 'data', 'processed', 'delhi_aqi_processed.csv')
    
    run_data_pipeline(input_csv=input_file, output_csv=output_file)
