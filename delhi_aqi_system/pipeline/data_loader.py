import pandas as pd
import numpy as np

def load_and_validate_data(filepath: str) -> pd.DataFrame:
    """
    Loads and validates the Delhi AQI dataset.
    """
    print(f"Loading data from {filepath}...")
    df = pd.read_csv(filepath)
    
    # 1. Confirm datetime column is present
    if 'date' in df.columns:
        df['datetime'] = pd.to_datetime(df['date'])
        df.drop(columns=['date'], inplace=True, errors='ignore')
    elif 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
    else:
        raise ValueError("No 'date' or 'datetime' column found in dataset.")
        
    # 2. Sort entire dataset by datetime (ascending) - critical for time-series integrity
    df.sort_values(by='datetime', ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # 3. Identify region columns
    region_cols = [col for col in df.columns if col.startswith('region_')]
    print(f"Identified region columns: {region_cols}")
    
    # 4. Check for nulls and forward fill/backward fill to maintain sequence
    null_counts = df.isnull().sum()
    if null_counts.sum() > 0:
        print("Missing values detected. Imputing values using ffill and bfill...")
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        
    # 5. Check for duplicate timestamps
    if len(region_cols) > 0:
        # Ensure we have a region_name column for grouping if not already present
        if 'region_name' not in df.columns:
            # Reconstruct region name from boolean indicators
            df['region_name'] = df[region_cols].idxmax(axis=1).str.replace('region_', '')
            
        duplicates = df.duplicated(subset=['datetime', 'region_name']).sum()
        if duplicates > 0:
            print(f"Found {duplicates} duplicate timestamps. Dropping duplicates...")
            df.drop_duplicates(subset=['datetime', 'region_name'], keep='last', inplace=True)
    else:
        duplicates = df.duplicated(subset=['datetime']).sum()
        if duplicates > 0:
            print(f"Found {duplicates} duplicate timestamps. Dropping duplicates...")
            df.drop_duplicates(subset=['datetime'], keep='last', inplace=True)

    # 6. Confirm AQI target column
    if 'AQI' not in df.columns:
        raise ValueError("AQI target column missing.")
        
    print(f"Data loaded successfully. Shape: {df.shape}")
    return df

def load_live_data(source: str) -> pd.DataFrame:
    """
    API-Ready Design: Loads live data from a source.
    Currently 'source' is a CSV file path. Future implementations can replace this with an API endpoint (e.g. CPCB API) without affecting the pipeline.
    """
    if source.endswith('.csv'):
        return load_and_validate_data(source)
    else:
        raise NotImplementedError("Currently only CSV sources are supported.")

if __name__ == "__main__":
    df = load_live_data('../data/raw/Delhi_AQI_final.csv')
    print(df.head())
