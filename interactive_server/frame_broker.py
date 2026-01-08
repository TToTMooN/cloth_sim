from __future__ import annotations

import threading
from typing import Optional

import numpy as np


class FrameBroker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None

    def submit_frame(self, frame: np.ndarray) -> None:
        if frame is None:
            return
        with self._lock:
            self._frame = frame.copy()

    def read_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()
