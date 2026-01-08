import asyncio

import numpy as np

from interactive_server.frame_broker import FrameBroker
from interactive_server.stream import SimVideoTrack


def test_stream_track_uses_broker_frame():
    async def run_test():
        broker = FrameBroker()
        frame = np.zeros((6, 8, 3), dtype=np.uint8)
        frame[:, :, 1] = 123
        broker.submit_frame(frame)
        track = SimVideoTrack(broker, width=8, height=6)
        video_frame = await track.recv()
        array = video_frame.to_ndarray(format="bgr24")
        assert array.shape == (6, 8, 3)
        assert array[0, 0, 1] == 123

    asyncio.run(run_test())
