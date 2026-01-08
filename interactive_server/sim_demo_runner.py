from __future__ import annotations

import threading
import time
from typing import Optional

import numpy as np

from interactive_server.frame_broker import FrameBroker


class DemoRunner:
    def __init__(self, broker: FrameBroker, fps: int = 30) -> None:
        self._broker = broker
        self._fps = fps
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        try:
            self._run_simulation()
        except Exception:
            self._run_placeholder()

    def _run_placeholder(self) -> None:
        base = 0
        while not self._stop_event.is_set():
            frame = np.zeros((540, 960, 3), dtype=np.uint8)
            frame[:, :, 0] = base
            frame[:, :, 1] = (base + 80) % 255
            frame[:, :, 2] = (base + 160) % 255
            self._broker.submit_frame(frame)
            base = (base + 2) % 255
            time.sleep(1 / self._fps)

    def _run_simulation(self) -> None:
        from omegaconf import OmegaConf
        import warp as wp
        import newton.viewer
        from sim.env.cloth_env_ARX import ClothEnvARXV1

        cfg = OmegaConf.load("cfg/default.yaml")
        cfg.env.viewer = "gl"
        cfg.env.headless = True
        viewer = newton.viewer.ViewerGL(headless=True)
        env = ClothEnvARXV1(cfg=cfg, viewer=viewer)

        targets = _demo_targets()
        target_idx = 0
        target = targets[target_idx, :-1].copy()
        to_target_time = targets[target_idx, -1]

        while not self._stop_event.is_set() and env.viewer.is_running():
            if not env.viewer.is_paused():
                with wp.ScopedTimer("step", active=False):
                    env.step({"target": target})

            if env.sim_time > to_target_time and target_idx < (targets.shape[0] - 1):
                target_idx += 1
                target = targets[target_idx, :-1].copy()
                to_target_time += targets[target_idx, -1]

            with wp.ScopedTimer("render", active=False):
                env.render()
            frame = self._extract_frame(viewer)
            if frame is not None:
                self._broker.submit_frame(frame)
            time.sleep(1 / self._fps)

    @staticmethod
    def _extract_frame(viewer) -> Optional[np.ndarray]:
        for attr in ("capture_frame", "get_frame", "read_frame", "get_image"):
            if hasattr(viewer, attr):
                frame = getattr(viewer, attr)()
                if isinstance(frame, np.ndarray):
                    return frame
        return None


def _demo_targets() -> np.ndarray:
    return np.array(
        [
            [
                0.60,
                -0.25,
                0.50,
                0.0,
                0.0,
                np.sin(np.pi / 8),
                np.cos(np.pi / 8),
                0.01,
                0.60,
                0.25,
                0.50,
                0.0,
                0.0,
                -np.sin(np.pi / 8),
                np.cos(np.pi / 8),
                0.01,
                0.5,
            ],
            [
                0.45,
                -0.17,
                0.205,
                -0.10401744,
                0.45360428,
                0.26122794,
                0.8456853,
                0.04,
                0.45,
                0.17,
                0.205,
                0.10401744,
                0.45360428,
                -0.26122794,
                0.845685,
                0.04,
                0.5,
            ],
            [
                0.45,
                -0.17,
                0.205,
                -0.10401744,
                0.45360428,
                0.26122794,
                0.8456853,
                0.01,
                0.45,
                0.17,
                0.205,
                0.10401744,
                0.45360428,
                -0.26122794,
                0.845685,
                0.01,
                0.5,
            ],
            [
                0.45,
                -0.17,
                0.30,
                -0.10401744,
                0.45360428,
                0.26122794,
                0.8456853,
                0.01,
                0.45,
                0.17,
                0.30,
                0.10401744,
                0.45360428,
                -0.26122794,
                0.845685,
                0.01,
                0.5,
            ],
            [
                0.60,
                -0.17,
                0.30,
                -0.10401744,
                0.45360428,
                0.26122794,
                0.8456853,
                0.01,
                0.60,
                0.17,
                0.30,
                0.10401744,
                0.45360428,
                -0.26122794,
                0.845685,
                0.01,
                0.5,
            ],
            [
                0.75,
                -0.17,
                0.30,
                -0.10401744,
                0.45360428,
                0.26122794,
                0.8456853,
                0.01,
                0.75,
                0.17,
                0.30,
                0.10401744,
                0.45360428,
                -0.26122794,
                0.845685,
                0.01,
                0.5,
            ],
            [
                0.75,
                -0.17,
                0.30,
                -0.10401744,
                0.45360428,
                0.26122794,
                0.8456853,
                0.04,
                0.75,
                0.17,
                0.30,
                0.10401744,
                0.45360428,
                -0.26122794,
                0.845685,
                0.04,
                0.5,
            ],
            [
                0.75,
                -0.17,
                0.40,
                -0.10401744,
                0.45360428,
                0.26122794,
                0.8456853,
                0.04,
                0.75,
                0.17,
                0.40,
                0.10401744,
                0.45360428,
                -0.26122794,
                0.845685,
                0.04,
                0.5,
            ],
        ],
        dtype=np.float32,
    )
