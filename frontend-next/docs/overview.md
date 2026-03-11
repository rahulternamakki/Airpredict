# Delhi AQI Forecast — Frontend Overview

This document provides a high-level summary of the `streamlit_frontend` application, which serves as the user interface for the Delhi AQI Intelligence System. This documentation is intended to guide the migration of the frontend from Streamlit to Next.js.

## Project Vision
The application provides real-time and 3-day forecasted air quality insights for various regions in Delhi. It aims to make complex environmental data accessible and actionable for both citizens and policymakers through predictive modeling and AI-driven explanations.

## Application Architecture (Current)
The current frontend is a multi-page Streamlit application that communicates with a FastAPI backend.

- **Entry Point**: `streamlit_frontend.py` (Main Dashboard)
- **Sub-pages**: Located in the `pages/` directory.
- **Components**: Reusable UI elements in the `components/` directory (cards, charts, banners).
- **API Client**: `api_client.py` handles all HTTP communication with the backend.

## User Flow
1. **Landing/Dashboard**: Users see an immediate 3-day forecast summary across all regions.
2. **Analysis**: Users can dive into "Model Insights" to understand the 'why' behind predictions or use "What-If Analysis" to simulate interventions.
3. **Explanation**: A "Scientific Explanation" page provides AI-generated narratives.
4. **Interaction**: "AI Agents" offer a conversational interface for specific technical or health-related queries.

## Key Stakeholders
- **Citizens**: Interested in local AQI levels, health impacts, and simple forecasts.
- **Policymakers**: Interested in system-wide trends, feature importance (SHAP), and the impact of specific interventions (Counterfactuals).
