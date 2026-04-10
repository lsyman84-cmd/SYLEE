import streamlit as st

st.set_page_config(page_title="날씨 확인 앱", page_icon="🌤️", layout="wide")

st.title("날씨 확인 앱")
st.caption("아래 링크를 눌러 앱을 여세요.")

st.markdown(
    """
### 실행 링크
[날씨 확인 앱 열기](./index.html)

> Streamlit Cloud에서는 Python 서버를 직접 바인딩할 수 없어서, 정적 파일 링크 방식으로 열어야 합니다.
"""
)
