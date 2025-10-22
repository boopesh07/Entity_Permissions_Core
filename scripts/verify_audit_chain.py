#!/usr/bin/env python
"""CLI utility to verify the audit log hash chain."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from app.core.database import session_scope
from app.services.audit_verifier import AuditVerifier, AuditVerificationError


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify audit log hash chain.")
    parser.add_argument("--start-sequence", type=int, default=None, help="Optional starting sequence (inclusive).")
    parser.add_argument("--end-sequence", type=int, default=None, help="Optional ending sequence (inclusive).")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        with session_scope() as session:
            verifier = AuditVerifier(session)
            result = verifier.verify(
                start_sequence=args.start_sequence,
                end_sequence=args.end_sequence,
            )
    except AuditVerificationError as exc:
        logging.error("Audit verification failed: %s", exc)
        return 1

    logging.info(
        "Audit chain verified successfully from sequence %s to %s (%s entries checked)",
        result.start_sequence,
        result.end_sequence,
        result.checked,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
