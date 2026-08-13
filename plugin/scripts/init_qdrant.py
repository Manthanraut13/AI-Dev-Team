"""Initialize Qdrant collections for the plugin.

Run once when Qdrant is available (docker container or cloud). Creates the four
collections used by long-term memory. Idempotent — safe to re-run.

Usage:
    python -m plugin.scripts.init_qdrant
"""
from __future__ import annotations

import logging

from plugin.config import settings
from plugin.memory.long_term import memory_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def init_collections() -> bool:
    """Create collections if Qdrant is reachable. Returns True on success."""
    if not memory_service.is_ready():
        logger.warning(
            "Qdrant not reachable at %s — collections not created. "
            "The plugin will keep working without long-term memory.",
            settings.QDRANT_URL,
        )
        return False

    # _ensure_collections creates any missing ones (VectorParams 384/cosine) and
    # logs each. It is already idempotent.
    memory_service._ensure_collections()
    logger.info("Qdrant collections ready.")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if init_collections() else 1)