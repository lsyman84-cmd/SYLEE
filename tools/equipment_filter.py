import re
import pandas as pd

# 조건 완화 비율 (조건 미충족 시 자동 완화)
_RELAX_RATIO = 0.10


def filter_equipment(df: pd.DataFrame, conditions: dict) -> tuple[pd.DataFrame, list]:
    """
    입력 조건에 맞는 장비 후보를 필터링한다.

    conditions 키:
        equipment_category (str): 장비 종류 키워드 (예: "CENTRIFUGAL PUMP")
        flow_rate (float, optional): 요구 유량
        design_pressure (float): 운전 압력 (barg)
        design_temperature (float): 운전 온도 (deg.C)
        project_type (str, optional): FPSO, FSO, Fixed P/F 등
        standards (list[str], optional): ["API 610", "ASME"] 등
        operation_mode (str, optional): "Normal" or "Transient"

    반환:
        filtered_df: 후보 DataFrame
        filter_log: 각 단계 결과 기록 list
    """
    log = []
    result = df.copy()
    total = len(result)

    # 1. 장비 카테고리 정확 매칭 (Excel J열 기준 exact match)
    category = conditions.get("equipment_category", "").strip().upper()
    if category:
        mask = result["equipment_category"].fillna("").str.upper() == category
        result = result[mask]
        log.append({
            "step": "equipment_category",
            "filter": category,
            "remaining": len(result),
            "dropped": total - len(result),
        })

    # 2. 설계 압력 필터링 (운전 압력 ≤ 장비 최대 설계 압력)
    op_pressure = conditions.get("design_pressure")
    if op_pressure is not None:
        before = len(result)
        pressure_mask = (
            result["design_pressure_barg"].isna() |
            (result["design_pressure_barg"] >= op_pressure)
        )
        result = result[pressure_mask]
        log.append({
            "step": "design_pressure",
            "filter": f">= {op_pressure} barg",
            "remaining": len(result),
            "dropped": before - len(result),
        })

    # 3. 설계 온도 필터링
    op_temp = conditions.get("design_temperature")
    if op_temp is not None:
        before = len(result)
        temp_mask = (
            result["design_temperature_degC"].isna() |
            (result["design_temperature_degC"] >= op_temp)
        )
        result = result[temp_mask]
        log.append({
            "step": "design_temperature",
            "filter": f">= {op_temp} degC",
            "remaining": len(result),
            "dropped": before - len(result),
        })

    # 4. 프로젝트 타입 필터링
    proj_type = conditions.get("project_type", "").strip().upper()
    if proj_type:
        before = len(result)
        type_mask = result["project_type"].fillna("").str.upper().str.contains(proj_type, regex=False)
        result = result[type_mask]
        log.append({
            "step": "project_type",
            "filter": proj_type,
            "remaining": len(result),
            "dropped": before - len(result),
        })

    # 5. 규격 요구사항 (Remark 컬럼 키워드 검색)
    standards = conditions.get("standards", [])
    if standards:
        before = len(result)
        def has_standard(remark):
            if not remark:
                return False
            r = str(remark).upper()
            return any(s.upper() in r for s in standards)
        std_mask = result["remark"].apply(has_standard)
        filtered_by_std = result[std_mask]
        if len(filtered_by_std) > 0:
            result = filtered_by_std
            log.append({
                "step": "standards",
                "filter": standards,
                "remaining": len(result),
                "dropped": before - len(result),
                "note": "Remark 컬럼 기준 매칭",
            })
        else:
            log.append({
                "step": "standards",
                "filter": standards,
                "remaining": len(result),
                "dropped": 0,
                "note": "규격 키워드 매칭 장비 없음 — 이 조건은 적용하지 않음 (Remark 데이터 미비 가능성)",
            })

    # 6. 결과 0건 시 조건 완화 재시도
    if len(result) == 0 and (op_pressure is not None or op_temp is not None):
        log.append({"step": "relax", "note": "0건 — 압력/온도 조건 자동 완화 후 재시도"})
        result, relax_log = _relax_and_retry(df, conditions)
        log.extend(relax_log)

    return result.reset_index(drop=True), log


def _relax_and_retry(df: pd.DataFrame, conditions: dict) -> tuple[pd.DataFrame, list]:
    relaxed = dict(conditions)
    log = []

    if conditions.get("design_pressure") is not None:
        relaxed_p = conditions["design_pressure"] * (1 - _RELAX_RATIO)
        relaxed["design_pressure"] = relaxed_p
        log.append({"step": "relax_pressure", "note": f"압력 조건 완화: {conditions['design_pressure']} → {relaxed_p:.1f} barg (-10%)"})

    if conditions.get("design_temperature") is not None:
        relaxed_t = conditions["design_temperature"] * (1 - _RELAX_RATIO)
        relaxed["design_temperature"] = relaxed_t
        log.append({"step": "relax_temperature", "note": f"온도 조건 완화: {conditions['design_temperature']} → {relaxed_t:.1f} degC (-10%)"})

    # 프로젝트 타입 조건도 제거
    relaxed.pop("project_type", None)
    log.append({"step": "relax_project_type", "note": "프로젝트 타입 조건 제거"})

    result, _ = filter_equipment(df, relaxed)
    log.append({"step": "relax_result", "remaining": len(result), "note": f"완화 조건으로 {len(result)}건 발견"})
    return result, log


def parse_capacity(val) -> float | None:
    """Capacity 컬럼에서 숫자 추출 (예: '500 m3/hr' → 500.0)"""
    if val is None:
        return None
    numbers = re.findall(r"\d+\.?\d*", str(val))
    return float(numbers[0]) if numbers else None


if __name__ == "__main__":
    from tools.db_loader import load_equipment_db

    db = load_equipment_db()
    conditions = {
        "equipment_category": "CENTRIFUGAL PUMP",
        "design_pressure": 10.0,
        "design_temperature": 65.0,
        "project_type": "FPSO",
    }
    candidates, log = filter_equipment(db, conditions)
    print(f"후보 장비: {len(candidates)}건")
    for entry in log:
        print(entry)
    if not candidates.empty:
        print(candidates[["equipment_category", "equipment_description", "design_pressure_barg", "design_temperature_degC"]].head())
