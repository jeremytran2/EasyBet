from fastapi import WebSocket
from typing import Dict
import json

class WebSocketManager:
    def __init__(self, crash_game_manager):
        self.active_connections: Dict[str, WebSocket] = {}  # Maps player_id to WebSocket connection
        self.crash_game_manager = crash_game_manager

    async def connect(self, player_id: str, websocket: WebSocket):
        """Add a new WebSocket connection for a player."""
        await websocket.accept()
        self.active_connections[player_id] = websocket
        print(f"Player {player_id} connected.")

    async def disconnect(self, player_id: str):
        """Remove a WebSocket connection for a player."""
        if player_id in self.active_connections:
            del self.active_connections[player_id]
            print(f"Player {player_id} disconnected.")

    async def send_message(self, player_id: str, message: str):
        """Send a message to a specific player."""
        if player_id in self.active_connections:
            websocket = self.active_connections[player_id]
            await websocket.send_text(message)

    async def broadcast_message(self, message: str):
        """Send a message to all connected players."""
        for player_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to {player_id}: {e}")

    async def receive_message(self, player_id: str, message: str):
        """Handle messages received from players."""
        print(f"Received raw message from {player_id}: {message}")
        try:
            # Parse the message as JSON
            data = json.loads(message)

            # Handle actions
            if data["action"] == "place_bet":
                self.crash_game_manager.place_bet(player_id, data["amount"])
            elif data["action"] == "cash_out":
                self.crash_game_manager.cash_out(player_id)
        except json.JSONDecodeError:
            print(f"Invalid JSON received from {player_id}: {message}")
        except KeyError as e:
            print(f"Missing key {e} in message from {player_id}: {message}")
