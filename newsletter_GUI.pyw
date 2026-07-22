import json
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import base64
import tkinter.messagebox as msgbox
import datetime
from datetime import timedelta
import threading
import time
import os
import requests
import ssl
import pyperclip
from bs4 import BeautifulSoup
from holidays.countries.south_korea import SouthKorea

import sys
import os

def resource_path(relative_path):
    """PyInstaller 임시폴더와 일반 실행 환경의 경로를 모두 호환하도록 지원"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 임시 폴더 경로
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 2번째 파일을 모듈로 가져옵니다.
import newsletter_mail_with_AI


class AutomationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IT전략팀 뉴스레터 HTML 생성 전용 APP")
        self.root.geometry("520x520") # 구분선 추가로 높이 약간 증가
        
        # --- 색상 설정 (라이트 테마) ---
        self.colors = {
            'bg': '#FFFFFF',           # 메인 배경
            'fg': '#333333',           # 기본 글자색
            'header_bg': '#EBECEF',    # 포인트 배경 (헤더/경고문구)
            'entry_bg': '#FFFFFF',     # 입력창 배경
            'entry_fg': '#000000',     # 입력창 글자
            'btn_bg': '#3C5493',       # 메인 버튼 (네이비)
            'btn_fg': '#FFFFFF',       # 버튼 글자
            'log_bg': '#F9F9F9',       # 로그창 배경
            'log_fg': '#333333',       # 로그 글자
            'status_fg': '#01579B',    # 상태바 강조 글자
            'sub_btn_bg': '#777777',   # 보조 버튼
            'warning_text': '#555555'  # 경고 문구 글자색
        }
        
        self.root.configure(bg=self.colors['bg'])
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 체크박스 스타일 커스텀
        self.style.configure("Light.TCheckbutton", 
                             background=self.colors['bg'], 
                             foreground=self.colors['fg'],
                             font=("Malgun Gothic", 10))

        self.log_history = []
        self.final_html_result = None
        self.html_file_path = ""
        
        self._init_ui()
        
        # 드라이버 경로 설정
        self.load_config()

    # --- 설정 파일 저장/불러오기 기능 ---
    def load_config(self):
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # 1. 드라이버 경로 불러오기
                if config.get("driver_path"):
                    self.entry_driver.config(state='normal')
                    self.entry_driver.delete(0, tk.END)
                    self.entry_driver.insert(0, config["driver_path"])
                    self.entry_driver.config(state='readonly')
                
                # 2. 사원번호 불러오기
                if config.get("emp_no"):
                    self.entry_emp_no.delete(0, tk.END)
                    self.entry_emp_no.insert(0, config["emp_no"])

                # 3. 비밀번호 불러오기 (보안 주의)
                if config.get("user_pw"):
                    self.entry_pw.delete(0, tk.END)
                    self.entry_pw.insert(0, config["user_pw"])

                # 4. VDI 여부 불러오기
                if config.get("is_vdi"):
                    self.vdi_var.set(config["is_vdi"])
                    
                self.add_log("이전 설정값을 불러왔습니다.")
            except Exception as e:
                self.add_log(f"설정 파일 로드 실패: {e}")

    def save_config(self):
        config = {
            "driver_path": self.entry_driver.get(),
            "emp_no": self.entry_emp_no.get(),
            "user_pw": self.entry_pw.get(),
            "is_vdi": self.vdi_var.get()
        }
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            # self.add_log("설정값이 저장되었습니다.") # 로그가 너무 많으면 생략 가능
        except Exception as e:
            self.add_log(f"설정 파일 저장 실패: {e}")

    def _init_ui(self):
        # 1. 상단 경고 문구 및 헤더 영역
        header_frame = tk.Frame(self.root, bg=self.colors['header_bg'], height=100)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        # 문구 1
        tk.Label(header_frame, text="※  IT전략팀의 뉴스레터 HTML 생성 전용 프로그램 입니다.", 
                 font=("Malgun Gothic", 11, "bold"), 
                 bg=self.colors['header_bg'], fg="#333333").pack(pady=(20, 5))
        
        # 문구 2
        tk.Label(header_frame, text="담당자 외 무단 사용을 금합니다.", 
                 font=("Malgun Gothic", 10), 
                 bg=self.colors['header_bg'], fg=self.colors['warning_text']).pack()

        # 2. 입력 폼 프레임
        form_frame = tk.Frame(self.root, bg=self.colors['bg'])
        form_frame.pack(fill='x', padx=40, pady=20)

        # 공통 Label 스타일
        lbl_opts = {'bg': self.colors['bg'], 'fg': self.colors['status_fg'], 'font': ("Malgun Gothic", 10, "bold")}

        # [Step 1] 드라이버 설정 (가장 위로 이동)
        tk.Label(form_frame, text="Edge 드라이버 :", **lbl_opts, anchor='w').grid(row=0, column=0, sticky='w', pady=5)
        
        driver_frame = tk.Frame(form_frame, bg=self.colors['bg'])
        driver_frame.grid(row=0, column=1, sticky='ew', padx=10, pady=5)
        
        # 읽기 전용(readonly)으로 설정하여 직접 입력 방지
        self.entry_driver = tk.Entry(driver_frame, bg="#F0F0F0", fg=self.colors['entry_fg'], 
                                    insertbackground='black', relief="solid", bd=1, state="readonly")
        self.entry_driver.pack(side='left', fill='x', expand=True)
        
        btn_browse = tk.Button(driver_frame, text="...", command=self.browse_file,
                               bg=self.colors['sub_btn_bg'], fg='white', width=3, relief='flat')
        btn_browse.pack(side='right', padx=(5, 0))

        # [구분선 추가]
        sep = ttk.Separator(form_frame, orient='horizontal')
        sep.grid(row=1, column=0, columnspan=2, sticky='ew', pady=15)

        # [Step 2] 사용자 정보 입력
        # [사원번호 입력] (Row 2)
        tk.Label(form_frame, text="사원번호 :", **lbl_opts, anchor='w').grid(row=2, column=0, sticky='w', pady=5)
        self.entry_emp_no = tk.Entry(form_frame, bg=self.colors['entry_bg'], fg=self.colors['entry_fg'], 
                                insertbackground='black', relief="solid", bd=1)
        self.entry_emp_no.grid(row=2, column=1, sticky='ew', padx=10, pady=5)

        # [비밀번호 입력] (Row 3)
        tk.Label(form_frame, text="비밀번호 :", **lbl_opts, anchor='w').grid(row=3, column=0, sticky='w', pady=5)
        self.entry_pw = tk.Entry(form_frame, show="*", bg=self.colors['entry_bg'], fg=self.colors['entry_fg'], 
                                insertbackground='black', relief="solid", bd=1)
        self.entry_pw.grid(row=3, column=1, sticky='ew', padx=10, pady=5)

        form_frame.columnconfigure(1, weight=1)
        
        # [VDI 여부 라디오버튼] (Row 4)
        self.vdi_var = tk.StringVar(value="Y")
        # 라벨 ("VDI 인터넷PC 여부 :")
        tk.Label(form_frame, text="VDI 인터넷PC 여부 :", **lbl_opts, anchor="w").grid(row=4, column=0, sticky='w', pady=5)
        radio_frame = tk.Frame(form_frame, bg='white')
        radio_frame.grid(row=4, column=1, sticky='ew', pady=5)
        # 라디오 버튼 (Y)
        self.rb_y = tk.Radiobutton(radio_frame, text="Y", font=("Malgun Gothic", 10), bg=self.colors['entry_bg'], fg=self.colors['entry_fg'],
                                   variable=self.vdi_var, value="Y", anchor="w")
        self.rb_y.pack(side='left', padx=(0, 40))
        # 라디오 버튼 (N)
        self.rb_n = tk.Radiobutton(radio_frame, text="N", font=("Malgun Gothic", 10), bg=self.colors['entry_bg'], fg=self.colors['entry_fg'],
                                   variable=self.vdi_var, value="N", anchor="w")
        self.rb_n.pack(side='left')

        # 3. 버튼 영역
        btn_frame = tk.Frame(self.root, bg=self.colors['bg'])
        btn_frame.pack(fill='x', padx=40, pady=10)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        self.btn_start = tk.Button(btn_frame, text="START", command=self.start_process,
                                   bg=self.colors['btn_bg'], fg=self.colors['btn_fg'], 
                                   font=("Malgun Gothic", 10, "bold"), height=2, relief='flat',
                                   activebackground='#2A3F75', activeforeground='white')
        self.btn_start.grid(row=0, column=0, sticky='ew', padx=(0, 5))

        self.btn_view_log = tk.Button(btn_frame, text="로그보기", command=self.open_log_window,
                                      bg=self.colors['sub_btn_bg'], fg='white', 
                                      font=("Malgun Gothic", 10), height=2, relief='flat')
        self.btn_view_log.grid(row=0, column=1, sticky='ew', padx=(5, 0))

        # 4. 하단 상태바 (배경색 헤더와 통일)
        status_frame = tk.LabelFrame(self.root, text="현재 상태", 
                                   bg=self.colors['bg'], fg=self.colors['fg'], 
                                   font=("Malgun Gothic", 9))
        status_frame.pack(fill='x', side='bottom', padx=40, pady=(0, 30))
        
        self.status_label = tk.Label(status_frame, text=" 대기 중...", anchor='w', 
                                   bg=self.colors['header_bg'], fg="#FF0000",
                                   font=("Malgun Gothic", 10, "bold"), height=2)
        self.status_label.pack(fill='x', padx=1, pady=1)

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Edge 드라이버 선택",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.entry_driver.config(state='normal') # 입력 가능하게 잠시 변경
            self.entry_driver.delete(0, tk.END)
            self.entry_driver.insert(0, filename)
            self.entry_driver.config(state='readonly') # 다시 읽기 전용으로 변경
            self.add_log(f"드라이버 경로 설정됨: {filename}")

    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.log_history.append(log_msg)
        
        display_msg = message if len(message) < 50 else message[:47] + "..."
        # 상태바 업데이트 (일반 로그 색상 적용)
        self.status_label.config(text=f" {display_msg}", fg=self.colors['fg'])
        
        self.root.update()

    def open_log_window(self):
        log_window = tk.Toplevel(self.root)
        log_window.title("전체 로그 기록")
        log_window.geometry("600x400")
        log_window.configure(bg=self.colors['bg'])

        log_text = scrolledtext.ScrolledText(log_window, width=70, height=20, 
                                           bg=self.colors['log_bg'], fg=self.colors['log_fg'],
                                           font=("Consolas", 10))
        log_text.pack(fill='both', expand=True, padx=10, pady=10)

        for log in self.log_history:
            log_text.insert(tk.END, log + "\n")
        
        log_text.see(tk.END)
        log_text.config(state='disabled')
        
        btn_close = tk.Button(log_window, text="닫기", command=log_window.destroy,
                              bg=self.colors['sub_btn_bg'], fg='white', relief='flat')
        btn_close.pack(pady=5)

    def start_process(self):
        # 시작 버튼 클릭 시 입력값 검증
        emp_no = self.entry_emp_no.get() # 사원번호
        user_pw = self.entry_pw.get()    # PW
        driver_path = self.entry_driver.get()

        # [필수] 모든 필드가 채워져야 함
        if not driver_path:
            msgbox.showwarning("입력 오류", "Edge 드라이버 경로를 설정해주세요.")
            return

        if not emp_no:
            msgbox.showwarning("입력 오류", "사원번호를 입력해주세요.")
            self.entry_emp_no.focus()
            return
        
        if not user_pw:
            msgbox.showwarning("입력 오류", "비밀번호를 입력해주세요.")
            self.entry_pw.focus()
            return
        
        self.save_config()
        
        # 2번째 파일에 드라이버 경로 설정 전달
        newsletter_mail_with_AI.driver_path = driver_path

        # 스레드 시작 (사원번호, ID, PW 전달)
        t = threading.Thread(target=self.run_process, args=(emp_no, user_pw))
        t.daemon = True
        t.start()

    # 이미지 파일을 Base64 문자열로 변환하는 함수
    def image_to_base64(self, filepath):
        try:
            if os.path.exists(filepath):
                with open(filepath, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    return f"data:image/png;base64,{encoded_string}"
            else:
                self.add_log(f"이미지 누락: {filepath}")
                return ""
        except Exception as e:
            self.add_log(f"이미지 변환 실패: {e}")
            return ""

    # --- 실제 작업 로직 ---
    def run_process(self, emp_no, user_pw):
        self.btn_start.config(state="disabled", bg="#999999") 
        try:
            # 1단계: HTML 생성 (newsletter_main 호출 시 사원번호 전달)
            self.newsletter_main(emp_no)
            
            self.open_result_file()
            time.sleep(1)
            
            # 2단계: 자동 발송 프로세스 (ID, PW로 로그인)
            if self.final_html_result:
                self.add_log("자동 발송 프로세스 시작...")
                time.sleep(1)
                
                newsletter_mail_with_AI.main(
                    self.final_html_result,
                    emp_no,
                    user_pw,
                    self.add_log
                )
                
                self.add_log("모든 작업이 완료되었습니다.")
                time.sleep(1)
                
        except Exception as e:
            self.add_log(f"오류 발생: {str(e)}")
            msgbox.showerror("오류", f"작업 중 오류가 발생했습니다:\n{e}")
        
        finally:
            self.btn_start.config(state="normal", bg=self.colors['btn_bg'])

    def open_result_file(self):
        self.add_log(f"결과 파일 실행: {self.html_file_path}")
        try:
            if os.path.exists(self.html_file_path):
                os.startfile(self.html_file_path)
            else:
                self.add_log("생성된 파일을 찾을 수 없습니다.")
        except Exception as e:
            self.add_log(f"파일 열기 실패: {e}")

    def newsletter_main(self, emp_no):
        # [기존 크롤링 및 HTML 생성 로직 유지]
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            news_num = 5
            now = datetime.datetime.now()
            
            establish_date = now.strftime('%Y.%m.%d')
            date_str = now.strftime('%Y-%m-%d_%H시%M분')
            self.add_log("날짜 및 공휴일 계산 중...")

            # [공휴일 및 날짜 계산 로직]
            kr_holidays = SouthKorea()
            
            # 시작일 어제부터 확인
            check_date = now - timedelta(days=1)
            while check_date.weekday() >= 5 or check_date.strftime('%Y-%m-%d') in kr_holidays:
                check_date -= timedelta(days=1)
            
            # 데이터 수집일 계산
            days_diff = (now - check_date).days
            
            # 기본 초기화
            ds_val = ''
            de_val = ''
            nso_val = ''
            period = ''
            
            if days_diff > 1:
                # 1일 이상 차이날 경우
                period = '3' 
                ds_val = check_date.strftime('%Y.%m.%d')
                de_val = now.strftime('%Y.%m.%d')
                nso_val = f'from{check_date.strftime("%Y%m%d")}to{now.strftime("%Y%m%d")}'
                self.add_log(f"연휴/주말 포함 검색: {ds_val} ~ {de_val} ({days_diff+1}일간)")
            else:
                period = '4'
                nso_val = '1d'
                self.add_log("일반 평일 검색 (1일간)")

            #증권사 +서비스 +도입 -who -칼럼 -전산장애
            news_url1 = f'https://search.naver.com/search.naver?ssc=tab.news.all&query=%EC%A6%9D%EA%B6%8C%EC%82%AC%20%2B%EC%84%9C%EB%B9%84%EC%8A%A4%20%2B%EB%8F%84%EC%9E%85%20-who%20-%EC%8B%A4%EC%A0%81%20-%EC%B9%BC%EB%9F%BC%20-%EC%A0%84%EC%82%B0%EC%9E%A5%EC%95%A0&sm=tab_opt&sort=0&photo=0&field=0&pd={period}&ds={ds_val}&de={de_val}&docid=&qdt=1&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Ar%2Cp%3A{nso_val}&is_sug_officeid=0&office_category=0&service_area=0'
            #증권사 +장애 +오류 -who -장애인
            news_url2 = f'https://search.naver.com/search.naver?ssc=tab.news.all&query=%EC%A6%9D%EA%B6%8C%EC%82%AC%20%2B%EC%9E%A5%EC%95%A0%20%2B%EC%98%A4%EB%A5%98%20-who%20-%EC%9E%A5%EC%95%A0%EC%9D%B8&sm=tab_opt&sort=0&photo=0&field=0&pd={period}&ds={ds_val}&de={de_val}&docid=&qdt=1&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Ar%2Cp%3A{nso_val}&is_sug_officeid=0&office_category=0&service_area=0'
            # 유안타증권 -출간 -연구원 -섹터 -추천주 -애널리스트 -ELS -임원
            news_url3 = f'https://search.naver.com/search.naver?ssc=tab.news.all&query=%EC%9C%A0%EC%95%88%ED%83%80%EC%A6%9D%EA%B6%8C%20-%EC%B6%9C%EA%B0%84%20-%EC%97%B0%EA%B5%AC%EC%9B%90%20-%EC%84%B9%ED%84%B0%20-%EC%B6%94%EC%B2%9C%EC%A3%BC%20-%EC%95%A0%EB%84%90%EB%A6%AC%EC%8A%A4%ED%8A%B8%20-ELS%20-%EC%9E%84%EC%9B%90&sm=tab_opt&sort=0&photo=0&field=0&pd={period}&ds={ds_val}&de={de_val}&docid=&qdt=1&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Ar%2Cp%3A{nso_val}&is_sug_officeid=0&office_category=0&service_area=0'
            #증권사 +클라우드 -맥주 -전산장애 -코스피
            news_url4 = f'https://search.naver.com/search.naver?ssc=tab.news.all&query=%EC%A6%9D%EA%B6%8C%EC%82%AC%20%2B%ED%81%B4%EB%9D%BC%EC%9A%B0%EB%93%9C%20-%EB%A7%A5%EC%A3%BC%20-%EC%A0%84%EC%82%B0%EC%9E%A5%EC%95%A0%20-%EC%BD%94%EC%8A%A4%ED%94%BC&sm=tab_opt&sort=0&photo=0&field=0&pd={period}&ds={ds_val}&de={de_val}&docid=&qdt=1&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Ar%2Cp%3A{nso_val}&is_sug_officeid=0&office_category=0&service_area=0'
            #금융 +보안 -who
            news_url5 = f'https://search.naver.com/search.naver?ssc=tab.news.all&query=%EA%B8%88%EC%9C%B5%20%EC%A6%9D%EA%B6%8C%EC%82%AC%20%2B%EB%B3%B4%EC%95%88%20-Who&sm=tab_opt&sort=0&photo=0&field=0&pd={period}&ds={ds_val}&de={de_val}&docid=&qdt=1&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Ar%2Cp%3A{nso_val}&is_sug_officeid=0&office_category=0&service_area=0'
            #증권사 +핀테크 +AI
            news_url6 = f'https://search.naver.com/search.naver?sm=tab_hty.top&where=news&ssc=tab.news.all&query=%EC%A6%9D%EA%B6%8C+%ED%95%80%ED%85%8C%ED%81%AC+AI&oquery=%EC%A6%9D%EA%B6%8C+%2B%ED%95%80%ED%85%8C%ED%81%AC+%2BAI&tqi=jf%2B52dqpsW4ssBbgwqK-092016&ackey=6ewqbv0z&nso=so%3Ar%2Cp%3A{nso_val}'
            #증권사 +금감원
            news_url7 = f'https://search.naver.com/search.naver?ssc=tab.news.all&query=%EC%A6%9D%EA%B6%8C%EC%82%AC%20%2B%EA%B8%88%EA%B0%90%EC%9B%90&sm=tab_opt&sort=0&photo=0&field=0&pd={period}&ds={ds_val}&de={de_val}&docid=&qdt=1&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Ar%2Cp%3A{nso_val}&is_sug_officeid=0&office_category=0&service_area=0'
            # 노란봉투법
            news_url8 = f'https://search.naver.com/search.naver?ssc=tab.news.all&query=%EB%85%B8%EB%9E%80%EB%B4%89%ED%88%AC%EB%B2%95&sm=tab_opt&sort=0&photo=0&field=0&pd={period}&ds={ds_val}&de={de_val}&docid=&qdt=1&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Ar%2Cp%3A{nso_val}&is_sug_officeid=0&office_category=0&service_area=0'

            ssl._create_default_https_context = ssl._create_unverified_context

            news_dict = []

            idx_item = 0
            while idx_item < 8:

                category_names = ["증권사 서비스 도입", "전산장애/오류", "유안타증권", "클라우드", "금융 보안", "핀테크/AI", "금융감독원", "노란봉투법"]
                self.add_log(f"진행 중... ({idx_item+1}/8) {category_names[idx_item]} 검색")
                
                if idx_item == 0:
                    req = requests.get(news_url1, headers=headers, verify=False)
                elif idx_item == 1:
                    req = requests.get(news_url2, headers=headers, verify=False)
                elif idx_item == 2:
                    req = requests.get(news_url3, headers=headers, verify=False)
                elif idx_item == 3:
                    req = requests.get(news_url4, headers=headers, verify=False)
                elif idx_item == 4:
                    req = requests.get(news_url5, headers=headers, verify=False)
                elif idx_item == 5:
                    req = requests.get(news_url6, headers=headers, verify=False)
                elif idx_item == 6:
                    req = requests.get(news_url7, headers=headers, verify=False)
                elif idx_item == 7:
                    req = requests.get(news_url8, headers=headers, verify=False)
                
                req.raise_for_status()
                soup = BeautifulSoup(req.text, 'html.parser')
                
                table = soup.find('ul',{'class' : 'list_news'})
                # 검색된 기사가 존재할 시 추출 시작
                if table is not None:                    
                    headline_spans = soup.select('span.sds-comps-text-type-headline1')

                    if idx_item == 0:
                        for n in headline_spans:
                            news_group = 'item1'
                            a_tag = n.find_parent('a', href=True)
                            news_title = n.get_text()
                            news_URL = a_tag['href']
                            
                            # 기사 전체 블럭 탐색 (최상위 부모)
                            outer_block = n
                            for _ in range(10):  # 최대 10단계까지 위로 탐색
                                outer_block = outer_block.parent
                                if outer_block is None:
                                    break
                                if outer_block.select_one('div.sds-comps-profile-source'):
                                    break

                            if outer_block is None:
                                continue
                            
                           # 언론사 이름
                            press_name_tag = outer_block.select_one('span.sds-comps-text-weight-sm span')
                            press_name = press_name_tag.get_text() if press_name_tag else None

                            # 언론사 이미지
                            press_img_tag = outer_block.select_one('div.sds-comps-image-circle img')
                            press_img_URL = press_img_tag.get('src') if press_img_tag else None

                            # 게시 시간
                            time_tag = outer_block.select_one('span.sds-comps-profile-info-subtext span')
                            news_before = time_tag.get_text(strip=True) if time_tag else None
                            
                            # "전"이 포함되지 않았다면, 한 번 더 시도
                            if '전' not in news_before:
                                second_time_tag = outer_block.select('span.sds-comps-profile-info-subtext span')
                                if len(second_time_tag) > 1:
                                    news_before = second_time_tag[1].get_text().strip()
                                else:
                                    news_before = ''

                            # 여전히 "전"이 없으면 공백으로 설정
                            if '전' not in news_before:
                                news_before = ''
                            
                            # 뉴스 내용
                            summary_tag = outer_block.select_one('span.sds-comps-text-type-body1')
                            news_contents = summary_tag.get_text() if summary_tag else None
    
                            news_dict.append({'news_group': news_group, 'news_title': news_title, 'news_URL': news_URL, 'press_img_URL': press_img_URL, 'press_name': press_name, 'news_before': news_before, 'news_contents': news_contents})
                            
                            # 중복 기사 입력 방지
                            if len(news_dict)-1 > 0:
                                l = 0
                                for t in news_dict:
                                    l += 1
                                    if l < len(news_dict)-1 and (news_title == t['news_title'] or news_URL == t['news_URL']):
                                        del news_dict[len(news_dict)-1]
                        
                            count_item1 = sum(1 for item in news_dict if item['news_group'] == 'item1')
                            if count_item1 >= news_num:
                                break
                        
                    elif idx_item == 1:
                        for n in headline_spans:
                            news_group = 'item2'
                            a_tag = n.find_parent('a', href=True)
                            news_title = n.get_text()
                            news_URL = a_tag['href']
                            
                            # 기사 전체 블럭 탐색 (최상위 부모)
                            outer_block = n
                            for _ in range(10):  # 최대 10단계까지 위로 탐색
                                outer_block = outer_block.parent
                                if outer_block is None:
                                    break
                                if outer_block.select_one('div.sds-comps-profile-source'):
                                    break

                            if outer_block is None:
                                continue
                            
                           # 언론사 이름
                            press_name_tag = outer_block.select_one('span.sds-comps-text-weight-sm span')
                            press_name = press_name_tag.get_text() if press_name_tag else None

                            # 언론사 이미지
                            press_img_tag = outer_block.select_one('div.sds-comps-image-circle img')
                            press_img_URL = press_img_tag.get('src') if press_img_tag else None

                            # 게시 시간
                            time_tag = outer_block.select_one('span.sds-comps-profile-info-subtext span')
                            news_before = time_tag.get_text(strip=True) if time_tag else None
                            
                            # "전"이 포함되지 않았다면, 한 번 더 시도
                            if '전' not in news_before:
                                second_time_tag = outer_block.select('span.sds-comps-profile-info-subtext span')
                                if len(second_time_tag) > 1:
                                    news_before = second_time_tag[1].get_text().strip()
                                else:
                                    news_before = ''

                            # 여전히 "전"이 없으면 공백으로 설정
                            if '전' not in news_before:
                                news_before = ''
                            
                            # 뉴스 내용
                            summary_tag = outer_block.select_one('span.sds-comps-text-type-body1')
                            news_contents = summary_tag.get_text() if summary_tag else None
                                    
                            news_dict.append({'news_group': news_group, 'news_title': news_title, 'news_URL': news_URL, 'press_img_URL': press_img_URL, 'press_name': press_name, 'news_before': news_before, 'news_contents': news_contents})
                            
                            # 중복 기사 입력 방지
                            if len(news_dict)-1 > 0:
                                l = 0
                                for t in news_dict:
                                    l += 1
                                    if l < len(news_dict)-1 and (news_title == t['news_title'] or news_URL == t['news_URL']):
                                        del news_dict[len(news_dict)-1]
                            
                            count_item2 = sum(1 for item in news_dict if item['news_group'] == 'item2')
                            if count_item2 >= news_num:
                                break
                                        
                    elif idx_item == 2:
                        for n in headline_spans:
                            news_group = 'item3'
                            a_tag = n.find_parent('a', href=True)
                            news_title = n.get_text()
                            news_URL = a_tag['href']
                            
                            # 기사 전체 블럭 탐색 (최상위 부모)
                            outer_block = n
                            for _ in range(10):  # 최대 10단계까지 위로 탐색
                                outer_block = outer_block.parent
                                if outer_block is None:
                                    break
                                if outer_block.select_one('div.sds-comps-profile-source'):
                                    break

                            if outer_block is None:
                                continue
                            
                           # 언론사 이름
                            press_name_tag = outer_block.select_one('span.sds-comps-text-weight-sm span')
                            press_name = press_name_tag.get_text() if press_name_tag else None

                            # 언론사 이미지
                            press_img_tag = outer_block.select_one('div.sds-comps-image-circle img')
                            press_img_URL = press_img_tag.get('src') if press_img_tag else None

                            # 게시 시간
                            time_tag = outer_block.select_one('span.sds-comps-profile-info-subtext span')
                            news_before = time_tag.get_text(strip=True) if time_tag else None
                            
                            # "전"이 포함되지 않았다면, 한 번 더 시도
                            if '전' not in news_before:
                                second_time_tag = outer_block.select('span.sds-comps-profile-info-subtext span')
                                if len(second_time_tag) > 1:
                                    news_before = second_time_tag[1].get_text().strip()
                                else:
                                    news_before = ''

                            # 여전히 "전"이 없으면 공백으로 설정
                            if '전' not in news_before:
                                news_before = ''
                            
                            # 뉴스 내용
                            summary_tag = outer_block.select_one('span.sds-comps-text-type-body1')
                            news_contents = summary_tag.get_text() if summary_tag else None
    
                            news_dict.append({'news_group': news_group, 'news_title': news_title, 'news_URL': news_URL, 'press_img_URL': press_img_URL, 'press_name': press_name, 'news_before': news_before, 'news_contents': news_contents})
                            
                            # 중복 기사 입력 방지
                            if len(news_dict)-1 > 0:
                                l = 0
                                for t in news_dict:
                                    l += 1
                                    if l < len(news_dict)-1 and (news_title == t['news_title'] or news_URL == t['news_URL']):
                                        del news_dict[len(news_dict)-1]
                            
                            count_item3 = sum(1 for item in news_dict if item['news_group'] == 'item3')
                            if count_item3 >= news_num:
                                break
                            
                    elif idx_item == 3:
                        for n in headline_spans:
                            news_group = 'item4'
                            a_tag = n.find_parent('a', href=True)
                            news_title = n.get_text()
                            news_URL = a_tag['href']
                            
                            # 기사 전체 블럭 탐색 (최상위 부모)
                            outer_block = n
                            for _ in range(10):  # 최대 10단계까지 위로 탐색
                                outer_block = outer_block.parent
                                if outer_block is None:
                                    break
                                if outer_block.select_one('div.sds-comps-profile-source'):
                                    break

                            if outer_block is None:
                                continue
                            
                           # 언론사 이름
                            press_name_tag = outer_block.select_one('span.sds-comps-text-weight-sm span')
                            press_name = press_name_tag.get_text() if press_name_tag else None

                            # 언론사 이미지
                            press_img_tag = outer_block.select_one('div.sds-comps-image-circle img')
                            press_img_URL = press_img_tag.get('src') if press_img_tag else None

                            # 게시 시간
                            time_tag = outer_block.select_one('span.sds-comps-profile-info-subtext span')
                            news_before = time_tag.get_text(strip=True) if time_tag else None
                            
                            # "전"이 포함되지 않았다면, 한 번 더 시도
                            if '전' not in news_before:
                                second_time_tag = outer_block.select('span.sds-comps-profile-info-subtext span')
                                if len(second_time_tag) > 1:
                                    news_before = second_time_tag[1].get_text().strip()
                                else:
                                    news_before = ''

                            # 여전히 "전"이 없으면 공백으로 설정
                            if '전' not in news_before:
                                news_before = ''
                            
                            # 뉴스 내용
                            summary_tag = outer_block.select_one('span.sds-comps-text-type-body1')
                            news_contents = summary_tag.get_text() if summary_tag else None
    
                            news_dict.append({'news_group': news_group, 'news_title': news_title, 'news_URL': news_URL, 'press_img_URL': press_img_URL, 'press_name': press_name, 'news_before': news_before, 'news_contents': news_contents})
                            
                            # 중복 기사 입력 방지
                            if len(news_dict)-1 > 0:
                                l = 0
                                for t in news_dict:
                                    l += 1
                                    if l < len(news_dict)-1 and (news_title == t['news_title'] or news_URL == t['news_URL']):
                                        del news_dict[len(news_dict)-1]
                            
                            count_item4 = sum(1 for item in news_dict if item['news_group'] == 'item4')
                            if count_item4 >= news_num:
                                break
                                        
                    elif idx_item == 4:
                        for n in headline_spans:
                            news_group = 'item5'
                            a_tag = n.find_parent('a', href=True)
                            news_title = n.get_text()
                            news_URL = a_tag['href']
                            
                            # 기사 전체 블럭 탐색 (최상위 부모)
                            outer_block = n
                            for _ in range(10):  # 최대 10단계까지 위로 탐색
                                outer_block = outer_block.parent
                                if outer_block is None:
                                    break
                                if outer_block.select_one('div.sds-comps-profile-source'):
                                    break

                            if outer_block is None:
                                continue
                            
                           # 언론사 이름
                            press_name_tag = outer_block.select_one('span.sds-comps-text-weight-sm span')
                            press_name = press_name_tag.get_text() if press_name_tag else None

                            # 언론사 이미지
                            press_img_tag = outer_block.select_one('div.sds-comps-image-circle img')
                            press_img_URL = press_img_tag.get('src') if press_img_tag else None

                            # 게시 시간
                            time_tag = outer_block.select_one('span.sds-comps-profile-info-subtext span')
                            news_before = time_tag.get_text(strip=True) if time_tag else None
                            
                            # "전"이 포함되지 않았다면, 한 번 더 시도
                            if '전' not in news_before:
                                second_time_tag = outer_block.select('span.sds-comps-profile-info-subtext span')
                                if len(second_time_tag) > 1:
                                    news_before = second_time_tag[1].get_text().strip()
                                else:
                                    news_before = ''

                            # 여전히 "전"이 없으면 공백으로 설정
                            if '전' not in news_before:
                                news_before = ''
                            
                            # 뉴스 내용
                            summary_tag = outer_block.select_one('span.sds-comps-text-type-body1')
                            news_contents = summary_tag.get_text() if summary_tag else None
    
                            news_dict.append({'news_group': news_group, 'news_title': news_title, 'news_URL': news_URL, 'press_img_URL': press_img_URL, 'press_name': press_name, 'news_before': news_before, 'news_contents': news_contents})
                            
                            # 중복 기사 입력 방지
                            if len(news_dict)-1 > 0:
                                l = 0
                                for t in news_dict:
                                    l += 1
                                    if l < len(news_dict)-1 and (news_title == t['news_title'] or news_URL == t['news_URL']):
                                        del news_dict[len(news_dict)-1]
                            
                            count_item5 = sum(1 for item in news_dict if item['news_group'] == 'item5')
                            if count_item5 >= news_num:
                                break
                            
                    elif idx_item == 5:
                        for n in headline_spans:
                            news_group = 'item6'
                            a_tag = n.find_parent('a', href=True)
                            news_title = n.get_text()
                            news_URL = a_tag['href']
                            
                            # 기사 전체 블럭 탐색 (최상위 부모)
                            outer_block = n
                            for _ in range(10):  # 최대 10단계까지 위로 탐색
                                outer_block = outer_block.parent
                                if outer_block is None:
                                    break
                                if outer_block.select_one('div.sds-comps-profile-source'):
                                    break

                            if outer_block is None:
                                continue
                            
                           # 언론사 이름
                            press_name_tag = outer_block.select_one('span.sds-comps-text-weight-sm span')
                            press_name = press_name_tag.get_text() if press_name_tag else None

                            # 언론사 이미지
                            press_img_tag = outer_block.select_one('div.sds-comps-image-circle img')
                            press_img_URL = press_img_tag.get('src') if press_img_tag else None

                            # 게시 시간
                            time_tag = outer_block.select_one('span.sds-comps-profile-info-subtext span')
                            news_before = time_tag.get_text(strip=True) if time_tag else None
                            
                            # "전"이 포함되지 않았다면, 한 번 더 시도
                            if '전' not in news_before:
                                second_time_tag = outer_block.select('span.sds-comps-profile-info-subtext span')
                                if len(second_time_tag) > 1:
                                    news_before = second_time_tag[1].get_text().strip()
                                else:
                                    news_before = ''

                            # 여전히 "전"이 없으면 공백으로 설정
                            if '전' not in news_before:
                                news_before = ''
                            
                            # 뉴스 내용
                            summary_tag = outer_block.select_one('span.sds-comps-text-type-body1')
                            news_contents = summary_tag.get_text() if summary_tag else None
    
                            news_dict.append({'news_group': news_group, 'news_title': news_title, 'news_URL': news_URL, 'press_img_URL': press_img_URL, 'press_name': press_name, 'news_before': news_before, 'news_contents': news_contents})
                            
                            # 중복 기사 입력 방지
                            if len(news_dict)-1 > 0:
                                l = 0
                                for t in news_dict:
                                    l += 1
                                    if l < len(news_dict)-1 and (news_title == t['news_title'] or news_URL == t['news_URL']):
                                        del news_dict[len(news_dict)-1]
                            
                            count_item6 = sum(1 for item in news_dict if item['news_group'] == 'item6')
                            if count_item6 >= news_num:
                                break
                            
                    elif idx_item == 6:
                        for n in headline_spans:
                            news_group = 'item7'
                            a_tag = n.find_parent('a', href=True)
                            news_title = n.get_text()
                            news_URL = a_tag['href']
                            
                            # 기사 전체 블럭 탐색 (최상위 부모)
                            outer_block = n
                            for _ in range(10):  # 최대 10단계까지 위로 탐색
                                outer_block = outer_block.parent
                                if outer_block is None:
                                    break
                                if outer_block.select_one('div.sds-comps-profile-source'):
                                    break

                            if outer_block is None:
                                continue
                            
                           # 언론사 이름
                            press_name_tag = outer_block.select_one('span.sds-comps-text-weight-sm span')
                            press_name = press_name_tag.get_text() if press_name_tag else None

                            # 언론사 이미지
                            press_img_tag = outer_block.select_one('div.sds-comps-image-circle img')
                            press_img_URL = press_img_tag.get('src') if press_img_tag else None

                            # 게시 시간
                            time_tag = outer_block.select_one('span.sds-comps-profile-info-subtext span')
                            news_before = time_tag.get_text(strip=True) if time_tag else None
                            
                            # "전"이 포함되지 않았다면, 한 번 더 시도
                            if '전' not in news_before:
                                second_time_tag = outer_block.select('span.sds-comps-profile-info-subtext span')
                                if len(second_time_tag) > 1:
                                    news_before = second_time_tag[1].get_text().strip()
                                else:
                                    news_before = ''

                            # 여전히 "전"이 없으면 공백으로 설정
                            if '전' not in news_before:
                                news_before = ''
                            
                            # 뉴스 내용
                            summary_tag = outer_block.select_one('span.sds-comps-text-type-body1')
                            news_contents = summary_tag.get_text() if summary_tag else None
    
                            news_dict.append({'news_group': news_group, 'news_title': news_title, 'news_URL': news_URL, 'press_img_URL': press_img_URL, 'press_name': press_name, 'news_before': news_before, 'news_contents': news_contents})
                            
                            # 중복 기사 입력 방지
                            if len(news_dict)-1 > 0:
                                l = 0
                                for t in news_dict:
                                    l += 1
                                    if l < len(news_dict)-1 and (news_title == t['news_title'] or news_URL == t['news_URL']):
                                        del news_dict[len(news_dict)-1]

                            count_item7 = sum(1 for item in news_dict if item['news_group'] == 'item7')
                            if count_item7 >= news_num:
                                break

                    elif idx_item == 7:
                        for n in headline_spans:
                            news_group = 'item8'
                            a_tag = n.find_parent('a', href=True)
                            news_title = n.get_text()
                            news_URL = a_tag['href']
                            
                            # 기사 전체 블럭 탐색 (최상위 부모)
                            outer_block = n
                            for _ in range(10):  # 최대 10단계까지 위로 탐색
                                outer_block = outer_block.parent
                                if outer_block is None:
                                    break
                                if outer_block.select_one('div.sds-comps-profile-source'):
                                    break

                            if outer_block is None:
                                continue
                            
                           # 언론사 이름
                            press_name_tag = outer_block.select_one('span.sds-comps-text-weight-sm span')
                            press_name = press_name_tag.get_text() if press_name_tag else None

                            # 언론사 이미지
                            press_img_tag = outer_block.select_one('div.sds-comps-image-circle img')
                            press_img_URL = press_img_tag.get('src') if press_img_tag else None

                            # 게시 시간
                            time_tag = outer_block.select_one('span.sds-comps-profile-info-subtext span')
                            news_before = time_tag.get_text(strip=True) if time_tag else None
                            
                            # "전"이 포함되지 않았다면, 한 번 더 시도
                            if '전' not in news_before:
                                second_time_tag = outer_block.select('span.sds-comps-profile-info-subtext span')
                                if len(second_time_tag) > 1:
                                    news_before = second_time_tag[1].get_text().strip()
                                else:
                                    news_before = ''

                            # 여전히 "전"이 없으면 공백으로 설정
                            if '전' not in news_before:
                                news_before = ''
                            
                            # 뉴스 내용
                            summary_tag = outer_block.select_one('span.sds-comps-text-type-body1')
                            news_contents = summary_tag.get_text() if summary_tag else None
    
                            news_dict.append({'news_group': news_group, 'news_title': news_title, 'news_URL': news_URL, 'press_img_URL': press_img_URL, 'press_name': press_name, 'news_before': news_before, 'news_contents': news_contents})
                            
                            # 중복 기사 입력 방지
                            if len(news_dict)-1 > 0:
                                l = 0
                                for t in news_dict:
                                    l += 1
                                    if l < len(news_dict)-1 and (news_title == t['news_title'] or news_URL == t['news_URL']):
                                        del news_dict[len(news_dict)-1]

                            count_item8 = sum(1 for item in news_dict if item['news_group'] == 'item8')
                            if count_item8 >= news_num:
                                break
                        
                idx_item += 1
                        
            count_item1 = sum(1 for item in news_dict if item['news_group'] == 'item1')
            count_item2 = sum(1 for item in news_dict if item['news_group'] == 'item2')
            count_item3 = sum(1 for item in news_dict if item['news_group'] == 'item3')
            count_item4 = sum(1 for item in news_dict if item['news_group'] == 'item4')
            count_item5 = sum(1 for item in news_dict if item['news_group'] == 'item5')
            count_item6 = sum(1 for item in news_dict if item['news_group'] == 'item6')
            count_item7 = sum(1 for item in news_dict if item['news_group'] == 'item7')
            count_item8 = sum(1 for item in news_dict if item['news_group'] == 'item8')

            print('크롤링 완료')
            self.add_log("뉴스 수집 완료. HTML 생성 중...")

            # 이미지 파일 Base64로 변환
            img_header = self.image_to_base64(resource_path("images/Newsletter_Title.png"))
            img_header_pic = self.image_to_base64(resource_path("images/Newsletter_Yuanta.jpg"))
            img_divider = self.image_to_base64(resource_path("images/Divider_Bar.png"))
            img_footer = self.image_to_base64(resource_path("images/End_Bar.png"))

            email_text = '''
                        <link href="https://fonts.googleapis.com" rel="preconnect">
            <link href="https://fonts.gstatic.com" rel="preconnect" crossorigin="">
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR&amp;display=swap" rel="stylesheet"> 
            <style> a { color: #3333cc;  text-decoration: none;  }
                    a:visited { color: #995466;    } </style> 
            <body>
                <table width="100%">
                    <tbody>
                        <tr>
                            <td class="wrapper" width="800" align="center"><table width="100%">
<tbody>
<tr>
<td class="wrapper" width="800" align="center"> <!-- Header image --> 
<table class="section header" cellpadding="0" cellspacing="0" width="800">
<tbody>
<tr>
<td class="column" width="600"> <!-- Left side with image and text --> 
<table class="">
<tbody>
<tr>
<td align="left"> <img src="'''+ img_header +'''" alt="Newsletter_Title" width="600" /> 
<h2><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 20pt;"> 금융 &amp; IT 뉴스 클리핑 Weekly </span><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 12pt;">('''+ establish_date + ''')</span></h2> <span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 11pt; color:#008080; text-align:left;"><br />
본 메일은 키워드 뉴스 검색으로 발행되는 유안타증권 IT본부 뉴스레터 입니다. <br />
 개선 의견이나 불편 사항은 회신 주시기 바랍니다.</span></td>
</tr>
</tbody>
</table></td>
<td class="column" width="200"> 
<p><br /></p> 
<p><br /></p> 
<p><br /></p><img src="'''+ img_header_pic +'''" style="border: 0px solid rgb(0, 0, 0); width: 155px; height: 165px; vertical-align: bottom; float: right;" title="" alt="" class="" /><br />
 
<div style="text-align: center;">
<p><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 9pt; color:#A4A4A4; font-style: italic;"><br />
<br /><br />
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;</span></p>
<p><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 9pt; color:#A4A4A4; font-style: italic;"><br /><br /><br /><br /><br /><br /><br />&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp;&nbsp; &nbsp;유안타증권 IT전략팀<br />
 &nbsp; &nbsp;&nbsp; &nbsp;&nbsp;&nbsp; &nbsp; &nbsp; &nbsp;since 2021.10</span></p></div></td>
</tr>
</tbody>
</table> </td>
</tr>
</tbody>
<tbody>
<tr>
<td class="wrapper" width="800" align="center"> <!-- Header image --> 
<table class="section header" cellpadding="0" cellspacing="0" width="800">
<tbody>'''

            i = 0

            while i <= len(news_dict)-1:
                if count_item1 > 0 and i < count_item1:
                    if i == 0:
                        email_text += '''<tr><td><br></td></tr>
                                    <tr>
                                    <td align= "center">
                                                        <img src="'''+ img_divider +'''" alt="Divider" width="800"  height="20"/>
                                                        <br><br><br><h2><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 16pt;"> #증권사 + 서비스 + 도입 </span></h2><br><br>
                                                        </td>
                                                        </tr>
                                    <tr>
                                                        <td align= "left">'''
                    
                    email_text += '''<span style="font-family:'Gothic';"><b><br><a href = "'''+news_dict[i]['news_URL']+'''" target="_blank" style="text-decoration:none !important; color:#3333cc !important; border-bottom:none !important;">&bull;&nbsp;&nbsp;&nbsp;&nbsp;'''+news_dict[i]['news_title']+ '''</a> &nbsp;</b></span><span style="font-family: David, &quot;Noto Sans KR&quot;, sans-serif; font-size: 9pt; color: rgb(164, 164, 164);">''' ' ( '+news_dict[i]['press_name']+ ' , '+news_dict[i]['news_before'] +' )' '''</span><br><br>'''
                        
                elif count_item2 > 0 and i < count_item1+count_item2:
                    if i == count_item1:
                        email_text += '''</td>
                                                    </tr><tr><td><br></td></tr>
                                                    <tr>
                                <td align= "center">
                                                        <img src="'''+ img_divider +'''" alt="Divider" width="800"  height="20"/>
                                                        <br><br><br><h2><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 16pt;"> #증권사 + 전산장애 </span></h2><br><br>
                                                        </td>
                                                        </tr>
                                <tr>
                                                        <td align= "left">'''
                    
                    email_text += '''<span style="font-family:'Gothic';"><b><br><a href = "'''+news_dict[i]['news_URL']+'''" target="_blank" style="text-decoration:none !important; color:#3333cc !important; border-bottom:none !important;">&bull;&nbsp;&nbsp;&nbsp;&nbsp;'''+news_dict[i]['news_title']+ '''</a> &nbsp;</b></span><span style="font-family: David, &quot;Noto Sans KR&quot;, sans-serif; font-size: 9pt; color: rgb(164, 164, 164);">''' ' ( '+news_dict[i]['press_name']+ ' , '+news_dict[i]['news_before'] +' )' '''</span><br><br>'''
                       
                elif count_item3 > 0 and i < count_item1+count_item2+count_item3:
                    if i == count_item1+count_item2:
                        email_text += '''</td>
                                                    </tr><tr><td><br></td></tr>
                                                    <tr>
                                <td align= "center">
                                                        <img src="'''+ img_divider +'''" alt="Divider" width="800"  height="20"/>
                                                        <br><br><br><h2><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 16pt;"> #유안타증권 </span></h2><br><br>
                                                        </td>
                                                        </tr>
                                <tr>
                                                        <td align= "left">'''

                    email_text += '''<span style="font-family:'Gothic';"><b><br><a href = "'''+news_dict[i]['news_URL']+'''" target="_blank" style="text-decoration:none !important; color:#3333cc !important; border-bottom:none !important;">&bull;&nbsp;&nbsp;&nbsp;&nbsp;'''+news_dict[i]['news_title']+ '''</a> &nbsp;</b></span><span style="font-family: David, &quot;Noto Sans KR&quot;, sans-serif; font-size: 9pt; color: rgb(164, 164, 164);">''' ' ( '+news_dict[i]['press_name']+ ' , '+news_dict[i]['news_before'] +' )' '''</span><br><br>'''
                       
                elif count_item4 > 0 and i < count_item1+count_item2+count_item3+count_item4:
                    if i == count_item1+count_item2+count_item3:
                        email_text += '''</td>
                                                    </tr><tr><td><br></td></tr>
                                                    <tr>
                                <td align= "center">
                                                        <img src="'''+ img_divider +'''" alt="Divider" width="800"  height="20"/>
                                                        <br><br><br><h2><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 16pt;"> #금융 + 클라우드 </span></h2><br><br>
                                                        </td>
                                                        </tr>
                                <tr>
                                                        <td align= "left">'''

                    email_text += '''<span style="font-family:'Gothic';"><b><br><a href = "'''+news_dict[i]['news_URL']+'''" target="_blank" style="text-decoration:none !important; color:#3333cc !important; border-bottom:none !important;">&bull;&nbsp;&nbsp;&nbsp;&nbsp;'''+news_dict[i]['news_title']+ '''</a> &nbsp;</b></span><span style="font-family: David, &quot;Noto Sans KR&quot;, sans-serif; font-size: 9pt; color: rgb(164, 164, 164);">''' ' ( '+news_dict[i]['press_name']+ ' , '+news_dict[i]['news_before'] +' )' '''</span><br><br>'''
                     
                elif count_item5 > 0 and i < count_item1+count_item2+count_item3+count_item4+count_item5:
                    if i == count_item1+count_item2+count_item3+count_item4:
                        email_text += '''</td>
                                                    </tr><tr><td><br></td></tr>
                                                    <tr>
                                <td align= "center">
                                                        <img src="'''+ img_divider +'''" alt="Divider" width="800"  height="20"/>
                                                        <br><br><br><h2><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 16pt;"> #금융 + 보안 </span></h2><br><br>
                                                        </td>
                                                        </tr>
                                <tr>
                                                        <td align= "left">'''

                    email_text += '''<span style="font-family:'Gothic';"><b><br><a href = "'''+news_dict[i]['news_URL']+'''" target="_blank" style="text-decoration:none !important; color:#3333cc !important; border-bottom:none !important;">&bull;&nbsp;&nbsp;&nbsp;&nbsp;'''+news_dict[i]['news_title']+ '''</a> &nbsp;</b></span><span style="font-family: David, &quot;Noto Sans KR&quot;, sans-serif; font-size: 9pt; color: rgb(164, 164, 164);">''' ' ( '+news_dict[i]['press_name']+ ' , '+news_dict[i]['news_before'] +' )' '''</span><br><br>'''
                     
                elif count_item6 > 0 and i < count_item1+count_item2+count_item3+count_item4+count_item5+count_item6:
                    if i == count_item1+count_item2+count_item3+count_item4+count_item5:
                        email_text += '''</td>
                                                    </tr><tr><td><br></td></tr>
                                                    <tr>
                                <td align= "center">
                                                        <img src="'''+ img_divider +'''" alt="Divider" width="800"  height="20"/>
                                                        <br><br><br><h2><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 16pt;"> #증권사 + 핀테크 + AI </span></h2><br><br>
                                                        </td>
                                                        </tr>
                                <tr>
                                                        <td align= "left">'''

                    email_text += '''<span style="font-family:'Gothic';"><b><br><a href = "'''+news_dict[i]['news_URL']+'''" target="_blank" style="text-decoration:none !important; color:#3333cc !important; border-bottom:none !important;">&bull;&nbsp;&nbsp;&nbsp;&nbsp;'''+news_dict[i]['news_title']+ '''</a> &nbsp;</b></span><span style="font-family: David, &quot;Noto Sans KR&quot;, sans-serif; font-size: 9pt; color: rgb(164, 164, 164);">''' ' ( '+news_dict[i]['press_name']+ ' , '+news_dict[i]['news_before'] +' )' '''</span><br><br>'''
                  
                elif count_item7 > 0 and i < count_item1+count_item2+count_item3+count_item4+count_item5+count_item6+count_item7:
                    if i == count_item1+count_item2+count_item3+count_item4+count_item5+count_item6:
                        email_text += '''</td>
                                                    </tr><tr><td><br></td></tr>
                                                    <tr>
                                <td align= "center">
                                                        <img src="'''+ img_divider +'''" alt="Divider" width="800"  height="20"/>
                                                        <br><br><br><h2><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 16pt;"> #증권사 + 금융감독원 </span></h2><br><br>
                                                        </td>
                                                        </tr>
                                <tr>
                                                        <td align= "left">'''

                    email_text += '''<span style="font-family:'Gothic';"><b><br><a href = "'''+news_dict[i]['news_URL']+'''" target="_blank" style="text-decoration:none !important; color:#3333cc !important; border-bottom:none !important;">&bull;&nbsp;&nbsp;&nbsp;&nbsp;'''+news_dict[i]['news_title']+ '''</a> &nbsp;</b></span><span style="font-family: David, &quot;Noto Sans KR&quot;, sans-serif; font-size: 9pt; color: rgb(164, 164, 164);">''' ' ( '+news_dict[i]['press_name']+ ' , '+news_dict[i]['news_before'] +' )' '''</span><br><br>'''

                elif count_item8 > 0 and i < count_item1+count_item2+count_item3+count_item4+count_item5+count_item6+count_item7+count_item8:
                    if i == count_item1+count_item2+count_item3+count_item4+count_item5+count_item6+count_item7:
                        email_text += '''</td>
                                                    </tr><tr><td><br></td></tr>
                                                    <tr>
                                <td align= "center">
                                                        <img src="'''+ img_divider +'''" alt="Divider" width="800"  height="20"/>
                                                        <br><br><br><h2><span style="font-family: David,'Noto Sans KR', sans-serif; font-size: 16pt;"> #노란봉투법 </span></h2><br><br>
                                                        </td>
                                                        </tr>
                                <tr>
                                                        <td align= "left">'''

                    email_text += '''<span style="font-family:'Gothic';"><b><br><a href = "'''+news_dict[i]['news_URL']+'''" target="_blank" style="text-decoration:none !important; color:#3333cc !important; border-bottom:none !important;">&bull;&nbsp;&nbsp;&nbsp;&nbsp;'''+news_dict[i]['news_title']+ '''</a> &nbsp;</b></span><span style="font-family: David, &quot;Noto Sans KR&quot;, sans-serif; font-size: 9pt; color: rgb(164, 164, 164);">''' ' ( '+news_dict[i]['press_name']+ ' , '+news_dict[i]['news_before'] +' )' '''</span><br><br>'''
                  
                if i == len(news_dict)-1:
                    email_text += '''</td>
                                                    </tr>
                                                    <tr>
                                <td align= "center">
                                                        <br><br><img src="'''+ img_footer +'''" alt="End_Bar" width="800"  height="55"/>
                                                        <p style="color:#A4A4A4; text-align:left";> 발행인 :  유안타증권 IT전략팀</p>
                                                        <p style="color:#A4A4A4; text-align:left";> 이메일주소 :  taewon.noh@yuantakorea.com</p>
                                                        <p style="color:#A4A4A4; text-align:left";> Copyright. 2024. taewon.Noh. All rights reserved.</p>
                                                        </td>
                                                        </tr>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </tbody>
                </table></body>'''
                
                i += 1

            self.final_html_result = email_text
            
            # 파일 저장 (사원번호 사용)
            if self.vdi_var.get() == "Y":
                self.html_file_path = f"C:\\Users\\{emp_no}\\newsletter"
            else:
                self.html_file_path = f"C:\\Users\\YSK\\Desktop\\newsletter"

            if not os.path.exists(self.html_file_path):
                os.makedirs(self.html_file_path)

            self.html_file_path += f"\\newsletter_{date_str}.txt"

            with open(self.html_file_path, 'w', encoding="UTF8") as f:
                f.write(email_text)
            
            pyperclip.copy(email_text)
            self.add_log("HTML 파일 생성 및 클립보드 복사 완료.")
            
        except Exception as e:
            self.add_log(f"처리 중 오류 발생: {e}")
            raise e

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationGUI(root)
    root.mainloop()