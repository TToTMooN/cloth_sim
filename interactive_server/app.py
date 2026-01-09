from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from aiortc import RTCPeerConnection, RTCSessionDescription
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from interactive_server.frame_broker import FrameBroker
from interactive_server.sim_demo_runner import DemoRunner
from interactive_server.state import SessionManager
from interactive_server.stream import SimVideoTrack


class Offer(BaseModel):
    sdp: str
    type: str
    session_id: str


app = FastAPI(title="Cloth Simulation Interactive Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_manager = SessionManager(ttl_seconds=300.0)
peer_connections: Dict[str, RTCPeerConnection] = {}
frame_broker = FrameBroker()
demo_runner = DemoRunner(frame_broker, session_manager)

app.mount("/website", StaticFiles(directory="interactive_server/website"), name="website")


@app.on_event("startup")
async def startup_event() -> None:
    demo_runner.start()


@app.post("/api/session/join")
async def join_session() -> dict:
    snapshot = await session_manager.join()
    return asdict(snapshot)


@app.post("/api/session/leave/{session_id}")
async def leave_session(session_id: str):
    await session_manager.leave(session_id)
    return {"status": "ok"}


@app.get("/api/session/{session_id}")
async def get_session_status(session_id: str):
    import time
    try:
        snapshot = await session_manager.status(session_id)
    except KeyError:
        return {"status": "expired"}
    
    is_controller = await session_manager.is_controller(session_id)
    
    expires_in = None
    if snapshot.expires_at:
        expires_in = max(0.0, snapshot.expires_at - time.time())
    
    return {
        "status": snapshot.status,
        "role": "controller" if is_controller else "viewer",
        "expires_in": expires_in,
        "sim_error": demo_runner._last_error,
        "restart_count": demo_runner._restart_count
    }


@app.post("/api/webrtc/offer")
async def webrtc_offer(offer: Offer) -> dict:
    try:
        await session_manager.status(offer.session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc

    pc = RTCPeerConnection()
    peer_connections[offer.session_id] = pc

    video_track = SimVideoTrack(frame_broker)
    pc.addTrack(video_track)

    await pc.setRemoteDescription(RTCSessionDescription(sdp=offer.sdp, type=offer.type))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}


@app.websocket("/api/control/{session_id}")
async def control_channel(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    is_controller = await session_manager.is_controller(session_id)
    if not is_controller:
        await websocket.close(code=4003)
        return
    try:
        while True:
            payload = await websocket.receive_json()
            await session_manager.record_input(session_id, payload)
    except WebSocketDisconnect:
        return


@app.on_event("shutdown")
async def shutdown_event() -> None:
    for pc in peer_connections.values():
        await pc.close()
    peer_connections.clear()
    demo_runner.stop()
