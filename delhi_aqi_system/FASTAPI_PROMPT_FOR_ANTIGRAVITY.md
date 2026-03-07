# FastAPI Creation Prompt for Antigravity / Claude Code

> Paste this entire prompt into Antigravity (Claude Code) and it will build your complete FastAPI layer without touching any of your existing code.

---

## PROMPT START — COPY EVERYTHING BELOW THIS LINE

---

You are an expert FastAPI engineer. Your task is to build a complete, production-grade FastAPI backend for an existing Delhi AQI prediction system. You must READ every existing source file first, then create new API files only. You must NOT modify, rename, move, or delete any existing file under any circumstance.

---

## STEP 1 — READ THE ENTIRE PROJECT FIRST (do this before writing a single line of code)

Read every file in this exact order before writing anything:

```
delhi_aqi_system/config.py
delhi_aqi_system/pipeline/data_loader.py
delhi_aqi_system/pipeline/feature_engineering.py
delhi_aqi_system/pipeline/model_predict.py
delhi_aqi_system/pipeline/shap_analysis.py
delhi_aqi_system/pipeline/counterfactual.py
delhi_aqi_system/pipeline/gemini_explainer.py
delhi_aqi_system/run_daily_pipeline.py
delhi_aqi_system/agents/agent_core.py
delhi_aqi_system/agents/context_builder.py
delhi_aqi_system/agents/suggested_questions.py
delhi_aqi_system/agents/system_prompts.py
delhi_aqi_system/outputs/predictions/predictions_3day.json
delhi_aqi_system/outputs/shap/shap_values.json
delhi_aqi_system/outputs/counterfactual/counterfactual_results.json
delhi_aqi_system/outputs/latest_result.json
```

After reading all files, confirm you understand:
- `run_daily_pipeline(new_csv_path)` is the main orchestrator in `run_daily_pipeline.py`
- `predict_future_days`, `perform_shap_analysis`, `generate_counterfactuals`, `generate_with_validation`, `save_daily_result` are the five pipeline functions
- `call_agent(user_message, agent_type, context, history)` is the chat function in `agents/agent_core.py`
- `build_context_for_agent(agent_type)` builds context from `outputs/latest_result.json`
- `latest_result.json` is the single source of truth with keys: `date`, `predictions`, `shap`, `counterfactuals`, `explanation`
- Regions are: Central Delhi, West Delhi, East Delhi, North Delhi, South Delhi, Overall Delhi
- All config (API keys, paths) lives in `config.py` and uses dotenv

---

## STEP 2 — TARGET FILE STRUCTURE TO CREATE

Create the following NEW files and directories only. Do NOT touch any existing file:

```
delhi_aqi_system/
└── api/
    ├── __init__.py                  (empty)
    ├── main.py                      (FastAPI app entry point)
    ├── dependencies.py              (shared dependencies: path resolution, result loader)
    ├── schemas/
    │   ├── __init__.py
    │   ├── prediction.py            (Pydantic models for prediction responses)
    │   ├── shap.py                  (Pydantic models for SHAP responses)
    │   ├── counterfactual.py        (Pydantic models for counterfactual responses)
    │   ├── explanation.py           (Pydantic models for Gemini explanation responses)
    │   ├── agent.py                 (Pydantic models for chat request/response)
    │   └── pipeline.py              (Pydantic models for pipeline trigger request/response)
    └── routers/
        ├── __init__.py
        ├── predictions.py           (GET endpoints for AQI forecast data)
        ├── shap.py                  (GET endpoints for SHAP analysis data)
        ├── counterfactual.py        (GET endpoints for counterfactual scenarios)
        ├── explanation.py           (GET endpoints for Gemini AI explanation)
        ├── agent.py                 (POST endpoint for AI chat)
        └── pipeline.py              (POST endpoint to trigger daily pipeline)
```

Also create at the project root (next to `delhi_aqi_system/` folder):
```
requirements_api.txt                 (FastAPI dependencies only)
```

---

## STEP 3 — IMPLEMENTATION RULES (follow these strictly)

### Rule 1: ZERO modifications to existing code
Do not change any file that already exists. If you need to call existing functions, import them using proper relative paths.

### Rule 2: Path resolution strategy
All existing code resolves paths relative to `delhi_aqi_system/` as the base. In `dependencies.py`, define a `get_base_dir()` function that resolves the correct absolute path to `delhi_aqi_system/` regardless of where uvicorn is launched from. Use this in all routers.

### Rule 3: Import strategy for existing pipeline modules
The existing pipeline scripts use local imports (e.g., `from data_loader import ...`). When calling them from the API, you must add the pipeline directory to `sys.path` before importing. Do this cleanly in `dependencies.py` using a startup function, not at module level in every router.

### Rule 4: Pydantic schemas must exactly mirror the actual JSON structures
- `predictions_3day.json` shape: `{prediction_date_start, generated_at, regions: {region_name: {day_1, day_2, day_3, category: [str,str,str]}}}`
- `shap_values.json` shape: list of `{region, prediction_day, base_value, predicted_value, top_features: [{feature, shap_value, actual_value}]}`
- `counterfactual_results.json` shape: list of `{region, original_day1_aqi, original_category, method, scenarios: [{name, type, feature_changes, new_aqi, new_category, aqi_reduction, percent_improvement, ...}]}`
- `latest_result.json` shape: `{date, pipeline_ran_at, gemini_model_used, gemini_attempts, validation_warnings, predictions, shap, counterfactuals, explanation: {prediction_explanation, shap_interpretation, counterfactual_analysis, health_impact_summary, recommended_intervention}}`

### Rule 5: No business logic in routers
Routers only: validate input → call existing function → return response. All logic stays in existing modules.

### Rule 6: Async compatibility
The existing pipeline functions are synchronous (blocking). Use `fastapi.concurrency.run_in_threadpool` or `asyncio.get_event_loop().run_in_executor` to call them from async endpoints so uvicorn is not blocked.

### Rule 7: Chat history management
The agent endpoints must maintain stateless design. The client sends the full `history` array with each request. The server calls `call_agent()` and returns the new response. Do not store history server-side.

---

## STEP 4 — DETAILED ENDPOINT SPECIFICATION

### Router: `routers/predictions.py`
Tag: `predictions`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/predictions` | Returns full 3-day forecast for all regions from `latest_result.json` |
| GET | `/api/v1/predictions/{region}` | Returns 3-day forecast for a single region (URL-encode spaces). Returns 404 if region not found. |
| GET | `/api/v1/predictions/summary` | Returns only `prediction_date_start`, `generated_at`, and a list of `{region, day_1_aqi, day_1_category}` |

### Router: `routers/shap.py`
Tag: `shap`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/shap` | Returns full SHAP analysis list  |
| GET | `/api/v1/shap/{region}` | Returns SHAP data for a specific region across all prediction days. 404 if not found. |
| GET | `/api/v1/shap/{region}/day/{day}` | Returns SHAP data for a specific region and day (1, 2, or 3). 422 if day not in [1,2,3]. |

### Router: `routers/counterfactual.py`
Tag: `counterfactual`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/counterfactual` | Returns all counterfactual results |
| GET | `/api/v1/counterfactual/{region}` | Returns counterfactual scenarios for a specific region. 404 if not found. |

### Router: `routers/explanation.py`
Tag: `explanation`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/explanation` | Returns the full Gemini explanation object (all 5 sections) from `latest_result.json` |
| GET | `/api/v1/explanation/prediction` | Returns only the `prediction_explanation` field |
| GET | `/api/v1/explanation/health` | Returns only the `health_impact_summary` field |
| GET | `/api/v1/explanation/intervention` | Returns only the `recommended_intervention` field |
| GET | `/api/v1/explanation/shap` | Returns only the `shap_interpretation` field |
| GET | `/api/v1/explanation/counterfactual` | Returns only the `counterfactual_analysis` field |

### Router: `routers/agent.py`
Tag: `agent`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/agent/chat` | Sends a message to the AI agent and returns the response |
| GET | `/api/v1/agent/questions/{agent_type}` | Returns suggested starter questions for `public` or `policy` agent |

**Chat Request Schema (`AgentChatRequest`):**
```python
class HistoryTurn(BaseModel):
    role: str          # "user" or "model"
    content: str

class AgentChatRequest(BaseModel):
    message: str                        # current user message
    agent_type: str = "public"          # "public" or "policy"
    history: List[HistoryTurn] = []     # full conversation history from client
```

**Chat Response Schema (`AgentChatResponse`):**
```python
class AgentChatResponse(BaseModel):
    response: str                       # agent's reply text
    agent_type: str                     # echoed back
    suggested_questions: List[str]      # 3 random suggestions for follow-up
```

The chat endpoint must:
1. Validate `agent_type` is "public" or "policy" — return 422 otherwise
2. Call `build_context_for_agent(agent_type)` from `agents/context_builder.py`
3. Convert `history` list to the format `[{"role": ..., "content": ...}]` that `call_agent` expects
4. Call `call_agent(message, agent_type, context, history)` in a thread pool (non-blocking)
5. Return response + 3 randomly sampled suggested questions from `get_suggested_questions(agent_type)`

### Router: `routers/pipeline.py`
Tag: `pipeline`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/pipeline/run` | Triggers the full daily pipeline with a new CSV data file path |
| GET | `/api/v1/pipeline/status` | Returns metadata about the last pipeline run from `latest_result.json` |

**Pipeline Run Request Schema (`PipelineRunRequest`):**
```python
class PipelineRunRequest(BaseModel):
    csv_path: str    # absolute or relative path to the new live data CSV
```

**Pipeline Run Response Schema (`PipelineRunResponse`):**
```python
class PipelineRunResponse(BaseModel):
    success: bool
    output_path: str
    gemini_attempts: int
    validation_warnings: List[str]
    date: str
    message: str
```

The pipeline run endpoint must:
1. Validate the `csv_path` exists on disk — return 400 with clear error if not
2. Call `run_daily_pipeline(csv_path)` from `run_daily_pipeline.py` in a thread pool
3. On success, return the full pipeline run response
4. On exception, return HTTP 500 with the error message

---

## STEP 5 — `main.py` REQUIREMENTS

```python
# delhi_aqi_system/api/main.py

# Must include:
# - FastAPI app with title="Delhi AQI System API", version="1.0.0", description="..."
# - CORS middleware: allow_origins=["*"] (for frontend dev), allow all methods and headers
# - Include all 5 routers with prefix="/api/v1" and their tags
# - Startup event that: (1) adds pipeline dir to sys.path, (2) logs confirmation
# - Root endpoint GET "/" returning {"status": "ok", "message": "Delhi AQI API running"}
# - Health check endpoint GET "/health" returning {"status": "healthy", "timestamp": datetime.now().isoformat()}
# - Global exception handler for unhandled errors returning {"detail": str(e)} with 500
```

---

## STEP 6 — `dependencies.py` REQUIREMENTS

```python
# delhi_aqi_system/api/dependencies.py

# Must include:
# - get_base_dir() -> str: returns absolute path to delhi_aqi_system/ directory
# - setup_sys_path(): adds pipeline dir and base dir to sys.path (idempotent)
# - get_latest_result() -> dict: loads and returns outputs/latest_result.json, raises HTTPException(503) if file not found
# - VALID_REGIONS: list of the 6 valid region names
# - VALID_AGENT_TYPES: ["public", "policy"]
```

---

## STEP 7 — `requirements_api.txt` CONTENT

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
python-multipart>=0.0.9
pydantic>=2.0.0
```

(Do NOT include the project's existing ML dependencies — those are already installed)

---

## STEP 8 — FINAL VERIFICATION CHECKLIST

After creating all files, verify:
- [ ] No existing file has been modified
- [ ] All 5 routers are registered in `main.py`
- [ ] All Pydantic schemas use `model_config = ConfigDict(from_attributes=True)` (Pydantic v2)
- [ ] Every endpoint has a `summary=` and `description=` in its decorator
- [ ] Region name matching in path params uses case-insensitive comparison or exact match with clear 404 message listing valid regions
- [ ] The chat endpoint never stores state server-side
- [ ] Pipeline endpoint wraps call in try/except and returns 500 on failure
- [ ] All file I/O uses absolute paths via `get_base_dir()`

---

## STEP 9 — HOW TO RUN (add this as a comment in `main.py`)

```bash
# From the project root (parent of delhi_aqi_system/):
uvicorn delhi_aqi_system.api.main:app --reload --port 8000

# API docs will be available at:
# http://localhost:8000/docs   (Swagger UI)
# http://localhost:8000/redoc  (ReDoc)
```

---

## FINAL REMINDER

- Read ALL existing files before writing any code
- Create NEW files only — never modify existing ones
- Import existing functions, never rewrite them
- Use thread pool for all blocking pipeline/agent calls
- Every endpoint must return proper HTTP status codes (200, 400, 404, 422, 500, 503)

Now begin. Read the files first, then build.

---

## PROMPT END
