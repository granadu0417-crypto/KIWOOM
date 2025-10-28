"""
조건검색식 관리 모듈
"""
from PyQt5.QtCore import QObject, pyqtSignal


class ConditionManager(QObject):
    """조건검색 관리 클래스"""

    # 시그널 정의
    condition_occurred = pyqtSignal(str, str, int)  # 종목코드, 조건검색명, 슬롯번호
    condition_removed = pyqtSignal(str, str, int)  # 종목코드, 조건검색명, 슬롯번호

    def __init__(self, kiwoom_api):
        super().__init__()
        self.api = kiwoom_api

        # 조건검색 슬롯 (최대 5개)
        self.condition_slots = []
        for i in range(5):
            self.condition_slots.append({
                'slot_number': i,
                'enabled': False,
                'condition_name': '',
                'condition_index': 0,
                'screen_no': f'010{i}',
                'matched_stocks': set(),  # 편입된 종목 목록
                'is_running': False
            })

        # API 시그널 연결
        self.api.OnReceiveTrCondition.connect(self._on_receive_tr_condition)
        self.api.OnReceiveRealCondition.connect(self._on_receive_real_condition)

    def load_conditions(self):
        """조건검색식 목록 로드"""
        ret = self.api.get_condition_load()
        return ret == 1

    def get_condition_list(self):
        """조건검색식 목록 반환"""
        return self.api.condition_list

    def start_condition(self, slot_number, condition_name):
        """조건검색 시작"""
        if slot_number < 0 or slot_number >= 5:
            print(f"[오류] 잘못된 슬롯 번호: {slot_number}")
            return False

        slot = self.condition_slots[slot_number]

        if condition_name not in self.api.condition_list:
            print(f"[오류] 조건검색식을 찾을 수 없음: {condition_name}")
            return False

        condition_index = self.api.condition_list[condition_name]
        screen_no = slot['screen_no']

        # 실시간 조건검색 시작
        ret = self.api.send_condition(screen_no, condition_name, condition_index, 1)

        if ret == 1:
            slot['enabled'] = True
            slot['condition_name'] = condition_name
            slot['condition_index'] = condition_index
            slot['is_running'] = True
            print(f"[조건검색 시작] 슬롯{slot_number}: {condition_name}")
            return True
        else:
            print(f"[조건검색 시작 실패] 슬롯{slot_number}: {condition_name}")
            return False

    def stop_condition(self, slot_number):
        """조건검색 중지"""
        if slot_number < 0 or slot_number >= 5:
            return False

        slot = self.condition_slots[slot_number]

        if not slot['is_running']:
            return False

        screen_no = slot['screen_no']
        condition_name = slot['condition_name']
        condition_index = slot['condition_index']

        self.api.send_condition_stop(screen_no, condition_name, condition_index)

        slot['enabled'] = False
        slot['is_running'] = False
        slot['matched_stocks'].clear()

        print(f"[조건검색 중지] 슬롯{slot_number}: {condition_name}")
        return True

    def _on_receive_tr_condition(self, screen_no, code_list, condition_name, index, next):
        """조건검색 결과 수신 (초기 조회)"""
        codes = code_list.split(';')[:-1] if code_list else []

        # 해당 스크린 번호의 슬롯 찾기
        slot_number = self._find_slot_by_screen(screen_no)
        if slot_number is None:
            return

        slot = self.condition_slots[slot_number]
        slot['matched_stocks'].update(codes)

        print(f"[조건검색 결과] 슬롯{slot_number} {condition_name}: {len(codes)}개 종목")

        # 편입된 종목 시그널 발생
        for code in codes:
            stock_name = self.api.get_master_code_name(code)
            print(f"  - {stock_name}({code})")
            self.condition_occurred.emit(code, condition_name, slot_number)

    def _on_receive_real_condition(self, code, event_type, condition_name, condition_index):
        """실시간 조건검색 수신"""
        # 해당 조건의 슬롯 찾기
        slot_number = self._find_slot_by_condition(condition_name)
        if slot_number is None:
            return

        slot = self.condition_slots[slot_number]
        stock_name = self.api.get_master_code_name(code)

        if event_type == 'I':  # 편입
            slot['matched_stocks'].add(code)
            print(f"[조건 편입] 슬롯{slot_number} {condition_name}: {stock_name}({code})")
            self.condition_occurred.emit(code, condition_name, slot_number)

        elif event_type == 'D':  # 이탈
            slot['matched_stocks'].discard(code)
            print(f"[조건 이탈] 슬롯{slot_number} {condition_name}: {stock_name}({code})")
            self.condition_removed.emit(code, condition_name, slot_number)

    def _find_slot_by_screen(self, screen_no):
        """스크린 번호로 슬롯 찾기"""
        for slot in self.condition_slots:
            if slot['screen_no'] == screen_no:
                return slot['slot_number']
        return None

    def _find_slot_by_condition(self, condition_name):
        """조건검색명으로 슬롯 찾기"""
        for slot in self.condition_slots:
            if slot['condition_name'] == condition_name and slot['is_running']:
                return slot['slot_number']
        return None

    def get_slot_info(self, slot_number):
        """슬롯 정보 반환"""
        if slot_number < 0 or slot_number >= 5:
            return None
        return self.condition_slots[slot_number]

    def get_all_matched_stocks(self):
        """모든 슬롯의 편입 종목 반환"""
        all_stocks = {}
        for slot in self.condition_slots:
            if slot['is_running']:
                all_stocks[slot['slot_number']] = {
                    'condition_name': slot['condition_name'],
                    'stocks': list(slot['matched_stocks'])
                }
        return all_stocks
