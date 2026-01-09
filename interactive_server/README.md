# Interactive Simulation Server

This server hosts a simple WebRTC stream and a session queue so only one user can control the simulation at a time.

## Quick start

Assumes you have already set up the simulation environment (e.g. via `uv` or `pixi`).

### 1. Install Server Dependencies

Ensure the interactive server requirements are installed in your active environment:

```bash
pip install -r interactive_server/requirements.txt
```

### 2. Run the Server

Launch the server using `uvicorn`:

```bash
uvicorn interactive_server.app:app --host 127.0.0.1 --port 8000
```

### 3. Local Testing

Once the server is running, you can test the interface by:
1. Opening `interactive_server/website/interactive/index.html` in your web browser.
2. Ensure the **Server URL** in the UI is set to `http://localhost:8000`.
3. Click **Connect**.

### Remote Testing (e.g. GitHub Pages)

If the website is hosted remotely:
1. Start a secure tunnel (e.g., `ngrok http 8000`).
2. Use the tunnel's public HTTPS URL in the **Server URL** field on the website.

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
