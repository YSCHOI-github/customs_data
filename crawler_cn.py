###############
# 품목분류 국내사례 > 품목분류사례 크롤링
###############

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
from datetime import datetime
import pandas as pd
from io import StringIO
import json

class ClassificationCrawler_cn:
    def __init__(self):
        """크롤러 초기화"""
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Selenium WebDriver 설정 (Streamlit Cloud 호환)"""
        options = webdriver.ChromeOptions()
        
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

        # 기존 설정 유지 (헤드리스 모드에서는 maximize_window 제거)
        # self.driver.maximize_window()  # 헤드리스 모드에서는 불필요
        self.wait = WebDriverWait(self.driver, 10)
        
    def navigate_to_classification_page(self, start_date='2024-01-01', navigation_callback=None, items_per_page=10):
        """관세법령정보포털 > 세계HS > 품목분류 외국사례 > 일본 페이지로 이동"""
        if navigation_callback:
            navigation_callback("사이트 접속", "running")
        # 1. 사이트 접속
        self.driver.get("https://unipass.customs.go.kr/clip/index.do")
        time.sleep(2)
        if navigation_callback:
            navigation_callback("사이트 접속", "completed")
        
        # 2. "세계HS" 클릭
        world_hs_menu = self.wait.until(
            EC.element_to_be_clickable((By.ID, "TOPMENU_LNK_M_ULS0200000000"))
        )
        world_hs_menu.click()
        print("세계HS 메뉴 클릭 완료")
        time.sleep(2)
        if navigation_callback:
            navigation_callback("사이트 접속", "completed")

        # 3. "품목분류 외국사례" 클릭
        domestic_cases_menu = self.wait.until(
            EC.element_to_be_clickable((By.ID, "LEFTMENU_LNK_M_ULS0807030052"))
        )
        domestic_cases_menu.click()
        print("품목분류 외국사례 메뉴 클릭 완료")
        time.sleep(2)
        if navigation_callback:
            navigation_callback("사이트 접속", "completed")

        # 4. "중국" 클릭
        committee_decisions_menu = self.wait.until(
            EC.element_to_be_clickable((By.ID, "LEFTMENU_LNK_UI-ULS-0203-023S"))
        )
        committee_decisions_menu.click()
        print("중국 메뉴 클릭 완료")
        time.sleep(2)
        if navigation_callback:
            navigation_callback("사이트 접속", "completed")

        # 5. 검색어 입력
        date_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "srchSrwr"))  # 검색어 입력 필드의 ID
        )
        date_input.clear()  # 기존 값 지우기
        date_input.send_keys("품목")  # 품목 입력
        print(f"검색어 입력 완료")
        date_input.send_keys(Keys.RETURN)  # Enter 키 입력
        time.sleep(2)
        if navigation_callback:
            navigation_callback("사이트 접속", "completed")

        # 6. "세로보기" 클릭
        popup_button = self.wait.until(
            EC.presence_of_element_located((By.ID, "VRTC"))  # 버튼의 ID 확인
        )

        # (a) scrollIntoView() 사용
        self.driver.execute_script("arguments[0].scrollIntoView(true);", popup_button)
        time.sleep(1)  # 스크롤 후 대기
        print("팝업보기 버튼 가시 영역에 배치")

        # (b) JavaScript로 클릭 강제 실행
        self.driver.execute_script("arguments[0].click();", popup_button)
        print("팝업보기 버튼 클릭 완료")
        time.sleep(2)
        if navigation_callback:
            navigation_callback("사이트 접속", "completed")
        
        # 7. "n개 보기" 설정
        dropdown = self.driver.find_element(By.NAME, 'pagePerRecord')
        select = Select(dropdown)
        select.select_by_value(str(items_per_page))
        self.driver.implicitly_wait(2)
        print(f"{items_per_page}개 보기 설정 완료")
        
    def get_case_links(self):
        """현재 페이지의 모든 사건별 세부정보 링크 수집"""
        # 스크롤 내리기 (JavaScript로 페이지 맨 아래까지)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # 팝업 링크들 찾기
        popup_link_wait = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.dtlInfo.org")) # td.ellipsis.hlzone2
        )

        links = self.driver.find_elements(By.CSS_SELECTOR, "a.dtlInfo.org")  # td.ellipsis.hlzone2
        print(f"Found {len(links)} links to process.")
        return links
        
    
    def scrape_case_detail(self, popup_link, case_index, total_cases):
        """세로보기로 변경"""
        
        try:
            # Scroll to the link and click
            self.driver.execute_script("arguments[0].scrollIntoView(true);", popup_link)
            self.driver.execute_script("arguments[0].click();", popup_link)
            # print(f"Clicked link {index + 1}/{link_count}.")
            time.sleep(1)

            popup_link.click()
            print("팝업 링크 클릭 완료")
            time.sleep(1)

            # 테이블이 로드될 때까지 대기
            wait = WebDriverWait(self.driver, 10)
            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.org")))
            
            # 테이블 데이터 추출
            data_temp = {}
            
            # 모든 행(tr) 찾기
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                # 각 행에서 th(헤더)와 td(데이터) 찾기
                th = row.find_element(By.TAG_NAME, "th") if row.find_elements(By.TAG_NAME, "th") else None
                td = row.find_element(By.TAG_NAME, "td") if row.find_elements(By.TAG_NAME, "td") else None
                
                if th and td:
                    # 헤더 텍스트를 키로, 데이터 텍스트를 값으로 저장
                    header = th.text.strip()
                    value = td.text.strip()
                    
                    data_temp[header] = value

            # Display the transformed DataFrame
            print(data_temp)
            print(f"테이블 데이터 크롤링 완료 ({case_index + 1}/{total_cases})")
            
            return data_temp
        except Exception as e:
            print(f"Error scraping case detail for index {case_index}: {e}")
            return None
            

            
    def go_to_next_page(self, page_num):
        """다음 페이지로 이동"""
        try:
            # 스크롤 내리기
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            next_page = self.driver.find_element(By.XPATH, f"//li/a[@href='#{page_num}']")
            next_page.click()
            print(f"페이지 {page_num} 이동 완료")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"Error moving to page {page_num}: {e}")
            return False
            
    def crawl_data(self, start_date='2024-01-01', max_pages=8, progress_callback=None, navigation_callback=None, items_per_page=10):
        """
        메인 크롤링 함수
        
        Args:
            start_date (str): 검색 시작일 (YYYY-MM-DD 형식)
            max_pages (int): 크롤링할 최대 페이지 수
            progress_callback (function): 진행률 콜백 함수
            
        Returns:
            list: 크롤링된 데이터 리스트
        """
        data = []
        
        try:
            # WebDriver 설정
            self.setup_driver()
            print("WebDriver 설정 완료")
            
            # 위원회결정사항 페이지로 이동
            self.navigate_to_classification_page(start_date, navigation_callback, items_per_page)
            print("위원회결정사항 페이지 이동 완료")
            
            # 각 페이지별 크롤링
            for k in range(2, max_pages + 2):  # 2부터 시작 (원본 코드 유지)
                current_page = k - 1
                print(f"\n=== 페이지 {current_page}/{max_pages} 처리 중 ===")
                
                # 현재 페이지의 사건 링크들 수집
                links = self.get_case_links()
                
                # 페이지 시작 시 진행률 업데이트
                if progress_callback:
                    progress_callback(current_page, max_pages, collected_count=len(data))
                
                # 각 사건별 상세 정보 스크래핑
                for j, popup_link in enumerate(links):
                    print(f"Processing case {j + 1}/{len(links)}")
                    
                    # 각 사건 처리 시 진행률 업데이트
                    if progress_callback:
                        progress_callback(current_page, max_pages, j + 1, len(links), len(data))
                    
                    case_data = self.scrape_case_detail(popup_link, j, len(links))
                    if case_data:
                        data.append(case_data)
                
                # 마지막 페이지가 아니면 다음 페이지로 이동
                if current_page < max_pages:
                    success = self.go_to_next_page(k)
                    if not success:
                        print(f"페이지 {k} 이동 실패. 크롤링을 중단합니다.")
                        break
            
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
            df_unique = df_temp.drop_duplicates()
            
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
    crawler = ClassificationCrawler_cn()
    
    # 날짜 설정
    srchStDt = '2024-01-01'
    
    print("크롤링 시작...")
    data = crawler.crawl_data(start_date=srchStDt, max_pages=3)  # 테스트용으로 3페이지만
    
    if data:
        print(f"크롤링 완료! 총 {len(data)}건의 데이터를 수집했습니다.")
        
        # 데이터 저장
        output_file = f"classification_scraped_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print(f"데이터가 {output_file}에 저장되었습니다.")
    else:
        print("수집된 데이터가 없습니다.")