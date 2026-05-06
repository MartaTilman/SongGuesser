import random
import string

from blockchain.blockchain import Blockchain


class Lobby:

    def __init__(self, lobby_id, host):
        self.id = lobby_id
        self.host = host
        self.players = []
        self.answers = []
        self.current_song = None
        self.current_decade = None
        self.used_songs = set()
        self.last_artist = None
        self.current_round = 1
        self.current_song_in_round = 1
        self.songs_per_round = 5
        self.total_rounds = 5
        self.answer_phase_started_at = None
        self.clip_started_at = None
        self.blockchain = Blockchain(lobby_id)


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
        return lobby

    def join_lobby(self, lobby_id, player):
        lobby_id = str(lobby_id or "").strip().upper()

        if not lobby_id:
            raise ValueError("Lobby kod je obavezan.")

        if lobby_id not in self.lobbies:
            raise ValueError("Lobby s tim kodom ne postoji.")

        lobby = self.lobbies[lobby_id]

        existing_names = [p.name.lower() for p in lobby.players]
        if player.name.lower() in existing_names:
            raise ValueError("Igrač s tim imenom već postoji u lobbyju.")

        if not lobby.host:
            lobby.host = player.name

        lobby.players.append(player)

        lobby.blockchain.add_player_join(player.name)
        lobby.blockchain.add_auth_event(player.name, "join_lobby")

        return lobby

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
                disconnected.append(player.name)

        for name in disconnected:
            self.remove_player(lobby_id, name)
