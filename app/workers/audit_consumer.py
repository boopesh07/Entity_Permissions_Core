"""Compatibility wrapper that runs the events engine audit consumer."""

from __future__ import annotations

import logging

from app.events_engine.consumers.audit import build_audit_consumer_from_env


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    consumer = build_audit_consumer_from_env()
    consumer.run_forever()


if __name__ == "__main__":
    main()
