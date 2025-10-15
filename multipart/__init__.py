"""Compatibility shim for libraries expecting `import multipart`."""

from __future__ import annotations

from python_multipart import __version__  # noqa: F401
from python_multipart.multipart import *  # noqa: F401,F403
