import time

import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame

from interactive_server.frame_broker import FrameBroker


class SimVideoTrack(VideoStreamTrack):
    def __init__(self, broker: FrameBroker, width: int = 960, height: int = 540) -> None:
        super().__init__()
        self._broker = broker
        self._width = width
        self._height = height
        self._start_time = time.time()

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame = self._broker.read_frame()
        if frame is None:
            frame = self._fallback_frame()
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

    def _fallback_frame(self) -> np.ndarray:
        elapsed = time.time() - self._start_time
        base = int((elapsed * 40) % 255)
        frame = np.zeros((self._height, self._width, 3), dtype=np.uint8)
        frame[:, :, 0] = base
        frame[:, :, 1] = (base + 80) % 255
        frame[:, :, 2] = (base + 160) % 255
        return frame
