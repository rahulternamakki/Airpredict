import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
import matplotlib.pyplot as plt
import joblib
import os
import logging
import optuna

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    non_zero = y_true != 0
    return np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100

def calculate_smape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    non_zero = denominator != 0
    return np.mean(np.abs(y_true[non_zero] - y_pred[non_zero]) / denominator[non_zero]) * 100

def optimize_hyperparameters(X, y, region_horizon):
    logging.info(f"Starting Optuna hyperparameter tuning for {region_horizon}...")
    
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 300),
            'max_depth': trial.suggest_int('max_depth', 3, 6),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'random_state': 42,
            'objective': 'reg:squarederror'
        }
        
        tscv = TimeSeriesSplit(n_splits=3)
        rmses = []
        
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            model = xgb.XGBRegressor(**params, early_stopping_rounds=20)
            
            model.fit(
                X_tr, y_tr,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
            
            preds = model.predict(X_val)
            rmse = np.sqrt(mean_squared_error(y_val, preds))
            rmses.append(rmse)
            
        return np.mean(rmses)
        
    study = optuna.create_study(direction='minimize')
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study.optimize(objective, n_trials=20, show_progress_bar=False) 
    
    logging.info(f"Best params for {region_horizon}: {study.best_params}")
    return study.best_params

def train_and_evaluate_model(X_train, y_train, X_test, y_test, region_horizon):
    
    # Run tuning using only the training data
    best_params = optimize_hyperparameters(X_train, y_train, region_horizon)
    
    logging.info(f"Training final XGBoost model for {region_horizon}...")
    # Add random state and objective to best params
    best_params['random_state'] = 42
    best_params['objective'] = 'reg:squarederror'
    
    model = xgb.XGBRegressor(**best_params, early_stopping_rounds=20)
    
    val_split_idx = int(len(X_train) * 0.9)
    X_tr, X_val = X_train.iloc[:val_split_idx], X_train.iloc[val_split_idx:]
    y_tr, y_val = y_train.iloc[:val_split_idx], y_train.iloc[val_split_idx:]
    
    # Fit final model with early stopping on the validation set
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    # Predict
    y_pred = model.predict(X_test)
    
    # Metrics
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mape = calculate_mape(y_test, y_pred)
    smape = calculate_smape(y_test, y_pred)
    
    logging.info(f"=== {region_horizon} Metrics ===")
    logging.info(f"MAE:   {mae:.2f}")
    logging.info(f"RMSE:  {rmse:.2f}")
    logging.info(f"R²:    {r2:.4f}")
    logging.info(f"MAPE:  {mape:.2f}%")
    logging.info(f"SMAPE: {smape:.2f}%")
    
    return model, y_pred, mae, rmse, r2, mape, smape

def plot_predictions(dates, y_true, y_pred, region_horizon, output_dir):
    plt.figure(figsize=(12, 6))
    plt.plot(dates, y_true, label='Actual AQI', color='blue', alpha=0.7)
    plt.plot(dates, y_pred, label='Predicted AQI', color='red', alpha=0.7)
    plt.title(f'{region_horizon} - Actual vs Predicted')
    plt.xlabel('Date')
    plt.ylabel('AQI')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    # Replace spaces and special characters for filename
    filename_prefix = region_horizon.replace(" ", "_").replace("(", "").replace(")", "").replace("+", "_")
    plt.savefig(os.path.join(output_dir, f'{filename_prefix}_prediction.png'))
    plt.close()

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, 'data', 'processed', 'delhi_aqi_processed.csv')
    models_dir = os.path.join(base_dir, 'models', 'saved')
    plots_dir = os.path.join(base_dir, 'outputs', 'predictions')
    
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)
    
    logging.info("Loading processed data...")
    df = pd.read_csv(data_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    # Prepare target scenarios (Day 1, 2, 3)
    target_col = 'AQI'
    exclude_cols = ['datetime', 'date', 'region_name', target_col, 'target_day1', 'target_day2', 'target_day3']
    regions = df['region_name'].unique().tolist()
    
    all_models = {}
    metrics_summary = []
    
    all_train_df = pd.DataFrame()
    all_test_df = pd.DataFrame()
    
    # 1. Train models for each of the 5 regions
    for region in regions:
        region_df = df[df['region_name'] == region].copy()
        region_df = region_df.sort_values(by='datetime').reset_index(drop=True)
        
        # Shift target for Day 1, Day 2, Day 3 independent prediction horizons
        region_df['target_day1'] = region_df['AQI'].shift(-1)
        region_df['target_day2'] = region_df['AQI'].shift(-2)
        region_df['target_day3'] = region_df['AQI'].shift(-3)
        region_df = region_df.dropna(subset=['target_day1', 'target_day2', 'target_day3']).reset_index(drop=True)
        
        split_idx = int(len(region_df) * 0.8)
        train_df = region_df.iloc[:split_idx].copy()
        test_df = region_df.iloc[split_idx:].copy()
        
        all_train_df = pd.concat([all_train_df, train_df])
        all_test_df = pd.concat([all_test_df, test_df])
        
        X_train_raw = train_df.drop(columns=[col for col in exclude_cols if col in train_df.columns])
        X_test_raw = test_df.drop(columns=[col for col in exclude_cols if col in test_df.columns])
        test_dates = test_df['datetime']
        
        X_train = X_train_raw.astype(float)
        X_test = X_test_raw.astype(float)
        
        region_display_name = f"{region} Delhi"
        all_models[region_display_name] = {}
        
        for day in [1, 2, 3]:
            y_train = train_df[f'target_day{day}']
            y_test = test_df[f'target_day{day}']
            
            horizon_name = f"{region_display_name} (Day+{day})"
            model, y_pred, mae, rmse, r2, mape, smape = train_and_evaluate_model(
                X_train, y_train, X_test, y_test, horizon_name
            )
            
            all_models[region_display_name][f"day_{day}"] = model
            
            plot_predictions(test_dates, y_test.values, y_pred, horizon_name, plots_dir)
            
            metrics_summary.append({
                'Region': region_display_name,
                'Horizon': f"Day+{day}",
                'MAE': mae,
                'RMSE': rmse,
                'R2': r2,
                'MAPE': mape,
                'SMAPE': smape
            })

    # 2. Train Overall Delhi Model
    logging.info("Preparing Overall Delhi data safely with isolated train/test aggregates...")
    
    # Aggregate strictly on train, then strictly on test
    overall_train = all_train_df.groupby('datetime').mean(numeric_only=True).reset_index()
    overall_train = overall_train.sort_values(by='datetime').reset_index(drop=True)
    
    overall_test = all_test_df.groupby('datetime').mean(numeric_only=True).reset_index()
    overall_test = overall_test.sort_values(by='datetime').reset_index(drop=True)
    
    X_train_overall = overall_train.drop(columns=[col for col in exclude_cols if col in overall_train.columns])
    X_test_overall = overall_test.drop(columns=[col for col in exclude_cols if col in overall_test.columns])
    test_dates_overall = overall_test['datetime']
    
    X_train_overall = X_train_overall.astype(float)
    X_test_overall = X_test_overall.astype(float)
    
    all_models["Overall Delhi"] = {}
    
    for day in [1, 2, 3]:
        y_train_overall = overall_train[f'target_day{day}']
        y_test_overall = overall_test[f'target_day{day}']
        
        horizon_name = f"Overall Delhi (Day+{day})"
        model, y_pred, mae, rmse, r2, mape, smape = train_and_evaluate_model(
            X_train_overall, y_train_overall, X_test_overall, y_test_overall, horizon_name
        )
        all_models["Overall Delhi"][f"day_{day}"] = model
        plot_predictions(test_dates_overall, y_test_overall.values, y_pred, horizon_name, plots_dir)
        
        metrics_summary.append({
            'Region': 'Overall Delhi',
            'Horizon': f"Day+{day}",
            'MAE': mae,
            'RMSE': rmse,
            'R2': r2,
            'MAPE': mape,
            'SMAPE': smape
        })
    
    # Save models
    model_path = os.path.join(models_dir, 'delhi_aqi_all_regions.pkl')
    joblib.dump(all_models, model_path)
    logging.info(f"✅ Successfully saved all models (nested dict) to {model_path}")
    
    # Save metrics summary
    metrics_df = pd.DataFrame(metrics_summary)
    metrics_path = os.path.join(plots_dir, 'evaluation_metrics.csv')
    metrics_df.to_csv(metrics_path, index=False)
    logging.info(f"Evaluation metrics saved to {metrics_path}")
    print("\n--- Final Model Metrics ---")
    print(metrics_df.to_string(index=False))

if __name__ == "__main__":
    main()
