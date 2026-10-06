from typing import Dict, List
from fastapi import WebSocket
import json

class ConnectManager:
    def __init__(self):
        # Maps item_id -> list of active WebSocket client connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, item_id: int):
        """Accept a new WebSocket connections and track it under the itme ID."""
        await websocket.accept()
        if item_id not in self.active_connections:
            self.active_connections[item_id] = []
        self.active_connections[item_id].append(websocket)

    def disconnect(self, websocket: WebSocket, item_id: int):
        """Remove a disconnected client from tracking."""
        if item_id in self.active_connections:
            if websocket in self.active_connections[item_id]:
                self.active_connections[item_id].remove(websocket)
            if not self.active_connections[item_id]:
                del self.active_connections[item_id]

    async def broadcast_new_bid(
            self,
            item_id: int,
            bid_id: int,
            amount: float,
            user_id: int,
            user_email: str,
            timestamp: str
            ):
        """Broadcast a NEW_BID payload to all mobile clients watching a specific item"""
        if item_id in self.active_connections:
            payload = json.dumps({
                "event": "NEW_BID",
                "item_id": item_id,
                "bid_id": bid_id,
                "current_price": amount,
                "user_id": user_id,
                "user_email": user_email,
                "timestamp": timestamp
                })

            # Send payload to each active connection on this item
            disconnected_clients = []
            for connection in self.active_connections[item_id]:
                try:
                    await connection.send_text(payload)
                except Exception:
                    disconnected_clients.append(connection)

            # Cleanup broken connections
            for client in disconnected_clients:
                self.disconnect(client, item_id)

# Singleton instance shred across routers
ws_manager = ConnectManager()

