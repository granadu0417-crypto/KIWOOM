"""
트레이딩 컨트롤러 - 모든 모듈을 통합 관리
"""
from PyQt5.QtCore import QObject, pyqtSignal
from kiwoom.kiwoom_api import KiwoomAPI
from trading.condition_manager import ConditionManager
from trading.buy_strategy import BuyStrategy
from trading.sell_strategy import SellStrategy
from utils.logger import TradingLogger
from utils.telegram_bot import TelegramBot
import config.settings as settings


class TradingController(QObject):
    """트레이딩 컨트롤러"""

    # 시그널
    login_completed = pyqtSignal(bool)
    account_updated = pyqtSignal(list)
    condition_list_updated = pyqtSignal(list)
    deposit_updated = pyqtSignal(int)
    log_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # 키움 API
        self.api = KiwoomAPI()

        # 조건검색 관리자
        self.condition_manager = ConditionManager(self.api)

        # 매수/매도 전략
        self.buy_strategy = BuyStrategy(self.api, settings.__dict__)
        self.sell_strategy = SellStrategy(self.api, self.buy_strategy)

        # 로거
        self.logger = TradingLogger()

        # 텔레그램 봇
        if settings.TELEGRAM_ENABLED:
            self.telegram = TelegramBot(settings.TELEGRAM_TOKEN, settings.TELEGRAM_CHAT_ID)
        else:
            self.telegram = None

        # 로그인 상태
        self.is_logged_in = False

        # 시그널 연결
        self.connect_signals()

    def connect_signals(self):
        """시그널 연결"""
        # 조건검색 시그널
        self.condition_manager.condition_occurred.connect(self.on_condition_occurred)
        self.condition_manager.condition_removed.connect(self.on_condition_removed)
        self.condition_manager.condition_loaded.connect(self.on_condition_loaded)

        # 매수 시그널
        self.buy_strategy.buy_order_sent.connect(self.on_buy_order_sent)
        self.buy_strategy.buy_completed.connect(self.on_buy_completed)

        # 매도 시그널
        self.sell_strategy.sell_order_sent.connect(self.on_sell_order_sent)
        self.sell_strategy.sell_completed.connect(self.on_sell_completed)

    # ===== 로그인 관련 =====

    def login(self):
        """로그인"""
        try:
            # API 사용 가능 여부 체크
            if not hasattr(self.api, 'is_api_available') or not self.api.is_api_available:
                self.log_message.emit("⚠️ 키움 OpenAPI+가 설치되지 않았습니다!")
                self.log_message.emit("설치 후 프로그램을 재시작하세요.")
                self.login_completed.emit(False)
                return

            self.log_message.emit("로그인 시도 중...")
            self.api.comm_connect()

            if self.api.is_connected:
                self.is_logged_in = True
                self.log_message.emit("로그인 성공!")

                # 계좌 정보 가져오기
                accounts = self.api.get_account_list()
                self.account_updated.emit(accounts)

                if accounts:
                    self.api.set_account_number(accounts[0])
                    self.log_message.emit(f"계좌 설정: {accounts[0]}")

                # 조건검색식 로드
                self.load_conditions()

                # 텔레그램 알림
                if self.telegram:
                    self.telegram.test_connection()

                self.login_completed.emit(True)
            else:
                self.log_message.emit("로그인 실패")
                self.login_completed.emit(False)

        except Exception as e:
            self.log_message.emit(f"로그인 오류: {e}")
            self.logger.log_error("로그인", str(e))
            self.login_completed.emit(False)

    def load_conditions(self):
        """조건검색식 로드 요청 (비동기)"""
        try:
            self.log_message.emit("조건검색식 로드 중...")
            self.condition_manager.load_conditions()
            # 실제 로드 완료는 on_condition_loaded에서 처리됨
        except Exception as e:
            self.log_message.emit(f"조건검색식 로드 오류: {e}")
            self.logger.log_error("조건검색", str(e))

    def on_condition_loaded(self, conditions):
        """조건검색식 로드 완료 시 (비동기 이벤트)"""
        try:
            self.log_message.emit(f"조건검색식 {len(conditions)}개 로드 완료")
            self.condition_list_updated.emit(conditions)
        except Exception as e:
            self.log_message.emit(f"조건검색식 업데이트 오류: {e}")
            self.logger.log_error("조건검색", str(e))

    # ===== 조건검색 관련 =====

    def start_condition_slot(self, slot_number, condition_name, settings_dict):
        """조건검색 슬롯 시작"""
        try:
            # 슬롯 설정 업데이트
            slot_settings = settings.CONDITION_SLOTS[slot_number]
            slot_settings['enabled'] = True
            slot_settings['condition_name'] = condition_name
            slot_settings['buy_settings']['buy_amount'] = settings_dict.get('buy_amount', 100000)
            slot_settings['sell_settings']['profit_cut_rate'] = settings_dict.get('profit_cut_rate', 5.0)
            slot_settings['sell_settings']['loss_cut_rate'] = settings_dict.get('loss_cut_rate', -3.0)
            slot_settings['sell_settings']['enable_profit_cut'] = True
            slot_settings['sell_settings']['enable_loss_cut'] = True

            # 조건검색 시작
            ret = self.condition_manager.start_condition(slot_number, condition_name)

            if ret:
                self.log_message.emit(f"슬롯{slot_number + 1} 시작: {condition_name}")
            else:
                self.log_message.emit(f"슬롯{slot_number + 1} 시작 실패: {condition_name}")

        except Exception as e:
            self.log_message.emit(f"조건검색 시작 오류: {e}")
            self.logger.log_error("조건검색 시작", str(e))

    def stop_condition_slot(self, slot_number):
        """조건검색 슬롯 중지"""
        try:
            ret = self.condition_manager.stop_condition(slot_number)

            if ret:
                settings.CONDITION_SLOTS[slot_number]['enabled'] = False
                self.log_message.emit(f"슬롯{slot_number + 1} 중지")
            else:
                self.log_message.emit(f"슬롯{slot_number + 1} 중지 실패")

        except Exception as e:
            self.log_message.emit(f"조건검색 중지 오류: {e}")
            self.logger.log_error("조건검색 중지", str(e))

    def on_condition_occurred(self, code, condition_name, slot_number):
        """조건 편입 시"""
        try:
            stock_name = self.api.get_master_code_name(code)
            self.log_message.emit(f"[조건 편입] {condition_name}: {stock_name}({code})")

            # 텔레그램 알림
            if self.telegram:
                self.telegram.send_condition_notification(condition_name, code, stock_name, 'I')

            # 매수 대기열에 추가
            slot_settings = settings.CONDITION_SLOTS[slot_number]
            buy_settings = slot_settings['buy_settings']

            if self.buy_strategy.add_to_buy_queue(code, slot_number, buy_settings):
                # 즉시 매수 실행
                if buy_settings.get('immediate_buy', True):
                    item = self.buy_strategy.buy_queue.pop(0)
                    self.buy_strategy.execute_buy(item)

        except Exception as e:
            self.log_message.emit(f"조건 편입 처리 오류: {e}")
            self.logger.log_error("조건 편입", str(e))

    def on_condition_removed(self, code, condition_name, slot_number):
        """조건 이탈 시"""
        stock_name = self.api.get_master_code_name(code)
        self.log_message.emit(f"[조건 이탈] {condition_name}: {stock_name}({code})")

        # 텔레그램 알림
        if self.telegram:
            self.telegram.send_condition_notification(condition_name, code, stock_name, 'D')

    # ===== 매수 관련 =====

    def on_buy_order_sent(self, code, quantity, price, hoga_type):
        """매수 주문 전송 시"""
        stock_name = self.api.get_master_code_name(code)
        self.log_message.emit(f"[매수 주문] {stock_name}({code}) {quantity}주 @ {price:,}원")

        # 로그 기록
        self.logger.log_order("매수", code, stock_name, quantity, price, "주문 완료")

    def on_buy_completed(self, code, quantity, price):
        """매수 체결 시"""
        stock_name = self.api.get_master_code_name(code)
        self.log_message.emit(f"[매수 체결] {stock_name}({code}) {quantity}주 @ {price:,}원")

        # 텔레그램 알림
        if self.telegram:
            bought_stocks = self.buy_strategy.get_bought_stocks()
            if code in bought_stocks:
                slot_number = bought_stocks[code]['slot_number']
                self.telegram.send_buy_notification(code, stock_name, quantity, price, slot_number)

    # ===== 매도 관련 =====

    def on_sell_order_sent(self, code, quantity, price, reason):
        """매도 주문 전송 시"""
        stock_name = self.api.get_master_code_name(code)
        self.log_message.emit(f"[매도 주문] {stock_name}({code}) {quantity}주 - {reason}")

        # 로그 기록
        self.logger.log_order("매도", code, stock_name, quantity, price, f"{reason}")

    def on_sell_completed(self, code, quantity, sell_price, profit_rate):
        """매도 체결 시"""
        stock_name = self.api.get_master_code_name(code)
        self.log_message.emit(f"[매도 체결] {stock_name}({code}) {quantity}주 @ {sell_price:,}원 ({profit_rate:+.2f}%)")

        # 수익 로그
        # self.logger.log_profit(code, stock_name, buy_price, sell_price, quantity, profit_rate)

        # 텔레그램 알림
        if self.telegram:
            self.telegram.send_sell_notification(code, stock_name, quantity, sell_price, profit_rate, "")

    # ===== 기타 =====

    def sell_all_stocks(self):
        """전체 매도"""
        try:
            self.log_message.emit("[전체 매도 시작]")
            self.sell_strategy.sell_all("전체청산")
        except Exception as e:
            self.log_message.emit(f"전체 매도 오류: {e}")
            self.logger.log_error("전체 매도", str(e))

    def get_bought_stocks(self):
        """보유 종목 목록"""
        return self.buy_strategy.get_bought_stocks()
