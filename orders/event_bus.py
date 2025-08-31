import json
import threading
import queue


class OrderEventBus:
    """간단한 인메모리 이벤트 버스 (프로세스 내)
    - 각 구독자(연결)마다 개별 Queue를 부여하여 동일 이벤트를 브로드캐스트
    - 스레드 안전을 위해 Lock 사용
    """

    def __init__(self):
        self._listeners = set()
        self._lock = threading.Lock()

    def add_listener(self) -> queue.Queue:
        q = queue.Queue()
        with self._lock:
            self._listeners.add(q)
        return q

    def remove_listener(self, q: queue.Queue):
        with self._lock:
            self._listeners.discard(q)
        # 큐 정리
        try:
            while not q.empty():
                q.get_nowait()
        except Exception:
            pass

    def broadcast(self, event_type: str, payload: dict):
        message = {
            'type': event_type,
            'data': payload,
        }
        with self._lock:
            for q in list(self._listeners):
                try:
                    # 원본 dict를 큐에 전달하고 SSE 뷰에서 직렬화
                    q.put_nowait(message)
                except Exception:
                    # 실패한 리스너는 제거 시도
                    try:
                        self._listeners.discard(q)
                    except Exception:
                        pass


order_event_bus = OrderEventBus()


