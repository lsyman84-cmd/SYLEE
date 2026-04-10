const WEATHER_CODE_MAP = {
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
  99: "강한 우박 동반 뇌우"
};

const statusEl = document.getElementById("status");
const cardEl = document.getElementById("weather-card");
const locationNameEl = document.getElementById("location-name");
const updatedAtEl = document.getElementById("updated-at");
const temperatureEl = document.getElementById("temperature");
const conditionEl = document.getElementById("condition");
const apparentTempEl = document.getElementById("apparent-temp");
const humidityEl = document.getElementById("humidity");
const windSpeedEl = document.getElementById("wind-speed");
const useLocationBtn = document.getElementById("use-location-btn");
const searchForm = document.getElementById("search-form");
const cityInput = document.getElementById("city-input");

const KOREAN_CITY_MAP = {
  서울: "Seoul",
  부산: "Busan",
  인천: "Incheon",
  대구: "Daegu",
  대전: "Daejeon",
  광주: "Gwangju",
  울산: "Ulsan",
  세종: "Sejong",
  수원: "Suwon",
  고양: "Goyang",
  용인: "Yongin",
  창원: "Changwon",
  청주: "Cheongju",
  전주: "Jeonju",
  제주: "Jeju",
  춘천: "Chuncheon",
  강릉: "Gangneung",
  천안: "Cheonan",
  포항: "Pohang",
  김해: "Gimhae"
};

function setStatus(message) {
  statusEl.textContent = message;
}

function weatherCodeToText(code) {
  return WEATHER_CODE_MAP[code] || "알 수 없음";
}

function formatNow() {
  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date());
}

function renderWeather({ name, current }) {
  locationNameEl.textContent = name;
  updatedAtEl.textContent = `업데이트: ${formatNow()}`;
  temperatureEl.textContent = `${Math.round(current.temperature_2m)}°C`;
  conditionEl.textContent = weatherCodeToText(current.weather_code);
  apparentTempEl.textContent = `${Math.round(current.apparent_temperature)}°C`;
  humidityEl.textContent = `${Math.round(current.relative_humidity_2m)}%`;
  windSpeedEl.textContent = `${Math.round(current.wind_speed_10m)} km/h`;

  cardEl.classList.remove("hidden");
}

async function fetchWeather(latitude, longitude) {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    current:
      "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
    timezone: "auto"
  });

  const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
  if (!response.ok) {
    throw new Error("날씨 정보를 가져오지 못했습니다.");
  }
  const data = await response.json();
  if (!data.current) {
    throw new Error("현재 날씨 데이터가 없습니다.");
  }
  return data;
}

async function geocodeCity(city) {
  const params = new URLSearchParams({
    name: city,
    count: "1",
    language: "ko",
    format: "json"
  });

  const response = await fetch(`https://geocoding-api.open-meteo.com/v1/search?${params}`);
  if (!response.ok) {
    throw new Error("도시 검색에 실패했습니다.");
  }

  const data = await response.json();
  const result = data?.results?.[0];
  if (!result) {
    throw new Error("도시를 찾을 수 없습니다. 다른 이름으로 시도해 주세요.");
  }
  return result;
}

function normalizeCityQuery(input) {
  const value = input.trim();
  return KOREAN_CITY_MAP[value] || value;
}

function toKoreanDisplayName(result, typedCity) {
  const koreanTyped = typedCity.trim();
  const matched = Object.entries(KOREAN_CITY_MAP).find(([, english]) => {
    return english.toLowerCase() === String(result.name || "").toLowerCase();
  });
  const cityName = matched?.[0] || (/[가-힣]/.test(koreanTyped) ? koreanTyped : result.name);
  return [cityName, result.admin1, result.country].filter(Boolean).join(", ");
}

async function loadByCoords({ latitude, longitude, label }) {
  setStatus("날씨 정보를 불러오는 중...");
  try {
    const weather = await fetchWeather(latitude, longitude);
    renderWeather({ name: label, current: weather.current });
    setStatus("완료");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "오류가 발생했습니다.");
  }
}

function requestCurrentLocation() {
  if (!("geolocation" in navigator)) {
    setStatus("이 기기에서는 위치 기능을 지원하지 않습니다.");
    return;
  }

  setStatus("위치 권한을 요청 중입니다...");
  navigator.geolocation.getCurrentPosition(
    (position) => {
      loadByCoords({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        label: "내 위치"
      });
    },
    () => {
      setStatus("위치 권한이 거부되었거나 위치를 확인할 수 없습니다.");
    },
    {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 60000
    }
  );
}

useLocationBtn.addEventListener("click", requestCurrentLocation);

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const city = cityInput.value.trim();
  if (!city) {
    setStatus("도시 이름을 입력해 주세요.");
    return;
  }

  setStatus("도시를 찾는 중...");
  try {
    const query = normalizeCityQuery(city);
    const result = await geocodeCity(query);
    const label = toKoreanDisplayName(result, city);
    await loadByCoords({
      latitude: result.latitude,
      longitude: result.longitude,
      label
    });
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "오류가 발생했습니다.");
  }
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // 서비스워커 등록 실패는 앱 동작에 치명적이지 않으므로 무시합니다.
    });
  });
}
