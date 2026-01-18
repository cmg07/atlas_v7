from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List

class BrokerBase(ABC):
    @abstractmethod
    def ping(self) -> bool:
        ...

    @abstractmethod
    def get_open_positions(self) -> List[Dict]:
        ...

    @abstractmethod
    def get_account_state(self) -> Dict:
        ...
