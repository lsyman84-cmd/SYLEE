# SYLEE

## 휴대폰에서 즉시 실행 가능한 날씨 확인앱

위치 권한 또는 도시 검색으로 현재 날씨를 확인할 수 있는 모바일 웹앱(PWA)입니다.

### 로컬에서 실행

정적 파일 서버로 실행하면 됩니다.

```bash
python3 -m http.server 8080
```

브라우저에서 아래 주소로 접속:

- PC: `http://localhost:8080`
- 휴대폰: `http://<PC-로컬IP>:8080` (같은 와이파이)

### 사용 방법

1. `내 위치로 확인` 버튼으로 현재 위치 날씨 조회
2. 또는 도시 이름(예: Seoul, Busan)으로 검색
3. 모바일 브라우저 메뉴에서 **홈 화면에 추가**하면 앱처럼 즉시 실행 가능

### 사용 API

- Open-Meteo Forecast API
- Open-Meteo Geocoding API
