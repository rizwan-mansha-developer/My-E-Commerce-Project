from __future__ import annotations

import os

from .base import *  # noqa: F403

DEBUG = True

# Local dev default — no Redis required. Set USE_REDIS_CHANNEL_LAYER=true for Redis.
if os.environ.get("USE_REDIS_CHANNEL_LAYER", "").lower() in ("true", "1", "yes"):
    pass
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
