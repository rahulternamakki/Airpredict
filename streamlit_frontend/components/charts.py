# streamlit_frontend/components/charts.py

import plotly.graph_objects as go
import plotly.express as px
from config_frontend import AQI_COLORS, REGIONS

def build_region_comparison_bar(predictions_data: dict,
                                  day_key: str = "day_1",
                                  title: str = "Day+1 AQI by Region") -> go.Figure:
    """
    Grouped bar chart comparing AQI values across all regions for a given day.
    """
    regions, aqi_vals, colors, categories = [], [], [], []
    for region, vals in predictions_data.get("regions", {}).items():
        cat = vals.get("category", ["Unknown"])[int(day_key[-1]) - 1]
        regions.append(region)
        aqi_vals.append(vals.get(day_key, 0))
        colors.append(AQI_COLORS.get(cat, "#888"))
        categories.append(cat)

    fig = go.Figure(go.Bar(
        x=regions, y=aqi_vals,
        marker_color=colors,
        text=[f"{v}<br>{c}" for v, c in zip(aqi_vals, categories)],
        textposition="outside",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Region", yaxis_title="AQI",
        yaxis=dict(range=[0, max(aqi_vals + [500]) * 1.15]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#333"),
        margin=dict(t=50, b=40),
        showlegend=False
    )
    return fig


def build_3day_trend_line(predictions_data: dict,
                           selected_regions: list = None) -> go.Figure:
    """
    Multi-line chart showing AQI trend across Day+1/2/3 for selected regions.
    """
    fig = go.Figure()
    days = ["Day+1", "Day+2", "Day+3"]
    for region, vals in predictions_data.get("regions", {}).items():
        if selected_regions and region not in selected_regions:
            continue
        aqi_series = [vals.get("day_1", 0), vals.get("day_2", 0), vals.get("day_3", 0)]
        fig.add_trace(go.Scatter(
            x=days, y=aqi_series,
            name=region, mode="lines+markers+text",
            text=aqi_series, textposition="top center"
        ))
    fig.update_layout(
        title="3-Day AQI Trend by Region",
        xaxis_title="Forecast Day", yaxis_title="AQI",
        yaxis=dict(range=[0, 520]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    return fig


def build_shap_waterfall(shap_entry: dict) -> go.Figure:
    """
    Builds a SHAP waterfall chart from a single shap_entry dict.
    shap_entry: {region, prediction_day, base_value, predicted_value, top_features:[...]}
    """
    base   = shap_entry.get("base_value", 0)
    feats  = shap_entry.get("top_features", [])
    labels = ["Base AQI"] + [f["feature"] for f in feats] + ["Predicted AQI"]
    values = [base] + [f["shap_value"] for f in feats] + [shap_entry.get("predicted_value", 0)]
    measure = ["absolute"] + ["relative"] * len(feats) + ["total"]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measure,
        x=labels, y=values,
        connector={"line": {"color": "rgb(63,63,63)"}},
        increasing={"marker": {"color": "#EF553B"}},
        decreasing={"marker": {"color": "#00CC96"}},
        totals={"marker":    {"color": "#AB63FA"}},
        text=[f"{v:+.1f}" if i not in (0, len(values)-1) else f"{v:.0f}"
              for i, v in enumerate(values)],
        textposition="outside"
    ))
    region = shap_entry.get("region", "")
    day    = shap_entry.get("prediction_day", "")
    fig.update_layout(
        title=f"SHAP Feature Impact — {region} Day+{day}",
        yaxis_title="AQI",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=60, b=60)
    )
    return fig


def build_counterfactual_bar(cf_entry: dict) -> go.Figure:
    """
    Horizontal bar chart showing original AQI vs each counterfactual scenario.
    """
    scenarios = cf_entry.get("scenarios", [])
    original  = cf_entry.get("original_day1_aqi", 0)
    orig_cat  = cf_entry.get("original_category", "")

    names  = ["Original"] + [s["name"] for s in scenarios]
    values = [original]   + [s["new_aqi"] for s in scenarios]
    cats   = [orig_cat]   + [s["new_category"] for s in scenarios]
    colors = [AQI_COLORS.get(c, "#888") for c in cats]

    fig = go.Figure(go.Bar(
        x=values, y=names,
        orientation="h",
        marker_color=colors,
        text=[f"{v} — {c}" for v, c in zip(values, cats)],
        textposition="inside",
    ))
    fig.update_layout(
        title=f"What-If Scenarios — {cf_entry.get('region', '')}",
        xaxis_title="AQI", xaxis=dict(range=[0, max(values) * 1.1]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=220, t=50)
    )
    return fig


def build_shap_feature_bar(shap_entry: dict) -> go.Figure:
    """
    Horizontal bar chart showing SHAP feature values (positive = red, negative = green).
    """
    feats   = shap_entry.get("top_features", [])
    feature_names = [f["feature"] for f in feats]
    shap_vals     = [f["shap_value"] for f in feats]
    bar_colors    = ["#EF553B" if v > 0 else "#00CC96" for v in shap_vals]

    fig = go.Figure(go.Bar(
        x=shap_vals, y=feature_names,
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v:+.2f}" for v in shap_vals],
        textposition="outside"
    ))
    fig.update_layout(
        title=f"SHAP Values — {shap_entry.get('region', '')} Day+{shap_entry.get('prediction_day', '')}",
        xaxis_title="SHAP Value (impact on AQI)",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=150, t=50)
    )
    return fig
