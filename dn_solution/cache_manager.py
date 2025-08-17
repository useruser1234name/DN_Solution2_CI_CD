# -*- coding: utf-8 -*-
"""
Lightweight cache_manager shim for development.

This module provides a minimal-compatible interface expected by legacy code
(`cache_manager` and `CacheManager`) while delegating to Django's default cache.

It avoids NameError and pattern-deletion issues seen in logs, without requiring
redis. In production, replace with a real pattern-aware cache layer if needed.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)


class CacheManager:
    """Minimal cache manager compatible surface."""

    # Fallback timeout presets (seconds)
    CACHE_TIMEOUTS = {
        'short': 300,     # 5 minutes
        'medium': 1800,   # 30 minutes
        'long': 3600,     # 1 hour
        'daily': 86400,   # 24 hours
    }

    def __init__(self) -> None:
        # For compatibility with diagnostics/log pages
        self.cache = cache
        self.cache_level = 'default'

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return cache.get(key, default)
        except Exception as exc:
            logger.error("cache_manager.get failed: %s", exc)
            return default

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        try:
            cache.set(key, value, timeout)
            return True
        except Exception as exc:
            logger.error("cache_manager.set failed: %s", exc)
            return False

    def delete(self, key: str) -> bool:
        try:
            return bool(cache.delete(key))
        except Exception as exc:
            logger.error("cache_manager.delete failed: %s", exc)
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Best-effort pattern deletion.

        Django's default cache backends do not support listing keys safely, so
        we cannot truly delete by pattern. We log and return 0 to avoid raising
        errors that break request flows. If a redis backend is used with key
        iteration enabled, this could be extended to actually scan and delete.
        """
        logger.info("cache_manager.delete_pattern best-effort: %s (no-op)", pattern)
        return 0

    def clear(self) -> bool:
        try:
            cache.clear()
            return True
        except Exception as exc:
            logger.error("cache_manager.clear failed: %s", exc)
            return False


# Singleton instance used across the codebase
cache_manager = CacheManager()


