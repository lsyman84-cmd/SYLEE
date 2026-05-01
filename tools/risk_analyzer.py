import pandas as pd

# 리스크 등급
HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"

# 압력/온도 마진 임계값
_HIGH_RISK_THRESHOLD = 0.90   # 운전값이 설계 최대의 90% 초과 → HIGH
_MED_RISK_THRESHOLD = 0.80    # 80~90% → MEDIUM

# 핵심 필드 (없으면 HIGH 리스크)
_CRITICAL_FIELDS = ["design_pressure_barg", "design_temperature_degC", "capacity"]
# 중요 필드 (없으면 MEDIUM 리스크)
_IMPORTANT_FIELDS = ["price_po_usd", "lead_time_po_weeks", "vendor_name"]


def analyze_risk(df: pd.DataFrame, conditions: dict) -> pd.DataFrame:
    """
    장비별 리스크 요소를 분석하여 등급(HIGH/MEDIUM/LOW)을 산정한다.

    반환:
        risk_df: 장비별 리스크 항목 및 등급 DataFrame
    """
    if df.empty:
        return pd.DataFrame()

    records = []
    op_pressure = conditions.get("design_pressure")
    op_temp = conditions.get("design_temperature")
    op_mode = conditions.get("operation_mode", "Normal").strip().upper()

    for _, row in df.iterrows():
        risks = []

        # 1. 압력 마진 리스크
        dp = row.get("design_pressure_barg")
        if pd.notna(dp) and op_pressure and dp > 0:
            ratio = op_pressure / dp
            if ratio > _HIGH_RISK_THRESHOLD:
                risks.append({"item": "압력 마진", "level": HIGH,
                              "detail": f"운전압력({op_pressure} barg) = 설계압력({dp} barg)의 {ratio*100:.0f}% — 마진 부족"})
            elif ratio > _MED_RISK_THRESHOLD:
                risks.append({"item": "압력 마진", "level": MEDIUM,
                              "detail": f"운전압력이 설계압력의 {ratio*100:.0f}% — 여유 감시 필요"})
        elif pd.isna(dp):
            risks.append({"item": "압력 마진", "level": HIGH,
                          "detail": "설계 압력 데이터 없음 — Vendor 확인 필요"})

        # 2. 온도 마진 리스크
        dt = row.get("design_temperature_degC")
        if pd.notna(dt) and op_temp and dt > 0:
            ratio = op_temp / dt
            if ratio > _HIGH_RISK_THRESHOLD:
                risks.append({"item": "온도 마진", "level": HIGH,
                              "detail": f"운전온도({op_temp} °C) = 설계온도({dt} °C)의 {ratio*100:.0f}% — 마진 부족"})
            elif ratio > _MED_RISK_THRESHOLD:
                risks.append({"item": "온도 마진", "level": MEDIUM,
                              "detail": f"운전온도가 설계온도의 {ratio*100:.0f}% — 여유 감시 필요"})
        elif pd.isna(dt):
            risks.append({"item": "온도 마진", "level": HIGH,
                          "detail": "설계 온도 데이터 없음 — Vendor 확인 필요"})

        # 3. 핵심 데이터 미비
        missing_critical = [f for f in _CRITICAL_FIELDS if pd.isna(row.get(f))]
        if missing_critical:
            risks.append({"item": "핵심 데이터 미비", "level": HIGH,
                          "detail": f"누락 항목: {', '.join(missing_critical)} — Vendor 직접 확인 필수"})

        # 4. 가격 데이터 없음
        if pd.isna(row.get("price_po_usd")):
            risks.append({"item": "가격 데이터 없음", "level": MEDIUM,
                          "detail": "PO 가격 없음 — 예산 계획 불가, Vendor 견적 요청 필요"})

        # 5. 납기 불명
        if pd.isna(row.get("lead_time_po_weeks")):
            risks.append({"item": "납기 미확인", "level": MEDIUM,
                          "detail": "납기 데이터 없음 — 프로젝트 일정 검토 필요"})

        # 6. Transient 운전 조건
        if op_mode == "TRANSIENT":
            risks.append({"item": "Transient 운전", "level": MEDIUM,
                          "detail": "DB 데이터는 정상 운전 기준 — 비정상 조건은 별도 동적 분석 필요"})

        # 7. 단일 Vendor
        vendor = row.get("vendor_name")
        if pd.notna(vendor):
            risks.append({"item": "Vendor 이력", "level": LOW,
                          "detail": f"Vendor: {vendor} — 단일 Vendor 의존 시 대안 검토 권고"})

        # 리스크 없으면 OK
        if not risks:
            risks.append({"item": "전체", "level": LOW, "detail": "주요 리스크 항목 없음"})

        overall = HIGH if any(r["level"] == HIGH for r in risks) else \
                  MEDIUM if any(r["level"] == MEDIUM for r in risks) else LOW

        records.append({
            "equipment_description": row.get("equipment_description", ""),
            "project_name": row.get("project_name", ""),
            "overall_risk": overall,
            "risk_items": risks,
            "high_count": sum(1 for r in risks if r["level"] == HIGH),
            "medium_count": sum(1 for r in risks if r["level"] == MEDIUM),
            "low_count": sum(1 for r in risks if r["level"] == LOW),
        })

    risk_df = pd.DataFrame(records)
    high_cnt = (risk_df["overall_risk"] == HIGH).sum()
    print(f"[SUCCESS] 리스크 분석 완료: HIGH {high_cnt}건, 전체 {len(risk_df)}건")
    return risk_df


def format_risk_for_report(risk_df: pd.DataFrame) -> pd.DataFrame:
    """리포트용 평탄화 DataFrame 생성"""
    rows = []
    for _, r in risk_df.iterrows():
        for item in r["risk_items"]:
            rows.append({
                "장비명": r["equipment_description"],
                "프로젝트": r["project_name"],
                "종합 리스크": r["overall_risk"],
                "리스크 항목": item["item"],
                "등급": item["level"],
                "상세": item["detail"],
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from tools.db_loader import load_equipment_db
    from tools.equipment_filter import filter_equipment

    db = load_equipment_db()
    conditions = {
        "equipment_category": "CENTRIFUGAL PUMP",
        "design_pressure": 5.5,
        "design_temperature": 62.0,
    }
    candidates, _ = filter_equipment(db, conditions)
    risk_df = analyze_risk(candidates.head(5), conditions)
    print(risk_df[["equipment_description", "overall_risk", "high_count"]])
