from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional
 
if TYPE_CHECKING:
    from interactive_server.state import SessionManager

import numpy as np

from interactive_server.frame_broker import FrameBroker

# Add relevant paths for simulation components
ROOT_DIR = Path(__file__).parents[1]
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "newton"))

# Force pyglet headless mode for remote sim
os.environ["PYGLET_HEADLESS"] = "1"


class DemoRunner:
    def __init__(self, broker: FrameBroker, session_manager: 'SessionManager', fps: int = 30) -> None:
        self._broker = broker
        self._session_manager = session_manager
        self._fps = 60
        self._stop_event = threading.Event()
        self._thread = None
        
        # Interactive state
        self._is_replaying = False # Default to manual control
        self._current_target = None
        self._last_error = None
        self._restart_count = 0

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
        while not self._stop_event.is_set():
            try:
                self._last_error = None
                self._run_simulation()
            except Exception as e:
                import traceback
                self._last_error = str(e)
                self._restart_count += 1
                print(f"Simulation error (Attempt {self._restart_count}): {e}")
                traceback.print_exc()
                
                # Update session manager with error if possible
                # (We'll assume the status poll can pick this up via a new property)
                
                if self._stop_event.is_set():
                    break
                
                # Brief wait before restart
                time.sleep(2)
                print("Restarting simulation...")

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
        from hydra import compose, initialize
        import warp as wp
        import newton.viewer
        from sim.env.cloth_env_ARX import ClothEnvARXV1

        # Correct config loading via Hydra composition
        with initialize(version_base="1.2", config_path="../cfg"):
            cfg = compose(config_name="default", overrides=["env.headless=True", "env.viewer=gl"])
        
        viewer = newton.viewer.ViewerGL(headless=True)
        env = ClothEnvARXV1(cfg=cfg, viewer=viewer)

        targets = _demo_targets()
        target_idx = 0
        to_target_time = targets[target_idx, -1]
        
        # Simple initialization from first demo target to avoid faults
        self._current_target = targets[0, :-1].copy()

        if self._is_replaying:
            # (redundant but safe if we change default)
            self._current_target = targets[0, :-1].copy()

        while not self._stop_event.is_set() and env.viewer.is_running():
            inputs = self._session_manager.get_controller_inputs(consume_commands=True)
            
            # Handle commands
            if inputs and inputs.get("commands"):
                for cmd in inputs["commands"]:
                    if cmd == "toggle_replay":
                        self._is_replaying = not self._is_replaying
                        if self._is_replaying:
                            # Reset environment when switching to replay
                            env.reset()
                            target_idx = 0
                            self._current_target = targets[target_idx, :-1].copy()
                            to_target_time = targets[target_idx, -1]
                        else:
                            # When switching to manual, stop and let people take control
                            # We keep the current target where it is
                            pass
            
            if self._is_replaying:
                # Demo Replay Mode
                if env.sim_time > to_target_time and target_idx < (targets.shape[0] - 1):
                    target_idx += 1
                    self._current_target = targets[target_idx, :-1].copy()
                    to_target_time += targets[target_idx, -1]
                elif target_idx >= (targets.shape[0] - 1) and env.sim_time > to_target_time:
                    # Loop demo
                    target_idx = 0
                    self._current_target = targets[target_idx, :-1].copy()
                    to_target_time = env.sim_time + targets[target_idx, -1]
            else:
                # Interactive Mode
                if inputs:
                    self._update_target_from_inputs(inputs)

            if not env.viewer.is_paused():
                with wp.ScopedTimer("step", active=False):
                    env.step({"target": self._current_target})

            with wp.ScopedTimer("render", active=False):
                env.render()
            frame = self._extract_frame(viewer)
            if frame is not None:
                self._broker.submit_frame(frame)
            time.sleep(1 / self._fps)

    def _update_target_from_inputs(self, inputs: dict) -> None:
        keys = inputs.get("keys", [])
        delta = 0.01
        
        # Left Arm (Index 0-7)
        if 'w' in keys:
            self._current_target[0] += delta
        if 's' in keys:
            self._current_target[0] -= delta
        if 'a' in keys:
            self._current_target[1] -= delta
        if 'd' in keys:
            self._current_target[1] += delta
        if 'r' in keys:
            self._current_target[2] += delta
        if 'f' in keys:
            self._current_target[2] -= delta
        if 'c' in keys:
            self._current_target[7] = 0.04 # Open
        if 'v' in keys:
            self._current_target[7] = 0.01 # Close
        
        # Right Arm (Index 8-15)
        if 'i' in keys:
            self._current_target[8] += delta
        if 'k' in keys:
            self._current_target[8] -= delta
        if 'j' in keys:
            self._current_target[9] -= delta
        if 'l' in keys:
            self._current_target[9] += delta
        if 'p' in keys:
            self._current_target[10] += delta
        if ';' in keys:
            self._current_target[10] -= delta
        if '.' in keys:
            self._current_target[15] = 0.04 # Open
        if ',' in keys:
            self._current_target[15] = 0.01 # Close

    @staticmethod
    def _extract_frame(viewer) -> Optional[np.ndarray]:
        import warp as wp
        for attr in ("capture_frame", "get_frame", "read_frame", "get_image"):
            if hasattr(viewer, attr):
                frame = getattr(viewer, attr)()
                if isinstance(frame, np.ndarray):
                    return frame
                if isinstance(frame, wp.array):
                    return frame.numpy()
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
