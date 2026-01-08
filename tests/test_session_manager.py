import asyncio

from interactive_server.state import SessionManager


def test_session_queue_and_expire():
    async def run_test():
        manager = SessionManager(ttl_seconds=0.05)
        first = await manager.join()
        assert first.status == "controller"
        second = await manager.join()
        assert second.status == "queued"
        assert second.queue_position == 1

        await asyncio.sleep(0.08)
        status_second = await manager.status(second.session_id)
        assert status_second.status == "controller"

    asyncio.run(run_test())
