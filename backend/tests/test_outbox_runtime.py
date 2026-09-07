import asyncio
import os
from unittest.mock import patch
from uuid import uuid4

import pytest
from fiapx_api import main
from fiapx_api.db import session_factory
from fiapx_api.models import OutboxEvent
from sqlalchemy import delete, select

pytestmark = pytest.mark.skipif(
    not os.getenv("FIAPX_OUTBOX_RUNTIME"),
    reason="FIAPX_OUTBOX_RUNTIME is not configured",
)


@pytest.mark.asyncio
async def test_two_publishers_claim_an_outbox_event_once() -> None:
    event_id = uuid4()
    async with session_factory() as session:
        session.add(
            OutboxEvent(
                id=event_id,
                event_type="video.uploaded",
                aggregate_id=uuid4(),
                payload="{}",
            )
        )
        await session.commit()

    calls: list[str] = []

    async def fake_publish(*args: object, **kwargs: object) -> None:
        calls.append(str(args[3]))
        await asyncio.sleep(0.2)

    try:
        with patch("fiapx_api.main.publish_raw", side_effect=fake_publish):
            results = await asyncio.gather(
                main.publish_pending_outbox(object(), object()),
                main.publish_pending_outbox(object(), object()),
            )

        assert sorted(results) == [0, 1]
        assert calls == ["video.uploaded"]
        async with session_factory() as session:
            published = (
                await session.execute(
                    select(OutboxEvent.published_at).where(OutboxEvent.id == event_id)
                )
            ).scalar_one()
            assert published is not None
    finally:
        async with session_factory() as session:
            await session.execute(delete(OutboxEvent).where(OutboxEvent.id == event_id))
            await session.commit()
