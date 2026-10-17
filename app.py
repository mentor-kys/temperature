# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ───────────────────────────────────────────────────────────────
# 1. 데이터 로드
# ───────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path: str = "seoul_temperature.csv") -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["날짜"] = df["날짜"].str.strip()
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")

    for col in ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["날짜"])
    return df

df = load_data("seoul_temperature.csv")

# ───────────────────────────────────────────────────────────────
# 제외 구간: 1950-09-01 ~ 1953-11-30
# 이 구간의 데이터는 차트/통계에서 모두 제외하고, 구간 사이를 잇지 않음
# ───────────────────────────────────────────────────────────────
exclude_start = "1950-09-01"
exclude_end = "1953-11-30"
df = df[(df["날짜"] < exclude_start) | (df["날짜"] > exclude_end)].copy()

# ───────────────────────────────────────────────────────────────
# 연도 범위: 1907~2026 (고정)
# ───────────────────────────────────────────────────────────────
MIN_YEAR, MAX_YEAR = 1907, 2026

df["연도"] = df["날짜"].dt.year
yearly = df.groupby("연도")["평균기온(℃)"].mean().sort_index()

# 데이터에 없는(결측치가 있는) 연도는 그래프에서 제외
yearly_valid = yearly.dropna()

# 연도축 = 1907~2026 (결측 연도가 있으면 NaN → 그래프에서 끊김)
yearly_plot = yearly_valid.reindex(list(range(MIN_YEAR, MAX_YEAR + 1)))

# 5년 이동평균 (데이터 있는 연도 기준으로 계산)
ma5 = yearly_plot.rolling(window=5, center=True, min_periods=5).mean()

# ───────────────────────────────────────────────────────────────
# 사이드바: 연도 범위 슬라이더 (통계 구간 선택)
# ───────────────────────────────────────────────────────────────
year_range = st.sidebar.slider(
    "연도 범위",
    min_value=MIN_YEAR,
    max_value=MAX_YEAR,
    value=(MIN_YEAR, MAX_YEAR),
    step=1,
)

start_y, end_y = int(year_range[0]), int(year_range[1])

# 선택 구간 일별 데이터 (통계 계산용, 제외 구간 제외)
daily_sel = df[(df["연도"] >= start_y) & (df["연도"] <= end_y)]

# ───────────────────────────────────────────────────────────────
# 선택 구간 통계
# ───────────────────────────────────────────────────────────────
st.subheader("선택 구간 요약")
if len(daily_sel) > 0:
    col_avg, col_max, col_min, col_n = st.columns(4)
    col_avg.metric("평균기온", f"{daily_sel['평균기온(℃)'].mean():.2f} ℃")
    col_max.metric("최고기온", f"{daily_sel['최고기온(℃)'].max():.2f} ℃")
    col_min.metric("최저기온", f"{daily_sel['최저기온(℃)'].min():.2f} ℃")
    col_n.metric("관측일수", f"{len(daily_sel):,}일")
else:
    st.warning("선택 구간이 제외 구간(1950-09-01 ~ 1953-11-30)과 겹쳐 데이터가 없습니다.")

# ───────────────────────────────────────────────────────────────
# 탭 전환: 선 / 막대 / 히트맵 / 산점도 / 상관계수 히트맵
# ───────────────────────────────────────────────────────────────
tab_line, tab_bar, tab_heat, tab_scatter, tab_corr = st.tabs(
    ["선 그래프", "막대 그래프", "히트맵(월평균)", "산점도", "상관계수 히트맵"]
)

# ── 1) 선 그래프 ────────────────────────────────────────────────
with tab_line:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=yearly_plot.index,
            y=yearly_plot.values,
            mode="lines+markers",
            name="연도별 평균기온",
            line=dict(color="#2E86AB", width=2),
            marker=dict(size=4),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ma5.index,
            y=ma5.values,
            mode="lines",
            name="5년 이동평균",
            line=dict(color="#F18F01", width=2, dash="dash"),
        )
    )
    fig.add_vrect(
        x0=start_y,
        x1=end_y,
        fillcolor="rgba(46, 134, 171, 0.08)",
        line_width=0,
        layer="below",
    )
    fig.update_layout(
        title="서울 연평균기온 추이 및 5년 이동평균",
        xaxis_title="연도",
        yaxis_title="평균기온 (℃)",
        hovermode="x unified",
        height=560,
        legend=dict(x=0.02, y=0.98),
    )
    fig.update_xaxes(range=[MIN_YEAR, MAX_YEAR], autorange=False)
    st.plotly_chart(fig, use_container_width=True)

# ── 2) 막대 그래프 ──────────────────────────────────────────────
with tab_bar:
    bar_df = yearly_plot.loc[start_y:end_y]
    fig = go.Figure(
        go.Bar(
            x=bar_df.index.astype(int),
            y=bar_df.values,
            name="연평균기온",
            marker_color="#2E86AB",
        )
    )
    fig.update_layout(
        title="연도별 평균기온 막대 그래프",
        xaxis_title="연도",
        yaxis_title="평균기온 (℃)",
        height=520,
    )
    fig.update_xaxes(range=[MIN_YEAR, MAX_YEAR], autorange=False)
    st.plotly_chart(fig, use_container_width=True)

# ── 3) 히트맵(월평균) ───────────────────────────────────────────
with tab_heat:
    heat_df = df.copy()
    heat_df["월"] = heat_df["날짜"].dt.month
    monthly_avg = heat_df.groupby(["연도", "월"])["평균기온(℃)"].mean().unstack()
    monthly_avg = monthly_avg.reindex(columns=range(1, 13))
    fig = go.Figure(
        go.Heatmap(
            z=monthly_avg.values.astype(float),
            x=list(range(1, 13)),
            y=list(range(MIN_YEAR, MAX_YEAR + 1)),
            colorscale="RdYlBu_r",
            colorbar=dict(title="평균기온 (℃)"),
        )
    )
    fig.update_layout(
        title="연도별 월평균기온 히트맵",
        xaxis_title="월",
        yaxis_title="연도",
        height=640,
    )
    fig.update_yaxes(range=[MIN_YEAR, MAX_YEAR + 1], autorange=False)
    st.plotly_chart(fig, use_container_width=True)

# ── 4) 산점도 ───────────────────────────────────────────────────
with tab_scatter:
    sc = df.copy()
    x = sc["평균기온(℃)"].values.astype(float)
    y = sc["최고기온(℃)"].values.astype(float)

    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker=dict(size=3, color="#2E86AB", opacity=0.5),
            name="일별 관측값",
        )
    )

    # 추세선 (선택 구간 기준)
    n = len(x)
    if n >= 2:
        mx = sum(x) / n
        my = sum(y) / n
        sxx = sum((xi - mx) ** 2 for xi in x)
        sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        if sxx != 0:
            slope = sxy / sxx
            intercept = my - slope * mx
            x_min, x_max = min(x), max(x)
            fig.add_trace(
                go.Scatter(
                    x=[x_min, x_max],
                    y=[slope * x_min + intercept, slope * x_max + intercept],
                    mode="lines",
                    name="추세선",
                    line=dict(color="#F18F01", width=2, dash="dash"),
                )
            )

    fig.update_layout(
        title="평균기온 vs 최고기온 산점도 (전체 기간)",
        xaxis_title="평균기온 (℃)",
        yaxis_title="최고기온 (℃)",
        height=560,
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── 5) 상관계수 히트맵 ──────────────────────────────────────────
with tab_corr:
    corr_cols = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]
    corr = df[corr_cols].corr()
    fig = go.Figure(
        go.Heatmap(
            z=corr.values,
            x=list(corr.columns),
            y=list(corr.index),
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=corr.values.round(2),
            texttemplate="%{text}",
            textfont={"size": 16},
            colorbar=dict(title="상관계수"),
        )
    )
    fig.update_layout(
        title="기온 변수 간 상관계수 히트맵",
        xaxis_title="변수",
        yaxis_title="변수",
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)
