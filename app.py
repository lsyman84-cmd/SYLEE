import io
import os
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.db_loader import load_equipment_db, load_equipment_db_from_bytes

GDRIVE_FILE_ID = "1XVYegsvT_LGKgLcpkINQqcVJDbUiGnCn"
GDRIVE_URL = f"https://docs.google.com/spreadsheets/d/{GDRIVE_FILE_ID}/export?format=xlsx"
from tools.equipment_comparator import compare_equipment
from tools.equipment_filter import filter_equipment
from tools.risk_analyzer import analyze_risk, format_risk_for_report
from tools.report_generator import generate_report

# ─── 페이지 설정 ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Mechanical Equipment Selection",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 컬럼 매핑 ───────────────────────────────────────────────────────────────

FILTER_COLS = {
    "equipment_category": "Category",
    "equipment_description": "Description",
    "project_type": "Project Type",
    "client": "Client",
    "built_year": "Built Year",
    "configuration": "Configuration",
    "capacity": "Capacity",
    "model_no": "Model No.",
    "dim_l_mm": "L (mm)",
    "dim_w_mm": "W (mm)",
    "dim_h_mm": "H (mm)",
    "weight_dry_kg": "Dry Wt (kg)",
    "weight_operating_kg": "Op. Wt (kg)",
    "design_pressure_barg": "Design P (barg)",
    "design_temperature_degC": "Design T (°C)",
    "vendor_name": "Vendor",
    "vendor_country": "Country",
}

COMPARE_COLS = {
    "equipment_description": "Description",
    "project_name": "Project",
    "capacity": "Capacity",
    "design_pressure_barg": "Design P (barg)",
    "design_temperature_degC": "Design T (°C)",
    "vendor_name": "Vendor",
    "vendor_country": "Country",
    "price_po_usd": "PO Price (USD)",
    "pressure_margin_score": "P-Margin ▲",
    "temperature_margin_score": "T-Margin ▲",
    "capacity_fit_score": "Cap. Fit ▲",
    "price_score": "Price ▲",
    "lead_time_score": "Lead Time ▲",
    "data_completeness_score": "Data ▲",
    "total_score": "TOTAL ★",
}

RISK_COLORS = {"HIGH": "#FF4444", "MEDIUM": "#FFA500", "LOW": "#44BB44"}

# ─── 유틸 ────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def cached_load_db() -> pd.DataFrame:
    resp = requests.get(GDRIVE_URL, timeout=60)
    resp.raise_for_status()
    return load_equipment_db_from_bytes(resp.content)


def score_bar(val: float) -> str:
    filled = round(val * 10)
    return "█" * filled + "░" * (10 - filled) + f"  {val:.2f}"


def render_risk_badge(level: str) -> str:
    color = RISK_COLORS.get(level, "#999")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:12px">{level}</span>'


def _df_display(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    cols = [c for c in col_map if c in df.columns]
    out = df[cols].copy()
    out.columns = [col_map[c] for c in cols]
    return out.reset_index(drop=True)


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    # 제목
    st.title("⚙️ Mechanical Equipment Selection System")
    st.caption("해양/플랜트 프로젝트 기계 장비 선정 자동화 도구 — FPSO · FSO · FPS · Fixed P/F")

    # ── 사이드바 ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("📂 데이터베이스")

        with st.spinner("DB 로딩 중..."):
            try:
                db = cached_load_db()
                st.success(f"✅ 장비 데이터: **{len(db):,}건** 로드 완료")
            except Exception as e:
                st.error(f"DB 로딩 실패: {e}")
                st.stop()

    # AI 키 .env에서 자동 감지
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    use_ai = bool(api_key)

    # ── 입력 패널 ─────────────────────────────────────────────────────────────
    st.header("🔍 검색 조건 입력")

    cats = sorted(db["equipment_category"].dropna().unique().tolist())
    proj_types = ["(전체)"] + sorted(db["project_type"].dropna().unique().tolist())

    col1, col2, col3 = st.columns([2, 2, 2])

    FLOW_UNITS = ["m³/hr", "m³/d", "BPD", "MMSCFD", "kg/hr", "t/hr", "L/min", "SCFM"]

    with col1:
        category = st.selectbox("장비 카테고리 *", cats)
        project_type = st.selectbox("프로젝트 타입", proj_types)

    with col2:
        design_pressure = st.number_input(
            "설계 압력 (barg) *", min_value=0.0, max_value=1000.0, value=10.0, step=0.5
        )
        design_temperature = st.number_input(
            "설계 온도 (°C) *", min_value=-50.0, max_value=600.0, value=65.0, step=5.0
        )

    with col3:
        flow_val_col, flow_unit_col = st.columns([2, 1])
        with flow_val_col:
            flow_rate_val = st.number_input(
                "요구 유량", min_value=0.0, value=0.0, step=10.0,
                help="0 입력 시 유량 조건 무시"
            )
        with flow_unit_col:
            flow_unit = st.selectbox("단위", FLOW_UNITS, label_visibility="visible")
        top_n = st.slider("비교 후보 수", min_value=5, max_value=30, value=10)

    st.divider()

    run_btn = st.button("🚀 분석 실행", type="primary", use_container_width=True)

    # ── 분석 실행 ─────────────────────────────────────────────────────────────
    if run_btn:
        conditions = {
            "equipment_category": category,
            "design_pressure": design_pressure,
            "design_temperature": design_temperature,
        }
        if flow_rate_val > 0:
            conditions["flow_rate"] = flow_rate_val
            conditions["flow_rate_display"] = f"{flow_rate_val:g} {flow_unit}"
        if project_type != "(전체)":
            conditions["project_type"] = project_type

        # 필터링
        with st.spinner("후보 장비 필터링 중..."):
            candidates, filter_log = filter_equipment(db, conditions)

        if candidates.empty:
            st.error("조건에 맞는 장비가 없습니다. 조건을 완화하거나 카테고리를 확인해 주세요.")
            _show_filter_log(filter_log)
            st.stop()

        # 비교
        with st.spinner(f"상위 {min(top_n, len(candidates))}건 비교 중..."):
            comparison_df, _ = compare_equipment(candidates.head(top_n * 2), conditions)
            top_comparison = comparison_df.head(top_n)

        # 리스크
        with st.spinner("리스크 분석 중..."):
            risk_df = analyze_risk(top_comparison.head(10), conditions)

        # AI
        ai_result = {}
        if use_ai:
            with st.spinner("AI 추천 생성 중 (30초 내외)..."):
                os.environ["ANTHROPIC_API_KEY"] = api_key
                from tools.ai_analyzer import analyze_and_recommend
                ai_context = {
                    "input_conditions": conditions,
                    "candidates": top_comparison.head(10).to_dict(orient="records"),
                    "risk_summary": risk_df[
                        ["equipment_description", "project_name",
                         "overall_risk", "high_count", "medium_count"]
                    ].to_dict(orient="records"),
                    "filter_log": filter_log,
                }
                ai_result = analyze_and_recommend(ai_context)

        # 보고서 생성 (다운로드용)
        with st.spinner("보고서 생성 중..."):
            report_paths = generate_report(
                conditions, candidates, top_comparison, risk_df, ai_result, filter_log
            )

        # 결과 저장
        st.session_state["results"] = {
            "conditions": conditions,
            "candidates": candidates,
            "comparison": top_comparison,
            "risk_df": risk_df,
            "ai_result": ai_result,
            "filter_log": filter_log,
            "report_paths": report_paths,
        }

    # ── 결과 표시 ─────────────────────────────────────────────────────────────
    if "results" not in st.session_state:
        st.info("조건을 입력하고 **분석 실행** 버튼을 눌러주세요.")
        return

    r = st.session_state["results"]
    candidates = r["candidates"]
    comparison = r["comparison"]
    risk_df = r["risk_df"]
    ai_result = r["ai_result"]
    filter_log = r["filter_log"]
    report_paths = r["report_paths"]

    # 메트릭 요약
    st.header("📊 분석 결과")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 후보 장비", f"{len(candidates):,}건")
    m2.metric("비교 대상", f"{len(comparison)}건")
    high_risk = (risk_df["overall_risk"] == "HIGH").sum() if not risk_df.empty else 0
    m3.metric("HIGH 리스크", f"{high_risk}건", delta=None)
    top_score = comparison["total_score"].iloc[0] if not comparison.empty else 0
    m4.metric("최고 점수", f"{top_score:.2f}")

    _show_filter_log(filter_log)

    # 탭
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 필터 결과", "📈 Top 10 비교", "🏆 Top 3 추천", "⚠️ 리스크 분석", "📥 다운로드"
    ])

    # ── Tab 1: 필터 결과 ────────────────────────────────────────────────────
    with tab1:
        st.subheader(f"후보 장비 전체 목록 ({len(candidates):,}건)")
        st.caption("정렬: DB 원본 순서. 컬럼 헤더 클릭 시 정렬 가능.")

        display_df = _df_display(candidates, FILTER_COLS)

        # 검색 필터
        search = st.text_input("🔎 테이블 내 검색 (설명, 벤더, 프로젝트명 등)", key="tab1_search")
        if search:
            mask = display_df.apply(
                lambda col: col.astype(str).str.contains(search, case=False, na=False)
            ).any(axis=1)
            display_df = display_df[mask]
            st.caption(f"검색 결과: {len(display_df)}건")

        st.dataframe(
            display_df,
            use_container_width=True,
            height=500,
            hide_index=True,
        )

    # ── Tab 2: Top 10 비교 ──────────────────────────────────────────────────
    with tab2:
        st.subheader(f"상위 {len(comparison)}건 다기준 비교")
        st.caption("▲ = 높을수록 좋음. TOTAL ★ = 가중 합산 점수 (0~1)")

        _render_compare_table(comparison, COMPARE_COLS)

        st.divider()
        st.subheader("평가 기준 가중치")
        wt_cols = st.columns(6)
        weights = {"압력 마진": 25, "온도 마진": 25, "용량 적합도": 20, "가격": 15, "납기": 10, "데이터 완전성": 5}
        for (label, pct), col in zip(weights.items(), wt_cols):
            col.metric(label, f"{pct}%")

    # ── Tab 3: Top 3 추천 ───────────────────────────────────────────────────
    with tab3:
        st.subheader("🏆 장비 추천 결과")

        if not ai_result:
            _show_score_based_top3(comparison)
        else:
            recs = ai_result.get("top_recommendations", [])
            if not recs:
                _show_score_based_top3(comparison)
            else:
                for rec in recs[:3]:
                    _render_recommendation_card(rec, comparison, risk_df)

            alt = ai_result.get("alternative_suggestions", "")
            if alt:
                with st.expander("💡 대안 / 설계 변경 제안"):
                    st.write(alt)

            review_pts = ai_result.get("human_review_points", [])
            if review_pts:
                st.divider()
                st.subheader("🔍 반드시 검토할 포인트")
                for pt in review_pts:
                    st.warning(f"• {pt}")

            note = ai_result.get("confidence_note", "")
            if note:
                st.caption(f"*AI 신뢰도 고지: {note}*")

    # ── Tab 4: 리스크 분석 ──────────────────────────────────────────────────
    with tab4:
        st.subheader("⚠️ 리스크 분석 결과")
        if risk_df.empty:
            st.info("리스크 데이터가 없습니다.")
        else:
            _render_risk_overview(risk_df)
            st.divider()
            st.subheader("상세 리스크 항목")
            flat_risk = format_risk_for_report(risk_df)
            _render_risk_detail(flat_risk)

    # ── Tab 5: 다운로드 ─────────────────────────────────────────────────────
    with tab5:
        st.subheader("📥 보고서 다운로드")
        st.write("분석 결과가 Excel(5시트) 및 PDF로 저장되었습니다.")

        dl1, dl2 = st.columns(2)

        excel_path = Path(report_paths.get("excel", ""))
        pdf_path = Path(report_paths.get("pdf", ""))

        with dl1:
            if excel_path.exists():
                with open(excel_path, "rb") as f:
                    st.download_button(
                        label="📊 Excel 리포트 다운로드",
                        data=f.read(),
                        file_name=excel_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                st.caption(f"시트: 핵심요약 · 후보비교 · 상세스펙 · 리스크분석 · Vendor비교")
            else:
                st.error("Excel 파일을 찾을 수 없습니다.")

        with dl2:
            if pdf_path.exists():
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📄 PDF 리포트 다운로드",
                        data=f.read(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        use_container_width=True,
                    )
                st.caption(f"내용: 핵심 요약 · 추천 장비 · 검토 포인트")
            else:
                st.error("PDF 파일을 찾을 수 없습니다.")

        st.divider()
        st.subheader("📋 현재 분석 조건")
        cond_df = pd.DataFrame(
            list(r["conditions"].items()), columns=["항목", "값"]
        )
        st.dataframe(cond_df, use_container_width=True, hide_index=True)

    # ── 하단 면책 문구 ───────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "⚠️ 본 결과는 1차 검토 보조 자료이며, 최종 판단은 담당 엔지니어가 수행해야 합니다."
    )


# ─── 보조 렌더링 함수 ────────────────────────────────────────────────────────

def _show_filter_log(filter_log: list):
    with st.expander("🔍 필터링 과정 상세", expanded=False):
        for entry in filter_log:
            step = entry.get("step", "")
            remaining = entry.get("remaining", "")
            dropped = entry.get("dropped", "")
            note = entry.get("note", "")
            if note:
                st.caption(f"[{step}] {note}")
            else:
                st.caption(f"[{step}] 남은 후보: **{remaining}건** (탈락: {dropped}건)")


def _render_compare_table(df: pd.DataFrame, col_map: dict):
    cols = [c for c in col_map if c in df.columns]
    disp = df[cols].copy()
    disp.columns = [col_map[c] for c in cols]

    score_col_names = [v for k, v in col_map.items() if k.endswith("_score")]

    def highlight_score(val):
        if not isinstance(val, (int, float)):
            return ""
        if val >= 0.7:
            return "background-color: #C6EFCE; color: #276221"
        if val >= 0.4:
            return "background-color: #FFEB9C; color: #9C5700"
        return "background-color: #FFC7CE; color: #9C0006"

    styled = disp.style.map(
        highlight_score,
        subset=[c for c in score_col_names if c in disp.columns],
    ).format(
        {c: "{:.3f}" for c in score_col_names if c in disp.columns},
        na_rep="—",
    )

    st.dataframe(styled, use_container_width=True, hide_index=True, height=420)


def _render_recommendation_card(rec: dict, comparison_df: pd.DataFrame, risk_df: pd.DataFrame):
    rank = rec.get("rank", "?")
    desc = rec.get("equipment_description", "N/A")
    project = rec.get("project_name", "N/A")
    reason = rec.get("reason", "")
    concerns = rec.get("concerns", "")

    # 해당 장비의 점수와 리스크 찾기
    score_row = comparison_df[
        comparison_df["equipment_description"].fillna("").str.contains(
            str(desc)[:30], regex=False
        )
    ]
    total_score = score_row["total_score"].iloc[0] if not score_row.empty else None

    risk_row = risk_df[
        risk_df["equipment_description"].fillna("").str.contains(
            str(desc)[:30], regex=False
        )
    ] if not risk_df.empty else pd.DataFrame()
    overall_risk = risk_row["overall_risk"].iloc[0] if not risk_row.empty else "N/A"

    rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "🔹")
    risk_color = RISK_COLORS.get(overall_risk, "#999")

    with st.container(border=True):
        h1, h2, h3 = st.columns([1, 5, 2])
        h1.markdown(f"### {rank_emoji} #{rank}")
        h2.markdown(f"**{desc}**  \n`{project}`")
        score_text = f"{total_score:.2f}" if total_score is not None else "N/A"
        h3.markdown(
            f"**점수:** {score_text}  \n"
            f"**리스크:** <span style='color:{risk_color};font-weight:bold'>{overall_risk}</span>",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**선정 이유**")
            st.write(reason)
        with c2:
            st.markdown("**검토 사항**")
            st.write(concerns if concerns else "—")


def _show_score_based_top3(comparison_df: pd.DataFrame):
    st.info("AI 추천 없음 — 점수 기반 상위 3개를 표시합니다.")
    for i, (_, row) in enumerate(comparison_df.head(3).iterrows(), 1):
        rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}[i]
        with st.container(border=True):
            st.markdown(
                f"### {rank_emoji} #{i} — {row.get('equipment_description', 'N/A')}  \n"
                f"`{row.get('project_name', 'N/A')}` · "
                f"설계압력 {row.get('design_pressure_barg', '—')} barg · "
                f"설계온도 {row.get('design_temperature_degC', '—')} °C · "
                f"Vendor: {row.get('vendor_name', '—')}  \n"
                f"**종합 점수: {row.get('total_score', 0):.3f}**"
            )


def _render_risk_overview(risk_df: pd.DataFrame):
    cols = st.columns(len(risk_df))
    for col, (_, row) in zip(cols, risk_df.iterrows()):
        level = row["overall_risk"]
        color = RISK_COLORS.get(level, "#999")
        col.markdown(
            f"<div style='border:2px solid {color};border-radius:8px;padding:10px;text-align:center'>"
            f"<b style='font-size:11px'>{str(row['equipment_description'])[:25]}</b><br>"
            f"<span style='color:{color};font-size:20px;font-weight:bold'>{level}</span><br>"
            f"<span style='font-size:11px'>HIGH:{row['high_count']} MED:{row['medium_count']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_risk_detail(flat_risk: pd.DataFrame):
    def color_level(val):
        color = RISK_COLORS.get(val, "#999")
        return f"background-color: {color}; color: white; font-weight: bold"

    if "등급" in flat_risk.columns:
        styled = flat_risk.style.map(color_level, subset=["등급"])
        st.dataframe(styled, use_container_width=True, hide_index=True, height=400)
    else:
        st.dataframe(flat_risk, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
