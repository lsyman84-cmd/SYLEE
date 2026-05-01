"""
장비 선정 자동화 실행 진입점

사용법:
    python run_selection.py                          # 대화형 입력
    python run_selection.py --input conditions.json  # JSON 파일 입력
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# tools 폴더를 모듈 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from tools.db_loader import load_equipment_db
from tools.equipment_filter import filter_equipment
from tools.equipment_comparator import compare_equipment
from tools.risk_analyzer import analyze_risk
from tools.ai_analyzer import analyze_and_recommend
from tools.report_generator import generate_report

DB_FILE = Path(__file__).parent / "Mechanical Equipment Database.xlsx"

# 선택 가능한 장비 카테고리 (주요 항목)
CATEGORY_HINTS = [
    "CENTRIFUGAL PUMP", "POSITIVE DISPLACEMENT PUMP", "CARGO PUMP",
    "GAS COMPRESSOR", "AIR COMPRESSOR AND DRYER PACKAGE",
    "PLATE HEAT EXCHANGER", "AIR COOLED HEAT EXCHANGER",
    "PRESSURE VESSEL", "FILTER / COALESCER",
    "TURBO GENERATOR", "ESSENTIAL DIESEL GENERATOR", "EMERGENCY DIESEL GENRATOR",
    "CHEMICAL INJECTION PACKAGE", "FUEL GAS CONDITIONING PACKAGE",
    "GAS DEHYDRATION PACKAGE", "FIRE WATER PUMP PACKAGE",
]

PROJECT_TYPE_HINTS = ["FPSO", "FSO", "FPS", "FPU", "Fixed P/F", "TLP", "SPAR Top"]


def _ask(prompt: str, default=None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    val = input(f"{prompt}{suffix}: ").strip()
    if not val and default is not None:
        return str(default)
    return val


def collect_conditions_interactive() -> dict:
    print("\n" + "=" * 60)
    print("  MECHANICAL EQUIPMENT SELECTION — 조건 입력")
    print("=" * 60)

    print(f"\n장비 카테고리 예시: {', '.join(CATEGORY_HINTS[:6])} ...")
    category = _ask("장비 카테고리 (Equipment Category)").upper()

    flow_raw = _ask("요구 유량 (Flow Rate, 숫자만 입력, 없으면 Enter)", default="")
    flow_rate = float(flow_raw) if flow_raw else None

    pressure = float(_ask("운전 압력 (Operating Pressure, barg)", default=10.0))
    temperature = float(_ask("운전 온도 (Operating Temperature, deg.C)", default=65.0))

    print(f"\n프로젝트 타입 예시: {', '.join(PROJECT_TYPE_HINTS)}")
    proj_type = _ask("프로젝트 타입 (없으면 Enter)", default="").upper()

    op_mode = _ask("운전 조건 (Normal / Transient)", default="Normal").upper()

    standards_raw = _ask("규격 요구사항 (예: API 610,ASME 없으면 Enter)", default="")
    standards = [s.strip() for s in standards_raw.split(",") if s.strip()]

    conditions = {
        "equipment_category": category,
        "design_pressure": pressure,
        "design_temperature": temperature,
        "operation_mode": op_mode,
    }
    if flow_rate:
        conditions["flow_rate"] = flow_rate
    if proj_type:
        conditions["project_type"] = proj_type
    if standards:
        conditions["standards"] = standards

    return conditions


def load_conditions_from_file(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run(conditions: dict):
    print("\n" + "=" * 60)
    print("  MECHANICAL EQUIPMENT SELECTION — 분석 시작")
    print("=" * 60)
    print(f"조건: {json.dumps(conditions, ensure_ascii=False)}\n")

    # Step 1: DB 로딩
    print("[1/6] DB 로딩 중...")
    df = load_equipment_db(str(DB_FILE))

    # Step 2: 필터링
    print("[2/6] 조건 필터링 중...")
    candidates, filter_log = filter_equipment(df, conditions)

    if candidates.empty:
        print("\n[경고] 조건에 맞는 장비를 찾지 못했습니다.")
        print("      입력 조건을 완화하거나 장비 카테고리를 확인해 주세요.")
        return

    print(f"      → 후보 {len(candidates)}건 발견")
    for entry in filter_log:
        note = entry.get("note", "")
        remaining = entry.get("remaining", "")
        step = entry.get("step", "")
        if note:
            print(f"        [{step}] {note}")
        elif remaining != "":
            print(f"        [{step}] 남은 후보: {remaining}건")

    # Step 3: 비교
    print("\n[3/6] 후보 장비 비교 중...")
    top_n = min(20, len(candidates))
    comparison_df, ranking = compare_equipment(candidates.head(top_n), conditions)

    # Step 4: 리스크 분석
    print("\n[4/6] 리스크 분석 중...")
    top_candidates = comparison_df.head(10)
    risk_df = analyze_risk(top_candidates, conditions)

    # Step 5: AI 추천
    print("\n[5/6] AI 추천 생성 중...")
    context = {
        "input_conditions": conditions,
        "candidates": top_candidates.to_dict(orient="records"),
        "risk_summary": risk_df[["equipment_description", "project_name",
                                  "overall_risk", "high_count", "medium_count"]].to_dict(orient="records"),
        "filter_log": filter_log,
    }
    ai_result = analyze_and_recommend(context)

    # Step 6: 보고서 생성
    print("\n[6/6] 보고서 생성 중...")
    paths = generate_report(conditions, comparison_df, risk_df, ai_result, filter_log)

    print("\n" + "=" * 60)
    print("  완료!")
    print(f"  Excel: {paths['excel']}")
    print(f"  PDF:   {paths['pdf']}")
    print("=" * 60)

    print("\n[AI 추천 요약]")
    for rec in ai_result.get("top_recommendations", []):
        print(f"  {rec['rank']}위: {rec['equipment_description']}")
        print(f"       이유: {rec['reason']}")
        print(f"       검토: {rec['concerns']}")

    print("\n[반드시 검토할 포인트]")
    for pt in ai_result.get("human_review_points", []):
        print(f"  • {pt}")


def main():
    parser = argparse.ArgumentParser(description="Mechanical Equipment Selection Tool")
    parser.add_argument("--input", help="조건 JSON 파일 경로 (없으면 대화형 입력)")
    args = parser.parse_args()

    if args.input:
        conditions = load_conditions_from_file(args.input)
        print(f"[INFO] JSON 파일에서 조건 로드: {args.input}")
    else:
        conditions = collect_conditions_interactive()

    run(conditions)


if __name__ == "__main__":
    main()
