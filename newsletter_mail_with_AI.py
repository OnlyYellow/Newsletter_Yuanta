import time
import threading
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoAlertPresentException

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime

import json
import re
import random
import ssl
import requests
from bs4 import BeautifulSoup

import sys
import os
from dotenv import load_dotenv
import pyperclip

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# .env 파일에 있는 변수들을 파이썬 환경으로 불러오기
load_dotenv() 

# os.environ.get을 사용해 키 값을 가져오기
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")


def _create_unverified_https_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

# SSL 모듈의 모든 컨텍스트 생성 함수를 '검증 안 함' 함수로 바꿔치기
ssl.create_default_context = lambda *args, **kwargs: _create_unverified_https_context()
ssl._create_default_https_context = _create_unverified_https_context

from google import genai
from google.genai import types

# EXE 실행인지 파이썬 실행인지 구별해서 경로 설정
if getattr(sys, 'frozen', False):
    # EXE로 실행 중일 때: 실제 EXE 파일이 있는 곳을 가리킴
    current_folder = os.path.dirname(sys.executable)
else:
    # 파이썬으로 실행 중일 때: 파일 위치를 가리킴
    current_folder = os.path.dirname(os.path.abspath(__file__))

if current_folder not in sys.path:
    sys.path.append(current_folder)

driver_path = None
# GOOGLE_API_KEY = "AIzaSyBWeuK8HEIyVmQZJ_BP7VjpSdKYyKvMvMQ"


# 로그 출력 함수
def log_print(message, callback=None):
    print(message)
    if callback:
        callback(message)

def get_article_content(url, log_callback=None):
    log_print("내용을 추출 중입니다...", log_callback)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' 
        }
        resp = requests.get(url, headers=headers, timeout=20, verify=False)

        if resp.status_code != 200:
            return "접속 실패", "내용을 가져올 수 없습니다."
        
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 요약
        og_desc = soup.find('meta', property='og:description')
        summary = og_desc['content'].strip() if og_desc else ""

        # 본문 리드문
        paragraphs = soup.find_all('p')
        full_text = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30])
        lead_text = full_text[:400] + "..." if full_text else "본문 추출 실패"

        if not summary:
            summary = lead_text[:100]

        return summary, lead_text
    except Exception as e:
        return "크롤링 에러", f"Error: {str(e)}"


def parse_and_enrich_data(html_content, log_callback=None):
    log_print("[전처리] 뉴스레터 HTML 내의 링크를 분석하고 상세 내용을 수집합니다...", log_callback)
    soup = BeautifulSoup(html_content, 'html.parser')

    enriched_data = []

    # h2 태그를 기준으로 카테고리 식별
    categories = soup.find_all('h2')
    total_links = 0

    for cat_header in categories:
        category_name = cat_header.get_text(strip=True)
        # 헤더 테스트 정체
        category_name = category_name.replace("News Clipping", "").strip()

        # 메인 타이틀 등 불필요한 헤더 건너뛰기
        if "뉴스 클리핑" in category_name or not category_name:
            continue

        log_print(f"[카테고리] {category_name}를 분석 중입니다...", log_callback)

        article_list = []

        # 현재 헤더가 속한 테이블 구조 탐색
        current_table = cat_header.find_parent('table')
        if current_table:
            header_tr = cat_header.find_parent('tr')
            next_tr = header_tr.find_next_sibling('tr')

            while next_tr:
                # 다음 카테고리 헤더가 나오면 중단
                if next_tr.find('h2'):
                    break

                # 기사 링크 찾기
                links = next_tr.find_all('a')
                for link in links:
                    url = link['href']
                    title = link.get_text(strip=True)

                    # 언론사 정보
                    source_span = link.find_next('span')
                    source_info = source_span.get_text(strip=True) if source_span else ""

                    # 실제 크롤링 수행
                    real_summary, real_lead = get_article_content(url)
                    article_data = {
                        "title": title,
                        "url": url,
                        "source": source_info,
                        "scraped_summary": real_summary,
                        "scraped_lead": real_lead
                    }
                    article_list.append(article_data)
                    total_links += 1
                    log_print(f"- 수집완료: {title[:15]}...", log_callback)
                next_tr = next_tr.find_next_sibling('tr')

        if article_list:
            enriched_data.append({
                "category": category_name,
                "articles": article_list
            })
    log_print(f"[전처리 완료] 총 {total_links}개 기사의 상세 내용을 확보했습니다.", log_callback)

    # 수집된 데이터 파일로 저장하기
    try:
        save_dir = os.path.join(current_folder, "crawled_html")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crawled_html_{timestamp}.json"
        save_path = os.path.join(save_dir, filename)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(enriched_data, f, ensure_ascii=False, indent=4)
        log_print(f"[중간 저장 완료] 크롤링된 데이터가 저장되었습니다: {save_path}", log_callback)
    except Exception as e:
        log_print(f"[저장 실패] 크롤링 데이터 파일 저장 중 오류 발생: {e}", log_callback)
    return enriched_data


def driver_init(log_callback=None):
    # edge driver 옵션 설정
    edge_options = Options()
    edge_options.add_experimental_option("detach", True) # 브라우저가 자동으로 닫히지 않도록 설정
    edge_options.add_argument("--start-maximized") # 창 최대화 옵션 추가
    edge_options.add_argument("--ignore-certificate-errors") # 인증서 오류 무시 옵션 추가
    edge_options.add_argument("--allow-insecure-localhost") # 로컬호스트의 보안되지 않은 콘텐츠 허용 옵션 추가

    # Selenium 전용 Edge 프로필 경로 고정
    profile_dir = os.path.join(os.environ["LOCALAPPDATA"], "Newsletter_Edge_Profile")
    os.makedirs(profile_dir, exist_ok=True)
    edge_options.add_argument(f"--user-data-dir={profile_dir}")
    log_print(f"Edge 프로필 경로: {profile_dir}", log_callback)

    # 지정된 경로의 Driver 실행 
    log_print(f"Edge Driver 실행 경로: {driver_path}", log_callback)
    log_print("Edge 브라우저를 실행합니다...", log_callback)

    try:
        # Service 객체에 실행 파일 경로 직접 지정
        service = Service(executable_path=driver_path)

        # 드라이버 실행
        driver = webdriver.Edge(service=service, options=edge_options)

        # 원하는 URL로 이동
        target_url = "http://i-mail.yuantakorea.com"
        log_print(f"{target_url} 로 이동 중...", log_callback)
        driver.get(target_url)
        log_print("접속 완료!", log_callback)
    except Exception as e:
        log_print("오류가 발생했습니다. 아래 내용을 확인해주세요.", log_callback)
        log_print(f"에러 메시지: {e}", log_callback)
    
    return driver


def alert_off(driver, log_callback=None):
    # 팝업(Alert) 확인 및 처리
    log_print("팝업(Alert) 확인 및 처리를 시작합니다...", log_callback)

    try:
        # 경고창 확인
        WebDriverWait(driver, 20).until(EC.alert_is_present())

        # 경고창으로 제어권 이동
        alert = driver.switch_to.alert

        # 경고창 내용 출력
        log_print(f"[팝업 내용]: {alert.text}", log_callback)

        # 확인 버튼 클릭
        alert.accept()
        log_print("[성공] '확인' 버튼을 클릭했습니다.", log_callback)
    except TimeoutException:
        log_print("[정보] 팝업이 뜨지 않았습니다.", log_callback)
    except NoAlertPresentException:
        log_print("[정보] 처리할 팝업창이 존재하지 않습니다.", log_callback)
    except Exception as e:
        log_print(f"[주의] 팝업 처리 중 오류가 발생했습니다.: {e}", log_callback)


def login(driver, emp_no, user_pw, log_callback=None):
    # 프레임 전환 및 로그인 정보 입력
    log_print("로그인을 시도합니다...", log_callback)

    try:
        # iframe으로 포커스 이동
        driver.switch_to.frame("main")
        log_print("[성공] main 프레임으로 전환했습니다.", log_callback)

        try:
            # 3초만 짧게 기다려봅니다. (이미 로그인 됐다면 바로 있을 테니까요)
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "span.egate_btn_write"))
            )
            log_print("[감지] 이미 로그인된 상태입니다. 로그인 단계를 건너뜁니다.", log_callback)
            return  # ★ 함수를 강제로 종료하여 로그인 입력을 스킵
        except TimeoutException:
            # 메일쓰기 버튼이 없으면 로그인이 되지 않은 상태로 인지 후 넘어감.
            pass

        # ID 입력창 찾기 및 값 입력
        user_id_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "id"))
        )
        user_id_input.clear() # 기존 값 삭제(선택)
        user_id = emp_no
        user_id_input.send_keys(user_id) # ID 값 입력
        log_print(f"[성공] ID 입력 완료: {user_id}", log_callback)

        # 비밀번호 입력
        pw_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        pw_input.clear()
        pw = user_pw
        pw_input.send_keys(pw) # 비밀번호 값 입력
        log_print(f"[성공] 비밀번호 입력 완료: {'*' * len(pw)}", log_callback)

        # Enter 키로 로그인
        pw_input.send_keys(Keys.RETURN)
        log_print("[성공] 로그인 시도(엔터)", log_callback)
        time.sleep(5)  # 로그인 처리 대기
    except TimeoutException:
        log_print("[실패] ID 입력창을 찾지 못했습니다.", log_callback)
    except Exception as e:
        log_print(f"[오류] ID 입력 중 오류가 발생했습니다.: {e}", log_callback)


def click_email(driver, log_callback=None):
    # 메일쓰기 버튼 클릭
    log_print("메일쓰기 버튼을 클릭합니다...", log_callback)

    try:
        # 프레임 재진입
        driver.switch_to.default_content()  # 기본 콘텐츠로 전환
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.NAME, "main"))
        )
        log_print("[성공] main 프레임으로 재전환했습니다.", log_callback)

        # 메일쓰기 버튼 찾기 및 클릭
        write_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "span.egate_btn_write"))
        )
        write_btn.click()
        log_print("[성공] 메일쓰기 버튼을 클릭했습니다.", log_callback)
        time.sleep(5)  # 메일쓰기 창 로딩 대기
    except TimeoutException:
        log_print("[실패] 메일쓰기 버튼을 찾지 못했습니다.", log_callback)
        return False
    except Exception as e:
        log_print(f"[오류] 메일쓰기 버튼 클릭 중 오류가 발생했습니다.: {e}", log_callback)
        return False


def prepare_email_header(driver, log_callback=None):
    # 정보 입력
    log_print("메일 작성 정보를 입력합니다...", log_callback)

    try:
        # 프레임 재진입
        driver.switch_to.default_content()  # 기본 콘텐츠로 전환
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.NAME, "main"))
        )
        log_print("[성공] main 프레임으로 재전환했습니다.", log_callback)

        # 수신자 입력칸 찾기
        receiver_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.egate_eugp_i_input[mode='send_to']"))
        )

        # 수신자 리스트 입력
        all_receivers = "IT본부, 대표이사실, 정보보호본부, 증권IT운영팀, 디지털플랫폼팀, 디지털전략팀"
        receiver_input.clear()
        receiver_input.send_keys(all_receivers)
        time.sleep(2)  # 입력 대기
        receiver_input.send_keys(Keys.RETURN)  # 엔터로 확정
    except Exception as e:
        log_print(f"[오류] 수신자 입력 중 오류가 발생했습니다.: {e}", log_callback)

    log_print("중복 확인 팝업을 처리합니다...", log_callback)

    try:
        # 팝업창 대기
        popup_dialog = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "ez-dialog-0"))
        )
        log_print("[감지] 중복 확인 팝업이 떴습니다.", log_callback)

        # jindex가 '0'인 모든 체크박스 찾기
        target_checkboxes = popup_dialog.find_elements(By.CSS_SELECTOR, "input[jindex='0']")

        count = 0
        for checkbox in target_checkboxes:
            if not checkbox.is_selected():
                checkbox.click()
                count += 1
        log_print(f"[성공] {count}개의 중복 수신자 체크박스를 선택했습니다.", log_callback)

        # 확인 버튼 클릭
        confirm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[text_lang='confirm']"))
        )
        confirm_btn.click()
        log_print("[성공] 중복 확인 팝업의 '확인' 버튼을 클릭했습니다.", log_callback)
        time.sleep(5)  # 팝업 닫힘 대기
    except TimeoutException:
        log_print("[정보] 중복 확인 팝업이 나타나지 않았습니다.", log_callback)
    except Exception as e:
        log_print(f"[오류] 중복 확인 팝업 처리 중 오류가 발생했습니다.: {e}", log_callback)

    log_print("메일 제목을 입력합니다...", log_callback)

    try:
        # 오늘 날짜 포맷 생성
        today_str = datetime.now().strftime("%y.%m.%d")

        # 최종 제목 문자열 완성
        subject_text = f"[정기메일] 금융 & IT 뉴스레터 입니다. ({today_str})"

        # 제목 입력칸 찾기
        subject_input = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.NAME, "Subject"))
        )

        # 제목 입력
        subject_input.clear()
        subject_input.send_keys(subject_text)
        log_print(f"[성공] 메일 제목 입력이 완료되었습니다: {subject_text}", log_callback)
    except Exception as e:
        log_print(f"[오류] 메일 제목 입력 중 오류가 발생했습니다.: {e}", log_callback)


def prepare_email_body(driver, log_callback=None):
    # 본문 입력 준비하기
    log_print("메일 본문 입력을 준비합니다...", log_callback)

    try:
        # ifbody 프레임 진입
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it("ifbody")
        )
        log_print("[성공] ifbody 프레임으로 전환했습니다.", log_callback)

        # 나모 에디터 프레임 진입
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it("NamoSE_Ifr__NamoEditor")
        )
        log_print("[성공] 나모 에디터 프레임으로 전환했습니다.", log_callback)

        # HTML 버튼 클릭
        html_mode_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "html"))
        )
        html_mode_btn.click()
        log_print("[성공] HTML 모드 버튼을 클릭했습니다.", log_callback)
        time.sleep(2)  # 모드 전환 대기
    except TimeoutException:
        log_print("[실패] 나모 에디터 프레임이나 HTML 모드 버튼을 찾지 못했습니다.", log_callback)
    except Exception as e:
        log_print(f"[오류] 본문 입력 준비 중 오류가 발생했습니다.: {e}", log_callback)

    log_print("입력창을 초기화합니다...", log_callback)

    try:
        # 텍스트 입력창 찾기
        source_textarea = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "NamoSE_editorshtml_NamoEditor"))
        )
        source_textarea.clear()
        log_print("[성공] 본문 입력창이 초기화되었습니다.", log_callback)

        # 포커스 이동
        source_textarea.click()
    except Exception as e:
        log_print(f"[오류] 본문 입력창 초기화 중 오류가 발생했습니다.: {e}", log_callback)


def normalize_text(value):
    """비교용 텍스트 정규화: 공백/줄바꿈 차이로 매칭이 깨지는 것을 방지"""
    return " ".join((value or "").split()).strip()


def normalize_url(url):
    """URL 비교용 정규화: href의 공백과 &amp; 차이만 보정"""
    return (url or "").strip().replace("&amp;", "&")


def get_section_name_from_h2(h2_tag):
    """카테고리 h2에서 섹션명을 뽑기"""
    if not h2_tag:
        return ""
    section_name = h2_tag.get_text(" ", strip=True)
    section_name = section_name.replace("News Clipping", "").strip()
    return normalize_text(section_name)


def is_news_section_name(section_name):
    """뉴스 카테고리 섹션인지 판별합니다. 상단 메인 제목은 제외"""
    if not section_name:
        return False
    if "뉴스 클리핑" in section_name:
        return False
    if "Weekly" in section_name and "금융" in section_name:
        return False
    return section_name.startswith("#")


def find_article_row_after_header(header_tr):
    """섹션 헤더 tr 다음에서 실제 기사 링크가 들어있는 tr을 찾기"""
    if not header_tr:
        return None

    next_tr = header_tr.find_next_sibling("tr")
    while next_tr:
        if next_tr.find("h2"):
            return None
        if next_tr.find("a", href=True):
            return next_tr
        next_tr = next_tr.find_next_sibling("tr")
    return None


def extract_article_blocks_from_td(article_td, section_name, start_counter=1):
    """
    기사 하나를 구성하는 HTML 묶음을 원본 그대로 추출
    원본 구조상 기사 1개는 보통 다음 묶음
      <span><b><br><a ...>제목</a></b></span><span>언론사/시간</span><br><br>
    따라서 <a>만 옮기지 않고, 해당 span부터 다음 기사 span 직전까지를 통째로 보존
    """
    contents = list(article_td.contents)
    article_start_indexes = []

    for idx, node in enumerate(contents):
        if getattr(node, "name", None) == "span" and node.find("a", href=True):
            article_start_indexes.append(idx)

    prefix_html = ""
    articles = []

    if not article_start_indexes:
        return prefix_html, articles, start_counter

    prefix_html = "".join(str(node) for node in contents[:article_start_indexes[0]])

    for pos, start_idx in enumerate(article_start_indexes):
        end_idx = article_start_indexes[pos + 1] if pos + 1 < len(article_start_indexes) else len(contents)
        block_nodes = contents[start_idx:end_idx]
        block_html = "".join(str(node) for node in block_nodes)

        block_soup = BeautifulSoup(block_html, "html.parser")
        a_tag = block_soup.find("a", href=True)
        if not a_tag:
            continue

        source_text = ""
        spans = block_soup.find_all("span")
        for span in spans:
            if not span.find("a", href=True):
                text = span.get_text(" ", strip=True)
                if text:
                    source_text = text
                    break

        article_id = f"art_{start_counter:04d}"
        articles.append({
            "article_id": article_id,
            "section": section_name,
            "title": normalize_text(a_tag.get_text(" ", strip=True)),
            "url": normalize_url(a_tag.get("href")),
            "source": normalize_text(source_text),
            "block_html": block_html,
        })
        start_counter += 1

    return prefix_html, articles, start_counter


def extract_newsletter_structure(raw_html):
    """
    원본 HTML에서 섹션과 기사 블록을 추출
    반환되는 soup의 태그 포인터를 그대로 사용해 나중에 기사 영역만 교체
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    sections = []
    article_counter = 1

    for h2 in soup.find_all("h2"):
        section_name = get_section_name_from_h2(h2)
        if not is_news_section_name(section_name):
            continue

        header_tr = h2.find_parent("tr")
        article_tr = find_article_row_after_header(header_tr)
        if not article_tr:
            continue

        article_td = article_tr.find("td")
        if not article_td:
            continue

        prefix_html, articles, article_counter = extract_article_blocks_from_td(
            article_td=article_td,
            section_name=section_name,
            start_counter=article_counter,
        )

        sections.append({
            "name": section_name,
            "header_tr": header_tr,
            "article_tr": article_tr,
            "article_td": article_td,
            "prefix_html": prefix_html,
            "articles": articles,
        })

    return soup, sections


def build_article_indexes(sections):
    article_by_id = {}
    article_by_url = {}
    all_articles = []

    for section in sections:
        for article in section["articles"]:
            article_by_id[article["article_id"]] = article
            article_by_url.setdefault(normalize_url(article["url"]), []).append(article)
            all_articles.append(article)

    return all_articles, article_by_id, article_by_url


def build_enriched_url_map(enriched_data_list):
    """크롤링 결과를 URL 기준으로 조회"""
    enriched_url_map = {}

    for section in enriched_data_list or []:
        for article in section.get("articles", []):
            url = normalize_url(article.get("url"))
            if not url:
                continue
            enriched_url_map[url] = article

    return enriched_url_map


def trim_for_prompt(text, max_chars=450):
    """Gemini 입력이 과도하게 길어지지 않도록 기사 본문 제한"""
    text = normalize_text(text)
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def build_curation_input(sections, enriched_data_list):
    """
    Gemini에 보낼 최소 데이터
    원본 HTML 전체를 보내지 않고, 기사 판단에 필요한 정보만 전송
    """
    enriched_url_map = build_enriched_url_map(enriched_data_list)
    curation_sections = []

    for section in sections:
        articles = []
        for article in section["articles"]:
            enriched = enriched_url_map.get(normalize_url(article["url"]), {})
            scraped_summary = enriched.get("scraped_summary", "")
            scraped_lead = enriched.get("scraped_lead", "")

            articles.append({
                "article_id": article["article_id"],
                "section": section["name"],
                "title": article["title"].replace('"', "'"),
                "url": article["url"],
                "source": article.get("source", ""),
                "scraped_summary": trim_for_prompt(scraped_summary, 450),
                "scraped_lead": trim_for_prompt(scraped_lead, 450),
            })

        curation_sections.append({
            "section": section["name"],
            "articles": articles,
        })

    return curation_sections


def safe_parse_json(raw_text):
    """Gemini 응답에 코드블록/설명이 섞여도 JSON 부분만 안전하게 파싱"""
    if raw_text is None:
        raise ValueError("Gemini 응답이 비어 있습니다.")

    text = raw_text.strip()
    if not text:
        raise ValueError("Gemini 응답이 비어 있습니다.")

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


def normalize_result_dict(raw_json_data):
    """모델이 리스트로 감싸서 반환하는 경우"""
    if isinstance(raw_json_data, list):
        return raw_json_data[0] if raw_json_data else {}
    if isinstance(raw_json_data, dict):
        return raw_json_data
    return {}


def get_log_list(result_dict, *keys):
    for key in keys:
        value = result_dict.get(key)
        if isinstance(value, list):
            return value
    return []


def resolve_article_id_from_log(log_item, article_by_id, article_by_url):
    """
    Gemini 로그를 실제 원본 기사와 매칭.
    1순위: article_id, 2순위: URL, 3순위: URL+섹션/제목 보조 비교
    """
    if not isinstance(log_item, dict):
        return None

    article_id = log_item.get("article_id") or log_item.get("id")
    if article_id in article_by_id:
        return article_id

    url = normalize_url(log_item.get("url"))
    if not url:
        return None

    candidates = article_by_url.get(url, [])
    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]["article_id"]

    target_section = normalize_text(
        log_item.get("section") or log_item.get("from") or log_item.get("from_section") or ""
    )
    target_title = normalize_text(log_item.get("title") or "")

    if target_section:
        for article in candidates:
            if normalize_text(article.get("section")) == target_section:
                return article["article_id"]

    if target_title:
        for article in candidates:
            if normalize_text(article.get("title")) == target_title:
                return article["article_id"]

    return candidates[0]["article_id"]


def enrich_removed_log(original_log, article):
    return {
        "article_id": article["article_id"],
        "section": article["section"],
        "title": article["title"],
        "url": article["url"],
        "score": original_log.get("score", 0) if isinstance(original_log, dict) else 0,
        "reason": original_log.get("reason", "삭제 대상으로 판단됨") if isinstance(original_log, dict) else "삭제 대상으로 판단됨",
    }


def enrich_moved_log(original_log, article, to_section):
    return {
        "article_id": article["article_id"],
        "title": article["title"],
        "url": article["url"],
        "score": original_log.get("score", 0) if isinstance(original_log, dict) else 0,
        "from": article["section"],
        "to": to_section,
        "reason": original_log.get("reason", "섹션 재배치 대상으로 판단됨") if isinstance(original_log, dict) else "섹션 재배치 대상으로 판단됨",
    }


def is_blank_divider_row(tr_tag):
    """섹션 사이의 <tr><td><br></td></tr> 같은 빈 줄인지 확인"""
    if not tr_tag:
        return False
    if tr_tag.find("h2") or tr_tag.find("a") or tr_tag.find("img"):
        return False
    return normalize_text(tr_tag.get_text(" ", strip=True)) == ""


def remove_empty_section_rows(section):
    """기사가 0개가 된 섹션의 헤더 row, 기사 row, 뒤 빈 row를 제거"""
    header_tr = section.get("header_tr")
    article_tr = section.get("article_tr")

    blank_tr = article_tr.find_next_sibling("tr") if article_tr else None
    if is_blank_divider_row(blank_tr):
        blank_tr.decompose()

    if article_tr:
        article_tr.decompose()
    if header_tr:
        header_tr.decompose()


def apply_gemini_decisions_to_html(raw_html_data, result_dict, log_callback=None):
    """
    Gemini는 판단만 하고, 실제 HTML 삭제/이동은 이 함수에서 수행.
    원본 기사 block_html을 그대로 재사용하므로 디자인/줄바꿈/폰트 훼손을 최소화.
    """
    soup, sections = extract_newsletter_structure(raw_html_data)
    all_articles, article_by_id, article_by_url = build_article_indexes(sections)
    section_names = [section["name"] for section in sections]
    section_name_set = set(section_names)

    removed_input_logs = get_log_list(result_dict, "removed_logs", "removed")
    moved_input_logs = get_log_list(result_dict, "moved_logs", "moved")
    selected_input_logs = get_log_list(result_dict, "selected_logs", "selected")

    removed_ids = set()
    effective_removed_logs = []

    for log_item in removed_input_logs:
        article_id = resolve_article_id_from_log(log_item, article_by_id, article_by_url)
        if not article_id:
            log_print(f"[주의] 삭제 로그 매칭 실패: {log_item}", log_callback)
            continue
        if article_id in removed_ids:
            continue
        removed_ids.add(article_id)
        effective_removed_logs.append(enrich_removed_log(log_item, article_by_id[article_id]))

    target_section_by_id = {}
    current_counts = {section["name"]: 0 for section in sections}

    for article in all_articles:
        if article["article_id"] in removed_ids:
            continue
        target_section_by_id[article["article_id"]] = article["section"]
        current_counts[article["section"]] = current_counts.get(article["section"], 0) + 1

    effective_moved_logs = []

    for log_item in moved_input_logs:
        article_id = resolve_article_id_from_log(log_item, article_by_id, article_by_url)
        if not article_id:
            log_print(f"[주의] 이동 로그 매칭 실패: {log_item}", log_callback)
            continue
        if article_id in removed_ids:
            continue

        article = article_by_id[article_id]
        from_section = target_section_by_id.get(article_id, article["section"])
        to_section = normalize_text(log_item.get("to") or log_item.get("target_section") or "")

        if not to_section:
            log_print(f"[주의] 이동 대상 섹션이 비어 있어 기존 섹션 유지: {article['title']}", log_callback)
            continue

        if to_section not in section_name_set:
            log_print(f"[주의] 존재하지 않는 섹션으로 이동 요청되어 기존 섹션 유지: {article['title']} -> {to_section}", log_callback)
            continue

        if from_section == to_section:
            continue

        # Gemini가 규칙을 어겨 섹션 기사 수가 5개를 초과할 경우 이동하지 않습니다.
        if current_counts.get(to_section, 0) >= 5:
            log_print(f"[주의] 대상 섹션 기사 수가 5개 이상이라 이동 취소: {article['title']} -> {to_section}", log_callback)
            continue

        current_counts[from_section] = max(current_counts.get(from_section, 0) - 1, 0)
        current_counts[to_section] = current_counts.get(to_section, 0) + 1
        target_section_by_id[article_id] = to_section
        effective_moved_logs.append(enrich_moved_log(log_item, article, to_section))

    new_articles_by_section = {section["name"]: [] for section in sections}
    moved_articles_by_section = {section["name"]: [] for section in sections}

    for article in all_articles:
        article_id = article["article_id"]
        if article_id in removed_ids:
            continue

        target_section = target_section_by_id.get(article_id, article["section"])
        if target_section == article["section"]:
            new_articles_by_section[target_section].append(article)
        else:
            moved_articles_by_section[target_section].append(article)

    for section_name in section_names:
        new_articles_by_section[section_name].extend(moved_articles_by_section[section_name])

    for section in sections:
        section_name = section["name"]
        final_articles = new_articles_by_section.get(section_name, [])

        if not final_articles:
            remove_empty_section_rows(section)
            continue

        article_td = section["article_td"]
        article_td.clear()

        rebuilt_html = section.get("prefix_html", "") + "".join(article["block_html"] for article in final_articles)
        article_td.append(BeautifulSoup(rebuilt_html, "html.parser"))

    final_html = str(soup)

    # 안전장치: 삭제된 기사 수만큼만 링크 수가 줄어야 함. 이동은 전체 기사 수를 바꾸지 않음.
    _, final_sections_for_check = extract_newsletter_structure(final_html)
    final_articles_for_check, _, _ = build_article_indexes(final_sections_for_check)
    expected_count = len(all_articles) - len(removed_ids)
    actual_count = len(final_articles_for_check)

    if actual_count != expected_count:
        log_print(
            f"[오류] HTML 재조립 후 기사 수 검증 실패: 예상 {expected_count}개, 실제 {actual_count}개. 원본 HTML을 반환합니다.",
            log_callback,
        )
        return raw_html_data, [], [], []

    selected_reason_by_id = {}
    for log_item in selected_input_logs:
        article_id = resolve_article_id_from_log(log_item, article_by_id, article_by_url)
        if article_id:
            selected_reason_by_id[article_id] = log_item

    selected_logs = []
    for section_name in section_names:
        for article in new_articles_by_section.get(section_name, []):
            article_id = article["article_id"]
            selected_log = selected_reason_by_id.get(article_id, {})
            selected_logs.append({
                "article_id": article_id,
                "section": section_name,
                "title": article["title"],
                "url": article["url"],
                "score": selected_log.get("score", 0) if isinstance(selected_log, dict) else 0,
                "reason": selected_log.get("reason", "유지 대상으로 판단됨") if isinstance(selected_log, dict) else "유지 대상으로 판단됨",
            })

    return final_html, selected_logs, effective_removed_logs, effective_moved_logs


def call_gemini_with_retry(client, model, prompt, config, log_callback=None, max_retries=3):
    """일시적인 timeout/서버 오류에 대비해 Gemini 호출을 재시도"""
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
        except Exception as e:
            last_error = e
            if attempt >= max_retries:
                break
            wait_seconds = min((2 ** attempt) + random.random(), 10)
            log_print(f"[Gemini] 요청 실패 {attempt}/{max_retries}. {wait_seconds:.1f}초 후 재시도합니다: {e}", log_callback)
            time.sleep(wait_seconds)

    raise last_error


def using_gemini_api(raw_html_data, log_callback=None):
    # 본문 내용 Gemini API로 정렬
    log_print("메일 본문 내용을 정렬합니다...", log_callback)

    TARGET_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    log_print(f"[Gemini] 뉴스레터 큐레이션을 시작합니다... (Model: {TARGET_MODEL})", log_callback)

    if not GOOGLE_API_KEY:
        log_print("[오류] GOOGLE_API_KEY가 설정되지 않았습니다. Gemini API를 사용할 수 없습니다.", log_callback)
        return raw_html_data, [], [], []

    soup, sections = extract_newsletter_structure(raw_html_data)
    all_articles, _, _ = build_article_indexes(sections)

    if not all_articles:
        log_print("[주의] 원본 HTML에서 기사 링크를 찾지 못했습니다. 원본 HTML을 그대로 반환합니다.", log_callback)
        return raw_html_data, [], [], []

    enriched_data_list = parse_and_enrich_data(raw_html_data, log_callback)
    curation_input = build_curation_input(sections, enriched_data_list)
    curation_json_str = json.dumps(curation_input, ensure_ascii=False, separators=(",", ":"))

    stop_event = threading.Event()

    def timer_logger():
        elapsed = 0
        while not stop_event.is_set():
            log_print(f"[Gemini] 프롬프트 생성 완료. API 요청을 보냅니다... ({elapsed}초)", log_callback)
            time.sleep(1)
            elapsed += 1

    timer_thread = threading.Thread(target=timer_logger)
    timer_thread.daemon = True
    timer_thread.start()

    try:
        client = genai.Client(
            api_key=GOOGLE_API_KEY,
            http_options={"timeout": 600000},
        )

        prompt = f"""
            [역할]
            당신은 금융권 IT 임원 및 실무자를 위한 뉴스레터 전문 수석 에디터입니다.
            단, 최종 HTML은 작성하지 않습니다. 기사별 유지/삭제/이동 판단만 JSON으로 반환합니다.
            실제 HTML 수정은 Python BeautifulSoup가 수행하므로 article_id와 url을 절대 변경하지 마세요.

            [판단 대상 기사 데이터]
            {curation_json_str}

            [핵심 지시 사항]
            1. 주제 적합성 평가 및 필터링
            - 각 기사를 '금융 IT 및 증권 산업'과의 연관성 기준으로 10점 만점 평가하세요.
            - 6점 미만 기사는 삭제 대상으로 분류하세요.
            - 단, 경쟁사 동향은 IT 기술 언급이 없더라도 폭넓게 수용하세요.

            2. 유지 대상 예시
            - 금융사/증권사의 IT 서비스 도입, DX, AI 적용 사례, 마이데이터
            - 전산 장애, 해킹, 개인정보 유출 등 보안 사고/대응/투자
            - 금융당국의 IT/플랫폼 관련 규제와 정책, 망분리 완화, 토큰증권 가이드라인
            - 주요 핀테크 기업의 기술 동향
            - 토스, 카카오페이증권, 대형 증권사 등의 신규 서비스, 제휴, M&A, 글로벌 진출 등 주요 사업 전략
            - '#유안타증권' 섹션은 단순 임원 관련 기사가 아닌 경우 폭넓게 유지
            - '#노란봉투법' 관련 기사는 금융 IT 직접 연관성이 낮더라도 노동/정책 동향 파악용으로 유지

            3. 삭제 대상 예시
            - 단순 가상자산 시세 및 개별 코인 이슈
            - 개별 주식 종목의 단순 주가 등락 및 시황
            - 부동산, 유통 등 비금융 일반 기업 뉴스
            - 단순 인사 동정, 부고, 홍보성 이벤트, 임원 개인 관련 이야기

            4. 문맥 기반 기사 재배치
            - 현재 섹션이 기사 내용과 맞지 않으면 가장 적합한 기존 섹션으로 이동시키세요.
            - 이동 대상 섹션은 반드시 입력 데이터에 존재하는 section 값 중 하나여야 합니다.
            - 이동 후 대상 섹션의 기사 수가 5개를 초과할 것으로 보이면 이동시키지 말고 기존 섹션에 유지하세요.

            5. 중복 제거
            - 섹션 내 또는 섹션 간 내용이 동일하거나 매우 유사하면 대표 기사 1개만 selected_logs에 남기고 나머지는 removed_logs로 보내세요.

            [출력 형식]
            반드시 순수 JSON만 출력하세요. 코드블록(```json) 금지.
            JSON의 문자열 값(title, reason 등) 내부에 쌍따옴표(")를 사용하지 말고, 필요시 홑따옴표(')를 사용하세요.
            최상위 key는 selected_logs, removed_logs, moved_logs 3개만 사용하세요.
            각 로그에는 반드시 article_id, url, title, score, reason을 포함하세요.
            이동 로그는 from, to도 포함하세요.

            {{
            "selected_logs": [
                {{
                "article_id": "art_0001",
                "url": "원본 URL",
                "section": "최종 섹션명",
                "title": "기사 제목",
                "score": 8,
                "reason": "유지 사유"
                }}
            ],
            "removed_logs": [
                {{
                "article_id": "art_0002",
                "url": "원본 URL",
                "section": "삭제 전 섹션명",
                "title": "기사 제목",
                "score": 3,
                "reason": "삭제 사유"
                }}
            ],
            "moved_logs": [
                {{
                "article_id": "art_0003",
                "url": "원본 URL",
                "title": "기사 제목",
                "score": 8,
                "from": "기존 섹션명",
                "to": "이동할 기존 섹션명",
                "reason": "이동 사유"
                }}
            ]
            }}
        """

        log_print("[Gemini] 프롬프트 생성 완료. API 요청을 보냅니다...", log_callback)
        start_time = time.time()

        response = call_gemini_with_retry(
            client=client,
            model=TARGET_MODEL,
            prompt=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
            log_callback=log_callback,
            max_retries=3,
        )

        end_time = time.time()
        stop_event.set()
        timer_thread.join(timeout=2.0)

        total_time = end_time - start_time
        log_print(f"[Gemini] API 요청 완료! (총 {total_time:.1f}초 소요)", log_callback)

        raw_json_data = safe_parse_json(getattr(response, "text", ""))
        result_dict = normalize_result_dict(raw_json_data)

        final_html, selected_logs, removed_logs, moved_logs = apply_gemini_decisions_to_html(
            raw_html_data=raw_html_data,
            result_dict=result_dict,
            log_callback=log_callback,
        )

        log_print(f"[Gemini] 뉴스레터 큐레이션이 완료되었습니다. 유지된 기사 수: {len(selected_logs)}", log_callback)
        log_print(f"[Gemini] 뉴스레터 큐레이션이 완료되었습니다. 삭제된 기사 수: {len(removed_logs)}", log_callback)
        log_print(f"[Gemini] 뉴스레터 큐레이션이 완료되었습니다. 이동된 기사 수: {len(moved_logs)}", log_callback)

        return final_html, selected_logs, removed_logs, moved_logs

    except Exception as e:
        log_print(f"[오류] Gemini API 요청/HTML 재조립 중 오류가 발생했습니다.: {type(e).__name__}: {e}", log_callback)
        return raw_html_data, [], [], []
    finally:
        stop_event.set()
        timer_thread.join(timeout=2.0)

def save_results_to_file(final_html, selected_logs, removed_logs, moved_logs, log_callback=None):
    log_print("결과 파일 저장을 시작합니다...", log_callback)

    # 저장할 폴더 경로 설정
    html_dir = os.path.join(current_folder, "HTML_Output")
    log_dir = os.path.join(current_folder, "Logs")

    # 폴더가 없으면 생성
    if not os.path.exists(html_dir):
        os.makedirs(html_dir)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 파일 구분용 타임스탬프 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # HTML 파일 저장
    html_filename = f"newsletter_final_{timestamp}.html"
    html_path = os.path.join(html_dir, html_filename)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(final_html)
    log_print(f"[성공] 최종 HTML 파일이 저장되었습니다: {html_path}", log_callback)

    # 로그 파일 저장
    log_filename = f"logs_{timestamp}.json"
    log_path = os.path.join(log_dir, log_filename)

    log_data = {
        "saved_at": timestamp,
        "selected_count": len(selected_logs),
        "removed_count": len(removed_logs),
        "moved_count": len(moved_logs),
        "selected_logs": selected_logs,
        "removed_logs": removed_logs,
        "moved_logs": moved_logs
    }

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=4)
    log_print(f"[성공] 로그 파일이 저장되었습니다: {log_path}", log_callback)


def paste_final_html(driver, final_html, log_callback=None):
    log_print("최종 HTML 본문 붙여넣기를 수행합니다...", log_callback)

    try:
        textarea = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "NamoSE_editorshtml_NamoEditor"))
        )

        # 클립보드에 최종 HTML 복사
        pyperclip.copy(final_html)

        # 붙여넣기 (Ctrl + V)
        textarea.send_keys(Keys.CONTROL, 'v')
        log_print("[성공] 최종 HTML 본문이 붙여넣기 되었습니다.", log_callback)
        log_print(final_html, log_callback)
    except Exception as e:
        log_print(f"[오류] 최종 HTML 본문 붙여넣기 중 오류가 발생했습니다.: {e}", log_callback)


def click_mail_button(driver, log_callback=None):
    log_print("메일을 전송합니다...", log_callback)
    try:
        driver.switch_to.default_content()
        WebDriverWait(driver, 15).until(EC.frame_to_be_available_and_switch_to_it("main"))

        # 버튼 찾기
        mail_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "send"))
        )

        # 클릭
        mail_btn.click()
        log_print("[성공] 버튼을 클릭했습니다.", log_callback)

        # 팝업(선택)
        try:
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            log_print(f"[알림] {alert.text}", log_callback)
        except TimeoutException:
            pass
    except Exception as e:
        log_print(f"[오류] 메일 전송 실패: {e}", log_callback)


def main(raw_html_data, emp_no, user_pw, log_callback=None):
    if not raw_html_data:
        log_print("[실패] 뉴스레터 HTML 데이터를 받지 못했습니다. 메일 작성 과정을 종료합니다.", log_callback)
        return
    
    driver = driver_init(log_callback)

    alert_off(driver, log_callback)
    login(driver, emp_no, user_pw, log_callback)
    
    click_email(driver, log_callback)
    prepare_email_header(driver, log_callback)
    prepare_email_body(driver, log_callback)

    final_html, selected_logs, removed_logs, moved_logs = using_gemini_api(raw_html_data, log_callback)
    save_results_to_file(final_html, selected_logs, removed_logs, moved_logs, log_callback)

    paste_final_html(driver, final_html, log_callback)
    # click_mail_button(driver, log_callback)
    log_print("모든 과정이 완료되었습니다.", log_callback)


if __name__ == '__main__':
    print("이 파일은 newsletter_GUI.py에서 실행되어야 합니다.")