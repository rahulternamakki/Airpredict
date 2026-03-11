# API Integration & Data Mapping

This document maps the frontend features to the corresponding backend API endpoints.

## Base URL
The frontend currently uses a configurable `API_V1` base URL.

## Predictions
| Feature | Endpoint | Method | Key Data |
| :--- | :--- | :--- | :--- |
| **Summary Dashboard** | `/predictions/summary` | GET | `regions` array with `day_1_aqi` and `day_1_category` |
| **Full Forecast Data** | `/predictions` | GET | Map of regions to 3-day AQI/Category arrays |
| **Regional Detail** | `/predictions/{region}` | GET | Specific 3-day forecast for one region |

## Explanability (SHAP)
| Feature | Endpoint | Method | Key Data |
| :--- | :--- | :--- | :--- |
| **All SHAP Data** | `/shap` | GET | List of all SHAP entries for all regions/days |
| **Regional SHAP** | `/shap/{region}` | GET | SHAP entries for specific region |
| **Single Insight** | `/shap/{region}/day/{day}` | GET | `base_value`, `predicted_value`, `top_features` list |

## What-If Analysis
| Feature | Endpoint | Method | Key Data |
| :--- | :--- | :--- | :--- |
| **All Counterfactuals**| `/counterfactual` | GET | List of intervention scenarios for all regions |
| **Regional Scenarios**| `/counterfactual/{region}`| GET | `original_day1_aqi`, `scenarios` array (new AQI, reduction) |

## AI Narratives
| Feature | Endpoint | Method | Key Data |
| :--- | :--- | :--- | :--- |
| **Full Scientific Expl**| `/explanation` | GET | Markdown strings for `prediction`, `shap`, `health`, etc. |
| **Specific Section** | `/explanation/{section}`| GET | Specific narrative block |

## Conversational AI
| Feature | Endpoint | Method | Payload |
| :--- | :--- | :--- | :--- |
| **Agent Chat** | `/agent/chat` | POST | `{message, agent_type, history}` |
| **Suggestions** | `/agent/questions/{type}`| GET | List of string questions |

## System Status
| Feature | Endpoint | Method | Key Data |
| :--- | :--- | :--- | :--- |
| **Pipeline Status** | `/pipeline/status` | GET | `pipeline_ran_at`, `gemini_model_used`, `validation_warnings` |
| **Trigger Pipeline** | `/pipeline/run` | POST | `{csv_path}` |
| **API Health** | `/health` | GET | 200 OK |
