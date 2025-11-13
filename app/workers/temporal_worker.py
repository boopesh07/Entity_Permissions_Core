"""Temporal worker entry point for production use."""

from __future__ import annotations

import asyncio
import logging
import sys

from app.workflow_orchestration.worker import run_worker


def main() -> None:
    """Run the Temporal worker with proper logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logging.info("\n⚠️  Worker stopped by user")
    except Exception as e:
        logging.error(f"❌ Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

