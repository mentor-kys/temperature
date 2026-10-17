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
# 연도 범위: 1907~2026 (고정)
# ───────────────────────────────────────────────────────────────
MIN_YEAR, MAX_YEAR = 1907, 2026

df["연도"] = df["날짜"].dt.year
yearly = df.groupby("연도")["평균기온(℃)"].mean().sort_index()

# 연도축 = 1907~2026 전체. 파일에 데이터가 없는 연도는 NaN(그래프 끊김)
yearly_full = yearly.reindex(list(range(MIN_YEAR, MAX_YEAR + 1)))

# 5년 이동평균 (중앙 기준, 결측 포함 윈도우는 NaN 유지)
ma5 = yearly_full.rolling(window=5, center=True, min_periods=5).mean()

# ───────────────────────────────────────────────────────────────
# 3. 사이드바: 연도 범위 슬라이더 (1907~2026)
# ───────────────────────────────────────────────────────────────
year_range = st.sidebar.slider(
    "연도 범위",
    min_value=MIN_YEAR,
    max_value=MAX_YEAR,
    value=(MIN_YEAR, MAX_YEAR),
    step=1,
)

start_y, end_y = int(year_range[0]), int(year_range[1])

# 선택 구간 일별 데이터 (통계 계산용)
daily_sel = df[(df["연도"] >= start_y) & (df["연도"] <= end_y)]

# ───────────────────────────────────────────────────────────────
# 4. 선택 구간 통계 (평균 / 최고 / 최저 / 관측일수)
# ───────────────────────────────────────────────────────────────
st.subheader("선택 구간 요약")
col_avg, col_max, col_min, col_n = st.columns(4)
col_avg.metric("평균기온", f"{daily_sel['평균기온(℃)'].mean():.2f} ℃")
col_max.metric("최고기온", f"{daily_sel['최고기온(℃)'].max():.2f} ℃")
col_min.metric("최저기온", f"{daily_sel['최저기온(℃)'].min():.2f} ℃")
col_n.metric("관측일수", f"{len(daily_sel):,}일")

# ───────────────────────────────────────────────────────────────
# 5. 그래프 (꺾은선 + 5년 이동평균)
# ───────────────────────────────────────────────────────────────
fig = go.Figure()

# 연도별 평균기온 (데이터 없는 연도는 선이 끊김)
fig.add_trace(
    go.Scatter(
        x=yearly_full.index,
        y=yearly_full.values,
        mode="lines+markers",
        name="연도별 평균기온",
        line=dict(color="#2E86AB", width=2),
        marker=dict(size=4),
    )
)

# 5년 이동평균 (같은 그래프에 겹침)
fig.add_trace(
    go.Scatter(
        x=ma5.index,
        y=ma5.values,
        mode="lines",
        name="5년 이동평균",
        line=dict(color="#F18F01", width=2, dash="dash"),
    )
)

# 선택 구간 강조
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
# x축 범위를 1907~2026으로 강제 (데이터 구간까지 자동 축소되지 않게 함)
fig.update_xaxes(range=[MIN_YEAR, MAX_YEAR], autorange=False)

st.plotly_chart(fig, use_container_width=True)
