###############
# 국가법령정보센터 판례 크롤러
###############

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import json
from datetime import datetime

class LawPortalCrawler:
    def __init__(self):
        """크롤러 초기화"""
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Selenium WebDriver 설정 (Streamlit Cloud 호환)"""
        options = Options()
        
        # 기존 옵션 유지
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Streamlit Cloud에서 필요한 추가 옵션들
        options.add_argument('--headless')  # GUI 없이 실행 (필수)
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        
        # ChromeDriver 설정 (Streamlit Cloud 호환)
        try:
            # 시스템에 설치된 chromium-driver 사용 시도
            service = Service('/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=options)
        except:
            try:
                # webdriver-manager를 사용하지 않고 직접 시도
                self.driver = webdriver.Chrome(options=options)
            except:
                try:
                    # 마지막 시도: webdriver-manager 사용 (로컬 환경용)
                    from webdriver_manager.chrome import ChromeDriverManager
                    self.driver = webdriver.Chrome(
                        service=Service(ChromeDriverManager().install()), 
                        options=options
                    )
                except Exception as e:
                    print(f"Chrome 드라이버 설정 실패: {e}")
                    raise e

        self.wait = WebDriverWait(self.driver, 10)
        
    def navigate_to_precedents_page(self, search_keyword="관세", items_per_page=50, navigation_callback=None):
        """국가법령정보센터 > 판례·해석례등 페이지로 이동 및 검색"""
        # 1. 사이트 접속
        if navigation_callback:
            navigation_callback("사이트 접속", "running")
        self.driver.get("https://www.law.go.kr/LSW/main.html")
        time.sleep(2)
        print("홈페이지 접속 완료")
        if navigation_callback:
            navigation_callback("사이트 접속", "completed")
        
        # 2. "판례,해석례등" 메뉴 클릭
        if navigation_callback:
            navigation_callback("판례·해석례등 메뉴 탐색", "running")
        try:
            precedents_menu = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '판례·해석례등')]"))
            )
            precedents_menu.click()
            print("판례,해석례등 메뉴 클릭 완료")
        except TimeoutException:
            # XPath가 작동하지 않을 경우 대체 방법 시도
            try:
                self.driver.execute_script("javascript:goLinkUrl('/precSc.do?menuId=7&subMenuId=47&tabMenuId=213&eventGubun=');saveSearchHistory();")
                print("자바스크립트로 판례,해석례등 메뉴 이동 완료")
            except Exception as e:
                print(f"메뉴 클릭 대체 방법도 실패: {e}")
                # 직접 URL로 이동
                self.driver.get("https://www.law.go.kr/precSc.do?menuId=7&subMenuId=47&tabMenuId=213")
                print("직접 URL로 판례 페이지 이동")

        # 페이지 로딩 대기
        time.sleep(3)
        if navigation_callback:
            navigation_callback("판례·해석례등 메뉴 탐색", "completed")
        
        # 3. 검색어 입력
        if navigation_callback:
            navigation_callback(f"검색어 입력 ('{search_keyword}')", "running")
        try:
            search_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="sr_area"]/div/div/input'))
            )
        except TimeoutException:
            # 대체 검색창 XPath 시도
            search_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'][title='검색어 입력']"))
            )

        search_input.clear()
        search_input.send_keys(search_keyword)
        print(f"검색어 '{search_keyword}' 입력 완료")
        if navigation_callback:
            navigation_callback(f"검색어 입력 ('{search_keyword}')", "completed")

        # 4. 엔터키 입력으로 검색 실행
        if navigation_callback:
            navigation_callback("검색 실행", "running")
        search_input.send_keys(Keys.RETURN)
        print("엔터키 입력으로 검색 실행")

        # 5. 검색 결과 로딩 대기
        time.sleep(5)
        if navigation_callback:
            navigation_callback("검색 실행", "completed")

        # 6. 페이지당 표시 개수 설정
        if navigation_callback:
            navigation_callback(f"검색 옵션 설정 ({items_per_page}개씩 보기)", "running")
        try:
            dropdown = self.wait.until(
                EC.presence_of_element_located((By.NAME, 'sunbun'))
            )
            select = Select(dropdown)
            select.select_by_value(str(items_per_page))
            print(f"{items_per_page}개씩 보기 설정 완료")
            time.sleep(2)
            if navigation_callback:
                navigation_callback(f"검색 옵션 설정 ({items_per_page}개씩 보기)", "completed")
        except Exception as e:
            print(f"페이지당 표시 개수 설정 실패: {e}")
            if navigation_callback:
                navigation_callback(f"검색 옵션 설정 ({items_per_page}개씩 보기)", "completed")
        
    def get_hidden_case_content(self, title_element):
        """숨겨진 판례 내용 가져오기"""
        try:
            # 현재 스크롤 위치 저장
            current_scroll_position = self.driver.execute_script("return window.pageYOffset;")
            
            # 링크 클릭하여 판례 로드
            title_element.click()
            print(f"판례 링크 클릭: {title_element.text[:30]}...")
            
            # 판례 컨텐츠가 로드될 때까지 대기
            hidden_case = self.wait.until(
                EC.presence_of_element_located((By.ID, "viewwrapCenter"))
            )
            
            # 판례 내용 추출
            case_content = hidden_case.text
            
            # 판례 제목 추출
            try:
                case_title = hidden_case.find_element(By.TAG_NAME, "h2").text
            except:
                case_title = "제목 없음"
                
            # 판례 번호 추출
            try:
                case_number = hidden_case.find_element(By.CLASS_NAME, "subtit1").text
            except:
                case_number = "판례번호 없음"
            
            # 원래 위치로 스크롤 복귀
            self.driver.execute_script(f"window.scrollTo(0, {current_scroll_position});")
            
            # "목록영역 늘리기" 버튼 클릭하여 판례 리스트로 돌아가기
            try:
                west_open_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.westOpen[title='펼치기']"))
                )
                west_open_button.click()
                print("목록영역 펼치기 버튼 클릭 완료")
            except Exception as btn_error:
                print(f"목록영역 펼치기 버튼 클릭 실패: {btn_error}")
                # 대안으로 JavaScript 실행 시도
                try:
                    self.driver.execute_script("document.querySelector('div.westOpen').click();")
                    print("JavaScript로 목록영역 펼치기 버튼 클릭 완료")
                except:
                    print("JavaScript로도 목록영역 펼치기 실패")
            
            # 페이지가 다시 로드될 때까지 잠시 대기
            time.sleep(2)
            
            return {
                "제목": case_title,
                "판례번호": case_number,
                "내용": case_content
            }
            
        except Exception as e:
            print(f"판례 내용 추출 중 오류: {e}")
            # 오류 발생 시에도 목록으로 돌아가려고 시도
            try:
                self.driver.find_element(By.CSS_SELECTOR, "div.westOpen[title='펼치기']").click()
            except:
                try:
                    self.driver.execute_script("document.querySelector('div.westOpen').click();")
                except:
                    print("오류 복구 과정에서 목록으로 돌아가기 실패")
            
            return {
                "제목": title_element.text,
                "판례번호": "오류 발생",
                "내용": f"내용 추출 실패: {str(e)}"
            }
        
    def scrape_page_data(self, page_num, max_pages=1, progress_callback=None, base_collected_count=0):
        """특정 페이지의 데이터 스크래핑"""
        page_data = []

        try:
            print(f"\n== {page_num} 페이지 크롤링 시작 ==")

            # 첫 페이지 외에는 movePage() 실행
            if page_num > 1:
                self.driver.execute_script(f"movePage('{page_num}')")
                time.sleep(3)
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#viewHeightDiv table tbody tr"))
                )

            # 테이블 데이터 수집
            try:
                table_rows = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//*[@id='viewHeightDiv']/table/tbody/tr"))
                )
                print(f"총 {len(table_rows)}개의 행 발견")
            except TimeoutException:
                table_rows = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#viewHeightDiv table tbody tr"))
                )
                print(f"대체 선택자로 {len(table_rows)}개의 행 발견")

            # 테이블 데이터 수집 (행 순회)
            # 예상 항목 수 계산 (행 수의 절반, 각 항목이 2행으로 구성)
            estimated_items = len(table_rows) // 2

            i = 0
            item_index = 0
            while i < len(table_rows):
                try:
                    # 제목 행
                    title_row = table_rows[i]

                    # 제목 셀 찾기
                    try:
                        title_cell = title_row.find_element(By.CSS_SELECTOR, "td.s_tit")
                    except NoSuchElementException:
                        title_cells = title_row.find_elements(By.TAG_NAME, "td")
                        if len(title_cells) > 1:
                            title_cell = title_cells[1]
                        else:
                            i += 1
                            continue

                    # 제목 링크 찾기
                    try:
                        title_element = title_cell.find_element(By.TAG_NAME, "a")
                    except NoSuchElementException:
                        i += 1
                        continue

                    title = title_element.text.strip()

                    # URL 추출 및 판례 유형 판단
                    url = ""
                    onclick_attr = title_element.get_attribute("onclick")
                    is_hidden_case = False
                    is_external_case = False

                    if onclick_attr:
                        if "lsEmpViewWideAll" in onclick_attr:
                            is_hidden_case = True
                            try:
                                doc_id = onclick_attr.split("'")[1]
                                url = f"https://www.law.go.kr/precSc.do?tabMenuId=213&eventNo={doc_id}"
                            except IndexError:
                                url = "내부 링크 추출 실패"
                        elif "showExternalLink" in onclick_attr:
                            is_external_case = True
                            print(f"외부 링크 판례 스킵: {title[:50]}...")
                            # 외부 링크 판례는 스킵하고 다음 항목으로 이동
                            i += 2
                            continue
                    elif title_element.get_attribute("href"):
                        # href가 있는 경우도 외부 링크로 간주하여 스킵
                        is_external_case = True
                        print(f"외부 링크 판례 스킵 (href 속성): {title[:50]}...")
                        i += 2
                        continue

                    # 내용 행 추출
                    content = ""
                    if i + 1 < len(table_rows):
                        content_row = table_rows[i + 1]
                        try:
                            content_element = content_row.find_element(By.CSS_SELECTOR, "td.tl p.tx")
                            content = content_element.text.strip()
                        except NoSuchElementException:
                            try:
                                content_cell = content_row.find_element(By.CSS_SELECTOR, "td.tl")
                                content = content_cell.text.strip()
                            except NoSuchElementException:
                                content = "내용 없음"

                    # 순번 추출
                    try:
                        number = title_row.find_element(By.TAG_NAME, "td").text.strip()
                    except NoSuchElementException:
                        number = str(i//2 + 1)

                    # 항목별 진행률 업데이트
                    item_index += 1
                    if progress_callback:
                        progress_callback(page_num, max_pages, item_index, estimated_items, base_collected_count + len(page_data))

                    # 판례의 상세 내용 가져오기 (숨겨진 판례만)
                    case_content = {}

                    if is_hidden_case:
                        print(f"숨겨진 판례 발견: {title}")
                        case_content = self.get_hidden_case_content(title_element)

                    # 데이터 저장
                    item_data = {
                        "순번": number,
                        "제목": title,
                        "내용": content,
                        "URL": url,
                        "판례유형": "숨겨진 판례" if is_hidden_case else "기타"
                    }

                    # 판례 내용이 있는 경우 상세 내용 추가
                    if case_content:
                        item_data["판례번호"] = case_content.get("판례번호", "")
                        item_data["판례전문"] = case_content.get("내용", "")

                    page_data.append(item_data)

                    print(f"항목 {item_index}/{estimated_items} 추출 완료: {title[:30]}...")

                    # 다음 제목 행으로 이동
                    i += 2

                except Exception as row_error:
                    print(f"행 {i} 처리 중 오류: {row_error}")
                    i += 1

        except Exception as e:
            print(f"{page_num}페이지 처리 중 오류 발생: {e}")
            
        return page_data
        
    def crawl_data(self, search_keyword="관세", max_pages=5, progress_callback=None, navigation_callback=None, items_per_page=50):
        """
        메인 크롤링 함수

        Args:
            search_keyword (str): 검색 키워드
            max_pages (int): 크롤링할 최대 페이지 수
            progress_callback (function): 진행률 콜백 함수
            navigation_callback (function): 네비게이션 콜백 함수
            items_per_page (int): 페이지당 표시 개수 (50, 100, 150)

        Returns:
            list: 크롤링된 데이터 리스트
        """
        data = []
        
        try:
            # WebDriver 설정
            self.setup_driver()
            print("WebDriver 설정 완료")

            # 판례 페이지로 이동 및 검색
            self.navigate_to_precedents_page(search_keyword, items_per_page, navigation_callback)
            print(f"'{search_keyword}' 검색 완료")

            # 각 페이지별 크롤링
            for page_num in range(1, max_pages + 1):
                print(f"\n=== 페이지 {page_num}/{max_pages} 처리 중 ===")

                # 진행률 업데이트 (페이지 시작 시)
                if progress_callback:
                    progress_callback(page_num, max_pages, collected_count=len(data))

                # 현재 페이지 데이터 스크래핑 (progress_callback 전달)
                page_data = self.scrape_page_data(page_num, max_pages, progress_callback, len(data))
                data.extend(page_data)

                print(f"페이지 {page_num} 완료: {len(page_data)}건 수집")
            
            # 최종 진행률 업데이트
            if progress_callback:
                progress_callback(max_pages, max_pages, collected_count=len(data))
                
        except Exception as e:
            print(f"크롤링 중 오류 발생: {e}")
            raise e
            
        finally:
            # WebDriver 종료
            if self.driver:
                self.driver.quit()
                print("WebDriver 종료 완료")
        
        # 중복 제거 및 데이터 정리
        if data:
            df_temp = pd.DataFrame(data)
            df_unique = df_temp.drop_duplicates(subset=['제목', 'URL'])
            
            print(f"크롤링 전체 데이터: {len(df_temp)}건")
            print(f"중복 제거 후 데이터: {len(df_unique)}건")
            
            # 중복 제거된 데이터를 딕셔너리 형태로 변환
            unique_data = df_unique.to_dict(orient="records")
            return unique_data
        else:
            print("수집된 데이터가 없습니다.")
            return []

# 독립 실행 시 테스트 코드
if __name__ == "__main__":
    # 테스트 실행
    crawler = LawPortalCrawler()
    
    print("크롤링 시작...")
    data = crawler.crawl_data(search_keyword="관세", max_pages=2)  # 테스트용으로 2페이지만
    
    if data:
        print(f"크롤링 완료! 총 {len(data)}건의 데이터를 수집했습니다.")
        
        # 데이터 저장
        output_file = f"law_portal_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print(f"데이터가 {output_file}에 저장되었습니다.")
        
        # 판례 전문만 따로 저장
        case_contents = [item for item in data if item.get('판례전문')]
        if case_contents:
            case_output_file = f"law_portal_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(case_output_file, "w", encoding="utf-8") as f:
                json.dump(case_contents, f, ensure_ascii=False, indent=4)
            print(f"판례 전문이 {case_output_file}에 저장되었습니다.")
    else:
        print("수집된 데이터가 없습니다.")