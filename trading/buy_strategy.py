"""
매수 전략 모듈
"""
from PyQt5.QtCore import QObject, pyqtSignal
import time


class BuyStrategy(QObject):
    """매수 전략 관리 클래스"""

    # 시그널 정의
    buy_order_sent = pyqtSignal(str, int, int, str)  # 종목코드, 수량, 가격, 주문타입
    buy_completed = pyqtSignal(str, int, int)  # 종목코드, 체결수량, 체결가격

    def __init__(self, kiwoom_api, config):
        super().__init__()
        self.api = kiwoom_api
        self.config = config

        # 매수 대기 목록
        self.buy_queue = []

        # 매수 완료 목록 (종목코드: 정보)
        self.bought_stocks = {}

        # 매수 진행 중 목록
        self.buying_stocks = set()

    def add_to_buy_queue(self, code, slot_number, settings):
        """매수 대기 목록에 추가"""
        stock_name = self.api.get_master_code_name(code)

        # 블랙리스트 체크
        if code in self.config.get('BLACKLIST', []):
            print(f"[매수 제외] {stock_name}({code}) - 블랙리스트")
            return False

        # 중복 매수 체크
        if not settings.get('allow_duplicate', False):
            if code in self.bought_stocks:
                print(f"[매수 제외] {stock_name}({code}) - 이미 보유 중")
                return False

        # 매수 중인지 체크
        if code in self.buying_stocks:
            print(f"[매수 제외] {stock_name}({code}) - 매수 진행 중")
            return False

        # 큐에 추가
        self.buy_queue.append({
            'code': code,
            'name': stock_name,
            'slot_number': slot_number,
            'settings': settings,
            'timestamp': time.time()
        })

        print(f"[매수 대기] {stock_name}({code}) - 슬롯{slot_number}")
        return True

    def execute_buy(self, item):
        """매수 실행"""
        code = item['code']
        name = item['name']
        settings = item['settings']

        # 매수 진행 중 표시
        self.buying_stocks.add(code)

        try:
            # 매수 수량 계산
            quantity, price = self._calculate_buy_quantity_and_price(code, settings)

            if quantity == 0:
                print(f"[매수 실패] {name}({code}) - 수량 계산 오류")
                return False

            # 호가 구분 결정
            hoga_gb = self._get_hoga_type(settings.get('price_type', 'market'))

            # 주문 전송
            order_type = 1  # 신규 매수
            screen_no = "0101"
            rqname = f"매수_{code}"

            ret = self.api.send_order(
                rqname,
                screen_no,
                self.api.account_number,
                order_type,
                code,
                quantity,
                price,
                hoga_gb,
                ""
            )

            if ret == 0:
                # 시장가인 경우 실제 매수가를 현재가로 저장
                actual_buy_price = price if price > 0 else self._get_current_price(code)

                print(f"[매수 주문] {name}({code}) {quantity}주 @ {actual_buy_price:,}원")
                self.buy_order_sent.emit(code, quantity, actual_buy_price, hoga_gb)

                # 매수 완료 목록에 추가 (임시)
                self.bought_stocks[code] = {
                    'name': name,
                    'quantity': quantity,
                    'buy_price': actual_buy_price,
                    'slot_number': item['slot_number'],
                    'settings': settings,
                    'buy_time': time.time(),
                    'additional_buys': []  # 추가 매수 이력
                }

                # 실시간 시세 등록
                self._register_real_price(code)

                return True
            else:
                print(f"[매수 실패] {name}({code}) - 주문 전송 오류: {ret}")
                return False

        finally:
            # 매수 진행 중 해제
            self.buying_stocks.discard(code)

    def _calculate_buy_quantity_and_price(self, code, settings):
        """매수 수량 및 가격 계산"""
        # 현재가 조회 필요 (간단히 시장가로 처리)
        current_price = self._get_current_price(code)

        if current_price == 0:
            return 0, 0

        # 매수 금액
        buy_amount = settings.get('buy_amount', 100000)

        # 수량 계산
        quantity = int(buy_amount / current_price)

        # 가격 결정
        if settings.get('price_type') == 'market':
            price = 0  # 시장가
        else:
            price = current_price  # 지정가

        return quantity, price

    def _get_current_price(self, code):
        """현재가 조회 (간단 구현)"""
        # 실제로는 TR을 통해 조회해야 하지만, 간단히 처리
        # TODO: opt10001 TR을 통한 현재가 조회 구현
        return 10000  # 임시값

    def _get_hoga_type(self, price_type):
        """호가 구분 반환"""
        if price_type == 'market':
            return "03"  # 시장가
        elif price_type == 'limit':
            return "00"  # 지정가
        else:
            return "03"  # 기본값: 시장가

    def execute_additional_buy(self, code, buy_type):
        """추가 매수 실행 (물타기/불타기)
        buy_type: 'averaging_down' (물타기) or 'pyramid' (불타기)
        """
        if code not in self.bought_stocks:
            return False

        stock_info = self.bought_stocks[code]
        settings = stock_info['settings']

        # 물타기
        if buy_type == 'averaging_down' and settings.get('enable_averaging_down', False):
            return self._execute_averaging_down(code, stock_info)

        # 불타기
        elif buy_type == 'pyramid' and settings.get('enable_pyramid', False):
            return self._execute_pyramid(code, stock_info)

        return False

    def _execute_averaging_down(self, code, stock_info):
        """물타기 실행"""
        # 현재가 조회
        current_price = self._get_current_price(code)
        buy_price = stock_info['buy_price']

        # 하락률 계산
        drop_rate = ((current_price - buy_price) / buy_price) * 100

        # 물타기 조건 체크
        averaging_down_rate = stock_info['settings'].get('averaging_down_rate', -3.0)

        if drop_rate <= averaging_down_rate:
            print(f"[물타기 실행] {stock_info['name']}({code}) {drop_rate:.2f}%")
            # 추가 매수 로직
            # TODO: 실제 추가 매수 구현
            return True

        return False

    def _execute_pyramid(self, code, stock_info):
        """불타기 실행 (추가 매수)"""
        # 현재가 조회
        current_price = self._get_current_price(code)
        buy_price = stock_info['buy_price']

        # 상승률 계산
        rise_rate = ((current_price - buy_price) / buy_price) * 100

        # 불타기 조건 체크
        pyramid_rate = stock_info['settings'].get('pyramid_rate', 3.0)

        if rise_rate >= pyramid_rate:
            print(f"[불타기 실행] {stock_info['name']}({code}) {rise_rate:.2f}%")
            # 추가 매수 로직
            # TODO: 실제 추가 매수 구현
            return True

        return False

    def _register_real_price(self, code):
        """실시간 시세 등록"""
        try:
            # 실시간 시세 등록 (주식체결)
            # FID: 10=현재가, 12=등락률, 13=누적거래량
            fid_list = "10;12;13"
            screen_no = "1000"
            self.api.set_real_reg(screen_no, code, fid_list, "1")  # "1"=추가 등록
            print(f"[실시간 시세 등록] {code}")
        except Exception as e:
            print(f"[실시간 시세 등록 실패] {code}: {e}")

    def add_existing_holdings(self, holdings):
        """기존 보유종목을 매수 목록에 추가"""
        for code, info in holdings.items():
            if code not in self.bought_stocks:
                # 기존 보유종목에는 기본 설정 적용
                default_settings = {
                    'profit_cut_rate': 5.0,
                    'loss_cut_rate': -3.0,
                    'enable_profit_cut': True,
                    'enable_loss_cut': True,
                    'enable_trailing_stop': False,
                    'trailing_stop_rate': 0.0,
                }

                # 슬롯 번호는 0으로 설정 (기존 보유)
                self.bought_stocks[code] = {
                    'name': info['name'],
                    'quantity': info['quantity'],
                    'buy_price': info['buy_price'],
                    'slot_number': 0,  # 기존 보유는 슬롯 0
                    'settings': default_settings,  # 기본 매도 설정
                    'buy_time': 0,  # 시간 정보 없음
                    'additional_buys': []
                }

                # 실시간 시세 등록
                self._register_real_price(code)

                print(f"[기존 보유종목 등록] {info['name']}({code}) | 수량:{info['quantity']} | 매입가:{info['buy_price']:,}")

    def get_bought_stocks(self):
        """매수 완료 종목 목록 반환"""
        return self.bought_stocks

    def remove_stock(self, code):
        """매수 목록에서 제거 (매도 완료 시)"""
        if code in self.bought_stocks:
            del self.bought_stocks[code]
            print(f"[매수 목록 제거] {code}")

            # 실시간 시세 해제
            try:
                self.api.set_real_remove("1000", code)
                print(f"[실시간 시세 해제] {code}")
            except:
                pass

    def clear_buy_queue(self):
        """매수 대기 큐 초기화"""
        self.buy_queue.clear()
