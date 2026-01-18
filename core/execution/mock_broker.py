from __future__ import annotations
from typing import Dict, List
from .broker_base import BrokerBase

class MockBroker(BrokerBase):
    def __init__(self):
        self._positions: List[Dict] = []

    def ping(self) -> bool:
        return True

    def get_open_positions(self) -> List[Dict]:
        return list(self._positions)

    def get_account_state(self) -> Dict:
        return {"status": "OK", "broker": "MOCK"}

    def _set_positions(self, positions: List[Dict]) -> None:
        self._positions = list(positions)
