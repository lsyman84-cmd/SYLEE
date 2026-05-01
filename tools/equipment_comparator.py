import re
import numpy as np
import pandas as pd

# 평가 가중치 (합계 = 1.0)
WEIGHTS = {
    "pressure_margin": 0.25,
    "temperature_margin": 0.25,
    "capacity_fit": 0.20,
    "price": 0.15,
    "lead_time": 0.10,
    "data_completeness": 0.05,
}

# 성능 점수 산정 기준 컬럼
_KEY_FIELDS = [
    "design_pressure_barg", "design_temperature_degC",
    "capacity", "price_po_usd", "lead_time_po_weeks",
]


def compare_equipment(df: pd.DataFrame, conditions: dict) -> tuple[pd.DataFrame, list]:
    """
    후보 장비 간 다기준 비교 및 점수 산정.

    반환:
        comparison_df: 항목별 점수 + 총점 포함 DataFrame (내림차순 정렬)
        ranking: 장비 설명 순위 list
    """
    if df.empty:
        return pd.DataFrame(), []

    scores = pd.DataFrame(index=df.index)

    # 1. 압력 마진 점수 (운전 압력 대비 설계 압력 여유)
    op_p = conditions.get("design_pressure")
    if op_p and op_p > 0:
        margin = (df["design_pressure_barg"] - op_p) / op_p
        scores["pressure_margin_score"] = _normalize_score(margin.clip(lower=0))
    else:
        scores["pressure_margin_score"] = 0.5

    # 2. 온도 마진 점수
    op_t = conditions.get("design_temperature")
    if op_t and op_t > 0:
        margin = (df["design_temperature_degC"] - op_t) / op_t
        scores["temperature_margin_score"] = _normalize_score(margin.clip(lower=0))
    else:
        scores["temperature_margin_score"] = 0.5

    # 3. 용량 적합도 점수 (요구 유량에 가까울수록 높음, 너무 크면 감점)
    req_flow = conditions.get("flow_rate")
    cap_values = df["capacity"].apply(_extract_number)
    if req_flow and req_flow > 0:
        ratio = cap_values / req_flow
        # 1.0 근처가 최적 (0.8~1.5 범위가 이상적)
        fit = ratio.apply(lambda r: _capacity_fit_score(r) if pd.notna(r) else 0.5)
        scores["capacity_fit_score"] = fit
    else:
        scores["capacity_fit_score"] = 0.5

    # 4. 가격 점수 (낮을수록 높은 점수, NaN은 중간값 처리)
    prices = df["price_po_usd"].copy()
    median_price = prices.median()
    prices = prices.fillna(median_price)
    if prices.max() > prices.min():
        scores["price_score"] = 1 - _normalize_score(prices)
    else:
        scores["price_score"] = 0.5

    # 5. 납기 점수 (짧을수록 높은 점수)
    lt = df["lead_time_po_weeks"].copy()
    median_lt = lt.median()
    lt = lt.fillna(median_lt)
    if lt.max() > lt.min():
        scores["lead_time_score"] = 1 - _normalize_score(lt)
    else:
        scores["lead_time_score"] = 0.5

    # 6. 데이터 완전성 점수 (핵심 필드 NaN 비율이 낮을수록 높은 점수)
    completeness = df[_KEY_FIELDS].notna().mean(axis=1)
    scores["data_completeness_score"] = completeness

    # 총점 계산
    scores["total_score"] = (
        scores["pressure_margin_score"] * WEIGHTS["pressure_margin"] +
        scores["temperature_margin_score"] * WEIGHTS["temperature_margin"] +
        scores["capacity_fit_score"] * WEIGHTS["capacity_fit"] +
        scores["price_score"] * WEIGHTS["price"] +
        scores["lead_time_score"] * WEIGHTS["lead_time"] +
        scores["data_completeness_score"] * WEIGHTS["data_completeness"]
    )

    result = pd.concat([
        df[["equipment_category", "equipment_description", "project_name",
            "project_type", "capacity", "design_pressure_barg",
            "design_temperature_degC", "vendor_name", "vendor_country",
            "price_po_usd", "lead_time_po_weeks"]].reset_index(drop=True),
        scores.reset_index(drop=True),
    ], axis=1)

    result = result.sort_values("total_score", ascending=False).reset_index(drop=True)

    ranking = result["equipment_description"].fillna("(unnamed)").tolist()
    print(f"[SUCCESS] 비교 완료: {len(result)}건, 최고점 {result['total_score'].iloc[0]:.2f}")
    return result, ranking


def _normalize_score(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - mn) / (mx - mn)


def _capacity_fit_score(ratio: float) -> float:
    """요구 용량 대비 장비 용량 비율에 따른 적합도 점수 (0~1)"""
    if ratio < 0.5:
        return 0.1  # 용량 부족
    if ratio > 3.0:
        return 0.2  # 지나친 over-spec
    if 0.8 <= ratio <= 1.5:
        return 1.0  # 이상적
    if ratio < 0.8:
        return 0.5 + (ratio - 0.5) * (0.5 / 0.3)
    return 1.0 - (ratio - 1.5) * (0.8 / 1.5)


def _extract_number(val) -> float | None:
    if val is None:
        return None
    numbers = re.findall(r"\d+\.?\d*", str(val))
    return float(numbers[0]) if numbers else None


if __name__ == "__main__":
    from tools.db_loader import load_equipment_db
    from tools.equipment_filter import filter_equipment

    db = load_equipment_db()
    conditions = {
        "equipment_category": "CENTRIFUGAL PUMP",
        "design_pressure": 10.0,
        "design_temperature": 65.0,
        "flow_rate": 350.0,
    }
    candidates, _ = filter_equipment(db, conditions)
    comparison, ranking = compare_equipment(candidates, conditions)
    print(comparison[["equipment_description", "total_score", "pressure_margin_score"]].head(10))
