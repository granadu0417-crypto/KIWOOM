"""
키움증권 자동매매 프로그램 설정 파일
"""

# 계좌 설정
ACCOUNT_TYPE = "MOCK"  # "REAL" or "MOCK" (실계좌/모의투자)
ACCOUNT_NUMBER = ""    # 계좌번호 (실행 시 자동으로 가져옴)

# 매매 설정
MAX_CONDITION_COUNT = 5  # 최대 조건검색식 개수
MAX_BUY_AMOUNT = 1000000  # 1회 최대 매수금액 (원)
TOTAL_BUY_LIMIT = 10000000  # 총 매수 한도 (원)

# API 호출 제한 (초당 5회)
API_CALL_INTERVAL = 0.2  # 초

# 텔레그램 봇 설정
TELEGRAM_ENABLED = False  # 텔레그램 알림 사용 여부
TELEGRAM_TOKEN = ""  # 텔레그램 봇 토큰
TELEGRAM_CHAT_ID = ""  # 텔레그램 채팅 ID

# 로그 설정
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "logs/trading.log"

# GUI 설정
WINDOW_TITLE = "키움증권 자동매매 프로그램"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800

# 매수 기본 설정
DEFAULT_BUY_SETTINGS = {
    "immediate_buy": True,  # 즉시 매수
    "price_type": "market",  # market: 시장가, limit: 지정가
    "quantity_type": "amount",  # amount: 금액, shares: 주식수
    "buy_amount": 100000,  # 매수 금액
    "enable_split_buy": False,  # 분할 매수
    "split_count": 1,  # 분할 횟수
    "enable_averaging_down": False,  # 물타기
    "averaging_down_rate": -3.0,  # 물타기 진입 비율 (%)
    "enable_pyramid": False,  # 불타기 (추가 매수)
    "pyramid_rate": 3.0,  # 불타기 진입 비율 (%)
}

# 매도 기본 설정
DEFAULT_SELL_SETTINGS = {
    # 익절 설정
    "enable_profit_cut": True,  # 익절 사용
    "profit_cut_rate": 5.0,  # 익절 비율 (%)
    "enable_split_sell": False,  # 분할 매도
    "split_sell_rates": [3.0, 5.0, 7.0],  # 분할 매도 비율 (%)

    # 손절 설정
    "enable_loss_cut": True,  # 손절 사용
    "loss_cut_rate": -3.0,  # 손절 비율 (%)

    # 스탑로스 설정
    "enable_trailing_stop": False,  # 트레일링 스탑
    "trailing_stop_rate": -2.0,  # 트레일링 스탑 비율 (%)

    # 이익보존 설정
    "enable_profit_protect": False,  # 이익보존 사용
    "profit_protect_trigger": 5.0,  # 이익보존 발동 비율 (%)
    "profit_protect_sell": 2.0,  # 이익보존 매도 비율 (%)

    # 기타 매도 설정
    "enable_time_exit": False,  # 시간 청산
    "time_exit_hour": 15,  # 청산 시각 (시)
    "time_exit_minute": 20,  # 청산 시각 (분)
}

# 조건검색식 설정 (5개 슬롯)
CONDITION_SLOTS = [
    {
        "enabled": False,
        "condition_name": "",
        "condition_index": 0,
        "buy_settings": DEFAULT_BUY_SETTINGS.copy(),
        "sell_settings": DEFAULT_SELL_SETTINGS.copy(),
        "allow_duplicate": False,  # 중복 매수 허용
        "allow_rebuy": True,  # 재매수 허용
    }
    for _ in range(MAX_CONDITION_COUNT)
]

# 블랙리스트 (매매 제외 종목)
BLACKLIST = []

# 거래 시간 설정
TRADING_START_TIME = "09:00"
TRADING_END_TIME = "15:20"
