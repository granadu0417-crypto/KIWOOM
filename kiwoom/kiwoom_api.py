"""
키움증권 OpenAPI+ 연동 클래스
"""
import sys
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtWidgets import QApplication
import time
from datetime import datetime


class KiwoomAPI(QAxWidget):
    """키움 OpenAPI+ 기본 클래스"""

    def __init__(self):
        super().__init__()

        # OpenAPI+ 사용 가능 여부
        self.is_api_available = False

        try:
            self._create_kiwoom_instance()
            self.is_api_available = True
        except Exception as e:
            print(f"\n{'='*60}")
            print("⚠️  키움 OpenAPI+ 연결 실패!")
            print(f"{'='*60}")
            print("\n다음 단계를 따라 설치하세요:\n")
            print("1. 키움증권 HTS(영웅문) 실행 후 로그인")
            print("2. 메뉴: 시스템(S) → OpenAPI+ → 조회 및 신청")
            print("3. OpenAPI+ 사용 신청")
            print("4. 다운로드 탭에서 'OpenAPI+ 모듈' 다운로드 및 설치")
            print("5. 컴퓨터 재시작")
            print("\n또는:")
            print("https://www.kiwoom.com/h/customer/download/VOpenApiInfoView")
            print("에서 직접 다운로드하세요.")
            print(f"\n{'='*60}\n")
            # 에러를 발생시키지 않고 계속 진행
            return

        # 이벤트 루프
        self.login_event_loop = None
        self.request_event_loop = QEventLoop()

        # 데이터 저장
        self.account_number = None
        self.account_list = []
        self.tr_data = {}
        self.condition_list = {}

        # API 호출 제한 (초당 5회)
        self.api_call_count = 0
        self.api_call_time = time.time()

        # 시그널 연결
        if self.is_api_available:
            self._connect_signals()

        # 로그인 상태
        self.is_connected = False

        # 실시간 시세 데이터 저장 {종목코드: {현재가, 등락률, ...}}
        self.real_data = {}

    def _create_kiwoom_instance(self):
        """키움 OpenAPI+ 인스턴스 생성"""
        result = self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
        if not result:
            raise Exception("OpenAPI+ 컨트롤 생성 실패")

    def _connect_signals(self):
        """시그널과 슬롯 연결"""
        # 로그인 관련
        self.OnEventConnect.connect(self._on_event_connect)

        # TR 데이터 수신
        self.OnReceiveTrData.connect(self._on_receive_tr_data)

        # 실시간 데이터 수신
        self.OnReceiveRealData.connect(self._on_receive_real_data)

        # 체결 데이터 수신
        self.OnReceiveChejanData.connect(self._on_receive_chejan_data)

        # 조건검색 관련
        self.OnReceiveConditionVer.connect(self._on_receive_condition_ver)
        self.OnReceiveTrCondition.connect(self._on_receive_tr_condition)
        self.OnReceiveRealCondition.connect(self._on_receive_real_condition)

        # 메시지 수신
        self.OnReceiveMsg.connect(self._on_receive_msg)

    # ===== 로그인 관련 =====
    def comm_connect(self):
        """로그인 요청"""
        self.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def _on_event_connect(self, err_code):
        """로그인 결과 처리"""
        if err_code == 0:
            print("[로그인 성공]")
            self.is_connected = True
        else:
            print(f"[로그인 실패] 에러코드: {err_code}")
            self.is_connected = False

        if self.login_event_loop:
            self.login_event_loop.exit()

    def get_connect_state(self):
        """연결 상태 확인"""
        ret = self.dynamicCall("GetConnectState()")
        return ret == 1

    def get_login_info(self, tag):
        """로그인 정보 가져오기"""
        ret = self.dynamicCall("GetLoginInfo(QString)", tag)
        return ret

    def get_server_gubun(self):
        """접속 서버 구분
        Returns:
            str: "1" (모의투자) 또는 "" (실서버)
        """
        try:
            # 방법 1: API 직접 호출
            ret = self.dynamicCall("GetLoginInfo(QString)", "GetServerGubun")
            if ret:
                return ret
        except:
            pass

        # 방법 2: 계좌번호로 판별 (모의투자 계좌는 8로 시작)
        if self.account_list:
            first_account = self.account_list[0]
            if first_account.startswith('8'):
                return "1"  # 모의투자

        return ""  # 실서버

    # ===== 계좌 관련 =====
    def get_account_list(self):
        """계좌번호 목록 가져오기"""
        account_list = self.get_login_info("ACCNO")
        self.account_list = account_list.split(';')[:-1]
        return self.account_list

    def set_account_number(self, account_number):
        """사용할 계좌번호 설정"""
        self.account_number = account_number

    def request_balance(self):
        """계좌평가잔고내역 요청 (OPW00018)"""
        if not self.account_number:
            print("[오류] 계좌번호가 설정되지 않았습니다")
            return {}

        self.tr_data['holdings'] = {}

        # TR 입력값 설정
        self.set_input_value("계좌번호", self.account_number)
        self.set_input_value("비밀번호", "")
        self.set_input_value("비밀번호입력매체구분", "00")
        self.set_input_value("조회구분", "1")  # 1:합산, 2:개별

        # TR 요청
        self.comm_rq_data("계좌평가잔고내역요청", "opw00018", 0, "2000")
        self.request_event_loop.exec_()

        return self.tr_data.get('holdings', {})

    # ===== TR 데이터 요청 =====
    def _api_call_limit(self):
        """API 호출 제한 체크 (초당 5회)"""
        current_time = time.time()
        if current_time - self.api_call_time >= 1.0:
            self.api_call_count = 0
            self.api_call_time = current_time

        if self.api_call_count >= 5:
            sleep_time = 1.0 - (current_time - self.api_call_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.api_call_count = 0
            self.api_call_time = time.time()

        self.api_call_count += 1

    def set_input_value(self, id, value):
        """TR 입력값 설정"""
        self.dynamicCall("SetInputValue(QString, QString)", id, value)

    def comm_rq_data(self, rqname, trcode, next, screen_no):
        """TR 데이터 요청"""
        self._api_call_limit()
        self.dynamicCall("CommRqData(QString, QString, int, QString)",
                         rqname, trcode, next, screen_no)
        self.request_event_loop.exec_()

    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        """TR 데이터 수신"""
        if next == '2':
            self.has_next_tr_data = True
        else:
            self.has_next_tr_data = False

        if rqname == "예수금상세현황요청":
            self._handle_deposit_data()
        elif rqname == "계좌평가잔고내역요청":
            self._handle_balance_data()
        elif rqname == "주식기본정보요청":
            self._handle_stock_info_data()

        self.request_event_loop.exit()

    def _handle_deposit_data(self):
        """예수금 데이터 처리"""
        deposit = self.get_comm_data("opw00001", "예수금상세현황요청", 0, "예수금")
        self.tr_data['deposit'] = int(deposit)

    def _handle_balance_data(self):
        """잔고 데이터 처리 (OPW00018)"""
        holdings = {}

        # 보유 종목 수
        cnt = self.get_repeat_cnt("opw00018", "계좌평가잔고내역요청")

        for i in range(cnt):
            code = self.get_comm_data("opw00018", "계좌평가잔고내역요청", i, "종목번호").strip()
            name = self.get_comm_data("opw00018", "계좌평가잔고내역요청", i, "종목명").strip()
            quantity = self.get_comm_data("opw00018", "계좌평가잔고내역요청", i, "보유수량").strip()
            buy_price = self.get_comm_data("opw00018", "계좌평가잔고내역요청", i, "매입가").strip()
            current_price = self.get_comm_data("opw00018", "계좌평가잔고내역요청", i, "현재가").strip()

            # 데이터 정제
            code = code.strip('A')  # 종목코드 앞의 'A' 제거
            quantity = int(quantity) if quantity else 0
            buy_price = abs(int(buy_price)) if buy_price else 0
            current_price = abs(int(current_price)) if current_price else 0

            if code and quantity > 0:
                holdings[code] = {
                    'name': name,
                    'quantity': quantity,
                    'buy_price': buy_price,
                    'current_price': current_price
                }

        self.tr_data['holdings'] = holdings

    def _handle_stock_info_data(self):
        """주식정보 데이터 처리"""
        pass

    def get_comm_data(self, trcode, rqname, index, item_name):
        """TR 데이터 가져오기"""
        ret = self.dynamicCall("GetCommData(QString, QString, int, QString)",
                               trcode, rqname, index, item_name)
        return ret.strip()

    def get_repeat_cnt(self, trcode, rqname):
        """반복 데이터 개수"""
        ret = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        return ret

    # ===== 실시간 데이터 =====
    def _on_receive_real_data(self, code, real_type, real_data):
        """실시간 데이터 수신"""
        if real_type == "주식체결":
            # 실시간 시세 데이터 저장
            current_price = self.get_comm_real_data(code, 10)  # 현재가
            change_rate = self.get_comm_real_data(code, 12)    # 등락률
            volume = self.get_comm_real_data(code, 13)         # 누적거래량

            # 데이터 저장
            self.real_data[code] = {
                'current_price': abs(int(current_price)),  # 부호 제거
                'change_rate': float(change_rate),
                'volume': int(volume)
            }

    def get_comm_real_data(self, code, fid):
        """실시간 데이터 가져오기
        FID:
        10: 현재가
        11: 전일대비
        12: 등락률
        13: 누적거래량
        27: (최우선)매도호가
        28: (최우선)매수호가
        """
        ret = self.dynamicCall("GetCommRealData(QString, int)", code, fid)
        return ret.strip()

    def set_real_reg(self, screen_no, code_list, fid_list, real_type):
        """실시간 데이터 등록
        screen_no: 화면번호
        code_list: 종목코드 리스트 (';'로 구분)
        fid_list: FID 리스트 (';'로 구분)
        real_type: "0"=기존 등록 제거 후 등록, "1"=기존 등록에 추가
        """
        ret = self.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                               screen_no, code_list, fid_list, real_type)
        return ret

    def set_real_remove(self, screen_no, code):
        """실시간 데이터 해제"""
        self.dynamicCall("SetRealRemove(QString, QString)", screen_no, code)

    # ===== 주문 관련 =====
    def send_order(self, rqname, screen_no, acc_no, order_type, code, quantity, price, hoga_gb, org_order_no):
        """주문 전송
        order_type: 1-신규매수, 2-신규매도, 3-매수취소, 4-매도취소, 5-매수정정, 6-매도정정
        hoga_gb: 00-지정가, 03-시장가, 05-조건부지정가, 06-최유리지정가, 등
        """
        self._api_call_limit()
        ret = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                               [rqname, screen_no, acc_no, order_type, code, quantity, price, hoga_gb, org_order_no])
        return ret

    def _on_receive_chejan_data(self, gubun, item_cnt, fid_list):
        """체결/잔고 데이터 수신
        gubun: "0"=주문체결, "1"=잔고통보, "3"=특이신호
        """
        if gubun == "0":  # 주문체결
            # 체결 정보
            order_status = self.get_chejan_data(913)  # 주문상태
            code = self.get_chejan_data(9001)         # 종목코드
            order_num = self.get_chejan_data(9203)    # 주문번호
            order_name = self.get_chejan_data(302)    # 종목명
            order_qty = self.get_chejan_data(900)     # 주문수량
            order_price = self.get_chejan_data(901)   # 주문가격
            exec_qty = self.get_chejan_data(911)      # 체결수량
            exec_price = self.get_chejan_data(910)    # 체결가

            print(f"[체결통보] {order_name}({code}) | 상태:{order_status} | 체결가:{exec_price} | 체결량:{exec_qty}")

        elif gubun == "1":  # 잔고통보
            # 잔고 정보
            code = self.get_chejan_data(9001)         # 종목코드
            stock_name = self.get_chejan_data(302)    # 종목명
            balance = self.get_chejan_data(930)       # 보유수량
            avg_price = self.get_chejan_data(931)     # 평균단가
            current_price = self.get_chejan_data(10)  # 현재가

            print(f"[잔고통보] {stock_name}({code}) | 보유:{balance} | 평균단가:{avg_price} | 현재가:{current_price}")

    def get_chejan_data(self, fid):
        """체결 데이터 가져오기
        FID:
        9001: 종목코드
        302: 종목명
        900: 주문수량
        901: 주문가격
        902: 미체결수량
        903: 주문구분(매수/매도)
        904: 원주문번호
        905: 주문번호
        908: 주문/체결시간
        909: 체결번호
        910: 체결가
        911: 체결량
        912: 주문수량(체결+미체결)
        913: 주문상태(접수/확인/체결)
        930: 보유수량
        931: 평균단가
        932: 총매입가
        933: 주문가능수량
        """
        ret = self.dynamicCall("GetChejanData(int)", fid)
        return ret.strip()

    # ===== 조건검색 관련 =====
    def get_condition_load(self):
        """조건검색식 목록 요청"""
        ret = self.dynamicCall("GetConditionLoad()")
        return ret

    def _on_receive_condition_ver(self, ret, msg):
        """조건검색식 목록 수신"""
        if ret == 1:
            condition_list = self.dynamicCall("GetConditionNameList()")
            conditions = condition_list.split(';')[:-1]

            for condition in conditions:
                index, name = condition.split('^')
                self.condition_list[name] = int(index)

            print(f"[조건검색식 로드 완료] {len(self.condition_list)}개")
        else:
            print(f"[조건검색식 로드 실패] {msg}")

    def send_condition(self, screen_no, condition_name, index, search_type):
        """조건검색 요청
        search_type: 0-조회, 1-실시간
        """
        ret = self.dynamicCall("SendCondition(QString, QString, int, int)",
                               screen_no, condition_name, index, search_type)
        return ret

    def _on_receive_tr_condition(self, screen_no, code_list, condition_name, index, next):
        """조건검색 결과 수신"""
        pass

    def _on_receive_real_condition(self, code, event_type, condition_name, condition_index):
        """실시간 조건검색 수신
        event_type: I-편입, D-이탈
        """
        pass

    def send_condition_stop(self, screen_no, condition_name, index):
        """조건검색 중지"""
        self.dynamicCall("SendConditionStop(QString, QString, int)",
                         screen_no, condition_name, index)

    # ===== 메시지 =====
    def _on_receive_msg(self, screen_no, rqname, trcode, msg):
        """메시지 수신"""
        print(f"[메시지] {msg}")

    # ===== 유틸리티 =====
    def get_master_code_name(self, code):
        """종목명 가져오기"""
        ret = self.dynamicCall("GetMasterCodeName(QString)", code)
        return ret

    def get_code_list_by_market(self, market):
        """시장별 종목코드 가져오기
        market: 0-코스피, 10-코스닥, 3-ELW, 8-ETF, 등
        """
        ret = self.dynamicCall("GetCodeListByMarket(QString)", market)
        code_list = ret.split(';')[:-1]
        return code_list
