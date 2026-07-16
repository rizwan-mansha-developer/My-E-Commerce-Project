from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def inmemory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
