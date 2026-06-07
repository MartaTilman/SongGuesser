import random
import string

from blockchain.blockchain import Blockchain
from blockchain.crypto_utils import (
    build_signed_action,
    verify_signed_action
)


class Lobby:

    def __init__(self, lobby_id, host):
        self.id = lobby_id
        self.host = host
        self.players = []
        self.answers = []
        self.current_song = None
        self.current_decade = None
        self.finishing_song = False
        self.last_result_payload = None
        self.used_songs = set()
        self.used_song_keys = set()
        self.used_artists = set()
        self.last_artist = None
        self.current_game_number = 1
        self.current_round = 1
        self.current_song_in_round = 1
        self.songs_per_round_by_round = {
            1: 5,
            2: 5,
            3: 6
        }
        self.songs_per_round = self.songs_per_round_by_round[1]
        self.total_rounds = len(self.songs_per_round_by_round)
        self.answer_phase_started_at = None
        self.clip_started_at = None
        self.round_ends_at = None
        self.year_options = []
        self.current_song_salt = None
        self.current_song_commitment = None
        self.blockchain = Blockchain(lobby_id)

    def reset_for_next_game(self):
        self.current_game_number += 1
        self.current_round = 1
        self.current_song_in_round = 1
        self.current_song = None
        self.current_decade = None
        self.answers = []
        self.finishing_song = False
        self.last_result_payload = None
        self.used_songs = set()
        self.used_song_keys = set()
        self.used_artists = set()
        self.last_artist = None
        self.answer_phase_started_at = None
        self.clip_started_at = None
        self.round_ends_at = None
        self.year_options = []
        self.current_song_salt = None
        self.current_song_commitment = None

        for player in self.players:
            player.score = 0
            player.answers = {}

        self.blockchain.add_game_started(self.current_game_number)


class LobbyManager:

    def __init__(self):
        self.lobbies = {}

    def generate_lobby_id(self, length=6):
        alphabet = string.ascii_uppercase + string.digits

        for _ in range(100):
            lobby_id = "".join(random.choice(alphabet) for _ in range(length))
            if lobby_id not in self.lobbies:
                return lobby_id

        raise RuntimeError("Ne mogu generirati jedinstveni lobby kod.")

    def create_lobby(self):
        lobby_id = self.generate_lobby_id()
        lobby = Lobby(lobby_id, "")
        self.lobbies[lobby_id] = lobby
        lobby.blockchain.add_lobby_created()
        lobby.blockchain.add_game_started(lobby.current_game_number)
        return lobby

    def join_lobby(self, lobby_id, player):
        lobby_id = str(lobby_id or "").strip().upper()

        if not lobby_id:
            raise ValueError("Lobby kod je obavezan.")

        if lobby_id not in self.lobbies:
            raise ValueError("Lobby s tim kodom ne postoji.")

        lobby = self.lobbies[lobby_id]

        for index, existing_player in enumerate(lobby.players):
            if player.name.lower() == existing_player.name.lower():
                if existing_player.connected:
                    raise ValueError("Ime je vec zauzeto u ovom lobbyju.")

                player.score = existing_player.score
                player.answers = existing_player.answers
                player.public_key = player.public_key or existing_player.public_key
                player.join_signature = player.join_signature or existing_player.join_signature
                player.connected = True
                lobby.players[index] = player
                lobby.blockchain.add_player_identity(
                    player.name,
                    player.public_key,
                    self.verify_join_signature(lobby, player)
                )
                lobby.blockchain.add_auth_event(player.name, "reconnect")
                return lobby

        if not lobby.host:
            lobby.host = player.name

        lobby.players.append(player)

        lobby.blockchain.add_player_join(player.name)
        lobby.blockchain.add_player_identity(
            player.name,
            player.public_key,
            self.verify_join_signature(lobby, player)
        )
        lobby.blockchain.add_auth_event(player.name, "join_lobby")

        return lobby

    def verify_join_signature(self, lobby, player):
        expected_payload = build_signed_action(
            "join_lobby",
            lobby.id,
            player.name,
            {
                "avatar": player.avatar
            }
        )

        return verify_signed_action(
            player.public_key,
            player.join_signature,
            "join_lobby",
            lobby.id,
            player.name
        ) and player.join_signature.get("payload") == expected_payload

    def remove_player(self, lobby_id, player_name):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return None

        lobby.players = [p for p in lobby.players if p.name != player_name]

        if len(lobby.players) == 0:
            del self.lobbies[lobby_id]
            return None

        if lobby.host == player_name:
            previous_host = lobby.host
            lobby.host = lobby.players[0].name
            lobby.blockchain.add_host_changed(previous_host, lobby.host)

        lobby.blockchain.add_auth_event(player_name, "disconnect")

        return lobby

    def remove_player_connection(self, lobby_id, player):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return None

        active_player = next((p for p in lobby.players if p.name == player.name), None)
        if active_player is not player:
            return lobby

        if lobby.current_song is not None or lobby.last_result_payload is not None:
            if player.connected:
                lobby.blockchain.add_auth_event(player.name, "disconnect")
            player.connected = False
            player.websocket = None
            return lobby

        return self.remove_player(lobby_id, player.name)

    def get_lobby_players(self, lobby_id):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return []
        return [player.to_dict() for player in lobby.players]

    async def broadcast(self, lobby_id, message):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return

        disconnected = []

        for player in lobby.players:
            try:
                await player.websocket.send_json(message)
            except Exception:
                disconnected.append(player)

        for player in disconnected:
            self.remove_player_connection(lobby_id, player)
