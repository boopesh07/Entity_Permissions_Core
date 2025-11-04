from __future__ import annotations

import json

from app.events_engine.consumers.base import unwrap_sns_envelope


def test_unwrap_sns_envelope_handles_plain_json() -> None:
    payload = {"event_type": "entity.archived"}
    result = unwrap_sns_envelope(json.dumps(payload))
    assert result == payload


def test_unwrap_sns_envelope_handles_sns_wrapping() -> None:
    inner = {"event_type": "entity.archived", "payload": {"foo": "bar"}}
    body = json.dumps({"Message": json.dumps(inner)})
    result = unwrap_sns_envelope(body)
    assert result == inner
