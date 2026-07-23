"""
modules/visualization.py
Semua fungsi visualisasi menggunakan Plotly untuk Streamlit.
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ── Palet warna konsisten ──────────────────────────────────────
COLORS = {
    "primary":   "#1a4a7a",
    "secondary": "#2980b9",
    "accent":    "#f39c12",
    "success":   "#27ae60",
    "danger":    "#e74c3c",
    "warning":   "#e67e22",
    "neutral":   "#7f8c8d",
    "light":     "#ecf0f1",
}

QUADRANT_COLORS = {
    "Benchmark Port":  "#27ae60",
    "Efficient Port":  "#2980b9",
    "Developing Port": "#f39c12",
    "Congested Port":  "#e74c3c",
    "Unknown":         "#95a5a6",
}

PLOTLY_TEMPLATE = "plotly_white"


def _base_layout(fig: go.Figure, title: str = "", height: int = 400) -> go.Figure:
    """Terapkan layout standar ke figure."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text=title, font=dict(size=15, color=COLORS["primary"]), x=0),
        height=height,
        margin=dict(l=40, r=20, t=50, b=40),
        font=dict(family="Inter, sans-serif", size=12),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


# ══════════════════════════════════════════════════════════════
# TRAFFIC CHARTS
# ══════════════════════════════════════════════════════════════

def plot_volume_donut(df_volume: pd.DataFrame) -> go.Figure:
    """
    Donut chart top 10 pelabuhan berdasarkan volume PKK + 'Lainnya'.
    """
    if df_volume.empty:
        return go.Figure()

    top10  = df_volume.head(10).copy()
    others = df_volume.iloc[10:]

    if not others.empty:
        other_row = pd.DataFrame([{
            "port": "Lainnya",
            "port_code": "",
            "volume": others["volume"].sum(),
            "share_pct": round(others["share_pct"].sum(), 2),
        }])
        pie_df = pd.concat([top10, other_row], ignore_index=True)
    else:
        pie_df = top10

    fig = go.Figure(go.Pie(
        labels=pie_df["port"],
        values=pie_df["volume"],
        hole=0.5,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Volume: %{value:,}<br>Share: %{percent}<extra></extra>",
        marker=dict(colors=px.colors.qualitative.Set3),
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text="Top 10 Pelabuhan — Share Volume PKK", font=dict(size=15, color=COLORS["primary"]), x=0),
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="Inter, sans-serif"),
        showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.5),
    )
    return fig


def plot_trend_quarterly(df: pd.DataFrame) -> go.Figure:
    """Bar chart tren volume per kuartal."""
    if df.empty:
        return go.Figure()

    bar_colors = [COLORS["primary"], COLORS["accent"], COLORS["danger"], COLORS["success"]]
    colors_list = [bar_colors[i % len(bar_colors)] for i in range(len(df))]

    fig = go.Figure(go.Bar(
        x=df["quarter"].astype(str),
        y=df["total_service"],
        marker_color=colors_list,
        text=df["total_service"].apply(lambda x: f"{x:,}"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Total: %{y:,}<extra></extra>",
    ))
    _base_layout(fig, "Tren Volume PKK per Kuartal 2025", height=380)
    fig.update_xaxes(title="Kuartal")
    fig.update_yaxes(title="Total Layanan")
    return fig


def plot_trend_monthly(df: pd.DataFrame) -> go.Figure:
    """Bar chart tren volume per bulan."""
    if df.empty:
        return go.Figure()

    max_val = df["total_service"].max()
    colors_list = [
        COLORS["danger"] if v >= df["total_service"].nlargest(3).min() else COLORS["secondary"]
        for v in df["total_service"]
    ]

    fig = go.Figure(go.Bar(
        x=df["month_name"] if "month_name" in df.columns else df["month"].astype(str),
        y=df["total_service"],
        marker_color=colors_list,
        text=df["total_service"].apply(lambda x: f"{x:,}"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Total: %{y:,}<extra></extra>",
    ))
    _base_layout(fig, "Tren Volume PKK per Bulan 2025", height=380)
    fig.update_xaxes(title="Bulan")
    fig.update_yaxes(title="Total Layanan", range=[0, max_val * 1.15])
    return fig


def plot_trend_daily(df: pd.DataFrame) -> go.Figure:
    """Bar chart tren volume per hari dalam seminggu."""
    if df.empty:
        return go.Figure()

    max_val = df["total_service"].max()
    colors_list = [
        COLORS["danger"] if v == max_val else COLORS["secondary"]
        for v in df["total_service"]
    ]

    fig = go.Figure(go.Bar(
        x=df["day"].astype(str),
        y=df["total_service"],
        marker_color=colors_list,
        text=df["total_service"].apply(lambda x: f"{int(x):,}"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Total: %{y:,}<extra></extra>",
    ))
    _base_layout(fig, "Tren Volume PKK per Hari", height=380)
    fig.update_xaxes(title="Hari")
    fig.update_yaxes(title="Total Layanan", range=[0, max_val * 1.12])
    return fig


def plot_trend_hourly(df: pd.DataFrame) -> go.Figure:
    """Bar chart tren volume per jam (jam kerja dihighlight)."""
    if df.empty:
        return go.Figure()

    max_val = df["total_service"].max()
    colors_list = [
        COLORS["accent"] if 8 <= h <= 17 else COLORS["secondary"]
        for h in df["hour"]
    ]

    fig = go.Figure(go.Bar(
        x=df["hour"].astype(int).astype(str).str.zfill(2) + ":00",
        y=df["total_service"],
        marker_color=colors_list,
        hovertemplate="<b>Jam %{x}</b><br>Total: %{y:,}<extra></extra>",
    ))
    _base_layout(fig, "Tren Volume PKK per Jam (Jam Kerja = Kuning)", height=380)
    fig.update_xaxes(title="Jam (Format 24h)")
    fig.update_yaxes(title="Total Layanan")
    return fig


# ══════════════════════════════════════════════════════════════
# SERVICE PERFORMANCE CHARTS
# ══════════════════════════════════════════════════════════════

def plot_service_distribution(df_dist: pd.DataFrame) -> go.Figure:
    """Donut chart distribusi kategori waktu persetujuan."""
    if df_dist.empty:
        return go.Figure()

    sla_colors = {
        "< 30 mnt":  "#27ae60",
        "30-60 mnt": "#2ecc71",
        "1-2 jam":   "#f39c12",
        "2-6 jam":   "#e67e22",
        "6-12 jam":  "#e74c3c",
        "12-24 jam": "#c0392b",
        "> 24 jam":  "#8e0000",
    }
    colors_list = [sla_colors.get(c, "#95a5a6") for c in df_dist["category"]]

    fig = go.Figure(go.Pie(
        labels=df_dist["category"],
        values=df_dist["total"],
        hole=0.5,
        marker=dict(colors=colors_list),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Total: %{value:,}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text="Distribusi Waktu Persetujuan PKK", font=dict(size=15, color=COLORS["primary"]), x=0),
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="Inter, sans-serif"),
        annotations=[dict(text="Kategori<br>Waktu", x=0.5, y=0.5, showarrow=False, font_size=12)],
    )
    return fig


def plot_approval_histogram(df: pd.DataFrame) -> go.Figure:
    """Histogram distribusi waktu persetujuan (< P95)."""
    if df.empty or "approval_minutes" not in df.columns:
        return go.Figure()

    data = df["approval_minutes"].dropna()
    p95  = data.quantile(0.95)
    data_p95 = data[data < p95]

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=data_p95,
        nbinsx=80,
        marker_color=COLORS["secondary"],
        marker_line=dict(color="white", width=0.3),
        name="Frekuensi",
        hovertemplate="Interval: %{x:.1f} mnt<br>Count: %{y:,}<extra></extra>",
    ))
    fig.add_vline(x=data_p95.mean(),   line_dash="dash", line_color=COLORS["danger"],
                  annotation_text=f"Mean={data_p95.mean():.1f}", annotation_position="top right")
    fig.add_vline(x=data_p95.median(), line_dash="solid", line_color=COLORS["accent"],
                  annotation_text=f"Median={data_p95.median():.1f}", annotation_position="top left")

    _base_layout(fig, "Distribusi Waktu Persetujuan PKK (< Persentil 95)", height=380)
    fig.update_xaxes(title="Waktu Persetujuan (menit)")
    fig.update_yaxes(title="Frekuensi")
    return fig


def plot_top_longest_approval(df_top: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart pelabuhan dengan waktu persetujuan terlama."""
    if df_top.empty:
        return go.Figure()

    df_sorted = df_top.sort_values("mean_minutes", ascending=True)

    fig = go.Figure(go.Bar(
        x=df_sorted["mean_minutes"],
        y=df_sorted["port"],
        orientation="h",
        marker_color=COLORS["danger"],
        text=df_sorted["mean_minutes"].apply(lambda x: f"{x:.1f} mnt"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Rata-rata: %{x:.1f} menit<extra></extra>",
    ))
    _base_layout(fig, "Top 10 — Pelabuhan dengan Waktu Persetujuan Terlama", height=400)
    fig.update_xaxes(title="Rata-rata Waktu Persetujuan (menit)")
    fig.update_yaxes(title="")
    return fig


def plot_sla_compliance_bar(df_sla: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """Horizontal bar chart SLA compliance rate per pelabuhan."""
    if df_sla.empty:
        return go.Figure()

    # Tampilkan worst performers dulu
    df_sorted = df_sla.sort_values("compliance_rate", ascending=True).head(top_n)
    colors_list = [
        COLORS["success"] if v >= 80 else COLORS["warning"] if v >= 50 else COLORS["danger"]
        for v in df_sorted["compliance_rate"]
    ]

    fig = go.Figure(go.Bar(
        x=df_sorted["compliance_rate"],
        y=df_sorted["port"],
        orientation="h",
        marker_color=colors_list,
        text=df_sorted["compliance_rate"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>SLA Compliance: %{x:.1f}%<extra></extra>",
    ))
    fig.add_vline(x=80, line_dash="dash", line_color=COLORS["success"],
                  annotation_text="Target 80%", annotation_position="top right")
    _base_layout(fig, f"SLA Compliance per Pelabuhan (Bottom {top_n})", height=max(400, top_n * 22))
    fig.update_xaxes(title="SLA Compliance Rate (%)", range=[0, 110])
    fig.update_yaxes(title="")
    return fig


def plot_sla_trend(df_trend: pd.DataFrame) -> go.Figure:
    """Line chart tren SLA compliance per bulan."""
    if df_trend.empty:
        return go.Figure()

    x_labels = df_trend["month_name"] if "month_name" in df_trend.columns else df_trend["month"].astype(str)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_labels,
        y=df_trend["compliance_rate"],
        mode="lines+markers",
        name="SLA Compliance",
        line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(size=8, color=COLORS["primary"]),
        hovertemplate="<b>%{x}</b><br>Compliance: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=80, line_dash="dash", line_color=COLORS["success"],
                  annotation_text="Target 80%", annotation_position="top right")
    _base_layout(fig, "Tren SLA Compliance per Bulan 2025", height=380)
    fig.update_xaxes(title="Bulan")
    fig.update_yaxes(title="SLA Compliance Rate (%)", range=[0, 105])
    return fig


# ══════════════════════════════════════════════════════════════
# PORT CLASSIFICATION CHARTS
# ══════════════════════════════════════════════════════════════

def plot_quadrant_scatter(df: pd.DataFrame) -> go.Figure:
    """
    Scatter plot kuadran interaktif (volume log × composite index).
    Setiap titik menampilkan nama pelabuhan saat hover.
    """
    if df.empty or "quadrant" not in df.columns:
        return go.Figure()

    fig = go.Figure()

    for quadrant, color in QUADRANT_COLORS.items():
        subset = df[df["quadrant"] == quadrant]
        if subset.empty:
            continue
        fig.add_trace(go.Scatter(
            x=subset["volume_log"],
            y=subset["composite_index"],
            mode="markers",
            name=quadrant,
            marker=dict(size=9, color=color, opacity=0.82, line=dict(width=0.7, color="white")),
            text=subset["port"],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Volume: %{customdata[0]:,}<br>"
                "Composite Index: %{y:.3f}<br>"
                "Kuadran: " + quadrant + "<extra></extra>"
            ),
            customdata=subset[["volume"]].values,
        ))

    # Garis threshold (median)
    med_vol_log  = np.log10(df["volume"].median())
    med_index    = df["composite_index"].median()

    fig.add_vline(x=med_vol_log, line_dash="dash", line_color="#2c3e50", line_width=1.5,
                  annotation_text=f"Median Volume ({int(df['volume'].median()):,})",
                  annotation_position="top left", annotation_font_size=10)
    fig.add_hline(y=med_index, line_dash="dash", line_color="#2c3e50", line_width=1.5,
                  annotation_text=f"Median Index ({med_index:.2f})",
                  annotation_position="bottom right", annotation_font_size=10)

    # Label kuadran
    xmin, xmax = df["volume_log"].min() - 0.2, df["volume_log"].max() + 0.2
    ymin, ymax = df["composite_index"].min() - 0.05, df["composite_index"].max() + 0.05

    label_positions = [
        ((med_vol_log + xmax) / 2, (med_index + ymax) / 2, "Benchmark Port"),
        ((xmin + med_vol_log) / 2, (med_index + ymax) / 2, "Efficient Port"),
        ((xmin + med_vol_log) / 2, (ymin + med_index) / 2, "Developing Port"),
        ((med_vol_log + xmax) / 2, (ymin + med_index) / 2, "Congested Port"),
    ]
    for lx, ly, label in label_positions:
        fig.add_annotation(
            x=lx, y=ly, text=f"<b>{label}</b>",
            showarrow=False, font=dict(size=12, color=QUADRANT_COLORS.get(label, "#333")),
            opacity=0.4,
        )

    _base_layout(fig, "Analisis Kuadran Performa Pelabuhan", height=540)
    fig.update_xaxes(
        title="Volume PKK (skala log)",
        tickvals=[0, 1, 2, 3, 4, 5],
        ticktext=["1", "10", "100", "1K", "10K", "100K"],
    )
    fig.update_yaxes(title="Composite Performance Index (0–1)")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1))
    return fig


def plot_performance_ranking(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """Horizontal bar chart ranking composite index."""
    if df.empty:
        return go.Figure()

    df_top = df.head(top_n).sort_values("composite_index", ascending=True)
    colors_list = [QUADRANT_COLORS.get(q, COLORS["neutral"]) for q in df_top["quadrant"]]

    fig = go.Figure(go.Bar(
        x=df_top["composite_index"],
        y=df_top["port"],
        orientation="h",
        marker_color=colors_list,
        text=df_top["composite_index"].apply(lambda x: f"{x:.3f}"),
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Composite Index: %{x:.3f}<br>"
            "Volume: %{customdata:,}<extra></extra>"
        ),
        customdata=df_top["volume"],
    ))
    _base_layout(fig, f"Ranking Top {top_n} — Composite Performance Index", height=max(420, top_n * 22))
    fig.update_xaxes(title="Composite Index (0–1)", range=[0, 1.1])
    fig.update_yaxes(title="")
    return fig
