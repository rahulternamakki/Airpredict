# Design System & UI Patterns

This document captures the visual identity and reusable UI patterns currently used in the Streamlit frontend.

## Visual Identity

### Color Palette (AQI Categories)
The application uses a standard color coding for AQI levels:
- **Good (0-50)**: Green (`#00E400`)
- **Satisfactory (51-100)**: Light Green (`#92D050`)
- **Moderate (101-200)**: Yellow (`#FFFF00`)
- **Poor (201-300)**: Orange (`#FF7E00`)
- **Very Poor (301-400)**: Red (`#FF0000`)
- **Severe (401-500)**: Maroon (`#7E0023`)

### Agent Themes
- **Vayu (Public)**: Greenish theme (`BG: #E8F5E9`, `Border: #2E7D32`)
- **DELPHI (Policy)**: Blueish theme (`BG: #E3F2FD`, `Border: #1565C0`)

## UI Components & Patterns

### 1. Indicators & Banners
- **Staleness Banner**: A custom component used at the top of pages to indicate data freshness. It uses `st.warning` or `st.info` with specific metadata like `pipeline_ran_at`.
- **AQI Cards**: Compact widgets containing:
    - Region Name
    - AQI Value (Large font)
    - Category Label (Color-coded background)

### 2. Layout Structure
- **Sidebar Navigation**: Used for primary page switching.
- **Wide Layout**: All pages are configured with `layout="wide"` to maximize screen real estate for charts.
- **Dividers & Subheaders**: Heavy use of `st.divider()` and `st.subheader()` to segment content.
- **Expanders**: Used for "secondary" or "deep-dive" information (e.g., detailed feature tables or cross-region summaries).

### 3. Charting Styles (Plotly)
- **Grouped Bars**: Used for region comparisons.
- **Multi-line Trends**: Used for time-series forecasts.
- **Waterfall Charts**: Specifically for SHAP analysis.
- **Horizontal Bar Charts**: Used for relative comparisons (What-If scenarios).
- **Styling**: Most charts use `paper_bgcolor="rgba(0,0,0,0)"` to blend into the application background.

### 4. Chat Interface
- Uses `st.chat_message` for a standard message flow.
- Includes "Question Chips": Horizontal buttons for suggested queries (quick interaction).
- Persists history in `st.session_state`.
