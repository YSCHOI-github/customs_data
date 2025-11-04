import streamlit as st
import json
import os
from html import escape as html_escape
from datetime import datetime
from crawler_customs_portal import CustomsCrawler
from crawler_classification_committee import ClassificationCrawler
from crawler_classification_council import ClassificationCrawler3
from crawler_classification_cases import ClassificationCrawler4
from crawler_us import ClassificationCrawler_us
from crawler_eu import ClassificationCrawler_eu
from crawler_jp import ClassificationCrawler_jp
from crawler_cn import ClassificationCrawler_cn
from crawler_moleg import LawPortalCrawler
from crawler_moleg_tax import LawPortalCrawler_tax
import sys
from io import StringIO

# 페이지 설정
st.set_page_config(
    page_title="관세법령정보포털 크롤러",
    page_icon="📊",
    layout="wide"
)

# 이미지 매핑 딕셔너리
CRAWLER_IMAGES = {
    "관세법령정보포털 판례": "images/customs_portal.png",
    "국가법령정보센터 판례": "images/moleg.png",
    "국가법령정보센터 내국세 판례": "images/moleg_tax.png",
    "국내품목분류위원회 사례": "images/classification_committee.png",
    "국내품목분류협의회 사례": "images/classification_council.png",
    "품목분류 사례": "images/classification_cases.png",
    "미국 품목분류 사례": "images/us_classification.png",
    "EU 품목분류 사례": "images/eu_classification.png",
    "일본 품목분류 사례": "images/jp_classification.png",
    "중국 품목분류 사례": "images/cn_classification.png"
}

# Session State 초기화
def init_session_state():
    if 'crawling_result' not in st.session_state:
        st.session_state.crawling_result = None
    if 'crawling_logs' not in st.session_state:
        st.session_state.crawling_logs = []
    if 'crawling_error' not in st.session_state:
        st.session_state.crawling_error = None
    if 'crawling_stats' not in st.session_state:
        st.session_state.crawling_stats = {}
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False
    if 'crawling_stages' not in st.session_state:
        st.session_state.crawling_stages = {
            'init': {'status': 'pending', 'message': ''},
            'connect': {'status': 'pending', 'message': ''},
            'collect': {'status': 'pending', 'message': ''},
            'process': {'status': 'pending', 'message': ''},
            'complete': {'status': 'pending', 'message': ''}
        }
    if 'stage_logs' not in st.session_state:
        st.session_state.stage_logs = {
            'init': [],
            'connect': [],
            'collect': [],
            'process': [],
            'complete': []
        }

# 로그 추가 함수
def add_log(message, level="INFO", stage=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    st.session_state.crawling_logs.append(log_entry)

    # 단계별 로그에도 추가
    if stage and stage in st.session_state.stage_logs:
        st.session_state.stage_logs[stage].append(log_entry)

    # 최근 15개만 유지
    if len(st.session_state.crawling_logs) > 15:
        st.session_state.crawling_logs = st.session_state.crawling_logs[-15:]

# 단계 상태 업데이트 함수
def update_stage(stage, status, message=""):
    if stage in st.session_state.crawling_stages:
        st.session_state.crawling_stages[stage]['status'] = status
        st.session_state.crawling_stages[stage]['message'] = message

# 단계별 진행 상황 표시 (ChatGPT 에이전트 스타일)
def render_progress_stages():
    stages_config = {
        'init': {'icon': '1', 'title': '초기화', 'desc': '크롤러 설정'},
        'connect': {'icon': '2', 'title': '웹사이트 접속', 'desc': '사이트 연결'},
        'collect': {'icon': '3', 'title': '데이터 수집', 'desc': '정보 크롤링'},
        'process': {'icon': '4', 'title': '데이터 처리', 'desc': '중복 제거'},
        'complete': {'icon': '5', 'title': '완료', 'desc': '작업 완료'}
    }

    stages = st.session_state.crawling_stages

    # CSS 스타일
    st.markdown("""
    <style>
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    .stage-container {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin: 20px 0;
    }
    .stage-card {
        background: white;
        border-radius: 10px;
        padding: 15px 20px;
        border-left: 4px solid #ddd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stage-card.pending {
        border-left-color: #e0e0e0;
        background: #f9f9f9;
    }
    .stage-card.running {
        border-left-color: #2196F3;
        background: #e3f2fd;
        animation: pulse 2s ease-in-out infinite;
    }
    .stage-card.completed {
        border-left-color: #4CAF50;
        background: #e8f5e9;
    }
    .stage-card.error {
        border-left-color: #f44336;
        background: #ffebee;
    }
    .stage-header {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .stage-icon {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 14px;
    }
    .stage-icon.pending {
        background: #e0e0e0;
        color: #999;
    }
    .stage-icon.running {
        background: #2196F3;
        color: white;
        animation: spin 2s linear infinite;
    }
    .stage-icon.completed {
        background: #4CAF50;
        color: white;
    }
    .stage-icon.error {
        background: #f44336;
        color: white;
    }
    .stage-title {
        font-size: 16px;
        font-weight: 600;
        color: #333;
    }
    .stage-desc {
        font-size: 13px;
        color: #666;
        margin-left: 44px;
        margin-top: 5px;
    }
    .stage-logs {
        margin-left: 44px;
        margin-top: 10px;
        padding: 10px;
        background: #fafafa;
        border-radius: 5px;
        font-family: monospace;
        font-size: 11px;
        max-height: 150px;
        overflow-y: auto;
    }
    .stage-log-entry {
        margin-bottom: 5px;
        color: #555;
    }
    </style>
    """, unsafe_allow_html=True)

    html = "<div class='stage-container'>"

    for stage_key, config in stages_config.items():
        stage = stages[stage_key]
        status = stage['status']
        message = stage['message']

        icon_symbol = '✓' if status == 'completed' else ('✗' if status == 'error' else config['icon'])
        if status == 'running':
            icon_symbol = '⟳'

        html += f"""
        <div class='stage-card {status}'>
            <div class='stage-header'>
                <div class='stage-icon {status}'>{icon_symbol}</div>
                <div style='flex: 1;'>
                    <div class='stage-title'>{config['title']}</div>
                </div>
            </div>
            <div class='stage-desc'>{message if message else config['desc']}</div>
        """

        # 단계별 상세 로그 (진행중이거나 완료된 단계만)
        if status in ['running', 'completed'] and stage_key in st.session_state.stage_logs:
            stage_logs = st.session_state.stage_logs[stage_key]
            if stage_logs:
                html += "<div class='stage-logs'>"
                for log in stage_logs[-5:]:
                    color = {
                        "INFO": "#0066cc",
                        "WARNING": "#ff9900",
                        "ERROR": "#cc0000",
                        "SUCCESS": "#009900"
                    }.get(log["level"], "#555")
                    html += f"<div class='stage-log-entry'><span style='color: #999;'>{log['timestamp']}</span> <span style='color: {color};'>{log['message']}</span></div>"
                html += "</div>"

        html += "</div>"

    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)

# 데이터 샘플을 카드 형태로 표시 (1개만)
def render_data_cards(data):
    if not data or len(data) == 0:
        st.info("표시할 데이터가 없습니다.")
        return

    # 첫 번째 데이터만 표시
    sample_item = data[0]

    st.markdown("""
    <style>
    .sample-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        color: white;
    }
    .sample-header {
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 20px;
        padding-bottom: 15px;
        border-bottom: 2px solid rgba(255,255,255,0.3);
        text-align: center;
    }
    .sample-field {
        margin: 12px 0;
        padding: 8px 0;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    .sample-label {
        font-weight: 600;
        font-size: 14px;
        opacity: 0.95;
        margin-bottom: 5px;
    }
    .sample-value {
        background: rgba(255,255,255,0.15);
        padding: 10px 15px;
        border-radius: 8px;
        font-size: 14px;
        line-height: 1.6;
        word-break: break-word;
        white-space: pre-wrap;
    }
    </style>
    """, unsafe_allow_html=True)

    # 카드 시작
    card_parts = ['<div class="sample-card">']
    card_parts.append('<div class="sample-header">데이터 샘플</div>')

    # 각 필드 추가
    for key, value in sample_item.items():
        # 값 처리
        str_value = str(value) if value is not None else ""

        # 너무 긴 값은 잘라내기
        if len(str_value) > 300:
            str_value = str_value[:300] + "..."

        # HTML 이스케이프
        safe_key = html_escape(str(key))
        safe_value = html_escape(str_value)

        card_parts.append(f'<div class="sample-field">')
        card_parts.append(f'  <div class="sample-label">{safe_key}</div>')
        card_parts.append(f'  <div class="sample-value">{safe_value}</div>')
        card_parts.append('</div>')

    # 카드 끝
    card_parts.append('</div>')

    # HTML 렌더링
    final_html = '\n'.join(card_parts)
    st.markdown(final_html, unsafe_allow_html=True)

# 새 크롤링 시작 (상태 초기화)
def reset_crawling_state():
    st.session_state.crawling_result = None
    st.session_state.crawling_logs = []
    st.session_state.crawling_error = None
    st.session_state.crawling_stats = {}
    st.session_state.show_results = False
    st.session_state.crawling_stages = {
        'init': {'status': 'pending', 'message': ''},
        'connect': {'status': 'pending', 'message': ''},
        'collect': {'status': 'pending', 'message': ''},
        'process': {'status': 'pending', 'message': ''},
        'complete': {'status': 'pending', 'message': ''}
    }
    st.session_state.stage_logs = {
        'init': [],
        'connect': [],
        'collect': [],
        'process': [],
        'complete': []
    }

def main():
    init_session_state()

    st.title("관세법령정보포털 크롤러")
    st.write("관세법령정보포털에서 판례 및 품목분류 데이터를 크롤링합니다.")

    # 새 크롤링 시작 버튼 (결과가 있을 때만 표시)
    if st.session_state.show_results:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 새 크롤링 시작", type="secondary", use_container_width=True):
                reset_crawling_state()
                st.rerun()

    # 사이드바 설정
    st.sidebar.header("크롤링 설정")

    # 크롤링 타입 선택
    crawl_type = st.sidebar.selectbox(
        "크롤링 타입 선택",
        ["관세법령정보포털 판례", "국가법령정보센터 판례", "국가법령정보센터 내국세 판례",
         "국내품목분류위원회 사례", "국내품목분류협의회 사례", "품목분류 사례",
         "미국 품목분류 사례", "EU 품목분류 사례", "일본 품목분류 사례", "중국 품목분류 사례"],
        help="크롤링할 데이터 유형을 선택하세요.",
        disabled=st.session_state.show_results
    )

    # 사이트 이미지 표시
    image_path = CRAWLER_IMAGES.get(crawl_type)
    if image_path and os.path.exists(image_path):
        st.sidebar.image(image_path, caption=f"{crawl_type} 화면", use_container_width=True)

    # 페이지당 표시 개수 선택
    items_per_page = 10
    if crawl_type == "관세법령정보포털 판례":
        items_per_page = st.sidebar.selectbox(
            "페이지당 표시 개수",
            [10, 20, 30, 50, 100],
            index=0,
            help="한 페이지에 표시할 데이터 개수를 선택하세요.",
            disabled=st.session_state.show_results
        )
    elif crawl_type == "국가법령정보센터 판례":
        items_per_page = st.sidebar.selectbox(
            "페이지당 표시 개수",
            [50, 100, 150],
            index=0,
            help="한 페이지에 표시할 데이터 개수를 선택하세요.",
            disabled=st.session_state.show_results
        )
    elif crawl_type == "국가법령정보센터 내국세 판례":
        items_per_page = st.sidebar.selectbox(
            "페이지당 표시 개수",
            [50, 100, 150],
            index=0,
            help="한 페이지에 표시할 데이터 개수를 선택하세요.",
            disabled=st.session_state.show_results
        )

    # 검색어 입력 필드
    search_keyword = ""
    if crawl_type == "국가법령정보센터 내국세 판례":
        search_keyword = st.sidebar.text_input(
            "검색어",
            value="부가가치세",
            help="검색할 키워드를 입력하세요.",
            disabled=st.session_state.show_results
        )

    # 크롤링 범위 설정
    st.sidebar.subheader("크롤링 범위 설정")

    max_pages = st.sidebar.number_input(
        "크롤링할 페이지 수",
        min_value=1,
        max_value=50,
        value=8,
        help=f"크롤링할 페이지 수를 입력하세요 (페이지당 최대 {items_per_page}건)",
        disabled=st.session_state.show_results
    )
    st.sidebar.info(f"예상 크롤링 건수: 최대 {max_pages * items_per_page}건")

    # 국내품목분류 사례용 추가 설정
    start_date = None
    if (crawl_type == "국내품목분류위원회 사례" or
        crawl_type == "국내품목분류협의회 사례" or
        crawl_type == "품목분류 사례" or
        crawl_type == "미국 품목분류 사례" or
        crawl_type == "EU 품목분류 사례"):
        start_date = st.sidebar.date_input(
            "검색 시작일",
            value=datetime(2024, 1, 1),
            help="검색 시작일을 선택하세요.",
            disabled=st.session_state.show_results
        ).strftime('%Y-%m-%d')

    # 크롤링 시작 버튼
    if st.sidebar.button("크롤링 시작", type="primary", disabled=st.session_state.show_results):
        # 상태 초기화
        reset_crawling_state()

        # 진행 상황 표시
        st.write("**크롤링 진행 상황**")

        # 단계별 진행 표시 컨테이너
        stage_container = st.empty()

        # 메트릭을 2열로 배치
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            progress_metric = st.empty()
        with metric_col2:
            collected_metric = st.empty()

        try:
            # 1단계: 초기화
            update_stage('init', 'running', '크롤러 설정 중...')
            add_log(f"{crawl_type} 크롤러 초기화 중...", "INFO", 'init')
            with stage_container.container():
                render_progress_stages()

            if crawl_type == "관세법령정보포털 판례":
                crawler = CustomsCrawler()
                crawler_type_name = "관세법령정보포털 판례"
            elif crawl_type == "국가법령정보센터 판례":
                crawler = LawPortalCrawler()
                crawler_type_name = "국가법령정보센터 판례"
            elif crawl_type == "국가법령정보센터 내국세 판례":
                crawler = LawPortalCrawler_tax()
                crawler_type_name = "국가법령정보센터 내국세 판례"
            elif crawl_type == "국내품목분류위원회 사례":
                crawler = ClassificationCrawler()
                crawler_type_name = "품목분류위원회 사례"
            elif crawl_type == "품목분류 사례":
                crawler = ClassificationCrawler4()
                crawler_type_name = "품목분류 사례"
            elif crawl_type == "미국 품목분류 사례":
                crawler = ClassificationCrawler_us()
                crawler_type_name = "미국 품목분류 사례"
            elif crawl_type == "EU 품목분류 사례":
                crawler = ClassificationCrawler_eu()
                crawler_type_name = "EU 품목분류 사례"
            elif crawl_type == "일본 품목분류 사례":
                crawler = ClassificationCrawler_jp()
                crawler_type_name = "일본 품목분류 사례"
            elif crawl_type == "중국 품목분류 사례":
                crawler = ClassificationCrawler_cn()
                crawler_type_name = "중국 품목분류 사례"
            else:  # "국내품목분류협의회 사례"
                crawler = ClassificationCrawler3()
                crawler_type_name = "품목분류협의회 사례"

            add_log(f"{crawler_type_name} 크롤러 생성 완료", "SUCCESS", 'init')
            update_stage('init', 'completed', '크롤러 설정 완료')
            with stage_container.container():
                render_progress_stages()

            # 2단계: 웹사이트 접속
            update_stage('connect', 'running', '웹사이트에 연결 중...')
            add_log(f"{crawler_type_name} 사이트 접속 시작", "INFO", 'connect')
            with stage_container.container():
                render_progress_stages()

            # 네비게이션 콜백 함수 (웹사이트 접속 단계의 상세 정보 업데이트)
            def navigation_callback(step_name, step_status="running"):
                """
                네비게이션 단계별 상태 업데이트
                Args:
                    step_name: 단계 이름 (예: "메뉴 클릭", "검색 설정")
                    step_status: 상태 ("running", "completed")
                """
                if step_status == "running":
                    update_stage('connect', 'running', f'{step_name} 중...')
                    add_log(f"{step_name} 시작", "INFO", 'connect')
                else:
                    add_log(f"{step_name} 완료", "SUCCESS", 'connect')

                with stage_container.container():
                    render_progress_stages()

            # 진행 상황 업데이트 함수
            def update_progress(current_page, total_pages, current_case=None, total_cases=None, collected_count=0):
                # 3단계: 데이터 수집 (처음 호출 시)
                if st.session_state.crawling_stages['connect']['status'] == 'running':
                    update_stage('connect', 'completed', '사이트 연결 완료')
                    update_stage('collect', 'running', f'페이지 {current_page}/{total_pages} 데이터 수집 중...')
                    with stage_container.container():
                        render_progress_stages()

                # 전체 진행률 계산
                if current_case is not None and total_cases is not None and total_cases > 0:
                    page_progress = (current_page - 1) / total_pages
                    case_progress = current_case / total_cases / total_pages
                    total_progress = page_progress + case_progress
                    add_log(f"페이지 {current_page}/{total_pages} - 사건 {current_case}/{total_cases} 처리 중", "INFO", 'collect')
                    update_stage('collect', 'running', f'페이지 {current_page}/{total_pages} | 사건 {current_case}/{total_cases} 처리 중')
                else:
                    total_progress = current_page / total_pages
                    add_log(f"페이지 {current_page}/{total_pages} 처리 중", "INFO", 'collect')
                    update_stage('collect', 'running', f'페이지 {current_page}/{total_pages} 처리 중')

                # 메트릭 업데이트 (2열 가로 배치)
                progress_percentage = total_progress * 100
                progress_metric.metric("전체 진행률", f"{progress_percentage:.1f}%", f"페이지 {current_page}/{total_pages}")

                # 수집 데이터 표시
                expected_max = max_pages * items_per_page
                collected_metric.metric("수집된 데이터", f"{collected_count}건", f"예상: ~{expected_max}건")

                # 단계 UI 업데이트
                with stage_container.container():
                    render_progress_stages()

            # 크롤러 타입에 따라 다른 파라미터로 실행
            if crawl_type == "관세법령정보포털 판례":
                data = crawler.crawl_data(
                    max_pages=max_pages,
                    progress_callback=update_progress,
                    navigation_callback=navigation_callback,
                    items_per_page=items_per_page
                )
            elif crawl_type == "국가법령정보센터 판례":
                data = crawler.crawl_data(
                    max_pages=max_pages,
                    progress_callback=update_progress,
                    navigation_callback=navigation_callback,
                    items_per_page=items_per_page
                )
            elif crawl_type == "국가법령정보센터 내국세 판례":
                data = crawler.crawl_data(
                    search_keyword=search_keyword,
                    max_pages=max_pages,
                    progress_callback=update_progress,
                    navigation_callback=navigation_callback,
                    items_per_page=items_per_page
                )
            else:  # 국내품목분류 사례들
                data = crawler.crawl_data(
                    start_date=start_date,
                    max_pages=max_pages,
                    progress_callback=update_progress,
                    navigation_callback=navigation_callback
                )

            # 4단계: 데이터 처리
            update_stage('collect', 'completed', '데이터 수집 완료')
            update_stage('process', 'running', '중복 제거 및 데이터 정리 중...')
            add_log("데이터 중복 제거 및 정리 시작", "INFO", 'process')
            with stage_container.container():
                render_progress_stages()

            update_stage('process', 'completed', f'{len(data) if data else 0}건 데이터 정리 완료')
            with stage_container.container():
                render_progress_stages()

            # 크롤링 통계 저장
            st.session_state.crawling_stats = {
                "crawler_type": crawler_type_name,
                "total_collected": len(data) if data else 0,
                "target_pages": max_pages,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            if data:
                # 5단계: 완료
                update_stage('complete', 'completed', f'총 {len(data)}건의 데이터 수집 완료')
                add_log(f"크롤링 완료! 총 {len(data)}건 수집", "SUCCESS", 'complete')
                with stage_container.container():
                    render_progress_stages()

                # 성공률 계산 및 메트릭 업데이트
                progress_metric.metric("전체 진행률", "100%", f"완료: {max_pages}개 페이지")
                collected_metric.metric("최종 수집 데이터", f"{len(data)}건")

                # 결과를 session state에 저장
                st.session_state.crawling_result = data
                st.session_state.show_results = True

                st.success(f"{crawler_type_name} 크롤링 완료! 총 {len(data)}건의 데이터를 수집했습니다.")

            else:
                update_stage('complete', 'error', '수집된 데이터가 없습니다')
                add_log("수집된 데이터가 없습니다.", "WARNING", 'complete')
                with stage_container.container():
                    render_progress_stages()
                st.warning("수집된 데이터가 없습니다. 검색 조건을 확인해주세요.")

        except Exception as e:
            error_msg = str(e)
            st.session_state.crawling_error = error_msg

            # 오류 발생 단계 표시
            for stage_key in ['init', 'connect', 'collect', 'process', 'complete']:
                if st.session_state.crawling_stages[stage_key]['status'] == 'running':
                    update_stage(stage_key, 'error', f'오류 발생: {error_msg[:50]}...')
                    add_log(f"오류 발생: {error_msg}", "ERROR", stage_key)
                    break

            with stage_container.container():
                render_progress_stages()

            st.error(f"크롤링 중 오류가 발생했습니다: {error_msg}")

            # 가능한 해결책 제시
            with st.expander("문제 해결 방법"):
                st.write("""
                **일반적인 문제 해결 방법:**
                1. 네트워크 연결 상태를 확인하세요
                2. 크롤링할 페이지 수를 줄여보세요 (예: 5페이지 이하)
                3. 잠시 후 다시 시도해보세요
                4. 웹사이트가 일시적으로 응답하지 않을 수 있습니다
                5. 브라우저 드라이버 문제일 경우 관리자에게 문의하세요
                """)

    # 결과 표시 영역 (session state에 저장된 결과)
    if st.session_state.show_results and st.session_state.crawling_result:
        data = st.session_state.crawling_result
        stats = st.session_state.crawling_stats

        st.markdown("---")
        st.header("📊 크롤링 결과")

        # 통계 정보
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("수집 건수", f"{stats['total_collected']}건")
        with col2:
            st.metric("크롤링 페이지", f"{stats['target_pages']}페이지")
        with col3:
            st.metric("크롤링 시각", stats['timestamp'].split()[1])

        # 데이터 미리보기
        st.subheader("데이터 미리보기")
        if len(data) > 0:
            # 데이터 샘플을 카드 형태로 표시 (3개만)
            render_data_cards(data)

        # 다운로드 버튼들
        st.subheader("📥 데이터 다운로드")

        col1, col2 = st.columns(2)

        # JSON 파일 생성
        json_data = json.dumps(data, ensure_ascii=False, indent=4)

        # 파일명을 크롤링 타입에 따라 구분
        crawl_type = stats['crawler_type']
        if "관세법령정보포털" in crawl_type:
            filename_base = "customs_rulings"
        elif "국가법령정보센터 내국세" in crawl_type:
            filename_base = "customs_rulings_moleg_tax"
        elif "국가법령정보센터" in crawl_type:
            filename_base = "customs_rulings_moleg"
        elif "품목분류위원회" in crawl_type:
            filename_base = "classification_cases_committee"
        elif "품목분류협의회" in crawl_type:
            filename_base = "classification_cases_consultation"
        elif "미국" in crawl_type:
            filename_base = "classification_cases_us"
        elif "EU" in crawl_type:
            filename_base = "classification_cases_eu"
        elif "일본" in crawl_type:
            filename_base = "classification_cases_jp"
        elif "중국" in crawl_type:
            filename_base = "classification_cases_cn"
        else:
            filename_base = "classification_cases"

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_filename = f"{filename_base}_{timestamp}.json"
        md_filename = f"{filename_base}_{timestamp}.md"

        with col1:
            st.download_button(
                label="📄 JSON 파일 다운로드",
                data=json_data,
                file_name=json_filename,
                mime="application/json",
                use_container_width=True,
                type="primary"
            )

        # 마크다운 파일 생성
        if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            headers = list(data[0].keys())
            md_lines = []
            md_lines.append('| ' + ' | '.join(headers) + ' |')
            md_lines.append('|' + '|'.join(['---'] * len(headers)) + '|')
            for row in data:
                md_lines.append('| ' + ' | '.join(str(row.get(h, '')).replace('|', '\\|').replace('\n', ' ') for h in headers) + ' |')
            md_data = '\n'.join(md_lines)
        else:
            md_data = str(data)

        with col2:
            st.download_button(
                label="📝 마크다운 파일 다운로드",
                data=md_data,
                file_name=md_filename,
                mime="text/markdown",
                use_container_width=True
            )

    # 사용법 안내 (결과가 없을 때만 표시)
    if not st.session_state.show_results:
        st.markdown("---")
        st.header("📖 사용법")
        st.write("""
        1. **크롤링 타입 선택**: 수집할 데이터 유형을 선택합니다.
            - 관세법령정보포털 판례: 관세법령정보포털의 판례 데이터
            - 국가법령정보센터 판례: 국가법령정보센터의 판례 데이터
            - 국가법령정보센터 내국세 판례: 국가법령정보센터의 내국세 판례 데이터
            - 국내품목분류위원회 사례: 품목분류 위원회결정사항 데이터
            - 국내품목분류협의회 사례: 품목분류 협의회결정사항 데이터
            - 품목분류 사례: 품목분류 사례 데이터
            - 미국 품목분류 사례: 미국의 품목분류 사례 데이터
            - EU 품목분류 사례: EU의 품목분류 사례 데이터
            - 일본 품목분류 사례: 일본의 품목분류 사례 데이터
            - 중국 품목분류 사례: 중국의 품목분류 사례 데이터
        2. **크롤링 범위 설정**: 페이지 수 또는 목표 건수를 선택합니다.
        3. **검색어 입력**: 필요한 경우 검색어를 입력합니다.
        4. **크롤링 시작**: 버튼을 클릭하여 데이터 수집을 시작합니다.
        5. **실시간 모니터링**: 진행 상황과 로그를 실시간으로 확인합니다.
        6. **다운로드**: 크롤링 완료 후 JSON 파일과 마크다운 파일을 다운로드할 수 있습니다.
        """)

        st.header("⚠️ 주의사항")
        st.warning("""
        - 크롤링 시간은 페이지 수와 네트워크 상황에 따라 달라질 수 있습니다.
        - 너무 많은 페이지를 한 번에 크롤링하면 시간이 오래 걸릴 수 있습니다.
        - 웹사이트의 정책을 준수하여 적절한 간격으로 크롤링하세요.
        - 국내품목분류 사례 크롤링 시 검색 시작일을 적절히 설정하세요.
        - 크롤링 중에는 페이지를 새로고침하지 마세요.
        """)

if __name__ == "__main__":
    main()
