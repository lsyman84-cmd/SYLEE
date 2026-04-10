# PST Mail Query App (KR/EN)

PST 파일을 업로드한 뒤, 한국어/영어 자연어 질문으로 필요한 메일 정보를 찾는 모바일 기반 앱 예제입니다.

This repository contains a mobile-first demo app that loads PST mail data and lets users query email information in Korean or English.

## Project Structure

- `backend/`: Node.js API server
  - PST parsing (`pst-extractor`)
  - in-memory dataset storage
  - bilingual query interpreter (Korean/English keywords)
- `mobile/`: Expo React Native app
  - PST file picker + upload
  - natural language question input
  - query result rendering

## 1) Backend Run

```bash
cd backend
npm install
npm run dev
```

Server default: `http://localhost:4000`

### Backend APIs

- `GET /health`
- `POST /api/pst/upload` (multipart form-data with `pstFile`)
- `GET /api/pst/:datasetId`
- `POST /api/pst/query` with JSON body:

```json
{
  "datasetId": "uuid",
  "question": "최근 \"회의\" 메일 찾아줘"
}
```

## 2) Mobile Run (Expo)

```bash
cd mobile
npm install
npm start
```

앱에서 backend URL을 지정 후 PST 파일 업로드 -> 질의 입력 순서로 사용하세요.

Set backend URL in app, upload a PST file, then ask questions.

## Example Questions

- `최근 "회의" 메일 찾아줘`
- `발신자 "alice@example.com" 메일 보여줘`
- `How many emails with "invoice"?`
- `Show latest mail about "budget"`

## Notes

- 현재 질의 해석은 키워드/따옴표 기반의 경량 룰 엔진입니다.
- 데이터 저장은 메모리 기반이라 서버 재시작 시 초기화됩니다.
- 아주 큰 PST 파일은 처리 시간이 길어질 수 있습니다.
