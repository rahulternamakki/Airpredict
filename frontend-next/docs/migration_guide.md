# Streamlit to Next.js Migration Guide

This guide provides strategic recommendations for migrating the `streamlit_frontend` features to a Next.js (App Router) environment using Tailwind CSS and Shacdn UI.

## 1. Page Structuring
Streamlit's flat `pages/` directory should be mapped to the Next.js App Router:

| Streamlit Page | Next.js Route | Recommended Layout |
| :--- | :--- | :--- |
| `streamlit_frontend.py` | `/dashboard` | Main Grid layout with summary cards on top |
| `02_model_insights.py` | `/insights` | Region selection in a sticky header or sidebar |
| `03_whatif.py` | `/simulations` | Interactive sliders (if updating to real-time) or cards |
| `04_ai_explanation.py` | `/science` | Clean typography-focused reading layout |
| `05_ai_agents.py` | `/assistant` | Full-height chat interface |

## 2. Component Mapping

| Streamlit Component | Next.js / Shadcn Equivalent | Recommended Lib |
| :--- | :--- | :--- |
| `st.metric` | `Card` with `Stat` display | Shadcn Card |
| `st.plotly_chart` | Interactive React charts | `Recharts` or `Plotly.js` |
| `st.selectbox` / `radio` | `Select` or `Tabs` / `RadioGroup` | Shadcn UI |
| `st.expander` | `Accordion` | Shadcn UI |
| `st.chat_input` | `Textarea` with submit icon | Radix UI / Shadcn |
| `st.dataframe` | `TanStack Table` (Data Table) | Shadcn Data Table |

## 3. State Management
- **Chat History**: Use `Zustand` or React `Context` to persist agent conversations across route changes.
- **Global Config**: Store `selectedRegion` and `forecastDay` in a global store or URL search params for bookmarkable states.
- **Data Fetching**: Use `React Query` (TanStack Query) for handling API calls, caching, and loading states (replacing Streamlit's implicit re-runs).

## 4. Visual Identity Implementation
- **Theming**: Implement the AQI category colors in `tailwind.config.ts` as custom utility classes (e.g., `bg-aqi-poor`).
- **Dark Mode**: Next.js makes dark mode easy via `next-themes`. Ensure charts are configured to switch color scales accordingly.
- **Staleness Banner**: A sticky or floating `Toast` or `Alert` component at the top of the dashboard.

## 5. Critical Logic Migration
- **AQI Calculation**: Move the `get_aqi_category` logic to a shared utility file (`utils/aqi.ts`) to be used both in UI coloring and table displays.
- **API Client**: Create a centralized `lib/api.ts` using `fetch` or `axios` that mirrors the structure of `api_client.py`.
