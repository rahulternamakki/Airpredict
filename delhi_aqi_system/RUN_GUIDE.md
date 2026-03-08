# Delhi AQI Prediction System - Complete Execution Guide

This document provides a comprehensive, start-to-end guide to setting up and running the Delhi AQI Prediction System. This system integrates XGBoost ML models, SHAP explainability, and Gemini AI to provide actionable air quality intelligence.

---

## 1. Project Overview

The system consists of three primary components:
1.  **ML Pipeline**: Processes data and generates predictions/explanations.
2.  **FastAPI Backend**: Serves structured data and handles AI agent logic.
3.  **Streamlit Frontend**: Provides an interactive dashboard and two specialized AI agents (Vayu and DELPHI).

---

## 2. Initial Setup

### Step 1: Install Google Cloud CLI (Required for Vertex AI)
Since the system uses Vertex AI, you must have the Google Cloud CLI installed to authenticate your environment.
- **Download**: [Google Cloud CLI Installer](https://cloud.google.com/sdk/docs/install#windows)
- **Installation Path**: You can install it in the **default location** suggested by the installer. This is usually:
  - `C:\Program Files (x86)\Google\Cloud SDK` (System-wide)
  - `C:\Users\<YourUser>\AppData\Local\Google\Cloud SDK` (User-specific)

> [!TIP]
> **After installation, you MUST close and reopen your terminal window** for the `gcloud` command to be recognized. If it still isn't recognized, ensure the `google-cloud-sdk\bin` folder is in your system **PATH**.

### Step 2: Authenticate with Google Cloud
Open **any** terminal window (it doesn't matter which folder you are in) and run the following command. This will open a browser window for you to log in:
```powershell
gcloud auth application-default login
```
*Note: This is a one-time global setup for your computer.*

### Step 3: Create a Virtual Environment
It is highly recommended to use a Python virtual environment.

```powershell
# Navigate to the project root
cd "c:\Users\Rahul Ternamakki\OneDrive\Desktop\AQI_Front"

# Create the virtual environment
python -m venv venv
```

### Step 2: Activate the Environment
You must activate the environment in **every new terminal window** you open.

**On Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
.\venv\Scripts\activate.bat
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

---

## 3. Dependency Installation

Install the required packages for both the API and the Frontend.

```powershell
# Install Backend & Pipeline requirements
pip install -r delhi_aqi_system/requirements_api.txt

# Install Frontend requirements
pip install -r streamlit_frontend/requirements_frontend.txt
```

---

## 4. Configuration (.env)

The system requires access to Google Gemini or Vertex AI. Create a `.env` file in the `delhi_aqi_system/` directory.

**File Path:** `delhi_aqi_system/.env`

**Required Variables:**
```env
# Google Cloud Project Details
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=asia-south1

# Optional: Gemini API Key (Only used if falling back to standard SDK)
GEMINI_API_KEY=your_gemini_api_key_here
```

> [!IMPORTANT]
> Ensure `GOOGLE_CLOUD_PROJECT` matches the project you logged into during Step 2.

---

## 5. Execution Order (Start-to-End)

Follow these steps in order to ensure the system has fresh data to display.

### Step 1: Run the Daily Pipeline
This script executes the ML models, generates SHAP/Counterfactual values, and calls Gemini AI for the scientific explanation. It creates the critical `outputs/latest_result.json` file.

```powershell
python delhi_aqi_system/run_daily_pipeline.py
```

### Step 2: Start the FastAPI Backend
Open a **new terminal**, activate the `venv`, and run:

```powershell
uvicorn delhi_aqi_system.api.main:app --host 0.0.0.0 --port 8000 --reload
```
*   **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### Step 3: Start the Streamlit Frontend
Open a **third terminal**, activate the `venv`, and run:

```powershell
streamlit run streamlit_frontend/streamlit_frontend.py
```

---

## 6. Project Architecture Summary

1.  **Data Loading**: `pipeline/data_loader.py` fetches the latest AQI readings.
2.  **Inference**: `pipeline/model_predict.py` uses XGBoost to forecast AQI for 6 Delhi regions.
3.  **Explainability**: `pipeline/shap_analysis.py` (Why) and `pipeline/counterfactual.py` (What-if).
4.  **Generative AI**: `pipeline/gemini_explainer.py` synthesizes outcomes into a narrative.
5.  **Service Layer**: FastAPI (`api/main.py`) exposes these results via REST endpoints.
6.  **Interface**: Streamlit (`streamlit_frontend.py`) visualizes forecasts and hosts the **Vayu** (Public) and **DELPHI** (Policy) agents.

---

## 7. Troubleshooting

-   **"ModuleNotFoundError"**: Ensure you have activated the `venv` and installed requirements from both `.txt` files.
-   **"No explanation data found"**: You must run Step 1 (Pipeline) successfully before the Frontend can display results.
-   **Port 8000 Busy**: If Uvicorn fails to start, another process is using port 8000. Specify a different port: `--port 8001`.
