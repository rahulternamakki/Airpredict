# Pages and Features Breakdown

This document details the functionality and UI components of each page in the `streamlit_frontend` application.

## 1. Main Dashboard (`streamlit_frontend.py`)
The primary landing page for the application.

- **Summary Cards**: Displays Tomorrow's (Day+1) AQI for all regions (North, South, East, West, Central, etc.). Each card is color-coded by AQI category.
- **Regional Comparison Chart**: A grouped bar chart allowing users to switch between Day+1, Day+2, and Day+3 forecasts.
- **Trend Chart**: A multi-line Plotly chart showing the 3-day AQI trend for user-selected regions.
- **Forecast Table**: A tabular view of all AQI values and categories for all regions and all three forecast days.
- **Staleness Banner**: Displays the last time the pipeline ran and the model configuration used.

## 2. Model Insights (`02_model_insights.py`)
Provides technical depth using SHAP (SHapley Additive exPlanations).

- **SHAP Waterfall Chart**: Shows how individual features (e.g., Temperature, NO2 levels) contributed to a specific region's forecast.
- **Feature Impact Bar Chart**: A horizontal bar chart summarizing the magnitude and direction of feature impacts.
- **Detail Table**: Lists observed feature values alongside their SHAP contributions.
- **Cross-Region Summary**: An expander showing SHAP summaries for all regions to identify global trends.

## 3. What-If Scenario Analysis (`03_whatif.py`)
Interactive simulation of emission reduction scenarios.

- **Metric Comparison**: Compares 'Original AQI' with 'Best Achievable AQI' based on counterfactual interventions.
- **Reduction Chart**: A bar chart showing the potential AQI reduction for various scenarios (e.g., "50% Traffic Reduction").
- **Scenario Cards**: Detailed expanders explaining exactly which features were modified and the resulting AQI category change.

## 4. AI Scientific Explanation (`04_ai_explanation.py`)
Generative narrative of the forecast data.

- **Forecast Explanation**: Natural language summary of the current AQI situation.
- **Technical Interpretation**: Explains SHAP and Counterfactual results in plain science.
- **Health & Intervention**: Provides actionable health advice and recommended policy interventions.

## 5. AI Agents (`05_ai_agents.py`)
A dual-agent conversational interface.

- **Vayu (Public Assistant)**: Focuses on plain language, health tips, and general queries.
- **DELPHI (Policy Advisor)**: Focuses on technical metrics, SHAP values, and GRAP (Graded Response Action Plan) status.
- **Features**: Chat history persistence, suggestion chips (quick questions), and chat export functionality.
