import streamlit as st
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import json
import tempfile
import os
from tracker_hub import log_app_usage

# 윈도우 맑은 고딕 폰트 적용하여 글자 깨짐 방지
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 앱 이름 설정 및 트래커 연동용 상수
APP_NAME = "tape_audio_analyzer"

def init_session():
    # 세션 시작 시 최초 1회만 오픈 로그 기록
    if "opened" not in st.session_state:
        st.session_state["opened"] = True
        log_app_usage(APP_NAME, "app_opened", details=json.dumps({"status": "success"}))

def plot_audio_data(audio_file, title):
    # 업로드 파일의 스트림 포인터 초기화
    audio_file.seek(0)
    
    # 원본 확장자를 유지한 임시 파일 생성
    file_extension = os.path.splitext(audio_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(audio_file.read())
        tmp_path = tmp_file.name
    
    try:
        # 파일 경로를 전달하여 librosa의 예외 디코더 작동 유도
        y, sr = librosa.load(tmp_path)
    finally:
        # 파일 로드가 끝나면 안전하게 임시 파일 삭제
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    # 윈도우 맑은 고딕 폰트 지정 및 마이너스 깨짐 방지
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False
    
    # constrained_layout 설정을 통해 두 그래프의 크기와 마진 일치
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), constrained_layout=True)
    
    # 1구역: 주파수 파형 시각화
    librosa.display.waveshow(y, sr=sr, ax=ax1, color="blue")
    ax1.set_title(f"{title} - 주파수 파형")
    ax1.set_xlabel("시간 (초)")
    ax1.set_ylabel("진폭")
    
    # 2구역: 무지개색 주파수 지도 시각화
    stft_data = librosa.stft(y)
    stft_db = librosa.amplitude_to_db(np.abs(stft_data), ref=np.max)
    img = librosa.display.specshow(stft_db, sr=sr, x_axis="time", y_axis="log", ax=ax2, cmap="rainbow")
    ax2.set_title(f"{title} - 무지개색 주파수 지도")
    ax2.set_xlabel("시간 (초)")
    ax2.set_ylabel("주파수 (Hz)")
    fig.colorbar(img, ax=ax2, format="%+2.0f dB")
    
    return fig

# 메인 UI 실행 및 세션 체크
init_session()

st.title("잡학다식 개발자 - 아날로그 감성 데이터 검증실")
st.subheader("디지털 원본 vs 카세트 테이프 녹음본 주파수 비교")

# 사이드바 설정 및 기능 이용 흔적 트래킹
st.sidebar.header("설정 및 제어")
selected_genre = st.sidebar.selectbox(
    "분석할 음악 장르 선택", 
    ["Lofi", "Synthwave", "City Pop", "Jazz"],
    key="genre_select"
)

# 콤보박스 변경 로그 기록
if st.session_state.genre_select:
    log_app_usage(
        APP_NAME, 
        "genre_changed", 
        details=json.dumps({"selected_genre": st.session_state.genre_select})
    )

# 파일 업로드 컴포넌트 배치 (m4a, flac, ogg 등 다양한 포맷 허용하도록 확장)
digital_file = st.file_uploader("Suno AI 디지털 원본 파일 업로드", type=["mp3", "wav", "m4a", "flac", "ogg"])
tape_file = st.file_uploader("빅터 데크 테이프 녹음본 파일 업로드", type=["wav", "mp3", "m4a", "flac", "ogg"])

# 분석 실행 버튼 및 트래킹
if st.button("주파수 교차 시각화 실행"):
    if digital_file and tape_file:
        # 버튼 사용 흔적 세부 정보 JSON 타입 정리 후 로그 전송
        log_app_usage(
            APP_NAME, 
            "analysis_button_clicked", 
            details=json.dumps({
                "genre": selected_genre,
                "digital_filename": digital_file.name,
                "tape_filename": tape_file.name
            })
        )
        
        # 화면 렌더링 부분 수정
        col1, col2 = st.columns(2)

        with col1:
            # 제목 길이를 최적화하여 상단 정렬 유지
            st.write("### 1구역: 디지털 원본")
            fig_digital = plot_audio_data(digital_file, "디지털 원본")
            st.pyplot(fig_digital)
            
        with col2:
            # 글자 수를 왼쪽과 맞춰 한 줄로 깔끔하게 정렬
            st.write("### 2구역: 테이프 녹음본")
            fig_tape = plot_audio_data(tape_file, "테이프 녹음본")
            st.pyplot(fig_tape)
            
    else:
        st.warning("두 개의 오디오 파일을 모두 업로드해야 비교 분석이 가능합니다.")