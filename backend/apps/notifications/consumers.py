from __future__ import annotations

import json
from datetime import datetime

from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("notifications", self.channel_name)
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection.established",
                    "message": "Connected to Darling real-time notifications.",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("notifications", self.channel_name)

    async def notification_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))
