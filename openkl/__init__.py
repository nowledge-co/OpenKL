"""
Open Knowledge Layer (OpenKL)

A local-first, open-source knowledge and memory layer for AI agents.
"""

__version__ = "0.1.0"
__author__ = "Siwei Gu"
__email__ = "siwei@nowledge.co"

from .cite import CitationManager
from .db import get_connection, init_db
from .graph import GraphManager
from .memory import MemoryManager
from .store import StoreManager

__all__ = [
    "init_db",
    "get_connection",
    "MemoryManager",
    "StoreManager",
    "GraphManager",
    "CitationManager",
]
