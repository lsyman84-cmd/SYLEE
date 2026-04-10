from __future__ import annotations

import datetime as dt
import re
from typing import Any

import requests
import streamlit as st

st.set_page_config(page_title="날씨 확인 앱", page_icon="🌤️", layout="centered")

WEATHER_CODE_MAP = {
    0: "맑음",
    1: "대체로 맑음",
    2: "약간 흐림",
    3: "흐림",
    45: "안개",
    48: "서리 안개",
    51: "약한 이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    56: "약한 어는 이슬비",
    57: "강한 어는 이슬비",
    61: "약한 비",
    63: "비",
    65: "강한 비",
    66: "약한 어는 비",
    67: "강한 어는 비",
    71: "약한 눈",
    73: "눈",
    75: "강한 눈",
    77: "싸락눈",
    80: "약한 소나기",
    81: "소나기",
    82: "강한 소나기",
    85: "약한 눈 소나기",
    86: "강한 눈 소나기",
    95: "뇌우",
    96: "약한 우박 동반 뇌우",
    99: "강한 우박 동반 뇌우",
}

KOREAN_CITY_MAP = {
    "서울": "Seoul",
    "부산": "Busan",
    "인천": "Incheon",
    "대구": "Daegu",
    "대전": "Daejeon",
    "광주": "Gwangju",
    "울산": "Ulsan",
    "세종": "Sejong",
    "수원": "Suwon",
    "창원": "Changwon",
    "청주": "Cheongju",
    "전주": "Jeonju",
    "제주": "Jeju",
}

FALLBACK_COORDS = {
    "서울": {"name": "서울", "latitude": 37.5665, "longitude": 126.9780, "admin1": "서울특별시"},
    "부산": {"name": "부산", "latitude": 35.1796, "longitude": 129.0756, "admin1": "부산광역시"},
    "인천": {"name": "인천", "latitude": 37.4563, "longitude": 126.7052, "admin1": "인천광역시"},
    "대구": {"name": "대구", "latitude": 35.8714, "longitude": 128.6014, "admin1": "대구광역시"},
    "대전": {"name": "대전", "latitude": 36.3504, "longitude": 127.3845, "admin1": "대전광역시"},
    "광주": {"name": "광주", "latitude": 35.1595, "longitude": 126.8526, "admin1": "광주광역시"},
    "울산": {"name": "울산", "latitude": 35.5384, "longitude": 129.3114, "admin1": "울산광역시"},
    "세종": {"name": "세종", "latitude": 36.4800, "longitude": 127.2890, "admin1": "세종특별자치시"},
    "수원": {"name": "수원", "latitude": 37.2636, "longitude": 127.0286, "admin1": "경기도"},
    "창원": {"name": "창원", "latitude": 35.2281, "longitude": 128.6811, "admin1": "경상남도"},
    "청주": {"name": "청주", "latitude": 36.6424, "longitude": 127.4890, "admin1": "충청북도"},
    "전주": {"name": "전주", "latitude": 35.8242, "longitude": 127.1480, "admin1": "전북특별자치도"},
    "제주": {"name": "제주", "latitude": 33.4996, "longitude": 126.5312, "admin1": "제주특별자치도"},
}


def normalize_city_input(city: str) -> str:
    cleaned = city.strip()
    cleaned = re.sub(r"(특별자치시|특별자치도|특별시|광역시|자치시|자치도|시|도)$", "", cleaned)
    return cleaned.strip()


def build_city_candidates(city: str) -> list[str]:
    raw = city.strip()
    normalized = normalize_city_input(raw)
    mapped = KOREAN_CITY_MAP.get(raw) or KOREAN_CITY_MAP.get(normalized, "")

    candidates = [raw, normalized, mapped, mapped.lower() if mapped else ""]
    uniq: list[str] = []
    for item in candidates:
        if item and item not in uniq:
            uniq.append(item)
    return uniq


@st.cache_data(ttl=600, show_spinner=False)
def geocode_city(query: str) -> dict[str, Any] | None:
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": query, "count": 1, "language": "ko", "format": "json"},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results") or []
    return results[0] if results else None


def resolve_city(city: str) -> dict[str, Any] | None:
    for query in build_city_candidates(city):
        try:
            result = geocode_city(query)
            if result:
                return result
        except requests.RequestException:
            continue

    normalized = normalize_city_input(city)
    fallback = FALLBACK_COORDS.get(normalized)
    if not fallback:
        return None

    return {
        "name": fallback["name"],
        "latitude": fallback["latitude"],
        "longitude": fallback["longitude"],
        "admin1": fallback["admin1"],
        "country": "대한민국",
    }


@st.cache_data(ttl=180, show_spinner=False)
def fetch_weather(latitude: float, longitude: float) -> dict[str, Any]:
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    current = payload.get("current")
    if not current:
        raise ValueError("현재 날씨 데이터가 없습니다.")
    return current


st.title("날씨 확인 앱")
st.caption("도시명(한글 가능)으로 현재 날씨를 즉시 조회합니다.")
st.info("예: 서울, 부산, 울산, 대구, 제주")

with st.form("weather-form"):
    city_input = st.text_input("도시 이름", placeholder="예: 서울")
    submitted = st.form_submit_button("날씨 확인")

if submitted:
    city = city_input.strip()
    if not city:
        st.warning("도시 이름을 입력해 주세요.")
    else:
        with st.spinner("도시와 날씨 정보를 확인하는 중..."):
            location = resolve_city(city)
            if not location:
                st.error("도시를 찾을 수 없습니다. 다른 이름으로 시도해 주세요.")
            else:
                try:
                    current = fetch_weather(float(location["latitude"]), float(location["longitude"]))
                except (requests.RequestException, ValueError):
                    st.error("날씨 정보를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")
                else:
                    city_name = normalize_city_input(city) if re.search(r"[가-힣]", city) else location.get("name", city)
                    label_parts = [city_name, location.get("admin1"), location.get("country")]
                    label = ", ".join([part for part in label_parts if part])
                    st.subheader(label)
                    st.caption(f"업데이트: {dt.datetime.now().strftime('%m/%d %H:%M')}")

                    temperature = round(float(current["temperature_2m"]))
                    apparent = round(float(current["apparent_temperature"]))
                    humidity = round(float(current["relative_humidity_2m"]))
                    wind_speed = round(float(current["wind_speed_10m"]))
                    condition = WEATHER_CODE_MAP.get(int(current["weather_code"]), "알 수 없음")

                    col1, col2 = st.columns(2)
                    col1.metric("현재 기온", f"{temperature}°C")
                    col2.metric("날씨", condition)

                    col3, col4, col5 = st.columns(3)
                    col3.metric("체감", f"{apparent}°C")
                    col4.metric("습도", f"{humidity}%")
                    col5.metric("풍속", f"{wind_speed} km/h")
