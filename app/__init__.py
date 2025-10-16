"""Omen Entity & Permissions Core service package."""

import warnings

warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

from .main import create_app  # noqa: F401
