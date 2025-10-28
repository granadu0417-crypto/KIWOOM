# 키움증권 자동매매 프로그램

TTN 스타일의 키움증권 자동매매 프로그램입니다.

## 주요 기능

### 📊 핵심 기능
- **조건검색 연동**: 최대 5개의 조건검색식 동시 운용
- **자동 매수/매도**: 설정한 전략에 따라 자동 매매 실행
- **실시간 모니터링**: 보유 종목 및 거래 내역 실시간 확인
- **텔레그램 알림**: 매매 및 조건 편입/이탈 알림

### 💰 매수 전략
- 즉시 매수 / 지정가 매수
- 분할 매수
- 물타기 (하락 시 추가 매수)
- 불타기 (상승 시 추가 매수)
- 중복 매수 제어
- 블랙리스트 관리

### 📈 매도 전략
- 익절 (목표 수익률 달성 시)
- 손절 (손실 한도 도달 시)
- 분할 매도
- 트레일링 스탑
- 이익보존 (수익 보호)
- 시간 청산 (장 마감 전 자동 매도)

## 시스템 요구사항

### 필수 환경
- **운영체제**: Windows 7 이상 (키움 API는 Windows 전용)
- **Python**: 3.7 이상
- **키움증권**: OpenAPI+ 설치 및 신청 완료
- **계좌**: 실계좌 또는 모의투자 계좌

### 필수 프로그램
1. 키움증권 OpenAPI+ ([신청 방법](https://www.kiwoom.com))
2. Python 3.7 이상
3. Visual C++ Redistributable

## 설치 방법

### 1. 키움 OpenAPI+ 설치

1. 키움증권 HTS(영웅문) 로그인
2. 메뉴: `시스템` → `OpenAPI+` → `조회 및 신청`
3. OpenAPI+ 사용 신청
4. OpenAPI+ 모듈 다운로드 및 설치

### 2. Python 패키지 설치

```bash
# 저장소 클론
git clone <repository-url>
cd KIWOOM

# 의존성 설치
pip install -r requirements.txt
```

## 설정 방법

### 1. 기본 설정 (`config/settings.py`)

```python
# 계좌 설정
ACCOUNT_TYPE = "MOCK"  # "REAL" or "MOCK"

# 매매 설정
MAX_BUY_AMOUNT = 1000000  # 1회 최대 매수금액
TOTAL_BUY_LIMIT = 10000000  # 총 매수 한도

# 텔레그램 설정 (선택사항)
TELEGRAM_ENABLED = True
TELEGRAM_TOKEN = "your-bot-token"
TELEGRAM_CHAT_ID = "your-chat-id"
```

### 2. 매수/매도 전략 설정

프로그램 실행 후 GUI에서 각 슬롯별로 설정 가능:
- 매수 금액
- 익절률 (%)
- 손절률 (%)
- 추가 옵션 (분할매수, 물타기, 불타기 등)

## 사용 방법

### 1. 프로그램 실행

```bash
python main.py
```

### 2. 로그인

1. 프로그램 실행 후 `로그인` 버튼 클릭
2. 키움 로그인 창에서 인증 완료
3. 계좌 선택

### 3. 조건검색 설정

1. **조건검색식 준비**
   - 키움 HTS에서 조건검색식 미리 생성
   - 프로그램에서 자동으로 불러옴

2. **슬롯 설정** (최대 5개)
   - 슬롯 활성화 체크
   - 조건검색식 선택
   - 매수금액, 익절/손절률 설정
   - 상세 설정 (⚙️ 버튼)

3. **시작**
   - `시작` 버튼 클릭
   - 조건 편입 시 자동 매수 시작

### 4. 모니터링

- **보유종목 탭**: 현재 보유 종목 및 수익률 실시간 확인
- **거래내역 탭**: 매수/매도 내역 확인
- **로그 탭**: 상세 로그 확인

### 5. 전체 매도

긴급 상황 시 `전체 매도` 버튼으로 모든 보유 종목 즉시 매도

## 프로젝트 구조

```
KIWOOM/
├── main.py                    # 메인 실행 파일
├── requirements.txt           # 의존성 목록
├── README.md                 # 사용 설명서
│
├── config/                   # 설정 파일
│   └── settings.py          # 전역 설정
│
├── kiwoom/                   # 키움 API
│   └── kiwoom_api.py        # API 연동 클래스
│
├── trading/                  # 매매 전략
│   ├── condition_manager.py # 조건검색 관리
│   ├── buy_strategy.py      # 매수 전략
│   ├── sell_strategy.py     # 매도 전략
│   └── trading_controller.py # 통합 컨트롤러
│
├── ui/                       # GUI
│   └── main_window.py       # 메인 윈도우
│
├── utils/                    # 유틸리티
│   ├── logger.py            # 로깅
│   └── telegram_bot.py      # 텔레그램 알림
│
├── logs/                     # 로그 파일
└── data/                     # 데이터 저장
```

## 텔레그램 봇 설정 (선택사항)

### 1. 봇 생성

1. 텔레그램에서 `@BotFather` 검색
2. `/newbot` 명령어로 봇 생성
3. 봇 토큰 받기

### 2. Chat ID 확인

1. 생성한 봇과 대화 시작
2. `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` 접속
3. `chat.id` 확인

### 3. 설정 파일 수정

```python
TELEGRAM_ENABLED = True
TELEGRAM_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID = "987654321"
```

## 안전 수칙

### ⚠️ 중요 주의사항

1. **모의투자로 먼저 테스트**
   - 실계좌 사용 전 반드시 모의투자로 충분히 테스트
   - 최소 1주일 이상 안정성 확인

2. **투자 한도 설정**
   - 적절한 매수 한도 설정
   - 총 투자금액 제한

3. **손절 설정 필수**
   - 모든 전략에 손절률 설정
   - 과도한 손실 방지

4. **정기적인 모니터링**
   - 완전 자동화라도 주기적으로 확인
   - 이상 징후 즉시 대응

5. **백업 및 로그**
   - 중요 설정은 백업
   - 거래 로그 정기적으로 확인

## 문제 해결

### 로그인 실패
- OpenAPI+ 설치 확인
- 공인인증서 유효성 확인
- 방화벽 설정 확인

### 조건검색 로드 실패
- HTS에서 조건검색식 저장 확인
- 조건검색 개수 제한 확인 (최대 100개)

### 주문 실패
- 계좌 잔고 확인
- 주문 가능 시간 확인 (09:00~15:20)
- API 호출 제한 확인

## 로그 파일

- `logs/trade_YYYYMMDD.log`: 거래 로그
- `logs/order_YYYYMMDD.log`: 주문 로그
- `logs/error_YYYYMMDD.log`: 에러 로그

## 면책 조항

이 프로그램은 교육 및 학습 목적으로 제공됩니다.

- 투자 손실에 대한 책임은 전적으로 사용자에게 있습니다
- 실제 투자 전 충분한 테스트를 권장합니다
- 프로그램 오류로 인한 손실에 대해 책임지지 않습니다

## 라이선스

MIT License

## 기여

이슈 및 PR은 언제나 환영합니다!

## 참고 자료

- [키움 OpenAPI+ 가이드](https://www.kiwoom.com)
- [WikiDocs - 키움증권 API](https://wikidocs.net/book/1173)
- [TTN 자동매매 매뉴얼](https://wikidocs.net/book/1240)
