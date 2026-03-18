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
        self.total_rounds = 4
        self.answer_phase_started_at = None
        self.clip_started_at = None
        self.blockchain = Blockchain()


class LobbyManager:

    def __init__(self):
        self.lobbies = {}

    def join_lobby(self, lobby_id, player):
        if lobby_id not in self.lobbies:
            lobby = Lobby(lobby_id, player.name)
            self.lobbies[lobby_id] = lobby
        else:
            lobby = self.lobbies[lobby_id]

        existing_names = [p.name.lower() for p in lobby.players]
        if player.name.lower() in existing_names:
            raise ValueError("Igrač s tim imenom već postoji u lobbyju.")

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
            lobby.host = lobby.players[0].name

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