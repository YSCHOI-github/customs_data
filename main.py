import streamlit as st
import json
import os
from datetime import datetime
from crawler import CustomsCrawler
from crawler2 import ClassificationCrawler
from crawler3 import ClassificationCrawler3
from crawler4 import ClassificationCrawler4
from crawler_us import ClassificationCrawler_us
from crawler_eu import ClassificationCrawler_eu
from crawler_jp import ClassificationCrawler_jp
from crawler_cn import ClassificationCrawler_cn
from crawler_moleg import LawPortalCrawler
from crawler_moleg_tax import LawPortalCrawler_tax



def main():
    st.title("관세법령정보포털 크롤러")
    st.write("관세법령정보포털에서 판례 및 품목분류 데이터를 크롤링합니다.")
    
    # 사이드바 설정
    st.sidebar.header("크롤링 설정")
    
    # 크롤링 타입 선택
    crawl_type = st.sidebar.selectbox(
        "크롤링 타입 선택",
        ["관세법령정보포털 판례", "국가법령정보센터 판례", "국가법령정보센터 내국세 판례", 
         "국내품목분류위원회 사례", "국내품목분류협의회 사례", "품목분류 사례", 
         "미국 품목분류 사례", "EU 품목분류 사례", "일본 품목분류 사례",  "중국 품목분류 사례"],
        help="크롤링할 데이터 유형을 선택하세요."
    )

    # 검색어 입력 필드
    search_keyword = ""
    if crawl_type == "국가법령정보센터 내국세 판례":
        search_keyword = st.sidebar.text_input(
            "검색어",
            value="부가가치세",
            help="검색할 키워드를 입력하세요."
        )

    # 공통 설정
    max_pages = st.sidebar.number_input(
        "크롤링할 페이지 수",
        min_value=1,
        max_value=50,
        value=8,
        help="크롤링할 페이지 수를 입력하세요 (페이지당 최대 50건)"
    )
    
    # 국내품목분류 사례용 추가 설정
    start_date = None
    if (crawl_type == "국내품목분류위원회 사례" or
        crawl_type == "국내품목분류협의회 사례" or
        crawl_type == "품목분류 사례" or
        crawl_type == "미국 품목분류 사례" or
        crawl_type == "EU 품목분류 사례"
        ):
        start_date = st.sidebar.date_input(
            "검색 시작일",
            value=datetime(2024, 1, 1),
            help="검색 시작일을 선택하세요."
        ).strftime('%Y-%m-%d')
    
    # 예상 크롤링 건수 표시
    st.sidebar.info(f"예상 크롤링 건수: 최대 {max_pages * 50}건")
    
    # 크롤링 시작 버튼
    if st.sidebar.button("크롤링 시작", type="primary"):
        # 진행 상황 표시 컨테이너들
        progress_container = st.container()
        
        with progress_container:
            st.subheader("크롤링 진행 상황")
            progress_bar = st.progress(0)
            status_text = st.empty()
            page_info = st.empty()
            case_info = st.empty()
            collected_info = st.empty()
        
        try:
            # 크롤러 타입에 따라 인스턴스 생성
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

            # 진행 상황 업데이트 함수
            def update_progress(current_page, total_pages, current_case=None, total_cases=None, collected_count=0):
                # 전체 진행률 계산
                if current_case is not None and total_cases is not None and total_cases > 0:
                    # 페이지 내 진행률도 고려
                    page_progress = (current_page - 1) / total_pages
                    case_progress = current_case / total_cases / total_pages
                    total_progress = page_progress + case_progress
                else:
                    total_progress = current_page / total_pages
                
                progress_bar.progress(min(total_progress, 1.0))
                
                # 상태 텍스트 업데이트
                if current_case is not None and total_cases is not None:
                    status_text.text(f"페이지 {current_page}/{total_pages} - 사건 {current_case}/{total_cases} 처리 중...")
                    case_info.text(f"현재 페이지에서 {current_case}/{total_cases}개 사건 처리 완료")
                else:
                    status_text.text(f"페이지 {current_page}/{total_pages} 처리 중...")
                    case_info.text("사건 링크 수집 중...")
                
                page_info.text(f"진행률: {total_progress*100:.1f}% (페이지 {current_page}/{total_pages})")
                collected_info.text(f"수집된 데이터: {collected_count}건")
            
            # 크롤링 실행
            status_text.text(f"{crawler_type_name} 크롤링을 시작합니다...")
            
            # 크롤러 타입에 따라 다른 파라미터로 실행
            if crawl_type == "관세법령정보포털 판례" or crawl_type == "국가법령정보센터 판례":
                data = crawler.crawl_data(
                    max_pages=max_pages,
                    progress_callback=update_progress
                )

            elif crawl_type == "국가법령정보센터 내국세 판례":
                data = crawler.crawl_data(
                    search_keyword=search_keyword,
                    max_pages=max_pages,
                    progress_callback=update_progress
                )
            
            else:  # 국내품목분류협의회 사례, 국내품목분류위원회 사례, 품목분류 사례
                data = crawler.crawl_data(
                    start_date=start_date,
                    max_pages=max_pages,
                    progress_callback=update_progress
                )
            
            if data:
                # 최종 완료 상태 표시
                progress_bar.progress(1.0)
                status_text.text("크롤링 완료!")
                page_info.text(f"완료: {max_pages}개 페이지 처리")
                case_info.text("모든 사건 처리 완료")
                collected_info.text(f"최종 수집된 데이터: {len(data)}건")
                
                # 결과 표시
                st.success(f"{crawler_type_name} 크롤링 완료! 총 {len(data)}건의 데이터를 수집했습니다.")
                
                # 데이터 미리보기
                st.subheader("데이터 미리보기")
                if len(data) > 0:
                    # 첫 번째 데이터의 키들을 보여주기
                    sample_data = data[0]
                    st.write("수집된 데이터 필드:")
                    for key in sample_data.keys():
                        st.write(f"- {key}")
                    
                    # 데이터 테이블 표시 (최대 5개)
                    st.write("데이터 샘플 (최대 5개):")
                    display_data = data[:5] if len(data) > 5 else data
                    st.json(display_data)
                
                # JSON 파일 생성 및 다운로드 버튼
                json_data = json.dumps(data, ensure_ascii=False, indent=4)
                
                # 파일명을 크롤링 타입에 따라 구분
                if crawl_type == "관세법령정보포털 판례":
                    filename = f"customs_rulings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                elif crawl_type == "국가법령정보센터 판례":
                    filename = f"customs_rulings_moleg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                elif crawl_type == "국가법령정보센터 내국세 판례":
                    filename = f"customs_rulings_moleg_tax_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                elif crawl_type == "국내품목분류위원회 사례":
                    filename = f"classification_cases_committee_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                elif crawl_type == "품목분류 사례":
                    filename = f"classification_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                elif crawl_type == "미국 품목분류 사례":
                    filename = f"classification_cases_us_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                elif crawl_type == "EU 품목분류 사례":
                    filename = f"classification_cases_eu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                elif crawl_type == "일본 품목분류 사례":
                    filename = f"classification_cases_jp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                elif crawl_type == "중국 품목분류 사례":
                    filename = f"classification_cases_cn_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                else: # "국내품목분류협의회 사례"
                    filename = f"classification_cases_consultation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                st.download_button(
                    label="JSON 파일 다운로드",
                    data=json_data,
                    file_name=filename,
                    mime="application/json"
                )
                
                # 마크다운 파일 생성 및 다운로드 버튼
                if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    headers = list(data[0].keys())
                    md_lines = []
                    md_lines.append('| ' + ' | '.join(headers) + ' |')
                    md_lines.append('|' + '|'.join(['---'] * len(headers)) + '|')
                    for row in data:
                        md_lines.append('| ' + ' | '.join(str(row.get(h, '')) for h in headers) + ' |')
                    md_data = '\n'.join(md_lines)
                else:
                    md_data = str(data)
                md_filename = filename.replace('.json', '.md')
                st.download_button(
                    label="마크다운 파일 다운로드",
                    data=md_data,
                    file_name=md_filename,
                    mime="text/markdown"
                )
                
            else:
                status_text.text("크롤링 완료 - 데이터 없음")
                st.warning("수집된 데이터가 없습니다. 검색 조건을 확인해주세요.")
                
        except Exception as e:
            status_text.text("크롤링 중 오류 발생")
            st.error(f"크롤링 중 오류가 발생했습니다: {str(e)}")
            st.write("오류 세부 정보:")
            st.code(str(e))
    
    # 사용법 안내
    st.header("사용법")
    st.write(f"""
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
    2. **검색어 입력**: 필요한 경우 검색어를 입력합니다 (예: "부가가치세").
    3. **크롤링할 페이지 수**: 수집할 페이지 수를 입력합니다 (페이지당 최대 50건).
    4. **추가 설정**: 국내품목분류 사례의 경우 검색 시작일을 설정할 수 있습니다.
    5. **크롤링 시작**: 버튼을 클릭하여 데이터 수집을 시작합니다.
    6. **다운로드**: 크롤링 완료 후 JSON 파일과 마크다운 파일을 다운로드할 수 있습니다.
    """)
    
    st.header("주의사항")
    st.warning("""
    - 크롤링 시간은 페이지 수와 네트워크 상황에 따라 달라질 수 있습니다.
    - 너무 많은 페이지를 한 번에 크롤링하면 시간이 오래 걸릴 수 있습니다.
    - 웹사이트의 정책을 준수하여 적절한 간격으로 크롤링하세요.
    - 국내품목분류 사례 크롤링 시 검색 시작일을 적절히 설정하세요.
    """)

if __name__ == "__main__":
    main()