# Delhi AQI System API Documentation

This documentation provides details for the Delhi AQI Prediction System API. The API offers real-time/latest forecasts, SHAP-based interpretations, counterfactual scenarios, and an AI chat interface.

## Base URL
The API is currently accessible at:
`http://localhost:8000/api/v1`

---

## 1. Predictions
Endpoints for retrieving AQI forecasts.

### Get Full 3-Day Forecast
Returns the full 3-day forecast for all regions.

- **URL:** `/predictions`
- **Method:** `GET`
- **Success Response:**
  - **Code:** 200
  - **Content:**
    ```json
    {
      "prediction_date_start": "2025-01-01",
      "generated_at": "2026-03-11 12:33:09",
      "regions": {
        "Central Delhi": {
          "day_1": 302.44,
          "day_2": 207.32,
          "day_3": 295.83,
          "category": ["Very Poor", "Poor", "Poor"]
        },
        "West Delhi": {
          "day_1": 305.42,
          "day_2": 280.45,
          "day_3": 301.41,
          "category": ["Very Poor", "Poor", "Very Poor"]
        }
      }
    }
    ```

### Get Forecast Summary
Returns a lightweight summary containing Day 1 predictions for all regions.

- **URL:** `/predictions/summary`
- **Method:** `GET`
- **Success Response:**
  - **Code:** 200
  - **Content:**
    ```json
    {
      "prediction_date_start": "2025-01-01",
      "generated_at": "2026-03-11 12:33:09",
      "regions": [
        {
          "region": "Central Delhi",
          "day_1_aqi": 302.44,
          "day_1_category": "Very Poor"
        },
        {
          "region": "West Delhi",
          "day_1_aqi": 305.42,
          "day_1_category": "Very Poor"
        }
      ]
    }
    ```

### Get Region Forecast
Returns the 3-day forecast for a specific region.

- **URL:** `/predictions/{region}`
- **Method:** `GET`
- **Path Parameters:**
  - `region` (string): The name of the region (e.g., `Central Delhi`, `West Delhi`). URL-encode spaces.
- **Success Response:**
  - **Code:** 200
  - **Content:**
    ```json
    {
      "day_1": 302.44,
      "day_2": 207.32,
      "day_3": 295.83,
      "category": ["Very Poor", "Poor", "Poor"]
    }
    ```

---

## 2. Explanations
Gemini-generated human-readable explanations.

### Get Full Explanation
Returns all 5 sections of the AI explanation.

- **URL:** `/explanation`
- **Method:** `GET`
- **Success Response:**
  - **Code:** 200
  - **Content:**
    ```json
    {
      "prediction_explanation": "...",
      "shap_interpretation": "...",
      "counterfactual_analysis": "...",
      "health_impact_summary": "...",
      "recommended_intervention": "..."
    }
    ```

### Get Specific Section
- `/explanation/prediction` - Prediction summary.
- `/explanation/health` - Health impact details.
- `/explanation/intervention` - Recommended actions.
- `/explanation/shap` - SHAP interpretation.
- `/explanation/counterfactual` - Counterfactual summary.

- **Method:** `GET`
- **Success Response:**
  - **Code:** 200
  - **Content:**
    ```json
    {
      "section": "prediction_explanation",
      "content": "Central Delhi is predicted to have 'Very Poor' air quality..."
    }
    ```

---

## 3. SHAP Analysis
Feature importance data for model predictions.

### Get All SHAP Data
Returns SHAP analysis for all regions and days.

- **URL:** `/shap`
- **Method:** `GET`
- **Success Response:**
  - **Code:** 200
  - **Content:**
    ```json
    [
      {
        "region": "Central Delhi",
        "prediction_day": 1,
        "base_value": 199.48,
        "predicted_value": 302.44,
        "top_features": [
          {
            "feature": "pm25",
            "shap_value": 63.09,
            "actual_value": 154.62
          }
        ]
      }
    ]
    ```

### Get SHAP for Region
- **URL:** `/shap/{region}`
- **Method:** `GET`

### Get SHAP for Region and Day
- **URL:** `/shap/{region}/day/{day}`
- **Method:** `GET`
- **Path Parameters:**
  - `day` (integer): 1, 2, or 3.

---

## 4. Counterfactuals
"What-if" scenarios for pollution reduction.

### Get All Counterfactual Scenarios
- **URL:** `/counterfactual`
- **Method:** `GET`
- **Success Response:**
  - **Code:** 200
  - **Content:**
    ```json
    [
      {
        "region": "Central Delhi",
        "original_day1_aqi": 302,
        "original_category": "Hazardous",
        "method": "Feature Perturbation",
        "scenarios": [
          {
            "name": "pm25 reduced by 25%",
            "type": "individual",
            "feature_changes": { "pm25": -25 },
            "new_aqi": 248,
            "new_category": "Very Unhealthy",
            "aqi_reduction": 54,
            "percent_improvement": "17.9%"
          }
        ]
      }
    ]
    ```

---

## 5. AI Agent
Interface for the Gemini-powered chat agent.

### Chat with Agent
Sends a message and history to the AI agent.

- **URL:** `/agent/chat`
- **Method:** `POST`
- **Request Body:**
  ```json
  {
    "message": "Why is the AQI high today?",
    "agent_type": "public",
    "history": []
  }
  ```
- **Success Response:**
  ```json
  {
    "response": "The AQI is high primarily due to elevated PM2.5 levels...",
    "agent_type": "public",
    "suggested_questions": ["What can I do?", "When will it improve?"]
  }
  ```

---

## 6. Pipeline
Triggers and status for the data processing pipeline.

### Trigger Pipeline
- **URL:** `/pipeline/run`
- **Method:** `POST`
- **Request Body:**
  ```json
  {
    "csv_path": "data/new_data.csv"
  }
  ```

### Get Pipeline Status
- **URL:** `/pipeline/status`
- **Method:** `GET`
- **Success Response:**
  ```json
  {
    "date": "2025-01-01",
    "pipeline_ran_at": "2026-03-11T12:33:35.090911",
    "gemini_attempts": 1,
    "validation_warnings": []
  }
  ```
