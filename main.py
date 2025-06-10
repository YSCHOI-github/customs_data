import streamlit as st
import json
import os
from datetime import datetime, date
from crawler import CustomsCrawler

def main():
    st.title("관세법령정보포털 판례 크롤러")
    st.write("관세법령정보포털에서 소송 관련 판례 데이터를 크롤링합니다.")
    
    # 사이드바 설정
    st.sidebar.header("크롤링 설정")
    
    # 검색 시작일 입력
    start_date = st.sidebar.date_input(
        "검색 시작일",
        value=date(2024, 1, 1),
        help="크롤링할 데이터의 시작 날짜를 선택하세요"
    )
    
    # 검색 건수 (페이지 수) 입력
    max_pages = st.sidebar.number_input(
        "크롤링할 페이지 수",
        min_value=1,
        max_value=50,
        value=8,
        help="크롤링할 페이지 수를 입력하세요 (페이지당 최대 100건)"
    )
    
    # 예상 크롤링 건수 표시
    st.sidebar.info(f"예상 크롤링 건수: 최대 {max_pages * 100}건")
    
    # 크롤링 시작 버튼
    if st.sidebar.button("크롤링 시작", type="primary"):
        # 진행 상황 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 크롤러 인스턴스 생성
            crawler = CustomsCrawler()
            
            # 크롤링 실행
            status_text.text("크롤링을 시작합니다...")
            data = crawler.crawl_data(
                start_date=start_date.strftime('%Y-%m-%d'),
                max_pages=max_pages,
                progress_callback=lambda current, total: progress_bar.progress(current / total)
            )
            
            if data:
                # 결과 표시
                st.success(f"크롤링 완료! 총 {len(data)}건의 데이터를 수집했습니다.")
                
                # 데이터 미리보기
                st.subheader("데이터 미리보기")
                if len(data) > 0:
                    # 첫 번째 데이터의 키들을 보여주기
                    sample_data = data[0]
                    st.write("수집된 데이터 필드:")
                    for key in sample_data.keys():
                        st.write(f"- {key}")
                    
                    # 데이터 테이블 표시 (최대 10개)
                    st.write("데이터 샘플 (최대 10개):")
                    display_data = data[:10] if len(data) > 10 else data
                    st.json(display_data)
                
                # JSON 파일 생성 및 다운로드 버튼
                json_data = json.dumps(data, ensure_ascii=False, indent=4)
                filename = f"customs_rulings_{start_date.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}.json"
                
                st.download_button(
                    label="JSON 파일 다운로드",
                    data=json_data,
                    file_name=filename,
                    mime="application/json"
                )
                
            else:
                st.warning("수집된 데이터가 없습니다. 검색 조건을 확인해주세요.")
                
        except Exception as e:
            st.error(f"크롤링 중 오류가 발생했습니다: {str(e)}")
            st.write("오류 세부 정보:")
            st.code(str(e))
        
        finally:
            # 진행 상황 초기화
            progress_bar.empty()
            status_text.empty()
    
    # 사용법 안내
    st.header("사용법")
    st.write("""
    1. **검색 시작일**: 크롤링할 데이터의 시작 날짜를 선택합니다.
    2. **크롤링할 페이지 수**: 수집할 페이지 수를 입력합니다 (페이지당 최대 100건).
    3. **크롤링 시작**: 버튼을 클릭하여 데이터 수집을 시작합니다.
    4. **다운로드**: 크롤링 완료 후 JSON 파일을 다운로드할 수 있습니다.
    """)
    
    st.header("주의사항")
    st.warning("""
    - 크롤링 시간은 페이지 수와 네트워크 상황에 따라 달라질 수 있습니다.
    - 너무 많은 페이지를 한 번에 크롤링하면 시간이 오래 걸릴 수 있습니다.
    - 웹사이트의 정책을 준수하여 적절한 간격으로 크롤링하세요.
    """)

if __name__ == "__main__":
    main()