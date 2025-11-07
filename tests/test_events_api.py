from __future__ import annotations

from fastapi.testclient import TestClient


def test_event_ingestion_and_listing(client: TestClient) -> None:
    payload = {
        "event_type": "document.verified",
        "source": "document_vault",
        "payload": {"document_id": "abc123"},
        "context": {"actor": "tester"},
        "correlation_id": "doc-abc123",
    }

    create_resp = client.post("/api/v1/events", json=payload)
    create_resp.raise_for_status()
    body = create_resp.json()
    assert body["event_type"] == "document.verified"
    assert body["source"] == "document_vault"
    assert body["delivery_state"] == "succeeded"

    # Deduplication should return the same event ID.
    duplicate_resp = client.post("/api/v1/events", json=payload)
    duplicate_resp.raise_for_status()
    assert duplicate_resp.json()["event_id"] == body["event_id"]

    list_resp = client.get("/api/v1/events", params={"source": "document_vault"})
    list_resp.raise_for_status()
    events = list_resp.json()
    assert any(item["event_id"] == body["event_id"] for item in events)

    detail_resp = client.get(f"/api/v1/events/{body['event_id']}")
    detail_resp.raise_for_status()
    assert detail_resp.json()["event_id"] == body["event_id"]
