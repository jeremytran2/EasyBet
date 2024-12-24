import asyncio
import hashlib
import random

class CrashGameManager:
    def __init__(self, websocket_manager):
        self.server_seed = self.generate_server_seed()
        self.hashed_server_seed = self.hash_server_seed(self.server_seed)
        self.nonce = 0
        self.crash_point = 0
        self.multiplier = 1.0
        self.bets = {}  # {player_id: {"amount": 100, "cash_out_multiplier": None, "client_seed": "seed"}}
        self.is_running = False
        self.websocket_manager = websocket_manager

    def generate_server_seed(self):
        """Generate a secure random server seed."""
        return hashlib.sha256(str(random.random()).encode()).hexdigest()

    def hash_server_seed(self, server_seed):
        """Hash the server seed using SHA-256."""
        return hashlib.sha256(server_seed.encode()).hexdigest()

    def calculate_crash_point(self, client_seed):
        """Calculate the crash point using the provably fair mechanism, including client seed."""
        combined = f"{self.server_seed}{client_seed}{self.nonce}"  # Include client seed
        hash_value = hashlib.sha256(combined.encode()).hexdigest()
        random_value = int(hash_value[:8], 16) / 0xFFFFFFFF
        if random_value < 0.01:
            return 1.0
        return round(1 / random_value, 2)

    async def start_round(self):
        """Start a new game round."""
        if self.is_running:
            print("Game is already running!")
            return

        # Reset game state
        self.nonce += 1
        self.multiplier = 1.0

        # Use the first player's client seed or a default seed
        if self.bets:
            first_bet = next(iter(self.bets.values()))  # Get the first bet
            client_seed = first_bet.get("client_seed", "default_seed")
        else:
            client_seed = "default_seed"

        self.crash_point = self.calculate_crash_point(client_seed)
        self.is_running = True
        self.bets = {}  # Reset active bets

        # Broadcast hashed server seed
        await self.websocket_manager.broadcast_message(
            f"New Round Started! Hashed Server Seed: {self.hashed_server_seed}"
        )

        print(f"Crash Point: {self.crash_point}")

        # Update multiplier in real-time
        await self.update_multiplier()

    async def update_multiplier(self):
        """Update the multiplier in real-time until the crash point."""
        growth_rate = 0.05  # Adjust to control speed
        try:
            while self.multiplier < self.crash_point:
                self.multiplier += growth_rate * self.multiplier
                await self.websocket_manager.broadcast_message(
                    f"Multiplier: {self.multiplier:.2f}x"
                )
                await asyncio.sleep(0.1)  # Update frequency
            self.is_running = False
            await self.end_round()
        except asyncio.CancelledError:
            self.is_running = False
            print("Game round cancelled.")

    async def end_round(self):
        """End the game round and process payouts."""
        await self.websocket_manager.broadcast_message(
            f"Game Crashed at: {self.crash_point:.2f}x"
        )
        print(f"Game Crashed at: {self.crash_point:.2f}x")

        # Broadcast the server seed for verification
        await self.websocket_manager.broadcast_message(
            f"Server Seed Revealed: {self.server_seed}"
        )

        # Process payouts
        for player_id, bet in self.bets.items():
            if bet["cash_out_multiplier"] is not None:
                if bet["cash_out_multiplier"] <= self.crash_point:
                    # Player cashed out before the crash
                    payout = bet["amount"] * bet["cash_out_multiplier"]
                    print(f"Player {player_id} won {payout}")
                    await self.websocket_manager.send_message(
                        player_id, f"You cashed out at {bet['cash_out_multiplier']}x! You won {payout}!"
                    )
                else:
                    # Player lost
                    print(f"Player {player_id} lost.")
                    await self.websocket_manager.send_message(
                        player_id, "You lost!"
                    )

    def place_bet(self, player_id, amount, client_seed=None):
        """
        Place a bet for the current round, including the client's optional seed.
        """
        if not self.is_running:
            print("Cannot place a bet. Game is not running.")
            return

        # Use the provided client seed or generate a default one
        client_seed = client_seed or "default_seed"
        self.bets[player_id] = {
            "amount": amount,
            "cash_out_multiplier": None,
            "client_seed": client_seed,
        }
        print(f"Player {player_id} placed a bet of {amount} with client seed: {client_seed}.")

    def cash_out(self, player_id):
        """Handle player cash-out requests."""
        if player_id in self.bets:
            self.bets[player_id]["cash_out_multiplier"] = self.multiplier
            print(f"Player {player_id} cashed out at {self.multiplier:.2f}x.")
