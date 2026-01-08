# Interactive Simulation Server

This server hosts a simple WebRTC stream and a session queue so only one user can control the simulation at a time.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r interactive_server/requirements.txt
uvicorn interactive_server.app:app --host 0.0.0.0 --port 8000
```

## Demo integration

By default the server starts a demo runner that attempts to execute the same target sequence from `experiments/demo.py`.
If the Newton simulation stack is unavailable, the runner automatically falls back to a placeholder animation.

To see the live simulation, ensure the Newton dependencies are installed and accessible in the same environment that runs
the server.

## API overview

- `POST /api/session/join`: request a session. Returns status and queue position.
- `GET /api/session/{session_id}`: check session status.
- `POST /api/webrtc/offer`: WebRTC signaling endpoint.
- `WS /api/control/{session_id}`: send control payloads as JSON.
