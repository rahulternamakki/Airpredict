import axios from 'axios';

// --- Interfaces ---

export interface RegionSummary {
  region: string;
  day_1_aqi: number;
  day_1_category: string;
}

export interface PredictionSummaryResponse {
  prediction_date_start: string;
  generated_at: string;
  regions: RegionSummary[];
}

export interface RegionForecast {
  day_1: number;
  day_2: number;
  day_3: number;
  category: string[];
}

export interface FullForecastResponse {
  prediction_date_start: string;
  generated_at: string;
  regions: Record<string, RegionForecast>;
}

export interface FullExplanationResponse {
  prediction_explanation: string;
  shap_interpretation: string;
  counterfactual_analysis: string;
  health_impact_summary: string;
  recommended_intervention: string;
}

export interface ExplanationSectionResponse {
  section: string;
  content: string;
}

export interface ShapFeature {
  feature: string;
  shap_value: number;
  actual_value: number;
}

export interface RegionShap {
  region: string;
  prediction_day: number;
  base_value: number;
  predicted_value: number;
  top_features: ShapFeature[];
}

export interface CounterfactualScenario {
  name: string;
  type: string;
  feature_changes: Record<string, number>;
  new_aqi: number;
  new_category: string;
  aqi_reduction: number;
  percent_improvement: string;
}

export interface RegionalCounterfactual {
  region: string;
  original_day1_aqi: number;
  original_category: string;
  method: string;
  scenarios: CounterfactualScenario[];
}

export interface ChatPayload {
  message: string;
  agent_type: string;
  history: any[];
}

export interface ChatResponse {
  response: string;
  agent_type: string;
  suggested_questions: string[];
}

export interface PipelineStatus {
  date: string;
  pipeline_ran_at: string;
  gemini_attempts: number;
  validation_warnings: string[];
}

// --- API Client ---

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getPredictionsSummary = () => api.get<PredictionSummaryResponse>('/predictions/summary');
export const getFullForecast = () => api.get<FullForecastResponse>('/predictions');
export const getRegionalDetail = (region: string) => api.get<RegionForecast>(`/predictions/${encodeURIComponent(region)}`);
export const getShapData = () => api.get<RegionShap[]>('/shap');
export const getRegionalShap = (region: string) => api.get<RegionShap[]>(`/shap/${encodeURIComponent(region)}`);
export const getSingleInsight = (region: string, day: number) => api.get<RegionShap>(`/shap/${encodeURIComponent(region)}/day/${day}`);
export const getCounterfactuals = () => api.get<RegionalCounterfactual[]>('/counterfactual');
export const getRegionalScenarios = (region: string) => api.get<RegionalCounterfactual[]>(`/counterfactual/${encodeURIComponent(region)}`);
export const getFullExplanation = () => api.get<FullExplanationResponse>('/explanation');
export const getExplanationSection = (section: string) => api.get<ExplanationSectionResponse>(`/explanation/${section}`);
export const chatWithAgent = (payload: ChatPayload) => api.post<ChatResponse>('/agent/chat', payload);
export const getAgentSuggestions = (type: string) => api.get<string[]>(`/agent/questions/${type}`);
export const getPipelineStatus = () => api.get<PipelineStatus>('/pipeline/status');
export const triggerPipeline = (csvPath: string) => api.post('/pipeline/run', { csv_path: csvPath });
export const checkHealth = () => api.get('/health');

export default api;
