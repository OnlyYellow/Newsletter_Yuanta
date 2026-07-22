# 📰 뉴스레터 자동화 및 AI 큐레이션 프로그램

## 📌 프로젝트 개요
이 프로젝트는 네이버 뉴스를 크롤링하여 특정 키워드(금융, IT, 증권사, AI, 보안 등) 기반의 기사를 수집하고, **Gemini AI**를 통해 기사의 적합성을 평가 및 큐레이션한 후, 사내 웹메일 시스템을 통해 자동으로 뉴스레터 HTML을 작성해 주는 자동화 프로그램입니다. 직관적인 사용자 UI(GUI)를 제공하여 실무자가 버튼 클릭 한 번으로 뉴스레터 초안을 작성할 수 있도록 돕습니다.

## 🚀 주요 기능
- **맞춤형 뉴스 크롤링:** 네이버 뉴스 검색을 통해 8가지 주요 카테고리(증권사 서비스 도입, 전산장애/오류, 클라우드, 금융 보안, 핀테크/AI 등)의 최신 기사 수집. (휴일/주말 일자 자동 계산 포함)
- **AI 기반 큐레이션 (Gemini API):** 수집된 기사를 분석하여 금융 IT와의 연관성(10점 만점)을 평가하고, 부적합 기사 자동 삭제 및 문맥에 맞는 카테고리 재배치 지원.
- **HTML 뉴스레터 자동 생성:** 수집 및 정제된 데이터를 바탕으로 시각적으로 깔끔한 형태의 이메일용 HTML 뉴스레터 자동 렌더링.
- **사내 메일 제어 자동화 (Selenium):** Edge WebDriver를 활용하여 사내 웹메일 시스템에 자동 로그인, 수신자 지정, 최종 HTML 본문 삽입 등 메일 작성 프로세스 전반을 자동화.
- **사용자 설정 자동 저장:** 사용자의 사번, 로컬 Edge 드라이버 경로 등을 `config.json`에 저장하여 다음 실행 시 자동으로 불러오는 편의 기능 제공.

## 📂 핵심 파일 구성 (실행 코드)
- `newsletter_GUI.py` (메인 실행 파일): 프로그램의 사용자 인터페이스(Tkinter) 화면을 구성하고 구성 요소를 관리. 크롤링 및 1차 HTML 생성 역할 담당.
- `newsletter_mail_with_AI.py` (백그라운드 로직): Selenium을 이용한 웹메일 브라우저 자동 제어, Gemini AI API 호출을 통한 기사 큐레이션, 최종 HTML 병합 및 붙여넣기 처리 담당.

## 📁 프로그램 실행 시 생성되는 폴더 및 파일 (결과물)
프로그램이 1회 이상 정상적으로 구동된 후에는, 작업 내역과 결과물을 보존하기 위해 아래와 같은 폴더와 파일들이 자동 생성됩니다.

- **`HTML_Output/` 폴더**
  - `newsletter_final_YYYYMMDD_HHMMSS.html`: Gemini AI의 큐레이션(불필요 기사 삭제, 섹션 재배치 등)이 모두 반영된 최종 뉴스레터 HTML 파일입니다.
- **`Logs/` 폴더**
  - `logs_YYYYMMDD_HHMMSS.json`: AI가 어떤 기사를 유지(selected), 삭제(removed), 이동(moved)했는지에 대한 상세 평가 점수와 큐레이션 사유를 기록한 로그 파일입니다.
- **`crawled_html/` 폴더**
  - `crawled_html_YYYYMMDD_HHMMSS.json`: 뉴스 크롤링 직후, 각 기사의 본문 일부와 요약 정보를 수집해 둔 중간 데이터 백업 파일입니다.
- **`config.json` (프로젝트 루트)**
  - 사용자가 GUI 창에 입력했던 Edge 드라이버 경로, 사번, VDI 여부 등을 다음 실행 시 그대로 불러오기 위해 자동 저장하는 설정 파일입니다.
- **로컬 PC 경로 백업물 (`C:\Users\{사원번호}\newsletter` 등)**
  - `newsletter_YYYY-MM-DD_HH시MM분.txt`: 1차 크롤링 직후 만들어진 원본 뉴스레터 텍스트(HTML 구조 포함) 형태의 백업 파일입니다. VDI 환경 체크 여부에 따라 저장 경로가 달라집니다.

## 🛠️ 요구 사항 (Prerequisites)
- **Python 3.8+**
- Microsoft Edge 브라우저 및 호환되는 [Edge WebDriver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)
- **필요한 Python 패키지:**
  ```bash
  pip install python-dotenv selenium beautifulsoup4 requests holidays pyperclip google-genai
  ```

## ⚙️ 설치 및 실행 방법
1. 본 저장소를 클론하거나 2개의 Python 파일을 동일한 폴더에 다운로드합니다.
2. 터미널에서 요구 사항의 패키지들을 모두 설치합니다.
3. 프로젝트 폴더 최상단에 `.env` 파일을 생성하고 아래와 같이 발급받은 Gemini API Key를 입력합니다.
   ```text
   GOOGLE_API_KEY=발급받은_API_키를_여기에_입력
   ```
4. 본인 PC의 Edge 브라우저 버전과 일치하는 WebDriver(.exe)를 다운로드하여 저장합니다.
5. 아래 명령어를 통해 프로그램을 실행합니다. (또는 파일 확장자를 `.pyw`로 변경하여 콘솔 창 없이 실행 가능)
   ```bash
   python newsletter_GUI.py
   ```
6. 실행된 GUI 화면에서 Edge 드라이버 경로, 사원번호, 비밀번호를 입력하고 **[START]** 버튼을 클릭합니다.

## ⚠️ 보안 및 주의 사항 (Security Notice)
- **API Key 노출 주의:** `.env` 파일에 저장된 API Key가 GitHub에 업로드되지 않도록 반드시 `.gitignore` 파일에 `.env`를 추가해 주세요.
- **개인정보 취급:** 자동 로그인을 위해 사용자가 입력한 비밀번호와 사번이 `config.json`에 평문으로 자동 저장됩니다. 따라서 `.gitignore` 파일에 `config.json`도 함께 추가하여 개인정보가 깃허브에 올라가지 않도록 설정하는 것을 권장합니다.
- **사내망 접속:** 사내 메일 전송 자동화 기능은 사내 인트라넷(VDI 또는 VPN) 환경에서 정상 작동할 수 있도록 작성되었습니다.
