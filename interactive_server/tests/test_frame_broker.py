import numpy as np

from interactive_server.frame_broker import FrameBroker


def test_frame_broker_round_trip():
    broker = FrameBroker()
    frame = np.ones((10, 12, 3), dtype=np.uint8) * 5
    broker.submit_frame(frame)
    stored = broker.read_frame()
    assert stored is not None
    assert stored.shape == (10, 12, 3)
    assert stored[0, 0, 0] == 5
    frame[0, 0, 0] = 9
    stored_again = broker.read_frame()
    assert stored_again[0, 0, 0] == 5
