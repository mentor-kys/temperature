# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ───────────────────────────────────────────────────────────────
# 1. 데이터 로드
#    - utf-8-sig : 파일 선두의 BOM(BOM) 제거
#    - 날짜 앞 탭 문자 제거 : 원본 형식 문제("	1907-10-01") 보정
#    - 평균/최저/최고기온 수치 변환, 파싱 실패 행 제거
# ───────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path: str = "seoul_temperature.csv") -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")

    df["날짜"] = df["날짜"].str.strip()                      # 탭·공백 제거
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce") # 날짜 변환

    for col in ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["날짜"])                          # 날짜 이상 행 제거
    return df


df = load_data("seoul_temperature.csv")

# ───────────────────────────────────────────────────────────────
# 2. 연도별 평균기온 계산 (데이터 없는 연도는 NaN → 그래프 끊김)
# ───────────────────────────────────────────────────────────────
df["연도"] = df["날짜"].dt.year
yearly = df.groupby("연도")["평균기온(℃)"].mean().sort_index()

min_year, max_year = int(yearly.index.min()), int(yearly.index.max())

# 데이터에 없는 연도까지 전부 포함한 연도 인덱스를 만들고
# 데이터가 없는 연도는 NaN(결측)으로 채움
years = pd.Series(index=range(min_year, max_year + 1), dtype="float64")
yearly_full = yearly.reindex(years.index)

# 5년 이동평균 (중앙 기준). 결측(데이터 없는 연도) 포함 윈도우는 NaN 유지
ma5 = yearly_full.rolling(window=5, center=True, min_periods=5).mean()

# ───────────────────────────────────────────────────────────────
# 3. 사이드바: 연도 범위 슬라이더
# ───────────────────────────────────────────────────────────────
year_range = st.sidebar.slider(
    "연도 범위",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),
    step=1,
)

start_y, end_y = int(year_range[0]), int(year_range[1])

# 선택 구간 일별 데이터 (통계 계산용)
daily_sel = df[(df["연도"] >= start_y) & (df["연도"] <= end_y)]

# 선택 구간 연도별 평균 표
sel_yearly = yearly_full.loc[start_y:end_y]

# ───────────────────────────────────────────────────────────────
# 4. 선택 구간 통계 (평균 / 최고 / 최저 / 관측일수)
# ───────────────────────────────────────────────────────────────
st.subheader("선택 구간 요약")
col_avg, col_max, col_min, col_n = st.columns(4)
col_avg.metric("평균기온", f"{daily_sel['평균기온(℃)'].mean():.2f} ℃")
col_max.metric("최고기온", f"{daily_sel['최고기온(℃)'].max():.2f} ℃")
col_min.metric("최저기온", f"{daily_sel['최저기온(℃)'].min():.2f} ℃")
col_n.metric("관측일수", f"{len(daily_sel):,}일")

st.write("선택 구간 연도별 평균기온:")
st.dataframe(sel_yearly.to_frame("연평균기온"))

# ───────────────────────────────────────────────────────────────
# 5. 그래프 (Plotly)
# ───────────────────────────────────────────────────────────────
fig = go.Figure()

# 연도별 평균기온 (NaN 연도는 선이 끊김)
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

# 선택 구간 강조 (plotly 4.12 이상)
# data-frame 좌표가 아닌 범주형 축의 경우 문자열(연도명)을 x0/x1에 전달
fig.add_vrect(
    x0=str(start_y),
    x1=str(end_y),
    fillcolor="rgba(46, 134, 171, 0.08)",
    line_width=0,
    layer="below",
    annotation_text="선택 구간",
    annotation_position="top left",
)

fig.update_layout(
    title="서울 연평균기온 추이 및 5년 이동평균",
    xaxis_title="연도",
    yaxis_title="평균기온 (℃)",
    hovermode="x unified",
    height=560,
    legend=dict(x=0.02, y=0.98),
)
# 범주형 축으로 설정 → 데이터 없는 연도는 마커·선이 끊겨 표기됨
fig.update_xaxes(type="category")

st.plotly_chart(fig, use_container_width=True)
