import json
import os
import time
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-opus-4-7"
MAX_RETRIES = 3


def analyze_and_recommend(context: dict) -> dict:
    """
    필터링·비교·리스크 결과를 종합하여 최종 추천과 설명을 생성한다.

    context 키:
        input_conditions (dict): 사용자 입력 조건
        candidates (list[dict]): 비교 점수 포함 상위 후보 목록 (최대 10건)
        risk_summary (list[dict]): 리스크 분석 요약
        filter_log (list[dict]): 필터링 과정 기록

    반환:
        top_recommendations (list[dict]): 1~3개 추천 장비 + 이유
        alternative_suggestions (str): 조건 미충족 시 대안 방향
        human_review_points (list[str]): 반드시 검토할 포인트
        confidence_note (str): AI 신뢰도 한계 고지
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(".env에 ANTHROPIC_API_KEY가 없습니다.")

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = (
        "You are an expert mechanical engineer specializing in offshore/onshore plant equipment selection "
        "for FPSO, FSO, and fixed platforms. Your task is to analyze equipment candidates from a historical "
        "project database and provide clear, actionable recommendations.\n\n"
        "Rules:\n"
        "1. Recommend 1 to 3 equipment items, ranked by suitability.\n"
        "2. Explain each recommendation in engineering terms: margin adequacy, operating fit, vendor reliability.\n"
        "3. Flag any HIGH risk items explicitly.\n"
        "4. If data is insufficient, say so and advise what to verify with vendors.\n"
        "5. Always note that the final selection must be reviewed by a qualified engineer.\n"
        "6. Respond ONLY in valid JSON matching the schema provided."
    )

    user_prompt = _build_prompt(context)

    response_schema = {
        "top_recommendations": [
            {
                "rank": 1,
                "equipment_description": "string",
                "project_name": "string",
                "reason": "string (engineering justification)",
                "concerns": "string (risks or data gaps to address)"
            }
        ],
        "alternative_suggestions": "string (if no suitable equipment found or conditions relaxed)",
        "human_review_points": ["string"],
        "confidence_note": "string"
    }

    full_prompt = (
        f"{user_prompt}\n\n"
        f"Respond ONLY with a JSON object matching this schema:\n"
        f"{json.dumps(response_schema, ensure_ascii=False, indent=2)}"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": full_prompt}],
            )
            raw = response.content[0].text.strip()
            # JSON 블록 추출
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            print(f"[SUCCESS] AI 분석 완료 (시도 {attempt}/{MAX_RETRIES})")
            return result
        except json.JSONDecodeError:
            print(f"[WARN] JSON 파싱 실패 (시도 {attempt}) — 재시도")
        except anthropic.APIError as e:
            print(f"[WARN] API 오류 (시도 {attempt}): {type(e).__name__}")
            if attempt < MAX_RETRIES:
                time.sleep(5)

    # AI 실패 시 기본 응답 반환
    print("[ERROR] AI 분석 실패 — 점수 기반 결과만 사용")
    return _fallback_response(context)


def _build_prompt(context: dict) -> str:
    cond = context.get("input_conditions", {})
    candidates = context.get("candidates", [])[:10]
    risks = context.get("risk_summary", [])
    log = context.get("filter_log", [])

    lines = ["## Input Conditions"]
    for k, v in cond.items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## Filter Log")
    for entry in log:
        lines.append(f"- {entry}")

    lines.append(f"\n## Equipment Candidates (top {len(candidates)}, ranked by score)")
    for i, c in enumerate(candidates, 1):
        lines.append(
            f"{i}. [{c.get('equipment_description', 'N/A')}] "
            f"Project: {c.get('project_name', 'N/A')} | "
            f"Score: {c.get('total_score', 0):.2f} | "
            f"Design P: {c.get('design_pressure_barg', 'N/A')} barg | "
            f"Design T: {c.get('design_temperature_degC', 'N/A')} °C | "
            f"Capacity: {c.get('capacity', 'N/A')} | "
            f"Vendor: {c.get('vendor_name', 'N/A')} ({c.get('vendor_country', 'N/A')}) | "
            f"PO Price: {c.get('price_po_usd', 'N/A')} USD | "
            f"Lead Time: {c.get('lead_time_po_weeks', 'N/A')} wks"
        )

    lines.append("\n## Risk Summary")
    for r in risks[:10]:
        lines.append(
            f"- [{r.get('equipment_description', 'N/A')}] "
            f"Overall: {r.get('overall_risk', 'N/A')} | "
            f"HIGH: {r.get('high_count', 0)}, MED: {r.get('medium_count', 0)}"
        )

    return "\n".join(lines)


def _fallback_response(context: dict) -> dict:
    candidates = context.get("candidates", [])
    top = candidates[:3] if candidates else []
    recs = [
        {
            "rank": i + 1,
            "equipment_description": c.get("equipment_description", "N/A"),
            "project_name": c.get("project_name", "N/A"),
            "reason": f"점수 기반 자동 선정 (Score: {c.get('total_score', 0):.2f})",
            "concerns": "AI 분석 실패 — 엔지니어가 직접 스펙을 검토해야 합니다.",
        }
        for i, c in enumerate(top)
    ]
    return {
        "top_recommendations": recs,
        "alternative_suggestions": "AI 분석을 사용할 수 없어 점수 기반 결과만 제공됩니다.",
        "human_review_points": [
            "AI 분석이 실패했습니다. 점수 기반 결과를 참고로만 사용하세요.",
            "추천 장비의 최신 Vendor 스펙을 반드시 확인하세요.",
        ],
        "confidence_note": "AI 분석 실패로 신뢰도 평가 불가.",
    }
