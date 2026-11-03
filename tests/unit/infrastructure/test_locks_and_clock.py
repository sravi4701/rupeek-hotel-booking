import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

from app.infrastructure.clock import FixedClock
from app.infrastructure.locks import KeyedLockManager


def test_same_key_is_mutually_exclusive() -> None:
    locks = KeyedLockManager()
    inside = 0
    max_inside = 0
    counter_lock = threading.Lock()

    def critical_section() -> None:
        nonlocal inside, max_inside
        with locks.hold(("p1", "rt1")):
            with counter_lock:
                inside += 1
                max_inside = max(max_inside, inside)
            time.sleep(0.001)
            with counter_lock:
                inside -= 1

    with ThreadPoolExecutor(max_workers=16) as pool:
        for _ in range(64):
            pool.submit(critical_section)

    assert max_inside == 1


def test_different_keys_do_not_block_each_other() -> None:
    locks = KeyedLockManager()
    entered_second = threading.Event()

    with locks.hold("a"):
        thread = threading.Thread(target=lambda: _enter_and_signal(locks, "b", entered_second))
        thread.start()
        assert entered_second.wait(timeout=1), "key 'b' was blocked by key 'a'"
        thread.join()


def _enter_and_signal(locks: KeyedLockManager, key: str, event: threading.Event) -> None:
    with locks.hold(key):
        event.set()


def test_fixed_clock_only_moves_when_advanced() -> None:
    clock = FixedClock(datetime(2027, 1, 1, 23, 0))

    assert clock.today() == date(2027, 1, 1)
    clock.advance(timedelta(hours=2))
    assert clock.today() == date(2027, 1, 2)
