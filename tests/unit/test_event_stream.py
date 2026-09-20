"""Unit tests for Server-Sent Events (SSE) EventBroker pub/sub."""

import asyncio
import json

import pytest

from apps.api.services.event_stream import EventBroker


@pytest.mark.asyncio
async def test_event_broker_publish_and_subscribe():
    broker = EventBroker()
    incident_id = "inc-sse-test-01"

    async def consume_events():
        events = []
        async for event in broker.subscribe(incident_id):
            events.append(event)
            if event["event"] == "resolved":
                break
        return events

    consume_task = asyncio.create_task(consume_events())
    await asyncio.sleep(0.01)  # Allow consumer to register subscription

    # Publish events
    await broker.publish(incident_id, "stage_change", {"stage": "PLANNING"})
    await broker.publish(incident_id, "evidence_found", {"id": "EV-01", "type": "log"})
    await broker.publish(incident_id, "resolved", {"status": "RESOLVED"})

    events = await asyncio.wait_for(consume_task, timeout=2.0)
    assert len(events) == 3
    assert events[0]["event"] == "stage_change"
    assert json.loads(events[0]["data"])["stage"] == "PLANNING"
    assert events[1]["event"] == "evidence_found"
    assert events[2]["event"] == "resolved"


@pytest.mark.asyncio
async def test_event_broker_history_replay():
    broker = EventBroker(history_buffer_size=10)
    incident_id = "inc-sse-replay-02"

    # Publish before subscriber connects
    await broker.publish(incident_id, "stage_change", {"stage": "INVESTIGATING"})
    await broker.publish(incident_id, "agent_thought", {"message": "Analyzing diff"})

    # Now subscriber connects and immediately receives historical events
    events = []
    async for event in broker.subscribe(incident_id):
        events.append(event)
        if len(events) == 2:
            break

    assert len(events) == 2
    assert events[0]["event"] == "stage_change"
    assert events[1]["event"] == "agent_thought"
