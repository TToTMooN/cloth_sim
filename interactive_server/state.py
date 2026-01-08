from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
import time
import uuid
from typing import Deque, Dict, Optional


@dataclass
class Session:
    session_id: str
    status: str
    created_at: float
    expires_at_monotonic: Optional[float] = None


@dataclass
class SessionSnapshot:
    session_id: str
    status: str
    queue_position: Optional[int]
    expires_at: Optional[float]


class SessionManager:
    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()
        self._controller_id: Optional[str] = None
        self._queue: Deque[str] = deque()
        self._sessions: Dict[str, Session] = {}
        self._expire_tasks: Dict[str, asyncio.Task] = {}

    async def join(self) -> SessionSnapshot:
        async with self._lock:
            self._promote_next_if_needed()
            session_id = uuid.uuid4().hex
            created_at = time.time()
            if self._controller_id is None:
                session = self._assign_controller(session_id, created_at)
                queue_position = None
            else:
                session = Session(
                    session_id=session_id,
                    status="queued",
                    created_at=created_at,
                )
                self._queue.append(session_id)
                queue_position = len(self._queue)
            self._sessions[session_id] = session
            return self._snapshot(session, queue_position)

    async def status(self, session_id: str) -> SessionSnapshot:
        async with self._lock:
            self._promote_next_if_needed()
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            queue_position = self._queue_position(session_id)
            return self._snapshot(session, queue_position)

    async def is_controller(self, session_id: str) -> bool:
        async with self._lock:
            self._promote_next_if_needed()
            return self._controller_id == session_id

    async def record_input(self, session_id: str, payload: dict) -> None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            if session.status != "controller":
                return
            session.created_at = session.created_at

    def _queue_position(self, session_id: str) -> Optional[int]:
        for idx, queued_id in enumerate(self._queue, start=1):
            if queued_id == session_id:
                return idx
        return None

    def _assign_controller(self, session_id: str, created_at: float) -> Session:
        expires_at_monotonic = time.monotonic() + self._ttl_seconds
        session = Session(
            session_id=session_id,
            status="controller",
            created_at=created_at,
            expires_at_monotonic=expires_at_monotonic,
        )
        self._controller_id = session_id
        self._schedule_expiration(session_id, expires_at_monotonic)
        return session

    def _schedule_expiration(self, session_id: str, expires_at_monotonic: float) -> None:
        existing_task = self._expire_tasks.pop(session_id, None)
        if existing_task:
            existing_task.cancel()
        ttl = max(0.0, expires_at_monotonic - time.monotonic())
        self._expire_tasks[session_id] = asyncio.create_task(
            self._expire_after(session_id, ttl)
        )

    async def _expire_after(self, session_id: str, ttl: float) -> None:
        await asyncio.sleep(ttl)
        async with self._lock:
            if self._controller_id != session_id:
                return
            session = self._sessions.get(session_id)
            if session:
                session.status = "expired"
                session.expires_at_monotonic = None
            self._controller_id = None
            self._promote_next_if_needed()

    def _promote_next_if_needed(self) -> None:
        if self._controller_id is not None:
            session = self._sessions.get(self._controller_id)
            if session and session.expires_at_monotonic:
                if time.monotonic() < session.expires_at_monotonic:
                    return
                session.status = "expired"
                session.expires_at_monotonic = None
            self._controller_id = None
        if self._queue:
            next_id = self._queue.popleft()
            session = self._sessions.get(next_id)
            if session:
                session.status = "controller"
                session.expires_at_monotonic = time.monotonic() + self._ttl_seconds
                self._controller_id = next_id
                self._schedule_expiration(next_id, session.expires_at_monotonic)

    def _snapshot(self, session: Session, queue_position: Optional[int]) -> SessionSnapshot:
        expires_at = None
        if session.expires_at_monotonic is not None:
            remaining = session.expires_at_monotonic - time.monotonic()
            expires_at = time.time() + max(0.0, remaining)
        return SessionSnapshot(
            session_id=session.session_id,
            status=session.status,
            queue_position=queue_position,
            expires_at=expires_at,
        )
