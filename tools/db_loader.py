import io
import re
import pandas as pd
import openpyxl
from abc import ABC, abstractmethod
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "Mechanical Equipment Database.xlsx"
DATA_START_ROW = 10  # 1-indexed in openpyxl

_NA_VALUES = {"-", "not available", "n/a", "na", "none", "tbd", "tbc", "not avail.", "-"}

COLUMNS = [
    "row_number", "project_name", "project_code", "project_type", "client",
    "built_year", "contractor_name", "contractor_location", "site",
    "equipment_category", "equipment_description", "rfq_no", "equipment_type",
    "configuration", "capacity", "model_no", "material",
    "dim_l_mm", "dim_w_mm", "dim_h_mm",
    "weight_dry_kg", "weight_operating_kg",
    "power_rated_kw", "power_absorbed_kw",
    "design_pressure_barg", "design_temperature_degC",
    "operating_pressure_barg", "operating_temperature_degC",
    "operating_diff_pressure_bar", "operating_surface_area_m2",
    "vendor_gad_no", "remark", "vendor_name", "vendor_country",
    "price_bidding_usd", "price_po_usd", "price_final_usd",
    "lead_time_po_weeks", "lead_time_actual_weeks",
    "rev", "date",
    "_col42", "_col43", "_col44",
]

NUMERIC_COLS = [
    "design_pressure_barg", "design_temperature_degC",
    "operating_pressure_barg", "operating_temperature_degC",
    "operating_diff_pressure_bar", "operating_surface_area_m2",
    "weight_dry_kg", "weight_operating_kg",
    "power_rated_kw", "power_absorbed_kw",
    "price_bidding_usd", "price_po_usd", "price_final_usd",
    "lead_time_po_weeks", "lead_time_actual_weeks",
    "dim_l_mm", "dim_w_mm", "dim_h_mm",
]


class DataSource(ABC):
    @abstractmethod
    def load(self) -> pd.DataFrame:
        pass


class ExcelDataSource(DataSource):
    def __init__(self, source=None):
        if isinstance(source, (bytes, bytearray)):
            self._src = io.BytesIO(source)
            self._is_path = False
        elif isinstance(source, io.BytesIO):
            self._src = source
            self._is_path = False
        else:
            self._src = Path(source) if source else DB_PATH
            self._is_path = True

    def load(self) -> pd.DataFrame:
        if self._is_path:
            if not self._src.exists():
                raise FileNotFoundError(f"DB 파일을 찾을 수 없습니다: {self._src}")
        wb = openpyxl.load_workbook(self._src, data_only=True)
        ws = wb["DATABASE"]

        rows = []
        for row in ws.iter_rows(min_row=DATA_START_ROW, values_only=True):
            if all(v is None for v in row):
                continue
            if row[0] is None:
                continue
            rows.append(row)

        num_cols = len(COLUMNS)
        padded = []
        for row in rows:
            lst = list(row)
            if len(lst) < num_cols:
                lst += [None] * (num_cols - len(lst))
            padded.append(lst[:num_cols])

        df = pd.DataFrame(padded, columns=COLUMNS)
        df = df.drop(columns=["_col42", "_col43", "_col44"], errors="ignore")
        df = _normalize(df)
        print(f"[SUCCESS] DB 로딩 완료: {len(df)}건")
        return df


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    # 문자열 정규화
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].apply(_clean_str)

    # 복합 압력/온도 값 파싱 (예: "15/65" → 최댓값 65, "FW:6\nSW:14" → 첫 번째 숫자 6)
    for col in ["design_pressure_barg", "design_temperature_degC",
                "operating_pressure_barg", "operating_temperature_degC"]:
        df[col] = df[col].apply(_parse_numeric_field)

    # 일반 숫자 컬럼 변환
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 장비 카테고리 대문자 통일
    if "equipment_category" in df.columns:
        df["equipment_category"] = df["equipment_category"].str.upper().str.strip()

    return df


def _clean_str(val) -> object:
    if val is None:
        return None
    s = str(val).strip().replace("\n", " ")
    if s.lower() in _NA_VALUES or s == "":
        return None
    return s


def _parse_numeric_field(val) -> float:
    """
    다양한 형식의 압력/온도 값을 숫자로 변환.
    "15/65" → 65 (최댓값)
    "FW:6 SW:14" → 14 (최댓값)
    "50" → 50.0
    """
    if val is None:
        return None
    s = str(val).strip()
    if s.lower() in _NA_VALUES or s == "":
        return None

    # 숫자만 추출해서 최댓값 반환
    numbers = re.findall(r"[-+]?\d*\.?\d+", s)
    if not numbers:
        return None
    return max(float(n) for n in numbers)


def load_equipment_db(file_path: str = None) -> pd.DataFrame:
    return ExcelDataSource(file_path).load()


def load_equipment_db_from_bytes(data: bytes) -> pd.DataFrame:
    return ExcelDataSource(data).load()


if __name__ == "__main__":
    df = load_equipment_db()
    print(df.dtypes)
    print(df[["equipment_category", "design_pressure_barg", "design_temperature_degC", "capacity"]].head(10))
