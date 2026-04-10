# SYLEE

## 휴대폰에서 즉시 실행 가능한 날씨 확인앱

위치 권한 또는 도시 검색으로 현재 날씨를 확인할 수 있는 모바일 웹앱(PWA)입니다.

### 로컬에서 실행

정적 파일 서버로 실행하면 됩니다.

```bash
python3 -m http.server 8080
```

또는 실행용 파이썬 파일로 바로 실행:

```bash
python3 run_weather_app.py
```

기본 포트는 `8080`이며, 포트를 바꾸려면:

```bash
python3 run_weather_app.py --port 9090
```

이미 사용 중인 포트면 에러가 나므로, 다른 포트로 실행하세요:

```bash
python3 run_weather_app.py --port 8502
```

### Streamlit Cloud 배포용 실행

Streamlit에서는 `run_weather_app.py` 대신 아래 파일을 엔트리포인트로 사용하세요.

- `streamlit_app.py`
- `requirements.txt` (자동 설치)

Streamlit App 설정:

- **Main file path**: `streamlit_app.py`

브라우저에서 아래 주소로 접속:

- PC: `http://localhost:8080`
- 휴대폰: `http://<PC-로컬IP>:8080` (같은 와이파이)

### 사용 방법

1. 도시 이름(예: 서울, 부산, 대구)을 입력하고 `날씨 조회`
2. 또는 좌표(위도/경도)로 직접 조회 가능
3. `최근 조회 도시` 버튼으로 빠르게 재조회

### 사용 API

- Open-Meteo Forecast API
- Open-Meteo Geocoding API
