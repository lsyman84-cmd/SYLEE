import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"


def _safe_path(filename: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = (OUTPUT_DIR / filename).resolve()
    if not str(path).startswith(str(OUTPUT_DIR.resolve())):
        raise ValueError(f"허용되지 않는 경로입니다: {filename}")
    return path


def export_to_excel(data: list, filename: str) -> str:
    if not data or not isinstance(data, list):
        raise ValueError("data는 비어있지 않은 리스트여야 합니다.")
    if not filename or not isinstance(filename, str):
        raise ValueError("filename은 비어있지 않은 문자열이어야 합니다.")
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"

    import pandas as pd

    path = _safe_path(filename)
    df = pd.DataFrame(data)
    df.to_excel(path, index=False, engine="openpyxl")
    print(f"[SUCCESS] Excel 저장 완료: {path.name}")
    return str(path)


def export_to_pdf(content: str, filename: str) -> str:
    if not content or not isinstance(content, str):
        raise ValueError("content는 비어있지 않은 문자열이어야 합니다.")
    if not filename or not isinstance(filename, str):
        raise ValueError("filename은 비어있지 않은 문자열이어야 합니다.")
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    path = _safe_path(filename)
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica", 11)
    y = height - 50
    for line in content.splitlines():
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - 50
        c.drawString(40, y, line)
        y -= 18

    c.save()
    print(f"[SUCCESS] PDF 저장 완료: {path.name}")
    return str(path)


if __name__ == "__main__":
    sample_data = [
        {"날짜": "2026-05-01", "항목": "테스트A", "값": 100},
        {"날짜": "2026-05-01", "항목": "테스트B", "값": 200},
    ]
    export_to_excel(sample_data, "test_output.xlsx")

    sample_text = "Contents Report\n\n항목A: 100\n항목B: 200\n\n생성일: 2026-05-01"
    export_to_pdf(sample_text, "test_output.pdf")
